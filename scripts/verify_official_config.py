"""Verifies which LLM configuration is official and which one is local only.

Decision of the owner (2026-11-03): the official configuration is
`gpt-4o-mini` with 5 s per call and one retry. Qwen lives only in
`.env.local`, a file that is not versioned, so a fresh clone runs the official
model and a development machine can keep the local Ollama without touching
`.env`.

This script reads the files as text, so it needs neither the app's
dependencies nor a running service. Run it from the backend root with

    python3 scripts/verify_official_config.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

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


def read_env(name: str) -> dict[str, str]:
    """Parse a dotenv file into a dictionary, without any dependency."""
    values: dict[str, str] = {}
    path = ROOT / name
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def main() -> None:
    official = read_env(".env")
    example = read_env(".env.example")
    local_example = read_env(".env.local.example")

    print("\n.env carries the official configuration")
    check("the model", official.get("LLM_MODEL"), "gpt-4o-mini")
    check("the base URL is empty, which means OpenAI", official.get("LLM_BASE_URL"), "")
    check("the ceiling of a call", official.get("LLM_TIMEOUT_MS"), "5000")
    check("the retries", official.get("LLM_MAX_RETRIES"), "1")
    check_that("no local provider is configured there", "qwen" not in str(official).lower())
    check_that("the audio ceiling is documented", official.get("AUDIO_MAX_CHUNK_BYTES") in (None, "32768"))

    print("\n.env.example is the template of the official configuration")
    check("the model", example.get("LLM_MODEL"), "gpt-4o-mini")
    check("the base URL is empty", example.get("LLM_BASE_URL"), "")
    check("the ceiling of a call", example.get("LLM_TIMEOUT_MS"), "5000")
    check("the retries", example.get("LLM_MAX_RETRIES"), "1")
    check("the audio ceiling", example.get("AUDIO_MAX_CHUNK_BYTES"), "32768")
    check("the connect ceiling", example.get("DB_CONNECT_TIMEOUT_SECONDS"), "5")
    check("the acquire ceiling", example.get("DB_ACQUIRE_TIMEOUT_SECONDS"), "5")
    check_that("no local provider is configured there", "qwen" not in str(example).lower())

    print("\n.env.local.example is the development-only override")
    check("the local model", local_example.get("LLM_MODEL"), "qwen3:4b-instruct")
    check("the local endpoint", local_example.get("LLM_BASE_URL"), "http://host.docker.internal:11434/v1")
    check("the placeholder key keeps the real one off the local server", local_example.get("LLM_API_KEY"), "ollama")

    print("\nthe local file does not enter the repository")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    check_that(".gitignore excludes .env.local", ".env.local" in gitignore.splitlines())

    print("\nthe settings read both files, the local one last")
    settings_source = (ROOT / "app/config/settings.py").read_text(encoding="utf-8")
    check_that(
        "the order is .env and then .env.local",
        'env_file=(".env", ".env.local")' in settings_source,
    )

    print("\ncompose passes the local file only when it exists")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    check_that("the local file is listed", "path: .env.local" in compose)
    check_that("and it is optional", "required: false" in compose)

    print()
    if failures:
        print(f"FAILED {len(failures)}: {', '.join(failures)}")
        sys.exit(1)
    print("all OK")


if __name__ == "__main__":
    main()
