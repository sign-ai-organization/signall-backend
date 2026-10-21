"""Checks that the catalog lookup folds the same way on both sides.

The catalog stores one canonical spelling per sign (BUENOS DIAS) but the LLM
emits accented and punctuated variants of the same words (BUENOS DÍAS, ¿QUÉ?).
Before normalization `search` was a plain dict lookup, so those variants missed
and the Android client fell back to its default sign. This exercises the
folding without needing a database: the point is the key function, not the
`asyncpg` plumbing.

    python scripts/verify_catalog_normalization.py
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# The repository only needs asyncpg for its type hints and the pool it queries
# at startup; the folding being checked here is pure. Stubbing it lets this
# script run without installing the whole backend stack.
if "asyncpg" not in sys.modules:
    stub = types.ModuleType("asyncpg")
    stub.Pool = object
    stub.Connection = object
    sys.modules["asyncpg"] = stub

from app.validation.catalog_repository import CatalogRepository, normalize_gloss

# (what the catalog stores, what a caller may search for)
MATCHING = [
    ("BUENOS DIAS", "BUENOS DÍAS"),
    ("BUENOS DIAS", "buenos días"),
    ("COMO", "CÓMO"),
    ("COMO", "¿Cómo?"),
    ("COMO ESTAS", "CÓMO ESTÁS?"),
    ("QUE", "¿QUÉ?"),
    ("QUE", "qué"),
    ("CUANDO", "¿CUÁNDO?"),
    ("DONDE", "¿DÓNDE?"),
    ("POR QUE", "¿POR QUÉ?"),
    ("QUIEN", "¿QUIÉN?"),
    ("TU", "TÚ"),
    ("TIO", "TÍO"),
    ("ADIOS", "ADIÓS"),
    ("PERDON", "PERDÓN"),
    ("MAS O MENOS", "Más o menos"),
    # Ñ is preserved, so these match on case only. Folding it to N would merge
    # two different glosses; see MUST_STAY_APART below.
    ("NIÑO", "niño"),
    ("NIÑA", "niña"),
    ("SEÑA", "seña"),
    ("YO", " yo "),
    ("POR QUE", "POR  QUE"),
]

# Different signs that must NOT collapse into one key.
MUST_STAY_APART = [
    ("NIÑO", "NINO"),
    ("CUANDO", "CUANTO"),
    ("QUE", "QUESO"),
]


def main() -> None:
    failures = 0

    print("matching variants (search must find the stored row):")
    for stored, query in MATCHING:
        # Stand in for the cache: one entry per stored gloss.
        repo = CatalogRepository(pool=None)
        repo.cache = {normalize_gloss(stored): stored}
        hit = repo.search(query)
        ok = hit is not None and hit == stored
        if not ok:
            failures += 1
        print(f"  {'ok  ' if ok else 'FAIL'} search({query!r}) -> {hit!r}")

    print("\ncollisions (different signs must not share a key):")
    for a, b in MUST_STAY_APART:
        same = normalize_gloss(a) == normalize_gloss(b)
        if same:
            failures += 1
        print(f"  {'FAIL' if same else 'ok  '} {a!r} and {b!r} -> "
              f"{normalize_gloss(a)!r} / {normalize_gloss(b)!r}")

    print("\ndegenerate input (must never look up a real entry):")
    for junk in ("", "   ", "¿?", "?"):
        key = normalize_gloss(junk)
        repo = CatalogRepository(pool=None)
        repo.cache = {"QUE": "QUE"}
        ok = repo.search(junk) is None and key != "QUE"
        if not ok:
            failures += 1
        print(f"  {'ok  ' if ok else 'FAIL'} search({junk!r}) -> {key!r}")

    print()
    print("FAILED" if failures else "all checks passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
