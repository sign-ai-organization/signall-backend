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

from app.nlp.gloss_lexicon import insert_implicit_pronoun, normalize_order, resolve_inflection  # noqa: E402
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
# The catalog has NIÑO *and* NIÑA, so the order of the candidates decides which
# one wins. Kept apart from VOCABULARY so the older "gender" check still means
# what it meant (a catalog with only the masculine).
VOCABULARY_WITH_BOTH = {
    **VOCABULARY,
    normalize_gloss("NIÑA"): "NIÑA",
    normalize_gloss("CON GUSTO"): "CON GUSTO",
    normalize_gloss("COMO ESTAS"): "COMO ESTAS",
    normalize_gloss("POR QUE"): "POR QUE",
    normalize_gloss("TRISTE"): "TRISTE",
}


def check_inflection() -> None:
    print("\ninflection: plural, gender, N/Ñ spelling")
    check("NINOS -> NIÑO", resolve_inflection("NINOS", VOCABULARY), "NIÑO")
    check("NINO -> NIÑO", resolve_inflection("NINO", VOCABULARY), "NIÑO")
    check("BIENVENIDOS -> BIENVENIDO", resolve_inflection("BIENVENIDOS", VOCABULARY), "BIENVENIDO")
    check("NIÑA -> NIÑO (gender)", resolve_inflection("NIÑA", VOCABULARY), "NIÑO")
    check("a gloss already exact is not 'resolved' again", resolve_inflection("NIÑO", VOCABULARY), None)
    check("an unrelated word resolves to nothing", resolve_inflection("ZUMBIDO", VOCABULARY), None)
    # With both genders in the catalog the order cannot be left to chance: the
    # set this used to return made the answer depend on PYTHONHASHSEED.
    check(
        "NIÑAS -> NIÑA when the catalog has both genders",
        resolve_inflection("NIÑAS", VOCABULARY_WITH_BOTH),
        "NIÑA",
    )
    check(
        "NINOS -> NIÑO when the catalog has both genders",
        resolve_inflection("NINOS", VOCABULARY_WITH_BOTH),
        "NIÑO",
    )
    check(
        "NINAS -> NIÑA, not NIÑO",
        resolve_inflection("NINAS", VOCABULARY_WITH_BOTH),
        "NIÑA",
    )


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
        "a first-person possessive ('mi abuelo') does not add YO",
        insert_implicit_pronoun("Mi abuelo nunca trabaja", ["FAMILIA"], VOCABULARY),
        ["FAMILIA"],
    )
    check(
        "a third-person verb with an explicit subject ('la mujer es') does not add TU",
        insert_implicit_pronoun("La mujer es juiciosa", ["FAMILIA"], VOCABULARY),
        ["FAMILIA"],
    )
    check(
        "already has a pronoun: left alone",
        insert_implicit_pronoun("Estoy contento", ["YO", "CONTENTO"], VOCABULARY),
        ["YO", "CONTENTO"],
    )
    check(
        "after a question gloss: '¿por qué estás triste?'",
        insert_implicit_pronoun("¿Por qué estás triste?", ["POR QUE", "TRISTE"], VOCABULARY_WITH_BOTH),
        ["POR QUE", "TU", "TRISTE"],
    )
    check(
        "a phrasal gloss that already carries the person gets no TU: '¿cómo estás?'",
        insert_implicit_pronoun("¿Cómo estás?", ["COMO ESTAS"], VOCABULARY_WITH_BOTH),
        ["COMO ESTAS"],
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


ORDER_GLOSSES = ["QUIEN", "VIVIR", "TU", "FAMILIA", "NIÑO", "TODOS", "TRABAJAR", "COMER", "USTEDES", "DONDE", "SENTIR"]
ORDER_VOCABULARY = {normalize_gloss(gloss): gloss for gloss in ORDER_GLOSSES}
ORDER_CATEGORIES = {
    normalize_gloss(gloss): category
    for gloss, category in [
        ("QUIEN", "interrogativo"),
        ("DONDE", "interrogativo"),
        ("VIVIR", "verbo"),
        ("COMER", "verbo"),
        ("TRABAJAR", "verbo"),
        ("SENTIR", "verbo"),
        ("TU", "pronombre"),
        ("USTEDES", "pronombre"),
        ("FAMILIA", "sustantivo"),
        ("NIÑO", "sustantivo"),
        ("TODOS", "determinante"),
    ]
}


def check_order() -> None:
    print("\norder: the corpus closes a question with the verb and keeps TODOS with the person")
    check(
        "in a question, the verb goes last",
        normalize_order(["QUIEN", "VIVIR", "TU", "FAMILIA"], ORDER_CATEGORIES),
        ["QUIEN", "TU", "FAMILIA", "VIVIR"],
    )
    check(
        "and after a pronoun subject",
        normalize_order(["QUIEN", "COMER", "USTEDES"], ORDER_CATEGORIES),
        ["QUIEN", "USTEDES", "COMER"],
    )
    check(
        "a question that already closes with the verb is left alone",
        normalize_order(["DONDE", "TU", "FAMILIA", "VIVIR"], ORDER_CATEGORIES),
        ["DONDE", "TU", "FAMILIA", "VIVIR"],
    )
    check(
        "TODOS joins the person before the verb",
        normalize_order(["NIÑO", "TRABAJAR", "TODOS"], ORDER_CATEGORIES),
        ["NIÑO", "TODOS", "TRABAJAR"],
    )
    check(
        "and is left alone when it already is there",
        normalize_order(["NIÑO", "TODOS", "TRABAJAR"], ORDER_CATEGORIES),
        ["NIÑO", "TODOS", "TRABAJAR"],
    )
    check(
        "a statement is never reordered: the corpus is not consistent there",
        normalize_order(["ABUELO", "FAMILIA", "VIVIR"], ORDER_CATEGORIES),
        ["ABUELO", "FAMILIA", "VIVIR"],
    )
    check(
        "without categories nothing is moved",
        normalize_order(["QUIEN", "VIVIR", "TU", "FAMILIA"], None),
        ["QUIEN", "VIVIR", "TU", "FAMILIA"],
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

    ordering = LLMClient(
        api_key="test",
        model="gpt-4o-mini",
        temperature=0.0,
        timeout_ms=5000,
        vocabulary=ORDER_VOCABULARY,
        categories=ORDER_CATEGORIES,
    )
    repaired = ordering._repair_glosses(["QUIEN", "VIVIR", "TU", "FAMILIA"], "¿Quién vive con tu familia?")
    check("the repair also fixes the order", repaired, ["QUIEN", "TU", "FAMILIA", "VIVIR"])

    repaired = ordering._repair_glosses(["NIÑOS", "TRABAJAR", "TODOS"], "Niños, trabajen todos")
    check("the singular and the quantifier land together", repaired, ["NIÑO", "TODOS", "TRABAJAR"])


def main() -> None:
    check_inflection()
    check_pronoun()
    check_order()
    check_llm_client_integration()

    print()
    if failures:
        print(f"FAILED {len(failures)}: " + ", ".join(failures))
        sys.exit(1)
    print("all OK")


if __name__ == "__main__":
    main()
