import asyncio

from app.config.settings import settings
from app.domain.models import PhraseType
from app.nlp.embedding_model import EmbeddingModel
from app.nlp.gloss_analyzer import GlossAnalyzer
from app.nlp.llm_client import LLMClient
from app.nlp.nlp_service_impl import NLPServiceImpl
from app.nlp.segmenter import SentenceSegmenter
from app.nlp.semantic_cache import SemanticCache
from app.orchestrator.orchestrator import Orchestrator
from app.persistence.database import create_pool
from app.validation.catalog_repository import CatalogRepository
from app.validation.validator_service_impl import ValidatorServiceImpl

TEST_SENTENCES = [
    "Necesito comer algo antes de firmar.",
    "¿Cuál es su nombre?",
    "buenas tardes me llamo andrea martínez tengo veinticinco años y dónde vive usted",
]


async def main() -> None:
    pool = await create_pool(settings.database_url, settings.db_pool_min_size, settings.db_pool_max_size)
    catalog_repository = CatalogRepository(pool)
    await catalog_repository.load_all()
    print(f"catalog entries loaded: {list(catalog_repository.cache.keys())}")

    nlp_service = NLPServiceImpl(
        GlossAnalyzer(),
        SemanticCache(
            pool,
            EmbeddingModel(),
            settings.semantic_cache_similarity_threshold,
        ),
        LLMClient(
            settings.llm_api_key,
            settings.llm_model,
            settings.llm_temperature,
            settings.llm_timeout_ms,
        ),
        SentenceSegmenter(settings.sentence_segmenter) if settings.sentence_segmenter.enabled else None,
    )
    orchestrator = Orchestrator(nlp_service, ValidatorServiceImpl(catalog_repository))

    for sentence in TEST_SENTENCES:
        print(f"\n{sentence!r}")
        validated_segments = await orchestrator.translate(sentence)
        for segment in validated_segments:
            print(f"  type={segment.type.value}")
            for gloss in segment.glosses:
                print(f"    {gloss.model_dump()}")

    await nlp_service.wait_for_pending_stores()
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
