"""Checks SentenceSegmenter against the reference output of the segmenter lab.

The fixture holds the lab's 191 cases: the input text, the expected cut
(gold, "||" cuts only) and the output of the lab's "hibrido_ligero" method
with default parameters. The backend version must reproduce lab_output exactly.
"""

import json
import time
from pathlib import Path

from app.config.sentence_segmenter import SentenceSegmenterSettings
from app.nlp.segmenter import SentenceSegmenter

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sentence_segmenter_cases.json"


def main() -> None:
    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    start = time.perf_counter()
    segmenter = SentenceSegmenter(SentenceSegmenterSettings())
    print(f"model load + warm-up: {(time.perf_counter() - start) * 1000:.0f} ms\n")

    differences = 0
    matches_expected = 0
    for case in cases:
        sentences = segmenter.segment(case["text"])
        matches_expected += sentences == case["expected"]
        if sentences != case["lab_output"]:
            differences += 1
            print(f"DIFF {case['source']}")
            print(f"  input:   {case['text']}")
            print(f"  lab:     {' || '.join(case['lab_output'])}")
            print(f"  backend: {' || '.join(sentences)}\n")

    print(f"{len(cases) - differences}/{len(cases)} cases identical to the lab")
    print(f"{matches_expected}/{len(cases)} cases identical to the expected cut (info only)")


if __name__ == "__main__":
    main()
