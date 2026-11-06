import asyncio
import json
import logging
import time
import urllib.request
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

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
from app.persistence.database import RetryPolicy, open_pool
from app.persistence.keep_alive import DatabaseKeepAlive
from app.validation.catalog_repository import CatalogRepository
from app.validation.validator_service_impl import ValidatorServiceImpl

configure_logging(settings.log_level)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    retry_policy = RetryPolicy(settings.db_max_retries, settings.db_retry_delay_seconds)
    pool = await open_pool(
        settings.database_url,
        settings.db_pool_min_size,
        settings.db_pool_max_size,
        settings.db_pool_max_inactive_connection_lifetime_seconds,
        command_timeout_seconds=settings.db_command_timeout_seconds,
        connect_timeout_seconds=settings.db_connect_timeout_seconds,
        policy=retry_policy,
    )
    db_keep_alive = DatabaseKeepAlive(
        pool,
        settings.db_keepalive_interval_seconds,
        settings.db_keepalive_idle_window_seconds,
    )
    db_keep_alive.start()

    catalog_repository = CatalogRepository(pool, retry_policy)
    try:
        await catalog_repository.load_all()
    except Exception:
        # A database that is down at this exact moment must not take the service
        # down with it: the container would stay dead and the Android client,
        # which reconnects on its own, would never reach it again. Without the
        # catalog every sign comes out as unavailable, but the service answers.
        logger.exception("Could not load the catalog; starting without it")

    semantic_cache = SemanticCache(
        pool,
        EmbeddingModel(settings.embedding_model_name),
        settings.semantic_cache_similarity_threshold,
        preload=settings.semantic_cache_preload,
        max_rows=settings.semantic_cache_max_rows,
        retry_policy=retry_policy,
        acquire_timeout_seconds=settings.db_acquire_timeout_seconds,
    )
    await semantic_cache.load_all()

    llm_client = LLMClient(
        settings.llm_api_key,
        settings.llm_model,
        settings.llm_temperature,
        settings.llm_timeout_ms,
        settings.llm_max_retries,
        settings.llm_base_url,
        # The catalog's glosses, for the post-hoc repair: an answer can never
        # reference a sign the app is unable to play. See the long comment at
        # the top of app/nlp/llm_client.py for why the old "one gloss = one
        # word" prompt broke this.
        #
        # They do NOT go into the prompt: decision D-7 (owner, 2026-10-16)
        # took the list out of it, because it does not scale and the validator
        # already marks a sign that is not in the catalog as unavailable. See
        # docs/performance.md section 9.
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
    # `/health` has to be able to say that the catalog is empty, because an
    # empty catalog is not a healthy translation service: every gloss comes out
    # as unavailable and the app shows "Seña no disponible" for everything.
    app.state.catalog_repository = catalog_repository
    metrics.gauge("cache_rows", semantic_cache.row_count)
    metrics.gauge("cache_loaded", 1 if semantic_cache.is_loaded else 0)
    metrics.gauge("catalog_glosses", len(catalog_repository.cache))

    # Warm-up runs apart from start-up: it is several seconds and no session
    # should have to wait for them. By the time the first connection arrives it
    # is already done.
    warmup_task = asyncio.create_task(_warm_up_llm(llm_client)) if settings.llm_warmup_enabled else None

    # The STT's own configuration, mirrored so the Android app can read it.
    app.state.stt_config = {}
    stt_config_task = (
        asyncio.create_task(_watch_stt_config(app)) if settings.stt_config_poll_seconds > 0 else None
    )

    yield

    if warmup_task is not None:
        warmup_task.cancel()
    if stt_config_task is not None:
        stt_config_task.cancel()
    await nlp_service.wait_for_pending_stores()
    await db_keep_alive.stop()
    if pool is not None:
        await pool.close()


async def _warm_up_llm(llm_client: LLMClient) -> None:
    started = time.monotonic()
    await llm_client.warm_up()
    elapsed_ms = (time.monotonic() - started) * 1000
    logger.info("LLM warm-up took %.0f ms", elapsed_ms)
    metrics.histogram("llm_warmup_ms", elapsed_ms, "Carga del modelo de lenguaje al arrancar")


def _http_origin(ws_url: str) -> str:
    """`ws://host:port/path` → `http://host:port`."""
    scheme = "https" if ws_url.startswith("wss://") else "http"
    return f"{scheme}://{ws_url.split('://', 1)[1].split('/', 1)[0]}"


def _read_stt_silence_timeout_ms(http_origin: str) -> int | None:
    """`SILENCE_TIMEOUT_MS` from the STT's /health, or None when it can't be read.

    Standard library only: this polls a local JSON endpoint and a new
    dependency for one number would not earn its place. Runs in a thread
    because it blocks.
    """
    try:
        with urllib.request.urlopen(f"{http_origin}/health", timeout=3) as response:
            value = json.loads(response.read()).get("silence_timeout_ms")
        return int(value) if value is not None else None
    except Exception:  # noqa: BLE001 - an unreachable STT is not this service's problem
        logger.debug("Could not read the STT /health", exc_info=True)
        return None


async def _watch_stt_config(app: FastAPI) -> None:
    """Keep the STT's runtime configuration readable from our own /health.

    `SILENCE_TIMEOUT_MS` decides when a phrase closes: it is the second biggest
    block of end-to-end latency, and it lives in the STT's environment, where
    nothing here can see it. The Android app needs it for its debug overlay —
    a test run should not depend on somebody remembering to write it down — and
    the app never talks to the STT, so the value has to come through here.

    It is re-read on an interval rather than once at start-up because the STT
    takes its configuration from the environment: a run has to show the value in
    force, not the one that happened to be in force when this service started.
    """
    http_origin = _http_origin(settings.stt_ws_url)
    while True:
        silence_timeout_ms = await asyncio.to_thread(_read_stt_silence_timeout_ms, http_origin)
        if silence_timeout_ms is not None:
            changed = app.state.stt_config.get("silence_timeout_ms") != silence_timeout_ms
            app.state.stt_config["silence_timeout_ms"] = silence_timeout_ms
            metrics.gauge("stt_silence_timeout_ms", silence_timeout_ms)
            if changed:
                logger.info("STT SILENCE_TIMEOUT_MS is %d ms", silence_timeout_ms)
        await asyncio.sleep(settings.stt_config_poll_seconds)


app = FastAPI(lifespan=lifespan)
app.include_router(controller_router)


@app.get("/health")
def health() -> dict[str, object]:
    cache = getattr(app.state, "semantic_cache", None)
    catalog = getattr(app.state, "catalog_repository", None)
    catalog_glosses = len(catalog.cache) if catalog else 0
    # A backend that started without its catalog is answering, but it cannot
    # translate: every sign comes out as unavailable. Saying "ok" in that state
    # hides a failure the operator can still fix by restarting the service.
    catalog_loaded = catalog_glosses > 0
    return {
        "status": "ok" if catalog_loaded else "degraded",
        "cache_loaded": bool(cache and cache.is_loaded),
        "cache_rows": cache.row_count if cache else 0,
        "catalog_loaded": catalog_loaded,
        "catalog_glosses": catalog_glosses,
        # Mirrored from the STT so the Android debug overlay can show it: the app
        # does not talk to the STT (see `_watch_stt_config`).
        **getattr(app.state, "stt_config", {}),
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


def _redact_url(url: str) -> str:
    """Keep the scheme and the path, hide the host and the port.

    `/metrics.json` has no authentication and is read from a phone during a
    demo, so the internal addresses are not published. The path is kept because
    it identifies the endpoint (`/v1`, `/ws/transcribe`) without saying which
    machine serves it.
    """
    if not url:
        return ""
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return "***"
    return f"{parts.scheme}://***{parts.path}"


@app.get("/metrics.json")
def metrics_json() -> dict[str, object]:
    cache = getattr(app.state, "semantic_cache", None)
    return {
        **metrics.snapshot(),
        "config": {
            "llm_model": settings.llm_model,
            "llm_base_url": _redact_url(settings.llm_base_url),
            "embedding_model": settings.embedding_model_name,
            "semantic_cache_preload": settings.semantic_cache_preload,
            "semantic_cache_threshold": settings.semantic_cache_similarity_threshold,
            "sentence_segmenter_enabled": settings.sentence_segmenter.enabled,
            "stt_ws_url": _redact_url(settings.stt_ws_url),
        },
        "cache": {
            "loaded": bool(cache and cache.is_loaded),
            "rows": cache.row_count if cache else 0,
        },
        "stt": getattr(app.state, "stt_config", {}),
    }
