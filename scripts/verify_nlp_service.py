import asyncio
import time

from app.config.settings import settings
from app.nlp.embedding_model import EmbeddingModel
from app.nlp.gloss_analyzer import GlossAnalyzer
from app.nlp.llm_client import LLMClient
from app.nlp.nlp_service_impl import NLPServiceImpl
from app.nlp.semantic_cache import SemanticCache
from app.persistence.database import create_pool

TEST_SENTENCES = [
    "Su cita quedó confirmada para las tres de la tarde.",
    "¿Cuál es su número de documento?",
    "No traiga copias adicionales.",
]


async def main() -> None:
    pool = await create_pool(settings.database_url, settings.db_pool_min_size, settings.db_pool_max_size)
    service = NLPServiceImpl(
        GlossAnalyzer(),
        SemanticCache(pool, EmbeddingModel(), settings.semantic_cache_similarity_threshold),
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

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
