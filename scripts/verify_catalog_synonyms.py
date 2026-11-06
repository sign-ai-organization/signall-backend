"""Checks the Fase 2 synonym table: `catalog_synonym`, folded into the
vocabulary `LLMClient._repair_glosses` uses, and into the key
`SemanticCache` normalizes phrases on.

Needs neither Neon nor the embedding model: the pool is a double that
returns the two tables' rows from Python lists, and `substitute_synonyms` is
exercised directly.

    python scripts/verify_catalog_synonyms.py
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("LLM_MODEL", "gpt-4o-mini")

from app.nlp.text_normalizer import normalize, substitute_synonyms  # noqa: E402
from app.validation.catalog_repository import CatalogRepository, normalize_gloss  # noqa: E402

failures: list[str] = []


def check(name: str, got, expected) -> None:
    ok = got == expected
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        expected: {expected!r}")
        print(f"        got:      {got!r}")
        failures.append(name)


CATALOG_ROWS = [
    {"gloss": "MUCHO", "semantic_category": "cuantificador", "glb_animation_path": "signs/mucho.glb"},
    {"gloss": "PERMISO", "semantic_category": "sustantivo", "glb_animation_path": "signs/permiso.glb"},
]
SYNONYM_ROWS = [
    {"synonym": "MUY", "gloss": "MUCHO"},
    {"synonym": "CON PERMISO", "gloss": "PERMISO"},
    {"synonym": "DAME PASAR", "gloss": "PERMISO"},
    # Points at a gloss the catalog does not have: must be skipped, not crash.
    {"synonym": "ALGUNA VEZ", "gloss": "NUNCA"},
    # Collides with an existing catalog gloss: must keep the catalog's own
    # entry, not overwrite it with a synonym's.
    {"synonym": "MUCHO", "gloss": "PERMISO"},
]


class FakePool:
    """Returns the catalog or the synonym rows, by matching the query text."""

    def __init__(self, catalog_rows, synonym_rows) -> None:
        self._catalog_rows = catalog_rows
        self._synonym_rows = synonym_rows

    async def fetch(self, query: str):
        if "catalog_synonym" in query:
            return self._synonym_rows
        return self._catalog_rows


async def check_catalog_repository() -> None:
    print("\nCatalogRepository.load_all() folds catalog_synonym into the vocabulary")
    repo = CatalogRepository(pool=FakePool(CATALOG_ROWS, SYNONYM_ROWS))
    await repo.load_all()

    vocabulary = repo.vocabulary()
    check("MUY resolves to the canonical display spelling", vocabulary.get(normalize_gloss("MUY")), "MUCHO")
    check(
        "CON PERMISO resolves to PERMISO",
        vocabulary.get(normalize_gloss("CON PERMISO")),
        "PERMISO",
    )
    check(
        "a synonym of a gloss the catalog does not have is skipped",
        normalize_gloss("ALGUNA VEZ") in vocabulary,
        False,
    )
    check(
        "a synonym that collides with a real gloss keeps the catalog's own entry",
        vocabulary.get(normalize_gloss("MUCHO")),
        "MUCHO",
    )
    check(
        "synonym_pairs carries the display spellings for SemanticCache",
        sorted(repo.synonym_pairs),
        sorted([("MUY", "MUCHO"), ("CON PERMISO", "PERMISO"), ("DAME PASAR", "PERMISO")]),
    )


def check_substitute_synonyms() -> None:
    print("\nsubstitute_synonyms: two phrasings of the same sign land on the same key")
    synonyms = {normalize(s): normalize(g) for s, g in [("MUY", "MUCHO"), ("CON PERMISO", "PERMISO")]}

    a = substitute_synonyms(normalize("tengo mucho sueño"), synonyms)
    b = substitute_synonyms(normalize("tengo muy sueño"), synonyms)
    check("'mucho' and its synonym 'muy' normalize to the same key", a, b)

    c = substitute_synonyms(normalize("con permiso, puedo pasar"), synonyms)
    d = substitute_synonyms(normalize("permiso, puedo pasar"), synonyms)
    check("the multi-word synonym 'con permiso' folds to 'permiso'", c, d)

    e = substitute_synonyms(normalize("hola buenos dias"), synonyms)
    check("a phrase with no synonym is left untouched", e, normalize("hola buenos dias"))


async def main() -> None:
    await check_catalog_repository()
    check_substitute_synonyms()

    print()
    if failures:
        print(f"FAILED {len(failures)}: " + ", ".join(failures))
        sys.exit(1)
    print("all OK")


if __name__ == "__main__":
    asyncio.run(main())
