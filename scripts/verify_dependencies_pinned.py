"""Verifies that the dependencies are pinned (RNF-MNT-04).

The requirement asks for the versions to be fixed; nine of the eleven
dependencies of the service were floating. A build that installs them today
is not the build that runs tomorrow, and a change in a dependency can change
what the pipeline answers without a single line of this project changing.

The two that were already pinned stay the way they are: spaCy, which is
pinned to the range the segmenter rules were evaluated with, and the Spanish
model of spaCy, which comes from an exact wheel.

Run it with

    python -m scripts.verify_dependencies_pinned
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIREMENTS = os.path.join(REPO_ROOT, "requirements.txt")

# The dependencies of the service, with the version the project runs with.
# They are the versions of the image of the backend, measured on 2026-10-21.
EXPECTED = {
    "fastapi": "0.143.0",
    "uvicorn[standard]": "0.54.0",
    "pydantic": "2.14.1",
    "pydantic-settings": "2.15.0",
    "asyncpg": "0.32.0",
    "sentence-transformers": "6.1.0",
    "langchain": "1.4.5",
    "langchain-openai": "1.7.1",
    "websockets": "16.1.1",
}

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


def parse_requirements(path: str) -> dict[str, str]:
    """The requirement lines of the file, as name -> the rest of the line."""
    requirements: dict[str, str] = {}
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            name = line.split("@", 1)[0].strip()
            for separator in ("==", ">=", "<=", "~=", ">", "<"):
                if separator in name:
                    name = name.split(separator, 1)[0].strip()
                    break
            requirements[name] = line
    return requirements


def main() -> None:
    print("\nevery dependency of the service is pinned")
    requirements = parse_requirements(REQUIREMENTS)

    for name, version in EXPECTED.items():
        line = requirements.get(name)
        check_that(f"{name} is there", line is not None, str(requirements))
        if line is None:
            continue
        check(f"{name} is pinned to {version}", line, f"{name}=={version}")

    print("\nthe two that were already pinned stay the way they are")
    spacy = requirements.get("spacy", "")
    check_that("spacy keeps its range", "spacy>=" in spacy, spacy)
    model = requirements.get("es_core_news_md", "")
    check_that("the Spanish model keeps its exact wheel", "es_core_news_md-3.8.0" in model, model)

    print("\nnothing else floats")
    for name, line in requirements.items():
        if name in EXPECTED or name in ("spacy", "es_core_news_md"):
            continue
        check_that(f"{name} is pinned", "==" in line, line)

    print()
    if failures:
        print(f"FAILED {len(failures)}: {', '.join(failures)}")
        sys.exit(1)
    print("all OK")


if __name__ == "__main__":
    main()
