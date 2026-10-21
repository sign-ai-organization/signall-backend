"""Verifies that a database problem does not take the backend down.

Decision of the owner (2026-10-18): every query has a ceiling of 5 s and is
tried again once, and the start-up does not depend on the database answering.

The reason is the clock of the Android client: it waits 15 s for a phrase and
then declares a failure of its own. A query with no ceiling takes the phrase
with it, and a database that is down at start-up used to kill the process: the
container stayed dead and the client, which reconnects on its own, never
reached it again.

This script needs neither Neon, nor the network, nor the STT: the pool and
the queries are replaced by doubles. Run it with

    python -m scripts.verify_database_resilience
"""

from __future__ import annotations

import asyncio
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("LLM_MODEL", "gpt-4o-mini")

import asyncpg  # noqa: E402
from app.config.settings import settings  # noqa: E402
from app.persistence import database  # noqa: E402
from app.persistence.database import RetryPolicy, open_pool, run_with_retry  # noqa: E402
from app.validation.catalog_repository import CatalogRepository  # noqa: E402

failures: list[str] = []


def check(name: str, got, expected) -> None:
    ok = got == expected
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        expected: {expected!r}")
        print(f"        got:      {got!r}")
        failures.append(name)


def check_that(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        if detail:
            print(f"        {detail}")
        failures.append(name)


class FailingPool:
    """A pool whose queries always fail, the way a database that is down does."""

    def __init__(self) -> None:
        self.calls = 0

    async def fetch(self, *_args, **_kwargs):
        self.calls += 1
        raise ConnectionError("the database is not answering")


async def main() -> None:
    print("\nthe configured numbers")
    check("the ceiling of a query is 5 s", settings.db_command_timeout_seconds, 5.0)
    check("a failed query is tried again once", settings.db_max_retries, 1)

    print("\nthe pool gets the ceiling")
    captured: dict[str, object] = {}

    async def fake_asyncpg_create_pool(*args, **kwargs):
        captured.update(kwargs)
        return "pool"

    original_create_pool = asyncpg.create_pool
    asyncpg.create_pool = fake_asyncpg_create_pool  # type: ignore[assignment]
    try:
        await database.create_pool(
            "postgresql://user:pass@localhost/db",
            5,
            10,
            0,
            command_timeout_seconds=settings.db_command_timeout_seconds,
        )
    finally:
        asyncpg.create_pool = original_create_pool  # type: ignore[assignment]
    check("the pool is created with the ceiling", captured.get("command_timeout"), 5.0)

    print("\na failed query is tried again")
    attempts = {"count": 0}

    async def fails_once() -> str:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise ConnectionError("the database is resuming")
        return "answered"

    policy = RetryPolicy(settings.db_max_retries, settings.db_retry_delay_seconds)
    result = await run_with_retry(fails_once, policy, "the test query")
    check("the second attempt answers", result, "answered")
    check("it took two attempts", attempts["count"], 2)

    print("\na query that keeps failing gives up")
    attempts["count"] = 0

    async def always_fails() -> str:
        attempts["count"] += 1
        raise ConnectionError("the database is not answering")

    raised = False
    try:
        await run_with_retry(always_fails, policy, "the test query")
    except ConnectionError:
        raised = True
    check_that("the error reaches the caller", raised)
    check("it did not try more than the policy allows", attempts["count"], policy.attempts)

    print("\nthe start-up does not depend on the database")
    # Port 1: nothing listens there, so the connection is refused right away
    # instead of waiting for a timeout.
    pool = await open_pool(
        "postgresql://user:pass@127.0.0.1:1/db",
        5,
        10,
        0,
        command_timeout_seconds=settings.db_command_timeout_seconds,
        policy=RetryPolicy(retries=0, delay_seconds=0),
    )
    check_that(
        "a pool that cannot be opened is not fatal",
        pool is None,
        "open_pool should return None when the database is unreachable",
    )

    print("\nthe catalog survives a database that does not answer")
    failing = FailingPool()
    repository = CatalogRepository(failing, RetryPolicy(retries=0, delay_seconds=0))
    raised = False
    try:
        await repository.load_all()
    except ConnectionError:
        raised = True
    check_that("the failure reaches the caller, which is what starts without it", raised)
    check("the catalog stays empty", repository.cache, {})
    check("and the search finds nothing", repository.search("HOLA"), None)

    print("\na repository without a pool starts empty")
    without_pool = CatalogRepository(None)
    await without_pool.load_all()
    check("the catalog is empty", without_pool.cache, {})

    print()
    if failures:
        print(f"FAILED {len(failures)}: {', '.join(failures)}")
        sys.exit(1)
    print("all OK")


if __name__ == "__main__":
    asyncio.run(main())
