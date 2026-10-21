"""Verifies that the project has its static analysis configured (RNF-MNT-03).

The requirement asks for static analyzers; the project had none: there was no
configuration of ruff or mypy anywhere, and no continuous integration either.

What this script checks is that the configuration exists and that the two
tools agree with it. When the tools are installed, it runs them; when they are
not —the image of the service does not carry them, and they are not needed to
run the backend— it says so and checks the configuration on its own.

Run it with

    python -m scripts.verify_static_analysis
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYPROJECT = os.path.join(REPO_ROOT, "pyproject.toml")
REQUIREMENTS_DEV = os.path.join(REPO_ROOT, "requirements-dev.txt")

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


def read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def main() -> None:
    print("\nthe configuration exists")
    check_that("there is a pyproject.toml", os.path.exists(PYPROJECT), PYPROJECT)
    contents = read(PYPROJECT)
    check_that("ruff is configured", "[tool.ruff]" in contents)
    check_that("mypy is configured", "[tool.mypy]" in contents)

    print("\nthe analyzers are pinned")
    dev_requirements = read(REQUIREMENTS_DEV)
    check_that("ruff is pinned", "ruff==" in dev_requirements, dev_requirements)
    check_that("mypy is pinned", "mypy==" in dev_requirements, dev_requirements)

    print("\ncontinuous integration runs them")
    workflow = os.path.join(REPO_ROOT, ".github", "workflows", "ci.yml")
    if not os.path.exists(os.path.join(REPO_ROOT, ".github")):
        # The image of the service does not carry the workflows: they belong to
        # the repository, not to the container that runs the backend.
        print("  SKIP  the workflows are not in this image (they are in the repository)")
    else:
        check_that("there is a workflow", os.path.exists(workflow), workflow)
        if os.path.exists(workflow):
            workflow_contents = read(workflow)
            check_that("it runs ruff", "ruff check" in workflow_contents)
            check_that("and mypy", "mypy" in workflow_contents)

    print("\nthe analyzers themselves")
    ruff = shutil.which("ruff")
    mypy = shutil.which("mypy")
    if ruff is None:
        print("  SKIP  ruff is not installed here (it is in requirements-dev.txt)")
    else:
        result = subprocess.run(
            [ruff, "check", "app", "scripts"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        check_that("ruff is happy", result.returncode == 0, result.stdout + result.stderr)

    if mypy is None:
        print("  SKIP  mypy is not installed here (it is in requirements-dev.txt)")
    else:
        result = subprocess.run(
            [mypy],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        check_that("mypy is happy", result.returncode == 0, result.stdout + result.stderr)

    print()
    if failures:
        print(f"FAILED {len(failures)}: {', '.join(failures)}")
        sys.exit(1)
    print("all OK")


if __name__ == "__main__":
    main()
