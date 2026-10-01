from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.logging import configure_logging
from app.config.settings import settings
from app.controller.router import router as controller_router
from app.nlp.embedding_model import EmbeddingModel
from app.nlp.gloss_analyzer import GlossAnalyzer
from app.nlp.llm_client import LLMClient
from app.nlp.nlp_service_impl import NLPServiceImpl
from app.nlp.semantic_cache import SemanticCache
from app.orchestrator.orchestrator import Orchestrator
from app.validation.catalog_repository import CatalogRepository
from app.validation.validator_service_impl import ValidatorServiceImpl

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    catalog_repository = CatalogRepository(settings.database_url)
    await catalog_repository.load_all()

    nlp_service = NLPServiceImpl(
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
            settings.llm_base_url,
        ),
    )
    validator_service = ValidatorServiceImpl(catalog_repository)

    app.state.orchestrator = Orchestrator(nlp_service, validator_service)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(controller_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
