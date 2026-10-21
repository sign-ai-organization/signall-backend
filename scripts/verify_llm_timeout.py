"""Verifies the ceiling and the retries of the call to the language model.

Decision of the owner (2026-10-18): the call to the model has a ceiling of 5 s
and one retry. The reason is the clock of the Android client: it waits 15 s
for a phrase and then declares a failure of its own. With three attempts of
10 s —which is what the model library did by default— the backend was the
last to answer a turn the app had already closed.

This script needs neither Neon, nor the network, nor the STT: it builds the
client and looks at the ceiling and the retries it was given. Run it with

    python -m scripts.verify_llm_timeout
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("LLM_MODEL", "gpt-4o-mini")

from app.config.settings import Settings, settings  # noqa: E402
from app.nlp.llm_client import LLMClient  # noqa: E402

# The window the Android client gives a phrase before it gives up on its own.
CLIENT_CLOCK_MS = 15_000

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


def main() -> None:
    print("\nthe configured numbers")
    # The defaults are the decision; the environment may move them, and the
    # check below is what keeps the moved ones safe.
    defaults = Settings.model_fields
    check("the default ceiling of a call is 5 s", defaults["llm_timeout_ms"].default, 5000)
    check("the default retries are one", defaults["llm_max_retries"].default, 1)
    check("the ceiling in use", settings.llm_timeout_ms, 5000)
    check("the retries in use", settings.llm_max_retries, 1)

    worst_case_ms = settings.llm_timeout_ms * (settings.llm_max_retries + 1)
    check_that(
        "the worst case stays under the client's clock",
        worst_case_ms < CLIENT_CLOCK_MS,
        f"worst case {worst_case_ms} ms, the client waits {CLIENT_CLOCK_MS} ms",
    )
    print(f"        worst case: {worst_case_ms} ms, the client waits {CLIENT_CLOCK_MS} ms")

    print("\nthe client hands both numbers to the model library")
    client = LLMClient(
        api_key="test",
        model="gpt-4o-mini",
        temperature=0.0,
        timeout_ms=settings.llm_timeout_ms,
        max_retries=settings.llm_max_retries,
    )
    check("the ceiling it keeps is the configured one", client.timeout_ms, settings.llm_timeout_ms)
    check("the retries it keeps are the configured ones", client.max_retries, settings.llm_max_retries)
    # `request_timeout` is the name the library gives to the `timeout` it is
    # given, in seconds.
    check("the library got the ceiling", client._chat.request_timeout, settings.llm_timeout_ms / 1000)
    check("the library got the retries", client._chat.max_retries, settings.llm_max_retries)

    print()
    if failures:
        print(f"FAILED {len(failures)}: {', '.join(failures)}")
        sys.exit(1)
    print("all OK")


if __name__ == "__main__":
    main()
