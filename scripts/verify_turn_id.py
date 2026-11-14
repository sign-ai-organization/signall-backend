"""Verifies the turn identifier the client puts on its frames.

Decision of the owner (2026-10-18): the client numbers every phrase it sends,
starting at 1 on each connection, and the backend copies that number into the
frames it sends back for that phrase. The number is opaque: the backend does
not parse it, does not compare it and does not make one up. It is the client
that has to know it, because the app may want to drop a phrase before its
first sentence even arrives.

The change is additive: a client that sends no identifier gets frames without
one, exactly as before.

This script needs neither Neon, nor the LLM, nor the STT: the client of the
STT and the orchestrator are replaced by doubles. Run it with

    python -m scripts.verify_turn_id
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
from app.controller.router import _parse_client_frame  # noqa: E402
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
    """Double of the STT client: it keeps what it was sent, without a network."""

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


class FakeOrchestrator:
    calls: list[str] = []

    async def translate_stream(self, text: str):
        FakeOrchestrator.calls.append(text)
        yield 0, 1, fake_segment()


def build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router_module.router)
    app.state.db_keep_alive = FakeKeepAlive()
    app.state.orchestrator = FakeOrchestrator()
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

    print("\nthe classifier reads the identifier")
    frame = _parse_client_frame('{"type":"text","text":"hola","turn":7}')
    check("the kind and the text", (frame.kind, frame.text) if frame else None, ("text", "hola"))
    check("and the identifier", frame.turn if frame else None, 7)

    frame = _parse_client_frame('{"type":"text","text":"hola"}')
    check("a frame without an identifier is still a frame", frame is not None, True)
    check("and the identifier is empty", frame.turn if frame else None, None)

    frame = _parse_client_frame('{"type":"text","text":"hola","turn":"abc"}')
    check("the identifier is copied as it came", frame.turn if frame else None, "abc")

    frame = _parse_client_frame('{"type":"end","turn":3}')
    check("the end frame has no phrase", frame.text if frame else None, "")

    print("\nthe frames of the phrase carry the identifier")
    with TestClient(build_app()) as client:
        with client.websocket_connect("/ws/translate") as ws:
            open_session(ws)
            ws.send_text('{"type":"text","text":"hola","turn":7}')
            messages = [ws.receive_json() for _ in range(2)]
    check("the segment carries it", messages[0].get("turn"), 7)
    check("and the done too", messages[1].get("turn"), 7)

    print("\na client that sends no identifier gets none")
    with TestClient(build_app()) as client:
        with client.websocket_connect("/ws/translate") as ws:
            open_session(ws)
            ws.send_text('{"type":"text","text":"hola"}')
            messages = [ws.receive_json() for _ in range(2)]
    check_that("the segment has no turn", "turn" not in messages[0])
    check_that("and the done has none either", "turn" not in messages[1])

    print("\nevery phrase of a connection has its own identifier")
    with TestClient(build_app()) as client:
        with client.websocket_connect("/ws/translate") as ws:
            open_session(ws)
            ws.send_text('{"type":"text","text":"hola","turn":1}')
            first = [ws.receive_json() for _ in range(2)]
            ws.send_text('{"type":"text","text":"adios","turn":2}')
            second = [ws.receive_json() for _ in range(2)]
    check("the first phrase keeps its own", first[1].get("turn"), 1)
    check("the second one has the next", second[1].get("turn"), 2)

    print("\nthe identifier does not leak into the next phrase")
    with TestClient(build_app()) as client:
        with client.websocket_connect("/ws/translate") as ws:
            open_session(ws)
            ws.send_text('{"type":"text","text":"hola","turn":7}')
            [ws.receive_json() for _ in range(2)]
            ws.send_text('{"type":"text","text":"adios"}')
            messages = [ws.receive_json() for _ in range(2)]
    check_that("the second phrase has no identifier", "turn" not in messages[0])

    print()
    if failures:
        print(f"FAILED {len(failures)}: {', '.join(failures)}")
        sys.exit(1)
    print("all OK")


if __name__ == "__main__":
    main()
