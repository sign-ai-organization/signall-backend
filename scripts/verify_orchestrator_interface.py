"""Checks that `Orchestrator` is an `OrchestratorService`, not just a class (fase 5, TRA-01).

`NLPService` and `ValidatorService` were already abstract bases; the
orchestrator — the one that glues them — was concrete, and `controller.py` had
to import it directly. Extracting the interface is mechanical, and the only way
it can go wrong is silently: the class stops matching the contract and the
controller keeps compiling against the concrete import.

So this script checks the contract itself, with doubles and no database:

1. The abstract base cannot be instantiated, and a subclass that forgets a
   method cannot be instantiated either — the two methods are really required.
2. `Orchestrator` is an instance of the interface, and `translate` /
   `translate_stream` still behave the same way through it.

Run it with: `python -m scripts.verify_orchestrator_interface`
"""

from __future__ import annotations

import asyncio
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("LLM_MODEL", "gpt-4o-mini")

from app.domain.models import Gloss, PhraseType, Segment, ValidatedSegment  # noqa: E402
from app.nlp.nlp_service import NLPService  # noqa: E402
from app.orchestrator.orchestrator import Orchestrator  # noqa: E402
from app.orchestrator.orchestrator_service import OrchestratorService  # noqa: E402
from app.validation.validator_service import ValidatorService  # noqa: E402

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


class FakeNLP(NLPService):
    def __init__(self, sentences: list[str]) -> None:
        self.sentences = sentences

    async def transform(self, text: str) -> list[Segment]:
        return [await self.transform_sentence(sentence) for sentence in self.sentences]

    def split(self, text: str) -> list[str]:
        return list(self.sentences)

    async def transform_sentence(self, sentence: str) -> Segment:
        return Segment(type=PhraseType.AFFIRMATIVE, glosses=[sentence.upper()])


class FakeValidator(ValidatorService):
    def validate(self, segments: list[Segment]) -> list[ValidatedSegment]:
        return [
            ValidatedSegment(
                type=segment.type,
                glosses=[Gloss(text=gloss, available=True, glb_path=f"signs/{gloss}.glb") for gloss in segment.glosses],
            )
            for segment in segments
        ]


class IncompleteOrchestrator(OrchestratorService):
    """Forgets `translate_stream` on purpose."""

    async def translate(self, text: str) -> list[ValidatedSegment]:
        return []


def cannot_instantiate(factory) -> bool:
    try:
        factory()
    except TypeError:
        return True
    return False


async def main() -> None:
    print("\nthe interface really requires both methods")
    check_that("the abstract base cannot be instantiated", cannot_instantiate(OrchestratorService))
    check_that(
        "a subclass without translate_stream cannot be instantiated",
        cannot_instantiate(IncompleteOrchestrator),
    )

    print("\nOrchestrator is an OrchestratorService and still translates")
    orchestrator = Orchestrator(FakeNLP(["Hola", "Buenos dias"]), FakeValidator())
    check_that("it is an instance of the interface", isinstance(orchestrator, OrchestratorService))

    segments = await orchestrator.translate("Hola. Buenos dias.")
    check("one validated segment per sentence", len(segments), 2)
    check("in sentence order", [segment.glosses[0].text for segment in segments], ["HOLA", "BUENOS DIAS"])
    check_that("and every gloss is available", all(gloss.available for segment in segments for gloss in segment.glosses))

    streamed = [item async for item in orchestrator.translate_stream("Hola. Buenos dias.")]
    check("the stream carries a real index", [index for index, _, _ in streamed], [0, 1])
    check("and the real total", [total for _, total, _ in streamed], [2, 2])
    check("and the same segments in order", [segment.glosses[0].text for _, _, segment in streamed], ["HOLA", "BUENOS DIAS"])

    print()
    if failures:
        print(f"FAILED {len(failures)}: {', '.join(failures)}")
        sys.exit(1)
    print("all OK")


if __name__ == "__main__":
    asyncio.run(main())
