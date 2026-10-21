"""Verifies that the prompt does not carry the catalog's gloss list (D-7).

Decision D-7 (owner, 2026-10-16): the prompt does not include the list of the
50 glosses of the catalog. The list does not scale — it is paid on every call
— it goes against the test plan, and the validator already marks a sign that
is not in the catalog as unavailable.

What stays is the repair: the vocabulary is still used in memory, to fix the
answer the model gives.

This script needs neither Neon, nor the LLM, nor the STT: it builds a client
with a vocabulary that no real catalog has, and looks at the prompt it ends up
with. Run it with

    python -m scripts.verify_llm_prompt
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("LLM_MODEL", "gpt-4o-mini")

from app.nlp.llm_client import PROMPT_TEMPLATE, LLMClient  # noqa: E402
from app.validation.catalog_repository import normalize_gloss  # noqa: E402

failures: list[str] = []

# A vocabulary with words that appear nowhere else, so a leak into the prompt
# cannot be mistaken for an example that was always there.
SECRET_GLOSSES = ["ZUMBIDO", "PTERODACTILO", "CARACOLIDO", "XILOFONO"]
# A real multi-word gloss, to check that the repair still joins the pieces.
MULTI_WORD_GLOSS = "COMO ESTAS"
VOCABULARY = {
    normalize_gloss(gloss): gloss for gloss in [*SECRET_GLOSSES, MULTI_WORD_GLOSS]
}


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        if detail:
            print(f"        {detail}")
        failures.append(name)


def build_client() -> LLMClient:
    return LLMClient(
        api_key="test",
        model="gpt-4o-mini",
        temperature=0.0,
        timeout_ms=5000,
        vocabulary=VOCABULARY,
    )


def main() -> None:
    client = build_client()
    prompt = client._prompt

    print("\nthe prompt does not carry the vocabulary")
    for gloss in SECRET_GLOSSES:
        check(f"'{gloss}' is not in the prompt", gloss not in prompt)

    print("\nthe prompt has no place to put the vocabulary")
    check("no '{vocabulary}' placeholder", "{vocabulary}" not in prompt)
    check("no 'closed vocabulary' rule", "closed vocabulary" not in prompt.lower())
    check("no rule mentions the vocabulary", "vocabulary" not in prompt.lower())

    print("\nthe example of a multi-word gloss stays")
    check("the example is still there", "COMO ESTAS" in prompt)
    check("and so is the counter-example", "TU,ESTAR,COMO" in prompt)

    print("\nthe template is the prompt, with nothing injected")
    check("the prompt is the template", prompt == PROMPT_TEMPLATE)

    print("\nthe vocabulary is still there for the repair")
    check("the client kept the vocabulary", client.vocabulary == VOCABULARY)

    # The repair is what covers the risk the closed vocabulary used to cover:
    # the model may answer with a sign that is not in the catalog.
    repaired = client._repair_glosses(["ZUMBIDO", "TRUENO"])
    check("a gloss of the catalog survives the repair", repaired == ["ZUMBIDO"], str(repaired))
    repaired = client._repair_glosses(["TRUENO"])
    # When nothing maps, the answer is kept as it came: an empty segment would
    # play nothing at all, and the validator is the one that marks a sign
    # outside the catalog as unavailable.
    check("an answer with nothing in the catalog is kept as it came", repaired == ["TRUENO"], str(repaired))

    # `_merge_fragments` is what puts "COMO ESTAS" back together when the
    # model splits it, which is the failure the prompt was rewritten for.
    merged = client._merge_fragments(["COMO", "ESTAS"])
    check("a split multi-word gloss is joined back", merged == ["COMO ESTAS"], str(merged))

    print()
    if failures:
        print(f"FAILED {len(failures)}: {', '.join(failures)}")
        sys.exit(1)
    print("all OK")


if __name__ == "__main__":
    main()
