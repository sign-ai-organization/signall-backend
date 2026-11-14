"""Métricas del backend, sin dependencias.

Mismo formato de exposición de Prometheus que el del STT (`signall-stt/app/metrics.py`),
implementado aparte porque los repos no comparten código y duplicar 150 líneas
es preferible a inventar un paquete común para dos consumidores.

Qué se mide y por qué
---------------------

La unidad de traducción es la **oración**, y la frase llega por el frame `text`
del cliente. Un backend de traducción tiene tres relojes distintos que se
confunden si se miden como uno solo:

- `rt_first_sign_ms`: frase recibida → primera oración traducida y enviada.
  **Es la latencia que percibe el usuario** y la única que importa para decidir
  si el producto se siente en tiempo real. El punto de partida es el envío del
  cliente, que es lo que RNF-DES-01 llama la confirmación del usuario.
- `rt_phrase_total_ms`: frase recibida → última oración enviada. Cuánto tarda
  la respuesta completa.
- `rt_sentence_delay_ms`: cada oración por separado, para ver si salen
  espaciadas o de golpe al final.

Los nombres antiguos `rt_utterance_*` y `rt_chunk_*` describían el camino por
palabras que ya no existe (traducir fragmentos mientras la persona todavía
habla) y se renombraron al volver al flujo por oraciones: lo que miden es la
misma cosa, pero el nombre tiene que decir qué cosa.

Los histogramas guardan hasta 512 muestras cada uno para el p95, y ese tope es
deliberado: el servicio produce miles de oraciones por hora y retenerlas todas
sería una fuga de memoria disfrazada de instrumentación.
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

_MAX_SAMPLES = 512

_HISTOGRAM_SUFFIXES = (
    ("_sum", "sum"),
    ("_count", "count"),
    ("_min", "min"),
    ("_max", "max"),
    ("_p50", "p50"),
    ("_p95", "p95"),
    ("_p99", "p99"),
)


@dataclass
class Histogram:
    name: str
    buckets: tuple[float, ...]
    count: int = 0
    total: float = 0.0
    minimum: float | None = None
    maximum: float | None = None
    samples: list[float] = field(default_factory=list)
    _cursor: int = 0

    def observe(self, value: float) -> None:
        self.count += 1
        self.total += value
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)

        if len(self.samples) < _MAX_SAMPLES:
            self.samples.append(value)
        else:
            self.samples[self._cursor] = value
            self._cursor = (self._cursor + 1) % _MAX_SAMPLES

    def percentile(self, pct: float) -> float:
        if not self.samples:
            return 0.0
        ordered = sorted(self.samples)
        index = min(len(ordered) - 1, max(0, round((pct / 100) * (len(ordered) - 1))))
        return ordered[index]

    def snapshot(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "sum": round(self.total, 3),
            "min": round(self.minimum, 3) if self.minimum is not None else 0.0,
            "max": round(self.maximum, 3) if self.maximum is not None else 0.0,
            "avg": round(self.total / self.count, 3) if self.count else 0.0,
            "p50": round(self.percentile(50), 3),
            "p95": round(self.percentile(95), 3),
            "p99": round(self.percentile(99), 3),
        }


class MetricsRegistry:
    """Contadores, gauges e histogramas seguros desde varias tareas asyncio.

    Se usa `threading.Lock` y no nada de asyncio porque el bucle de eventos corre
    `SentenceTransformer.encode` en `asyncio.to_thread` (`SemanticCache`), o sea
    que hay hilos reales entrando al mismo registro. Además las operaciones son
    varias y no atómicas, así que el GIL no alcanza como garantía.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._histograms: dict[tuple[str, tuple[tuple[str, str], ...]], Histogram] = {}
        self._help: dict[str, str] = {}
        self._started_at = time.time()

    @staticmethod
    def _key(name: str, labels: dict[str, str] | None) -> tuple[str, tuple[tuple[str, str], ...]]:
        return name, tuple(sorted((labels or {}).items()))

    def counter(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            self._counters[self._key(name, labels)] += value

    def gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            self._gauges[self._key(name, labels)] = value

    def histogram(self, name: str, value: float, help_text: str = "", labels: dict[str, str] | None = None) -> None:
        key = self._key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = Histogram(
                    name=name,
                    buckets=(1, 5, 10, 25, 50, 100, 200, 300, 500, 800, 1200, 2000, 4000, 8000),
                )
                if help_text:
                    self._help[name] = help_text
            self._histograms[key].observe(value)

    def counter_value(self, name: str, labels: dict[str, str] | None = None) -> float:
        with self._lock:
            return self._counters.get(self._key(name, labels), 0.0)

    def gauge_value(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Current value of a gauge.

        Counters and gauges live in separate maps, so reading one with
        `counter_value` always answers 0. That made every gauge that did
        `gauge(name, counter_value(name) + 1)` —`sessions_active`— report 1 no
        matter how many sessions were open: it never saw its own previous value.
        """
        with self._lock:
            return self._gauges.get(self._key(name, labels), 0.0)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "uptime_s": round(time.time() - self._started_at, 1),
                "counters": {_render_name(k[0], k[1]): v for k, v in sorted(self._counters.items())},
                "gauges": {_render_name(k[0], k[1]): v for k, v in sorted(self._gauges.items())},
                "histograms": {_render_name(k[0], k[1]): h.snapshot() for k, h in sorted(self._histograms.items())},
            }

    def render(self) -> str:
        with self._lock:
            counters = dict(self._counters)
            gauges = dict(self._gauges)
            histograms = dict(self._histograms)

        lines: list[str] = []
        declared: set[str] = set()

        def declare(name: str, metric_type: str) -> None:
            if name not in declared:
                lines.append(f"# HELP {name} {self._help.get(name, name)}")
                lines.append(f"# TYPE {name} {metric_type}")
                declared.add(name)

        for (name, labels), value in sorted(counters.items()):
            declare(name, "counter")
            lines.append(f"{_render_name(name, labels)} {_num(value)}")

        for (name, labels), value in sorted(gauges.items()):
            declare(name, "gauge")
            lines.append(f"{_render_name(name, labels)} {_num(value)}")

        for (name, labels), histogram in sorted(histograms.items()):
            declare(name, "histogram")
            for edge in histogram.buckets:
                cumulative = sum(1 for sample in histogram.samples if sample <= edge)
                bucket_labels = dict(labels) | {"le": str(edge)}
                lines.append(f"{_render_name(name + '_bucket', tuple(sorted(bucket_labels.items())))} {cumulative}")
            inf_labels = dict(labels) | {"le": "+Inf"}
            lines.append(f"{_render_name(name + '_bucket', tuple(sorted(inf_labels.items())))} {histogram.count}")

            snapshot = histogram.snapshot()
            for suffix, key in _HISTOGRAM_SUFFIXES:
                lines.append(f"{_render_name(name + suffix, labels)} {_num(snapshot[key])}")

        return "\n".join(lines) + "\n"


def _render_name(name: str, labels: tuple[tuple[str, str], ...]) -> str:
    parts = [f'{key}="{value}"' for key, value in labels]
    return f"{name}{{{','.join(parts)}}}" if parts else name


def _num(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return repr(round(value, 3))


metrics = MetricsRegistry()


class Timer:
    """Cronometra un bloque y lo publica como histograma.

        with metrics_timer("rt_update_ms", "...") as timer:
            ...
        logger.info("tardó %.0f ms", timer.elapsed_ms)
    """

    def __init__(self, name: str, help_text: str, labels: dict[str, str] | None = None) -> None:
        self.name = name
        self.help = help_text
        self.labels = labels
        self.elapsed_ms = 0.0

    def __enter__(self) -> "Timer":
        self._started = time.perf_counter()
        return self

    def __exit__(self, *exc: object) -> None:
        self.elapsed_ms = (time.perf_counter() - self._started) * 1000
        metrics.histogram(self.name, self.elapsed_ms, self.help, self.labels)


def metrics_timer(name: str, help_text: str, labels: dict[str, str] | None = None) -> Timer:
    return Timer(name, help_text, labels)
