"""Administration endpoints: the ones that do not belong to a session.

Today there is one: reloading the semantic cache without restarting the
service (fase 5 of `docs/plan-pruebas/Plan de implementación 2`).

Why an endpoint and not `LISTEN/NOTIFY`
---------------------------------------

`SemanticCache.load_all()` runs once, at start-up. An `UPDATE` or a `DELETE`
run by hand on Neon was invisible until the container restarted, and a restart
drops every open WebSocket session — the avatar stops, the phone reconnects,
and the operator has to type the phrase again just to see whether the edit
worked. The plan offers both and picks the simple one for the measured use
case: an occasional manual edit, not a table that changes on its own.

Why a token and not "it is only localhost"
------------------------------------------

The backend is not behind an authenticating proxy, and during a demo it is
reachable from the local network. A route that makes the service re-read a
table is not destructive, but it is a lever: anyone who can reach the port can
make it hammer the database in a loop. So the route exists only when
`ADMIN_TOKEN` is set, and it is compared with `compare_digest`; when the
variable is empty the route answers 404, as if it did not exist. That keeps the
default deployment from carrying a door nobody asked for.
"""

import logging
import secrets

from fastapi import APIRouter, Header, HTTPException, Request

from app.config.settings import settings
from app.metrics import metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/cache/reload")
async def reload_semantic_cache(
    request: Request,
    x_admin_token: str | None = Header(default=None),
) -> dict[str, object]:
    """Re-read `semantic_cache` into memory and report how many rows it holds.

    The previous index keeps serving until the new one is built, and it keeps
    serving when the read fails: the endpoint answers 503 and says so, instead
    of reporting a reload that did not happen.

    What it does **not** reload is the catalog. `catalog` and `catalog_synonym`
    are also read once at start-up, and the copy the model repairs against
    lives inside `LLMClient`; refreshing them is a different change than the
    one this phase asks for. After reseeding the catalog, the container still
    has to be restarted.
    """
    if not settings.admin_token:
        # Same answer a route that does not exist would give: the deployment
        # that never set a token does not advertise an admin surface.
        raise HTTPException(status_code=404, detail="Not Found")

    if x_admin_token is None or not secrets.compare_digest(x_admin_token, settings.admin_token):
        logger.warning("Rejected /admin/cache/reload: missing or wrong X-Admin-Token")
        metrics.counter("admin_cache_reload_total", labels={"result": "forbidden"})
        raise HTTPException(status_code=403, detail="X-Admin-Token inválido")

    cache = getattr(request.app.state, "semantic_cache", None)
    if cache is None:
        raise HTTPException(status_code=503, detail="La cache semántica no está disponible")

    try:
        rows = await cache.reload()
    except Exception as error:  # noqa: BLE001 - the caller needs a status, not a traceback
        # The old index is still in memory: `reload` fetches before it swaps, so
        # a failed read changes nothing. Saying so is the point of the 503.
        logger.exception("Could not reload the semantic cache")
        metrics.counter("admin_cache_reload_total", labels={"result": "error"})
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo recargar la cache; se sigue usando la anterior ({type(error).__name__})",
        ) from error

    metrics.counter("admin_cache_reload_total", labels={"result": "ok"})
    metrics.gauge("cache_rows", cache.row_count)
    logger.info("Semantic cache reloaded from /admin/cache/reload: %d rows", rows)
    return {"status": "ok", "rows": rows, "cache_rows": cache.row_count}
