"""Checks the Fase 2 vocabulary layer: inflection resolution and the
implicit-pronoun rule, both in isolation and wired into `LLMClient`.

Needs neither Neon nor the LLM: `resolve_inflection` and
`insert_implicit_pronoun` are pure functions over a fake vocabulary, and
`LLMClient._repair_glosses` is exercised directly.

    python scripts/verify_gloss_lexicon.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("LLM_MODEL", "gpt-4o-mini")

from app.nlp.gloss_lexicon import insert_implicit_pronoun, resolve_inflection  # noqa: E402
from app.nlp.llm_client import LLMClient  # noqa: E402
from app.validation.catalog_repository import normalize_gloss  # noqa: E402

failures: list[str] = []


def check(name: str, got, expected) -> None:
    ok = got == expected
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        expected: {expected!r}")
        print(f"        got:      {got!r}")
        failures.append(name)


VOCABULARY = {
    normalize_gloss(gloss): gloss
    for gloss in ["NIÑO", "BIENVENIDO", "YO", "TU", "CONTENTO", "FAMILIA", "MAL"]
}


def check_inflection() -> None:
    print("\ninflection: plural, gender, N/Ñ spelling")
    check("NINOS -> NIÑO", resolve_inflection("NINOS", VOCABULARY), "NIÑO")
    check("NINO -> NIÑO", resolve_inflection("NINO", VOCABULARY), "NIÑO")
    check("BIENVENIDOS -> BIENVENIDO", resolve_inflection("BIENVENIDOS", VOCABULARY), "BIENVENIDO")
    check("NIÑA -> NIÑO (gender)", resolve_inflection("NIÑA", VOCABULARY), "NIÑO")
    check("a gloss already exact is not 'resolved' again", resolve_inflection("NIÑO", VOCABULARY), None)
    check("an unrelated word resolves to nothing", resolve_inflection("ZUMBIDO", VOCABULARY), None)


def check_pronoun() -> None:
    print("\nimplicit pronoun: second person, first person, ambiguous, none")
    check(
        "second person ('tu familia') adds TU",
        insert_implicit_pronoun("¿Dónde vive tu familia?", ["FAMILIA"], VOCABULARY),
        ["TU", "FAMILIA"],
    )
    check(
        "first person ('estoy contento') adds YO",
        insert_implicit_pronoun("Estoy contento", ["CONTENTO"], VOCABULARY),
        ["YO", "CONTENTO"],
    )
    check(
        "ambiguous usted/él ('se siente mal') defaults to TU",
        insert_implicit_pronoun("¿Se siente mal?", ["MAL"], VOCABULARY),
        ["TU", "MAL"],
    )
    check(
        "already has a pronoun: left alone",
        insert_implicit_pronoun("Estoy contento", ["YO", "CONTENTO"], VOCABULARY),
        ["YO", "CONTENTO"],
    )
    check(
        "no person marker at all: left alone",
        insert_implicit_pronoun("zumbido trueno", ["FAMILIA"], VOCABULARY),
        ["FAMILIA"],
    )
    check(
        "empty glosses: left alone",
        insert_implicit_pronoun("Estoy contento", [], VOCABULARY),
        [],
    )


def check_llm_client_integration() -> None:
    print("\nwired into LLMClient._repair_glosses")
    client = LLMClient(
        api_key="test",
        model="gpt-4o-mini",
        temperature=0.0,
        timeout_ms=5000,
        vocabulary=VOCABULARY,
    )
    repaired = client._repair_glosses(["NINOS"], "los ninos")
    check("an inflected gloss survives the repair", repaired, ["NIÑO"])

    repaired = client._repair_glosses(["CONTENTO"], "Estoy contento")
    check("the repair also adds the implicit pronoun", repaired, ["YO", "CONTENTO"])

    repaired = client._repair_glosses(["YO", "CONTENTO"], "Estoy contento")
    check("an explicit pronoun from the model is not duplicated", repaired, ["YO", "CONTENTO"])


def main() -> None:
    check_inflection()
    check_pronoun()
    check_llm_client_integration()

    print()
    if failures:
        print(f"FAILED {len(failures)}: " + ", ".join(failures))
        sys.exit(1)
    print("all OK")


if __name__ == "__main__":
    main()
