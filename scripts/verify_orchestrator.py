import asyncio

from app.config.settings import settings
from app.domain.models import PhraseType
from app.nlp.embedding_model import EmbeddingModel
from app.nlp.gloss_analyzer import GlossAnalyzer
from app.nlp.llm_client import LLMClient
from app.nlp.nlp_service_impl import NLPServiceImpl
from app.nlp.semantic_cache import SemanticCache
from app.orchestrator.orchestrator import Orchestrator
from app.validation.catalog_repository import CatalogRepository
from app.validation.validator_service_impl import ValidatorServiceImpl

TEST_SENTENCES = [
    "Necesito comer algo antes de firmar.",
    "¿Cuál es su nombre?",
]


async def main() -> None:
    catalog_repository = CatalogRepository(settings.database_url)
    await catalog_repository.load_all()
    print(f"catalog entries loaded: {list(catalog_repository.cache.keys())}")

    orchestrator = Orchestrator(
        NLPServiceImpl(
            GlossAnalyzer(),
            SemanticCache(
                settings.database_url,
                EmbeddingModel(),
                settings.semantic_cache_similarity_threshold,
            ),
            LLMClient(
                settings.llm_api_key,
                settings.llm_model,
                settings.llm_temperature,
                settings.llm_timeout_ms,
            ),
        ),
        ValidatorServiceImpl(catalog_repository),
    )

    for sentence in TEST_SENTENCES:
        print(f"\n{sentence!r}")
        validated_segments = await orchestrator.translate(sentence)
        for segment in validated_segments:
            print(f"  type={segment.type.value}")
            for gloss in segment.glosses:
                print(f"    {gloss.model_dump()}")


if __name__ == "__main__":
    asyncio.run(main())
