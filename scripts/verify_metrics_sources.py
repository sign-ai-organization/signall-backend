"""Where the latency metrics say the answer came from.

The SRS asks for two latency ranges (RNF-DES-01 and RNF-DES-03): one for a
phrase the semantic cache resolved, and one for a phrase that needed the
language model. Until now `/metrics` could not tell them apart — the hit and
the miss only existed as a line in the log — so the published number was the
average of two scenarios that are not comparable, and the difference between
them had to be reconstructed by reading logs.

This script checks, without a database and without a model:

1. `rt_cache_total` counts the three origins apart: exact, semantic, miss.
2. `rt_first_sign_ms` and `rt_phrase_total_ms` carry the source of the answer,
   and a phrase counts as `llm` as soon as one of its sentences needed the
   model.
3. `rt_phrase_sentences` is a histogram, as the SDD has always said.
4. `rt_turn_queue_ms` measures the wait between the phrase arriving at the
   socket and its translation starting.

Run it with: `python -m scripts.verify_metrics_sources`
"""

import asyncio
import hashlib
import time

from app.controller.controller import Controller
from app.controller.router import _PhraseTranslator
from app.domain.models import PhraseType
from app.metrics import metrics
from app.nlp.gloss_analyzer import GlossAnalyzer
from app.nlp.models import Fingerprint
from app.nlp.nlp_service_impl import NLPServiceImpl
from app.nlp.semantic_cache import SemanticCache
from app.orchestrator.orchestrator import Orchestrator
from app.validation.catalog_repository import CatalogRepository
from app.validation.validator_service_impl import ValidatorServiceImpl

AFFIRMATIVE = PhraseType.AFFIRMATIVE.value


class _StubEmbeddings:
    """A deterministic embedding: the vector depends on the first word.

    No model and no network, and still the two cases that matter: two texts
    that start with the same word land on the same vector, which is a semantic
    hit, and a different first word lands on another, which is a miss.
    """

    DIMENSIONS = 32

    def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.split()[0].lower().encode("utf-8")).digest()
        return [(digest[index] - 128) / 128.0 for index in range(self.DIMENSIONS)]


class _FakePool:
    """A pool that answers the two start-up queries and nothing else."""

    def __init__(self, cache_rows: list[dict], catalog_rows: list[dict]) -> None:
        self._cache_rows = cache_rows
        self._catalog_rows = catalog_rows

    async def fetch(self, query: str, *args: object) -> list[dict]:
        if "semantic_cache" in query:
            return self._cache_rows
        return self._catalog_rows

    async def acquire(self) -> "_FakePool":
        return self

    async def release(self, connection: object) -> None:
        return None

    async def execute(self, query: str, *args: object) -> str:
        return "OK"


class _StubLLM:
    """A model that always answers the same, without calling anyone."""

    def __init__(self) -> None:
        self.calls = 0

    async def transform(self, text: str) -> list[str]:
        self.calls += 1
        return ["HOLA"]


class _StubWebSocket:
    def __init__(self) -> None:
        self.frames: list[dict] = []

    async def send_json(self, frame: dict) -> None:
        self.frames.append(frame)


class _StubController:
    """Only what `_PhraseTranslator` calls."""

    def __init__(self) -> None:
        self.phrases: list[str] = []
        self.started = asyncio.Event()

    async def handle_text(self, text: str, turn: object = None) -> None:
        self.phrases.append(text)
        self.started.set()


def _vector_text(vector: list[float]) -> str:
    return "[" + ",".join(str(value) for value in vector) + "]"


async def main() -> None:
    embeddings = _StubEmbeddings()
    pool = _FakePool(
        cache_rows=[
            {
                "original_text": "Hola",
                "phrase_type": AFFIRMATIVE,
                "glosses": ["HOLA"],
                "embedding": _vector_text(embeddings.embed("hola")),
            }
        ],
        catalog_rows=[
            {
                "gloss": "HOLA",
                "semantic_category": "SALUDO",
                "glb_animation_path": "glb/0001.glb",
            }
        ],
    )

    cache = SemanticCache(pool, embeddings, similarity_threshold=0.05)
    await cache.load_all()

    fingerprint = Fingerprint(
        category=PhraseType.AFFIRMATIVE,
        secondary_signals=[],
        has_collision=False,
    )

    # 1. The three origins of a cache answer, counted apart.
    print("1. origen de la respuesta de la caché")
    assert await cache.lookup("hola", fingerprint) == ["HOLA"], "expected an exact hit"
    assert await cache.lookup("hola amigo", fingerprint) == ["HOLA"], "expected a semantic hit"
    assert await cache.lookup("adios", fingerprint) is None, "expected a miss"

    counters = metrics.snapshot()["counters"]
    assert counters.get('rt_cache_total{source="exact"}') == 1, counters
    assert counters.get('rt_cache_total{source="semantic"}') == 1, counters
    assert counters.get('rt_cache_total{source="miss"}') == 1, counters
    print(f"   exact={counters['rt_cache_total{source=\"exact\"}']} "
          f"semantic={counters['rt_cache_total{source=\"semantic\"}']} "
          f"miss={counters['rt_cache_total{source=\"miss\"}']}")

    # 2. The latency histograms carry the source of the answer.
    print("2. la latencia con su origen")
    llm = _StubLLM()
    nlp_service = NLPServiceImpl(GlossAnalyzer(), cache, llm, segmenter=None)
    orchestrator = Orchestrator(nlp_service, ValidatorServiceImpl(CatalogRepository(pool)))
    websocket = _StubWebSocket()
    controller = Controller(websocket, orchestrator, stt_client=None)

    await controller.handle_text("hola")
    await controller.handle_text("adios")
    await nlp_service.wait_for_pending_stores()

    histograms = metrics.snapshot()["histograms"]
    assert histograms['rt_first_sign_ms{source="cache"}']["count"] == 1, histograms
    assert histograms['rt_first_sign_ms{source="llm"}']["count"] == 1, histograms
    assert histograms['rt_sentence_delay_ms{source="cache"}']["count"] == 1, histograms
    assert histograms['rt_sentence_delay_ms{source="llm"}']["count"] == 1, histograms
    assert histograms['rt_phrase_total_ms{source="cache"}']["count"] == 1, histograms
    assert histograms['rt_phrase_total_ms{source="llm"}']["count"] == 1, histograms
    assert llm.calls == 1, f"the model should have been asked once, not {llm.calls} times"
    print(f"   cache: p50={histograms['rt_first_sign_ms{source=\"cache\"}']['p50']} ms, "
          f"llm: p50={histograms['rt_first_sign_ms{source=\"llm\"}']['p50']} ms")

    # 3. The sentences per phrase are a histogram, as the SDD says.
    print("3. oraciones por frase")
    assert histograms["rt_phrase_sentences"]["count"] == 2, histograms
    assert "rt_phrase_sentences" not in metrics.snapshot()["gauges"]
    print(f"   rt_phrase_sentences: count={histograms['rt_phrase_sentences']['count']} "
          f"avg={histograms['rt_phrase_sentences']['avg']}")

    # 4. The wait between the phrase arriving and its translation starting.
    print("4. espera de la frase en la cola")
    stub_controller = _StubController()
    translator = _PhraseTranslator(stub_controller)
    translator.submit("hola", None, time.perf_counter())
    await asyncio.wait_for(stub_controller.started.wait(), timeout=5)

    histograms = metrics.snapshot()["histograms"]
    assert histograms["rt_turn_queue_ms"]["count"] == 1, histograms
    assert histograms["rt_turn_queue_ms"]["max"] >= 0
    print(f"   rt_turn_queue_ms: p50={histograms['rt_turn_queue_ms']['p50']} ms")

    print("\nOK: las métricas dicen de dónde salió cada respuesta.")


if __name__ == "__main__":
    asyncio.run(main())
