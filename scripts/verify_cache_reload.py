"""Checks `SemanticCache.reload`, the body of `POST /admin/cache/reload` (fase 5).

The point of the endpoint is that an edit made by hand on Neon shows up without
restarting the container, and that a failed reload is not a step backwards. So
the four things this script checks are:

1. A row edited and a row deleted by hand are gone after the reload.
2. A row inserted by hand is served after the reload.
3. A reload whose read fails leaves the previous cache serving, and the failure
   is raised so the endpoint can answer 503 instead of reporting success.
4. With `semantic_cache_preload` off there is no index to rebuild and the reload
   says so (0 rows) instead of pretending to have loaded something.

Needs neither Neon nor the model: the pool is a double and the embeddings are a
fixed table. Run it with

    python -m scripts.verify_cache_reload
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
from app.persistence.database import RetryPolicy  # noqa: E402

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


AFFIRMATIVE = Fingerprint(category=PhraseType.AFFIRMATIVE, secondary_signals=[], has_collision=False)


class FakeEmbeddingModel:
    """One fixed direction per phrase, so a deleted row can never match by accident."""

    VECTORS = {
        "hola": [1.0, 0.0, 0.0],
        "gracias": [0.0, 1.0, 0.0],
        "buenos dias": [0.0, 0.0, 1.0],
    }

    def embed(self, text: str) -> list[float]:
        return list(self.VECTORS.get(text, [0.5, 0.5, 0.0]))


def row(text: str, glosses: list[str]) -> dict[str, object]:
    vector = FakeEmbeddingModel.VECTORS.get(text, [0.5, 0.5, 0.0])
    return {
        "original_text": text,
        "phrase_type": PhraseType.AFFIRMATIVE.value,
        "glosses": glosses,
        "embedding": "[" + ",".join(str(value) for value in vector) + "]",
    }


class FakePool:
    """A pool that answers the cache read and can be told to fail."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.fail = False
        self.reads = 0

    async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
        self.reads += 1
        if self.fail:
            raise RuntimeError("neon did not answer")
        return self.rows


def build_cache(pool: FakePool, preload: bool = True) -> SemanticCache:
    return SemanticCache(
        pool,  # type: ignore[arg-type] - a double with the one method the cache uses
        FakeEmbeddingModel(),  # type: ignore[arg-type]
        # 0.0: only the row's own vector is close enough, so a deleted phrase
        # cannot come back as a semantic hit from a leftover row.
        0.0,
        preload=preload,
        # No retry and no wait: a failure has to be checked, not slept through.
        retry_policy=RetryPolicy(retries=0, delay_seconds=0),
    )


async def main() -> None:
    print("\nthe cache starts from what the table says")
    pool = FakePool([row("hola", ["HOLA"]), row("gracias", ["GRACIAS"])])
    cache = build_cache(pool)
    await cache.load_all()
    check("the row count", cache.row_count, 2)
    check("an exact phrase is served", await cache.lookup("hola", AFFIRMATIVE), ["HOLA"])

    print("\na reload picks up the edits made by hand")
    pool.rows = [
        row("hola", ["HOLA", "BUENOS DIAS"]),  # edited
        # "gracias" deleted
        row("buenos dias", ["BUENOS DIAS"]),  # inserted
    ]
    check("the reload reports the new count", await cache.reload(), 2)
    check("the counter follows", cache.row_count, 2)
    check("the edited glosses are the new ones", await cache.lookup("hola", AFFIRMATIVE), ["HOLA", "BUENOS DIAS"])
    check("the inserted row is served", await cache.lookup("buenos dias", AFFIRMATIVE), ["BUENOS DIAS"])
    check("the deleted row is gone", await cache.lookup("gracias", AFFIRMATIVE), None)

    print("\na failed reload keeps the previous cache and says so")
    pool.fail = True
    raised = False
    try:
        await cache.reload()
    except RuntimeError:
        raised = True
    check_that("the failure is raised, so the endpoint can answer 503", raised)
    check("the old index is still in memory", cache.row_count, 2)
    check("and still answers", await cache.lookup("hola", AFFIRMATIVE), ["HOLA", "BUENOS DIAS"])

    print("\nwithout preload there is no in-memory index to rebuild")
    plain = build_cache(pool, preload=False)
    await plain.load_all()
    check("the reload loads nothing", await plain.reload(), 0)
    check_that("and it is not marked as loaded", not plain.is_loaded)

    print()
    if failures:
        print(f"FAILED {len(failures)}: {', '.join(failures)}")
        sys.exit(1)
    print("all OK")


if __name__ == "__main__":
    asyncio.run(main())
