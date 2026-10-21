"""Verifies that the catalog's semantic category is read and travels with the sign.

Decision of the owner (for the point 11 of the contrast): the column
`catalog.semantic_category` is documented in the design and in the diagram of
the persistence, and no code read it. The decision was to read it, so that the
code agrees with the diagram and not the other way around.

This script needs neither Neon, nor the LLM, nor the STT: the pool is
replaced by a double that returns rows. Run it with

    python -m scripts.verify_catalog_semantic_category
"""

from __future__ import annotations

import asyncio
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("LLM_MODEL", "gpt-4o-mini")

from app.domain.models import PhraseType, Segment  # noqa: E402
from app.validation.catalog_repository import CatalogRepository  # noqa: E402
from app.validation.validator_service_impl import ValidatorServiceImpl  # noqa: E402

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


class FakePool:
    """A pool that answers the catalog's query with two rows."""

    def __init__(self) -> None:
        self.queries: list[str] = []

    async def fetch(self, query: str, *_args, **_kwargs):
        self.queries.append(query)
        return [
            {
                "gloss": "HOLA",
                "semantic_category": "SALUDOS",
                "glb_animation_path": "/static/hola.glb",
            },
            {
                "gloss": "COMO ESTAS",
                "semantic_category": "PREGUNTAS",
                "glb_animation_path": "/static/como_estas.glb",
            },
        ]


async def main() -> None:
    pool = FakePool()
    repository = CatalogRepository(pool)
    await repository.load_all()

    print("\nthe column is asked for")
    check_that("the query reads the column", "semantic_category" in pool.queries[0], pool.queries[0])

    print("\nthe category reaches the catalog")
    entry = repository.search("HOLA")
    check("the entry has it", entry.semantic_category if entry else None, "SALUDOS")
    entry = repository.search("COMO ESTAS")
    check("and the multi-word one too", entry.semantic_category if entry else None, "PREGUNTAS")

    print("\nthe category travels with the sign")
    validator = ValidatorServiceImpl(repository)
    validated = validator.validate(
        [Segment(type=PhraseType.AFFIRMATIVE, glosses=["HOLA", "UNA SEÑA QUE NO ESTÁ"])]
    )
    glosses = validated[0].glosses
    check("the sign of the catalog carries it", glosses[0].semantic_category, "SALUDOS")
    check("and it is still available", glosses[0].available, True)
    check("a sign that is not in the catalog has none", glosses[1].semantic_category, "")
    check("and it is not available", glosses[1].available, False)

    print()
    if failures:
        print(f"FAILED {len(failures)}: {', '.join(failures)}")
        sys.exit(1)
    print("all OK")


if __name__ == "__main__":
    asyncio.run(main())
