"""Checks `recover_database`, the retry that PR-RES-04 asks for.

A backend that starts while the database is down has no pool, an empty catalog
and an empty cache. The old behaviour was to stay `degraded` until a restart.
What this script checks:

1. While the database is still down, every round fails quietly and nothing is
   half-attached: the catalog stays empty and the service keeps running.
2. When the database comes back, the pool is attached to the catalog, the cache
   and the keep-alive, the catalog loads, the LLM client receives it, and the
   cache index is rebuilt.
3. The task ends by itself once everything is loaded.
4. A pool that opened but whose catalog read failed is kept, and the next round
   only loads what is missing (it does not open a second pool).

Needs neither Neon nor the model: every collaborator is a double. Run it with

    python -m scripts.verify_database_recovery
"""

from __future__ import annotations

import asyncio
import os
import sys
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("LLM_MODEL", "gpt-4o-mini")

from app.persistence import database, recovery  # noqa: E402

failures: list[str] = []


def check(name: str, got, expected) -> None:
    ok = got == expected
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        got {got!r}, expected {expected!r}")
        failures.append(name)


class FakeCatalog:
    def __init__(self, fail_loads: int = 0) -> None:
        self.cache: dict[str, str] = {}
        self.synonym_pairs: list[tuple[str, str]] = []
        self.pool = None
        self.fail_loads = fail_loads

    def attach_pool(self, pool) -> None:
        self.pool = pool

    async def load_all(self) -> None:
        if self.fail_loads > 0:
            self.fail_loads -= 1
            raise RuntimeError("database not ready")
        self.cache = {"HOLA": "HOLA"}
        self.synonym_pairs = [("MUY", "MUCHO")]

    def vocabulary(self) -> dict[str, str]:
        return dict(self.cache)

    def categories(self) -> dict[str, str]:
        return {key: "saludo" for key in self.cache}


class FakeCache:
    def __init__(self) -> None:
        self.is_loaded = False
        self.row_count = 0
        self.pool = None
        self.synonyms = None
        self.reloads = 0

    def attach_pool(self, pool) -> None:
        self.pool = pool

    def set_synonym_pairs(self, pairs) -> None:
        self.synonyms = pairs

    async def reload(self) -> int:
        self.reloads += 1
        self.is_loaded = True
        self.row_count = 4
        return 4


class FakeLLM:
    def __init__(self) -> None:
        self.vocabulary: dict[str, str] = {}
        self.categories: dict[str, str] = {}

    def update_catalog(self, vocabulary, categories) -> None:
        self.vocabulary = vocabulary
        self.categories = categories


class FakeKeepAlive:
    def __init__(self) -> None:
        self.pool = None

    def attach_pool(self, pool) -> None:
        self.pool = pool


async def run(database_ups: list[bool], catalog: FakeCatalog) -> dict[str, object]:
    """Drive `recover_database` with a database that is up or down per attempt."""
    attempts = {"pools": 0}
    pool = object()

    async def fake_create_pool(*args, **kwargs):
        index = attempts["pools"]
        attempts["pools"] += 1
        if not database_ups[min(index, len(database_ups) - 1)]:
            raise ConnectionRefusedError("database down")
        return pool

    database.create_pool = fake_create_pool
    recovery.settings.db_recovery_interval_seconds = 0.01

    app = SimpleNamespace(state=SimpleNamespace(db_pool=None))
    cache, llm, keep_alive = FakeCache(), FakeLLM(), FakeKeepAlive()
    task = asyncio.create_task(recovery.recover_database(app.state, catalog, cache, llm, keep_alive))
    try:
        await asyncio.wait_for(task, timeout=1)
        finished = True
    except TimeoutError:
        finished = False
    return {
        "finished": finished,
        "pools_opened": attempts["pools"],
        "pool": pool,
        "app": app,
        "cache": cache,
        "llm": llm,
        "keep_alive": keep_alive,
    }


async def main_checks() -> None:
    print("\nthe database stays down: nothing is attached and the task keeps trying")
    catalog = FakeCatalog()
    result = await run([False], catalog)
    check("the task has not finished", result["finished"], False)
    check("no pool was attached to the app", result["app"].state.db_pool, None)
    check("the catalog is still empty", catalog.cache, {})

    print("\nthe database comes back on the third attempt")
    catalog = FakeCatalog()
    result = await run([False, False, True], catalog)
    check("the task ended by itself", result["finished"], True)
    check("the pool is on the app", result["app"].state.db_pool is result["pool"], True)
    check("the catalog has the pool", catalog.pool is result["pool"], True)
    check("the cache has the pool", result["cache"].pool is result["pool"], True)
    check("the keep-alive has the pool", result["keep_alive"].pool is result["pool"], True)
    check("the catalog loaded", catalog.cache, {"HOLA": "HOLA"})
    check("the LLM client got the vocabulary", result["llm"].vocabulary, {"HOLA": "HOLA"})
    check("the LLM client got the categories", result["llm"].categories, {"HOLA": "saludo"})
    check("the cache got the synonyms", result["cache"].synonyms, [("MUY", "MUCHO")])
    check("the cache index was rebuilt", result["cache"].is_loaded, True)

    print("\nthe pool opens but the catalog read fails once")
    catalog = FakeCatalog(fail_loads=1)
    result = await run([True], catalog)
    check("the task ended by itself", result["finished"], True)
    check("only one pool was opened", result["pools_opened"], 1)
    check("the catalog loaded on the second round", catalog.cache, {"HOLA": "HOLA"})
    check("the cache was rebuilt once", result["cache"].reloads, 1)


asyncio.run(main_checks())

if failures:
    print(f"\n{len(failures)} check(s) failed")
    sys.exit(1)
print("\nAll checks passed")
