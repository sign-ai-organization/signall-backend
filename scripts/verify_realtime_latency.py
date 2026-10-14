"""Medidor de latencia del tramo backend -> cliente.

Abre una sesion `/ws/translate`, manda una frase por `{"type":"text"}` y
cronometra cuanto tarda en llegar cada `segment` y el `done`. Es el termometro
del trabajo en tiempo real: sin el, cualquier cambio en el pipeline es
indistinguible de ruido.

    python scripts/verify_realtime_latency.py
    python scripts/verify_realtime_latency.py --url ws://127.0.0.1:8080/ws/translate -n 5

Por frase reporta:

    primer_segmento   espera desde que se mando la frase hasta el primer signo
                      listo para reproducir (es la latencia que percibe el usuario)
    primer_glosa     ms hasta la primera glosa, no el segmento entero
    total             hasta el `done`

`--replay-audio WAV` salta el microfono: reproduce un WAV PCM16 mono 16 kHz en
tiempo real (o a `--speed`x) y cronometra desde el primer sample enviado hasta
cada mensaje del backend. Asi se mide la cadena completa sin hablar.
"""

import argparse
import asyncio
import json
import statistics
import sys
import time
import wave
from pathlib import Path

import websockets

DEFAULT_URL = "ws://127.0.0.1:8080/ws/translate"

# Frases de la vida real del caso de uso "Registro Basico de Datos", ordenadas
# de la mas corta a la mas larga. Cortas primero a proposito: el caso de uso es
# un campo a campo, no un parrafo, y una frase de 4 palabras es la que tiene que
# ser instantanea.
PHRASES = [
    "hola",
    "buenos dias",
    "como estas",
    "me llamo ana",
    "vivo en bogota",
    "tengo treinta anos",
    "mucho gusto",
    "hasta mañana",
    "yo soy sordomudo",
    "bien",
]


def _ms(start: float) -> float:
    return (time.monotonic() - start) * 1000


class Timings:
    def __init__(self) -> None:
        self.sent_at: float | None = None
        self.first_gloss_ms: float | None = None
        self.first_segment_ms: float | None = None
        self.done_ms: float | None = None
        self.segments: list[dict] = []
        self.transcripts: list[tuple[str, bool]] = []
        self.first_partial_ms: float | None = None

    def summary(self) -> str:
        return (
            f"final={self.done_ms:.0f}ms "
            f"1er_glosa={self.first_gloss_ms if self.first_gloss_ms is not None else -1:.0f}ms "
            f"1er_signo={self.first_segment_ms if self.first_segment_ms is not None else -1:.0f}ms "
            f"segmentos={len(self.segments)}"
        )


async def _run_phrase(url: str, phrase: str, timeout: float, quiet: bool = False) -> Timings:
    timings = Timings()
    async with websockets.connect(url, max_size=None) as socket:

        async def receive() -> None:
            while True:
                raw = await socket.recv()
                now = time.monotonic()
                if isinstance(raw, bytes):
                    continue
                payload = json.loads(raw)
                kind = payload.get("type")

                if kind == "transcript":
                    if timings.sent_at is None:
                        continue
                    is_final = bool(payload.get("final"))
                    timings.transcripts.append((payload.get("text", ""), is_final))
                    if not is_final and timings.first_partial_ms is None:
                        timings.first_partial_ms = _ms(timings.sent_at)
                    if is_final:
                        continue

                elif kind == "segment":
                    if timings.sent_at is None:
                        continue
                    if timings.first_segment_ms is None:
                        timings.first_segment_ms = _ms(timings.sent_at)
                    if timings.first_gloss_ms is None:
                        timings.first_gloss_ms = _ms(timings.sent_at)
                    timings.segments.append(payload)

                elif kind == "done":
                    timings.done_ms = _ms(timings.sent_at or now)
                    return

                elif kind == "error":
                    print(f"  [error] {payload.get('message')}", file=sys.stderr)
                    timings.done_ms = _ms(timings.sent_at or now)
                    return

        receiver = asyncio.create_task(receive())
        await asyncio.sleep(0.2)  # que el STT termine de conectar antes de medir
        timings.sent_at = time.monotonic()
        await socket.send(json.dumps({"type": "text", "text": phrase}))

        try:
            await asyncio.wait_for(receiver, timeout)
        except asyncio.TimeoutError:
            receiver.cancel()
            print(f"  [timeout] {phrase!r} no produjo done en {timeout:.0f}s", file=sys.stderr)

    if not quiet and timings.segments:
        glosses = [
            gloss["text"]
            for segment in timings.segments
            for gloss in segment["segment"]["glosses"]
        ]
        print(f"    glosas: {' , '.join(glosses)}")

    return timings


def _read_wav_pcm16(path: str) -> bytes:
    with wave.open(path, "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getframerate() != 16000:
            raise SystemExit(
                f"{path}: se espera mono PCM16 a 16 kHz, "
                f"viene {wav.getnchannels()}ch {wav.getsampwidth() * 8}bit {wav.getframerate()}Hz"
            )
        return wav.readframes(wav.getnframes())


async def _replay_audio(url: str, path: str, speed: float, timeout: float, verbose: bool = True) -> Timings:
    """Reproduce un WAV por el WebSocket a velocidad real y cronometra.

    El reloj arranca en el primer sample enviado, que es lo que el microfono
    haria: de ahi en adelante cada mensaje del backend se puede comparar con la
    linea de tiempo del audio.
    """
    pcm = _read_wav_pcm16(path)
    frame_bytes = 960  # 30 ms a 16 kHz PCM16
    sleep_per_frame = (frame_bytes / 2 / 16000) / max(speed, 0.01)

    timings = Timings()
    events: list[tuple[float, str, str]] = []

    async with websockets.connect(url, max_size=None) as socket:

        async def receive() -> None:
            while True:
                raw = await socket.recv()
                if isinstance(raw, bytes):
                    continue
                payload = json.loads(raw)
                kind = payload.get("type")
                if kind == "segment":
                    glosses = ", ".join(g["text"] for g in payload["segment"]["glosses"])
                    events.append((timings.sent_at and _ms(timings.sent_at) or 0, "segment", glosses))
                    timings.segments.append(payload)
                    if timings.first_segment_ms is None:
                        timings.first_segment_ms = _ms(timings.sent_at or time.monotonic())
                    if timings.first_gloss_ms is None:
                        timings.first_gloss_ms = timings.first_segment_ms
                elif kind == "transcript":
                    final = bool(payload.get("final"))
                    events.append((_ms(timings.sent_at or time.monotonic()), "transcript", payload.get("text", "")))
                    if not final and timings.first_partial_ms is None:
                        timings.first_partial_ms = _ms(timings.sent_at)
                elif kind == "done":
                    timings.done_ms = _ms(timings.sent_at or time.monotonic())
                    return
                elif kind == "error":
                    events.append((_ms(timings.sent_at or time.monotonic()), "error", payload.get("message", "")))

        receiver = asyncio.create_task(receive())
        await asyncio.sleep(0.2)
        timings.sent_at = time.monotonic()

        for start in range(0, len(pcm), frame_bytes):
            await socket.send(pcm[start : start + frame_bytes])
            await asyncio.sleep(sleep_per_frame)

        # `{"type":"end"}`, no la cadena suelta "end". El backend clasifica los
        # frames de texto con json.loads y descarta en silencio lo que no parsea,
        # así que mandar "end" a secas cierra el socket de una y el utterance
        # muere sin final. El cliente Android manda el frame con `type`.
        await socket.send(json.dumps({"type": "end"}))
        try:
            await asyncio.wait_for(receiver, timeout)
        except asyncio.TimeoutError:
            receiver.cancel()
            print("  [timeout] el backend no produjo done", file=sys.stderr)

    if verbose:
        print("\n  linea de tiempo (ms desde el primer sample de audio):")
        for at, kind, detail in events:
            print(f"    {at:8.0f}  {kind:<10} {detail}")
        if timings.first_partial_ms is not None:
            print(f"    {timings.first_partial_ms:8.0f}  1er parcial")
    return timings


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((pct / 100) * (len(ordered) - 1))))
    return ordered[index]


async def _run_fixtures(url: str, fixtures_dir: Path, timeout: float, only: list[str] | None) -> int:
    """Reproduce todos los fixtures y arma la tabla que importa.

    Una corrida por fixture es suficiente para el perfil de latencia: cada uno ya
    lleva entre 0.5 y 5.7 s de audio, o sea cientos de muestras de VAD. Lo que
    se busca no es dispersión estadística sino "¿el número grande está donde
    espero?".
    """
    index_path = fixtures_dir / "index.json"
    if not index_path.exists():
        print(
            f"no está {index_path}. Generá los fixtures con\n"
            f"  ../sign-ai-stt/.venv-tts/bin/python ../sign-ai-stt/scripts/make_audio_fixtures.py --all",
            file=sys.stderr,
        )
        return 2

    clips = json.loads(index_path.read_text())["clips"]
    if only:
        clips = [clip for clip in clips if clip["id"] in only]

    rows: list[tuple[str, str, float, float, float, int]] = []
    for clip in clips:
        wav = fixtures_dir / f"{clip['id']}.wav"
        if not wav.exists():
            continue
        timings = await _replay_audio(url, str(wav), 1.0, timeout, verbose=False)
        first = timings.first_segment_ms
        rows.append(
            (
                clip["id"],
                clip["text"],
                first if first is not None else -1.0,
                timings.first_partial_ms if timings.first_partial_ms is not None else -1.0,
                timings.done_ms if timings.done_ms is not None else -1.0,
                len(timings.segments),
            )
        )

    print(f"\n{'fixture':<22} {'1er signo':>10} {'1er texto':>10} {'completo':>10} {'signos':>7}  frase")
    print("-" * 100)
    for name, text, first, partial, total, count in rows:
        print(
            f"{name:<22} {first:9.0f}ms {partial:9.0f}ms {total:9.0f}ms {count:7d}  {text[:34]}"
        )

    firsts = [row[2] for row in rows if row[2] >= 0]
    if firsts:
        print(
            f"\nPRIMERA SEÑA  p50={statistics.median(firsts):.0f}ms  "
            f"p95={_percentile(firsts, 95):.0f}ms  max={max(firsts):.0f}ms  "
            f"(n={len(firsts)}/{len(rows)} fixtures con al menos una seña)"
        )
    return 0


async def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--phrase", action="append", help="frase a medir (repetible)")
    parser.add_argument("-n", "--runs", type=int, default=1, help="repeticiones por frase")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--replay-audio", help="WAV mono PCM16 16 kHz para reproducir por el socket")
    parser.add_argument("--all-fixtures", action="store_true", help="reproducir todo el set de fixtures de audio")
    parser.add_argument(
        "--fixtures-dir",
        default="../sign-ai-stt/fixtures/audio",
        help="directorio con los WAV y su index.json",
    )
    parser.add_argument("--only", action="append", help="id de fixture a medir con --all-fixtures")
    parser.add_argument("--speed", type=float, default=1.0, help="multiplicador de velocidad del replay")
    args = parser.parse_args()

    if args.replay_audio:
        await _replay_audio(args.url, args.replay_audio, args.speed, args.timeout)
        return 0

    if args.all_fixtures:
        return await _run_fixtures(args.url, Path(args.fixtures_dir), args.timeout, args.only)

    phrases = args.phrase or PHRASES
    rows: dict[str, list[Timings]] = {}

    for phrase in phrases:
        rows[phrase] = []
        for run in range(args.runs):
            timings = await _run_phrase(args.url, phrase, args.timeout)
            rows[phrase].append(timings)
            print(f"  {phrase!r} run {run + 1}: {timings.summary()}")

    print(f"\n{'frase':<24} {'1er signo (p50/p95)':<22} {'total (p50/p95)':<20}")
    print("-" * 68)
    all_first: list[float] = []
    all_total: list[float] = []
    for phrase, runs in rows.items():
        first = [r.first_segment_ms for r in runs if r.first_segment_ms is not None]
        total = [r.done_ms for r in runs if r.done_ms is not None]
        all_first += first
        all_total += total
        first_txt = f"{_percentile(first, 50):.0f} / {_percentile(first, 95):.0f} ms" if first else "n/d"
        total_txt = f"{_percentile(total, 50):.0f} / {_percentile(total, 95):.0f} ms" if total else "n/d"
        print(f"{phrase:<24} {first_txt:<22} {total_txt:<20}")

    if all_first:
        print(
            f"\nGLOBAL  1er signo p50={statistics.median(all_first):.0f}ms "
            f"p95={_percentile(all_first, 95):.0f}ms   "
            f"total p50={statistics.median(all_total):.0f}ms "
            f"p95={_percentile(all_total, 95):.0f}ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))