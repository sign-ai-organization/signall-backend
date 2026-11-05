"""The database pool, and the policy the project agreed on for it.

Two things live here, and both come from the same decision (owner, 2026-10-18,
RNF-REL-03): a query cannot hang, and a query that fails is tried again once.

The ceiling exists because the app's clock is the one that gives up first. The
Android client waits 15 s for a phrase and then reports a failure of its own;
a backend that keeps waiting past that point answers a turn the client already
closed. With a 5 s ceiling and one retry the worst case is about 10 s, which
leaves the backend the one that reports the failure.

The retry exists because the database this project uses suspends its compute
when it goes idle, and the first query after that suspension is the one that
fails. One more attempt, a moment later, is the difference between a phrase
that works and a phrase that does not.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import asyncpg

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetryPolicy:
    """How many times a failed query is tried again, and how long to wait."""

    retries: int = 1
    delay_seconds: float = 0.5

    @property
    def attempts(self) -> int:
        return self.retries + 1


async def _warm_up_connection(conn: asyncpg.Connection) -> None:
    # Resolve the pgvector type once per connection, so the first real
    # semantic_cache query does not pay asyncpg's type introspection.
    await conn.fetchval("SELECT $1::vector IS NULL", "[0]")


async def create_pool(
    database_url: str,
    min_size: int,
    max_size: int,
    max_inactive_connection_lifetime: float = 0,
    command_timeout_seconds: float | None = None,
    connect_timeout_seconds: float | None = None,
) -> asyncpg.Pool:
    """The pool, with a ceiling on every statement it runs.

    `command_timeout_seconds` is asyncpg's default timeout for the statements
    of a connection: a query that goes over it is cancelled and raises. It is
    what turns "the database stopped answering" into an error the caller can
    see, instead of a phrase that never comes back. `connect_timeout_seconds`
    does the same for each connection: a database that accepts TCP and then
    stalls cannot hold the start-up for the operating system's timeout.
    """
    return await asyncpg.create_pool(
        database_url,
        min_size=min_size,
        max_size=max_size,
        max_inactive_connection_lifetime=max_inactive_connection_lifetime,
        command_timeout=command_timeout_seconds,
        timeout=connect_timeout_seconds,
        init=_warm_up_connection,
    )


async def open_pool(
    database_url: str,
    min_size: int,
    max_size: int,
    max_inactive_connection_lifetime: float = 0,
    command_timeout_seconds: float | None = None,
    connect_timeout_seconds: float | None = None,
    policy: RetryPolicy | None = None,
) -> asyncpg.Pool | None:
    """Open the pool, or return None when the database is not reachable.

    The backend starts without a database on purpose. A Neon that is down at
    this exact moment must not take the service down with it: the container
    would stay dead, and the Android client — which reconnects on its own —
    would never reach it again, not even after Neon came back.

    Without a pool there is no catalog and no persisted cache, so every sign
    comes out as unavailable and every phrase goes to the model. The service
    answers, which is what matters while the database is down.
    """
    effective_policy = policy or RetryPolicy()
    try:
        return await run_with_retry(
            lambda: create_pool(
                database_url,
                min_size,
                max_size,
                max_inactive_connection_lifetime,
                command_timeout_seconds,
                connect_timeout_seconds,
            ),
            effective_policy,
            "could not open the database pool",
        )
    except Exception:
        logger.exception("The database is not reachable; starting without it")
        return None


async def run_with_retry[T](
    operation: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    description: str,
) -> T:
    """Run a database operation, trying it again once if it fails.

    The operation is a callable and not a coroutine because it has to be run
    from the start again: a query that failed halfway cannot be resumed, and
    the connection it was using is already gone.
    """
    for attempt in range(1, policy.attempts):
        try:
            return await operation()
        except Exception:
            logger.warning(
                "%s failed (attempt %d of %d); retrying in %.1f s",
                description,
                attempt,
                policy.attempts,
                policy.delay_seconds,
                exc_info=True,
            )
            await asyncio.sleep(policy.delay_seconds)
    return await operation()
