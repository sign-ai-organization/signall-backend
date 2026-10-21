"""Verifies that the cache is written with an UPSERT, and never with an empty answer.

Decision of the owner (for the point 38 of the contrast): the cache used to
do a plain INSERT, so the same phrase stored twice left two rows that no
lookup could tell apart, and the table grew with copies of answers that were
already there. The write is now an UPSERT over `(original_text, phrase_type)`,
and an answer with no glosses in it is not stored at all: it is not a
translation, and a hit with nothing in it would play nothing at all.

This script needs neither Neon, nor the LLM, nor the STT: the pool is
replaced by a double that records the query it was given. Run it with

    python -m scripts.verify_cache_upsert
"""

from __future__ import annotations

import asyncio
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("LLM_MODEL", "gpt-4o-mini")

from app.domain.models import PhraseType  # noqa: E402
from app.nlp.models import Fingerprint  # noqa: E402
from app.nlp.semantic_cache import SemanticCache  # noqa: E402

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


class FakeConnection:
    def __init__(self, pool: FakePool) -> None:
        self._pool = pool

    async def execute(self, query: str, *args) -> str:
        self._pool.writes.append((query, args))
        return "INSERT 0 1"


class FakePool:
    """A pool that records the writes it is given."""

    def __init__(self) -> None:
        self.writes: list[tuple[str, tuple]] = []
        self.released = 0

    async def acquire(self):
        return FakeConnection(self)

    async def release(self, _conn) -> None:
        self.released += 1


class FakeEmbeddingModel:
    """An embedding model that answers with a vector of the right size."""

    def embed(self, text: str) -> list[float]:
        return [0.0] * 384


AFFIRMATIVE = Fingerprint(
    category=PhraseType.AFFIRMATIVE,
    secondary_signals=[],
    has_collision=False,
)


async def main() -> None:
    pool = FakePool()
    cache = SemanticCache(
        pool,
        FakeEmbeddingModel(),  # type: ignore[arg-type]
        0.05,
        preload=False,
    )

    print("\nthe write is an UPSERT")
    await cache.store("hola, como estas", AFFIRMATIVE, ["COMO ESTAS"])
    check_that("something was written", len(pool.writes) == 1, str(pool.writes))
    query = pool.writes[0][0]
    check_that("it is an INSERT", "INSERT INTO semantic_cache" in query, query)
    check_that(
        "it conflicts on the phrase and its type",
        "ON CONFLICT (original_text, phrase_type)" in query,
        query,
    )
    check_that("and it updates the row", "DO UPDATE SET" in query, query)

    print("\nthe same phrase does not pile up rows")
    await cache.store("hola, como estas", AFFIRMATIVE, ["COMO ESTAS"])
    check("two writes, two UPSERTs", len(pool.writes), 2)
    check_that("both are UPSERTs", all("ON CONFLICT" in write[0] for write in pool.writes))

    print("\nan empty answer is not stored")
    before = len(pool.writes)
    await cache.store("una frase sin respuesta", AFFIRMATIVE, [])
    check("nothing was written", len(pool.writes), before)

    print("\nthe connection goes back to the pool")
    check("every write released its connection", pool.released, len(pool.writes))

    print("\nthe migration that the UPSERT needs exists")
    migration = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "app",
        "persistence",
        "migrations",
        "004_semantic_cache_upsert.sql",
    )
    check_that("the file is there", os.path.exists(migration), migration)
    with open(migration, encoding="utf-8") as handle:
        contents = handle.read()
    check_that(
        "it creates the unique index the UPSERT conflicts against",
        "CREATE UNIQUE INDEX" in contents and "(original_text, phrase_type)" in contents,
    )
    check_that(
        "and it removes the rows that cannot be used",
        "cardinality(glosses) = 0" in contents,
    )

    print()
    if failures:
        print(f"FAILED {len(failures)}: {', '.join(failures)}")
        sys.exit(1)
    print("all OK")


if __name__ == "__main__":
    asyncio.run(main())
