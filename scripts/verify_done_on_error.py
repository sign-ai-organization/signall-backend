"""Verifies that the turn is closed even when the translation fails.

Decision of the owner (2026-10-18), for the point 39 of the contrast: when a
phrase fails halfway, the backend sent the `error` and nothing else. The
client waits for the `done` to know that the phrase is over, so without it
the app waited out its own 15 s clock and then reported a failure of a phrase
that had already failed.

This script needs neither Neon, nor the LLM, nor the STT: the client of the
STT and the orchestrator are replaced by doubles. Run it with

    python -m scripts.verify_done_on_error
"""

from __future__ import annotations

import asyncio
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("LLM_MODEL", "gpt-4o-mini")
os.environ["DEBUG_TRACE_ENABLED"] = "false"

from app.controller import router as router_module  # noqa: E402
from app.domain.models import Gloss, PhraseType, ValidatedSegment  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

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


class FakeSttClient:
    sent_audio: list[bytes] = []
    end_calls = 0
    close_calls = 0
    incoming: list[tuple[str, bool]] = []
    stt_closed = False

    def __init__(self, url: str) -> None:
        self.url = url
        self._closed = asyncio.Event()

    async def connect(self) -> None:
        return None

    async def send_audio(self, chunk: bytes) -> None:
        FakeSttClient.sent_audio.append(chunk)

    async def send_end(self) -> None:
        FakeSttClient.end_calls += 1

    async def receive_transcript(self):
        if FakeSttClient.stt_closed:
            return None
        if not FakeSttClient.incoming:
            await self._closed.wait()
            return None
        return FakeSttClient.incoming.pop(0)

    async def close(self) -> None:
        FakeSttClient.close_calls += 1
        self._closed.set()


class FakeKeepAlive:
    def wake_up(self) -> None:
        return None

    def mark_activity(self) -> None:
        return None


def fake_segment() -> ValidatedSegment:
    return ValidatedSegment(
        type=PhraseType.AFFIRMATIVE,
        glosses=[Gloss(text="HOLA", available=True, glb_path="/static/hola.glb")],
    )


class FailingOrchestrator:
    """An orchestrator whose translation always fails."""

    async def translate_stream(self, text: str):
        raise RuntimeError("the model is not answering")
        yield 0, 1, fake_segment()  # pragma: no cover - never reached


class HalfFailingOrchestrator:
    """An orchestrator that sends one sentence and then fails."""

    async def translate_stream(self, text: str):
        yield 0, 2, fake_segment()
        raise RuntimeError("the model is not answering")


def build_app(orchestrator) -> FastAPI:
    app = FastAPI()
    app.include_router(router_module.router)
    app.state.db_keep_alive = FakeKeepAlive()
    app.state.orchestrator = orchestrator
    return app


def open_session(ws) -> None:
    """Consume the frame every session opens with, and check what it announces.

    Since `8a31cc2` the backend tells the client what the session can do before
    answering anything, so the first frame is never the answer to a phrase and
    every positional read is one frame off without this. It is checked rather
    than skipped: opening with it is part of the contract.
    """
    check("the session opens announcing audio", ws.receive_json(), {"type": "capability", "audio": True})


def main() -> None:
    router_module.SttServiceClientImpl = FakeSttClient  # type: ignore[assignment,misc]

    print("\na phrase that fails is closed anyway")
    with TestClient(build_app(FailingOrchestrator())) as client:
        with client.websocket_connect("/ws/translate") as ws:
            open_session(ws)
            ws.send_text('{"type":"text","text":"hola"}')
            messages = [ws.receive_json() for _ in range(2)]
    check("the error comes first", messages[0].get("type"), "error")
    check("and the done closes the turn", messages[1].get("type"), "done")
    check_that("the error says what happened", bool(messages[0].get("message")))

    print("\na phrase that fails halfway is closed too")
    with TestClient(build_app(HalfFailingOrchestrator())) as client:
        with client.websocket_connect("/ws/translate") as ws:
            open_session(ws)
            ws.send_text('{"type":"text","text":"hola"}')
            messages = [ws.receive_json() for _ in range(3)]
    check("the sentence that was ready went out", messages[0].get("type"), "segment")
    check("then the error", messages[1].get("type"), "error")
    check("and the done closes the turn", messages[2].get("type"), "done")

    print("\nthe session survives the failure")
    with TestClient(build_app(FailingOrchestrator())) as client:
        with client.websocket_connect("/ws/translate") as ws:
            open_session(ws)
            ws.send_text('{"type":"text","text":"hola"}')
            [ws.receive_json() for _ in range(2)]
            # A second phrase in the same session: the client is free to try
            # again without reconnecting.
            ws.send_text('{"type":"text","text":"adios"}')
            messages = [ws.receive_json() for _ in range(2)]
    check("the error comes first", messages[0].get("type"), "error")
    check("and the done closes the turn", messages[1].get("type"), "done")

    print("\nthe done carries the identifier of the phrase it closes")
    with TestClient(build_app(FailingOrchestrator())) as client:
        with client.websocket_connect("/ws/translate") as ws:
            open_session(ws)
            ws.send_text('{"type":"text","text":"hola","turn":4}')
            messages = [ws.receive_json() for _ in range(2)]
    check("the error carries it", messages[0].get("turn"), 4)
    check("and the done too", messages[1].get("turn"), 4)

    print()
    if failures:
        print(f"FAILED {len(failures)}: {', '.join(failures)}")
        sys.exit(1)
    print("all OK")


if __name__ == "__main__":
    main()
