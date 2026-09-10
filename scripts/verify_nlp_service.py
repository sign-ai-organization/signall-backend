import asyncio
import time

from app.config.settings import settings
from app.nlp.embedding_model import EmbeddingModel
from app.nlp.gloss_analyzer import GlossAnalyzer
from app.nlp.llm_client import LLMClient
from app.nlp.nlp_service_impl import NLPServiceImpl
from app.nlp.semantic_cache import SemanticCache

TEST_SENTENCES = [
    "Su cita quedó confirmada para las tres de la tarde.",
    "¿Cuál es su número de documento?",
    "No traiga copias adicionales.",
]


async def main() -> None:
    service = NLPServiceImpl(
        GlossAnalyzer(),
        SemanticCache(
            settings.database_url, EmbeddingModel(), settings.semantic_cache_similarity_threshold
        ),
        LLMClient(
            settings.llm_api_key, settings.llm_model, settings.llm_temperature, settings.llm_timeout_ms
        ),
    )

    for sentence in TEST_SENTENCES:
        print(f"\n{sentence!r}")

        start = time.perf_counter()
        first = await service.transform(sentence)
        elapsed = time.perf_counter() - start
        print(f"  1st call (expected MISS -> LLM): {first} ({elapsed:.2f}s)")

        start = time.perf_counter()
        second = await service.transform(sentence)
        elapsed = time.perf_counter() - start
        print(f"  2nd call (expected HIT -> cache): {second} ({elapsed:.2f}s)")

        assert first == second, "same text should produce the same Segment both times"


if __name__ == "__main__":
    asyncio.run(main())
