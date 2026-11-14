"""Finishing the start-up that a missing database left half done (PR-RES-04)."""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from app.config.settings import settings
from app.metrics import metrics
from app.persistence import database

if TYPE_CHECKING:
    from app.nlp.llm_client import LLMClient
    from app.nlp.semantic_cache import SemanticCache
    from app.persistence.keep_alive import DatabaseKeepAlive
    from app.validation.catalog_repository import CatalogRepository

logger = logging.getLogger(__name__)


async def _open_pool(
    state: Any,
    catalog_repository: "CatalogRepository",
    semantic_cache: "SemanticCache",
    db_keep_alive: "DatabaseKeepAlive",
) -> None:
    """Opens the pool and hands it to the components that were built without it."""
    pool = await database.create_pool(
        settings.database_url,
        settings.db_pool_min_size,
        settings.db_pool_max_size,
        settings.db_pool_max_inactive_connection_lifetime_seconds,
        command_timeout_seconds=settings.db_command_timeout_seconds,
        connect_timeout_seconds=settings.db_connect_timeout_seconds,
    )
    state.db_pool = pool
    catalog_repository.attach_pool(pool)
    semantic_cache.attach_pool(pool)
    db_keep_alive.attach_pool(pool)
    logger.info("The database is reachable again; the pool is open")


async def _load_catalog(
    catalog_repository: "CatalogRepository",
    semantic_cache: "SemanticCache",
    llm_client: "LLMClient",
) -> bool:
    """Loads the catalog and tells the components that depend on it. False when it stayed empty."""
    await catalog_repository.load_all()
    if not catalog_repository.cache:
        return False
    llm_client.update_catalog(catalog_repository.vocabulary(), catalog_repository.categories())
    # The cache keys depend on the synonyms, so the index is rebuilt below even
    # if it had loaded without them.
    semantic_cache.set_synonym_pairs(catalog_repository.synonym_pairs)
    metrics.gauge("catalog_glosses", len(catalog_repository.cache))
    logger.info("Catalog loaded after start-up: %d glosses", len(catalog_repository.cache))
    return True


async def _reload_cache(semantic_cache: "SemanticCache") -> None:
    await semantic_cache.reload()
    metrics.gauge("cache_rows", semantic_cache.row_count)
    metrics.gauge("cache_loaded", 1 if semantic_cache.is_loaded else 0)


async def _recover_once(
    state: Any,
    catalog_repository: "CatalogRepository",
    semantic_cache: "SemanticCache",
    llm_client: "LLMClient",
    db_keep_alive: "DatabaseKeepAlive",
    cache_pending: bool,
) -> None:
    """One round: open the pool, load the catalog and rebuild the cache if needed.

    A step that fails leaves the previous one in place: the next round only
    picks up what is still missing.
    """
    if state.db_pool is None:
        await _open_pool(state, catalog_repository, semantic_cache, db_keep_alive)

    if not catalog_repository.cache:
        if not await _load_catalog(catalog_repository, semantic_cache, llm_client):
            return  # the catalog read failed: retry next round
        cache_pending = settings.semantic_cache_preload

    if cache_pending:
        await _reload_cache(semantic_cache)


async def recover_database(
    state: Any,
    catalog_repository: "CatalogRepository",
    semantic_cache: "SemanticCache",
    llm_client: "LLMClient",
    db_keep_alive: "DatabaseKeepAlive",
) -> None:
    """Finish what start-up could not do because the database was down.

    A backend that starts with the database unreachable answers, but it has no
    pool, an empty catalog and an empty cache, and until now nothing tried
    again: it stayed `degraded` until a restart, and `/admin/cache/reload`
    answered 503 even after the database was back. Every
    `db_recovery_interval_seconds` this opens the pool if it is missing, loads
    the catalog if it is empty and rebuilds the cache index if it never
    loaded, and hands the result to the components that were built without it.
    It ends for good once all three are in place, so a healthy backend pays
    nothing for it.

    Each step is safe to repeat: a failure leaves what already worked in place
    and the next round continues from there. `state` is `app.state`; the pool
    lives in `state.db_pool` so the shutdown closes whichever one exists.
    """
    while True:
        await asyncio.sleep(settings.db_recovery_interval_seconds)
        cache_pending = settings.semantic_cache_preload and not semantic_cache.is_loaded
        if state.db_pool is not None and catalog_repository.cache and not cache_pending:
            logger.info("Database recovery check: nothing left to load; stopping")
            return

        try:
            await _recover_once(state, catalog_repository, semantic_cache, llm_client, db_keep_alive, cache_pending)
        except Exception as error:  # noqa: BLE001 - the next round tries again
            logger.warning("Database recovery attempt failed (%s); trying again later", type(error).__name__)
