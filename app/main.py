import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from app.config.logging import configure_logging
from app.config.settings import settings
from app.controller.router import router as controller_router
from app.metrics import metrics
from app.nlp.embedding_model import EmbeddingModel
from app.nlp.gloss_analyzer import GlossAnalyzer
from app.nlp.llm_client import LLMClient
from app.nlp.nlp_service_impl import NLPServiceImpl
from app.nlp.segmenter import SentenceSegmenter
from app.nlp.semantic_cache import SemanticCache
from app.orchestrator.orchestrator import Orchestrator
from app.persistence.database import create_pool
from app.persistence.keep_alive import DatabaseKeepAlive
from app.validation.catalog_repository import CatalogRepository
from app.validation.validator_service_impl import ValidatorServiceImpl

configure_logging(settings.log_level)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await create_pool(
        settings.database_url,
        settings.db_pool_min_size,
        settings.db_pool_max_size,
        settings.db_pool_max_inactive_connection_lifetime_seconds,
    )
    db_keep_alive = DatabaseKeepAlive(
        pool,
        settings.db_keepalive_interval_seconds,
        settings.db_keepalive_idle_window_seconds,
    )
    db_keep_alive.start()

    catalog_repository = CatalogRepository(pool)
    await catalog_repository.load_all()

    semantic_cache = SemanticCache(
        pool,
        EmbeddingModel(),
        settings.semantic_cache_similarity_threshold,
        preload=settings.semantic_cache_preload,
        max_rows=settings.semantic_cache_max_rows,
    )
    await semantic_cache.load_all()

    llm_client = LLMClient(
        settings.llm_api_key,
        settings.llm_model,
        settings.llm_temperature,
        settings.llm_timeout_ms,
        settings.llm_base_url,
        # The catalog's glosses go into the prompt as a closed vocabulary, so
        # the model cannot answer with a sign that has no animation. See the
        # long comment at the top of app/nlp/llm_client.py for why the old
        # "one gloss = one word" prompt broke this.
        catalog_repository.vocabulary(),
    )

    nlp_service = NLPServiceImpl(
        GlossAnalyzer(),
        semantic_cache,
        llm_client,
        SentenceSegmenter(settings.sentence_segmenter) if settings.sentence_segmenter.enabled else None,
    )
    validator_service = ValidatorServiceImpl(catalog_repository)

    app.state.orchestrator = Orchestrator(nlp_service, validator_service)
    app.state.db_keep_alive = db_keep_alive
    app.state.semantic_cache = semantic_cache
    metrics.gauge("cache_rows", semantic_cache.row_count)
    metrics.gauge("cache_loaded", 1 if semantic_cache.is_loaded else 0)
    metrics.gauge("catalog_glosses", len(catalog_repository.cache))

    # Warm-up runs apart from start-up: it is several seconds and no session
    # should have to wait for them. By the time the first connection arrives it
    # is already done.
    warmup_task = asyncio.create_task(_warm_up_llm(llm_client)) if settings.llm_warmup_enabled else None

    yield

    if warmup_task is not None:
        warmup_task.cancel()
    await nlp_service.wait_for_pending_stores()
    await db_keep_alive.stop()
    await pool.close()


async def _warm_up_llm(llm_client: LLMClient) -> None:
    started = time.monotonic()
    await llm_client.warm_up()
    elapsed_ms = (time.monotonic() - started) * 1000
    logger.info("LLM warm-up took %.0f ms", elapsed_ms)
    metrics.histogram("llm_warmup_ms", elapsed_ms, "Carga del modelo de lenguaje al arrancar")


app = FastAPI(lifespan=lifespan)
app.include_router(controller_router)


@app.get("/health")
def health() -> dict[str, object]:
    cache = getattr(app.state, "semantic_cache", None)
    return {
        "status": "ok",
        "cache_loaded": bool(cache and cache.is_loaded),
        "cache_rows": cache.row_count if cache else 0,
    }


@app.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics() -> str:
    """Metrics in Prometheus exposition format.

    What to look at first to answer "does this feel live?":

        rt_first_sign_ms_p95    phrase received -> first sentence sent
        rt_phrase_total_ms_p95  phrase received -> last sentence sent
        rt_sentence_delay_ms_p95 each sentence on its own
    """
    return metrics.render()


@app.get("/metrics.json")
def metrics_json() -> dict[str, object]:
    cache = getattr(app.state, "semantic_cache", None)
    return {
        **metrics.snapshot(),
        "config": {
            "llm_model": settings.llm_model,
            "llm_base_url": settings.llm_base_url,
            "semantic_cache_preload": settings.semantic_cache_preload,
            "semantic_cache_threshold": settings.semantic_cache_similarity_threshold,
            "sentence_segmenter_enabled": settings.sentence_segmenter.enabled,
            "stt_ws_url": settings.stt_ws_url,
        },
        "cache": {
            "loaded": bool(cache and cache.is_loaded),
            "rows": cache.row_count if cache else 0,
        },
    }