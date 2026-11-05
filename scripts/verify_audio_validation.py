"""Verifies that a client audio fragment is checked before it reaches the STT.

Decision of the owner (2026-11-03), RNF-SEC-02: a fragment has to be non-empty,
an even number of bytes (PCM16 samples are two bytes each) and no larger than
`AUDIO_MAX_CHUNK_BYTES`. A fragment that breaks any of the three is not audio:

- an empty one carries nothing to transcribe,
- an odd one cannot be split into samples,
- a huge one lets a client make the backend push an arbitrary amount of data
  into the STT.

The session is closed instead of ignored, because a client that sent a frame
that is not audio is not going to start sending audio on the next one.

This script needs neither Neon, nor the LLM, nor the STT: the STT client and
the orchestrator are doubles. Run it with

    python -m scripts.verify_audio_validation
"""

from __future__ import annotations

import asyncio
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("LLM_MODEL", "gpt-4o-mini")
os.environ["DEBUG_TRACE_ENABLED"] = "false"

from app.config.settings import settings  # noqa: E402
from app.controller import router as router_module  # noqa: E402
from app.domain.models import Gloss, PhraseType, ValidatedSegment  # noqa: E402
from app.metrics import metrics  # noqa: E402
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

    def __init__(self, url: str) -> None:
        self.url = url
        self._closed = asyncio.Event()

    async def connect(self) -> None:
        return None

    async def send_audio(self, chunk: bytes) -> None:
        FakeSttClient.sent_audio.append(chunk)

    async def send_end(self) -> None:
        return None

    async def receive_transcript(self):
        await self._closed.wait()
        return None

    async def close(self) -> None:
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
    async def translate_stream(self, text: str):
        yield 0, 1, fake_segment()


def build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router_module.router)
    app.state.db_keep_alive = FakeKeepAlive()
    app.state.orchestrator = FakeOrchestrator()
    return app


def rejection_count(reason: str) -> float:
    return metrics.counter_value("audio_chunks_rejected_total", {"reason": reason})


def session_with(chunk: bytes) -> list[dict]:
    """Open a session, send one fragment, and return every frame that arrives."""
    frames: list[dict] = []
    with TestClient(build_app()) as client:
        with client.websocket_connect("/ws/translate") as ws:
            ws.send_bytes(chunk)
            try:
                while True:
                    frames.append(ws.receive_json())
            except Exception:
                # Starlette closes the socket after the error frame; the
                # exception type changed between versions, and what matters is
                # that nothing else arrives.
                pass
    return frames


def main() -> None:
    router_module.SttServiceClientImpl = FakeSttClient  # type: ignore[assignment]
    maximum = settings.audio_max_chunk_bytes

    print("\nthe limits that apply")
    check("the ceiling is the one documented", maximum, 32768)
    check("a normal 30 ms chunk fits", maximum > 960, True)

    print("\na normal fragment reaches the STT")
    FakeSttClient.sent_audio = []
    chunk = b"\x00\x00" * 480
    with TestClient(build_app()) as client:
        with client.websocket_connect("/ws/translate") as ws:
            ws.send_bytes(chunk)
            # A phrase closes the session on its own; without it the read loop
            # waits for the next frame and the test never returns.
            ws.send_text('{"type":"text","text":"hola","turn":1}')
            messages = [ws.receive_json() for _ in range(2)]
    check("the fragment was forwarded", FakeSttClient.sent_audio, [chunk])
    check("and the phrase still went through", [m.get("type") for m in messages], ["segment", "done"])

    print("\nan empty fragment closes the session")
    FakeSttClient.sent_audio = []
    before = rejection_count("empty")
    frames = session_with(b"")
    check("the client is told why", frames[0].get("type"), "error")
    check("the message is the one the app shows", frames[0].get("message"), "El audio recibido no es válido.")
    check("nothing was forwarded", FakeSttClient.sent_audio, [])
    check("and the rejection is counted", rejection_count("empty") - before, 1)

    print("\nan odd number of bytes closes the session")
    FakeSttClient.sent_audio = []
    before = rejection_count("odd_length")
    frames = session_with(b"\x01\x02\x03")
    check("the client is told why", frames[0].get("type"), "error")
    check("nothing was forwarded", FakeSttClient.sent_audio, [])
    check("and the rejection is counted", rejection_count("odd_length") - before, 1)

    print("\na fragment over the ceiling closes the session")
    FakeSttClient.sent_audio = []
    before = rejection_count("too_large")
    frames = session_with(b"\x00\x00" * (maximum // 2 + 1))
    check("the client is told why", frames[0].get("type"), "error")
    check("nothing was forwarded", FakeSttClient.sent_audio, [])
    check("and the rejection is counted", rejection_count("too_large") - before, 1)

    print("\nthe ceiling itself is accepted")
    FakeSttClient.sent_audio = []
    with TestClient(build_app()) as client:
        with client.websocket_connect("/ws/translate") as ws:
            ws.send_bytes(b"\x00\x00" * (maximum // 2))
            ws.send_text('{"type":"text","text":"hola","turn":1}')
            messages = [ws.receive_json() for _ in range(2)]
    check("a fragment of exactly the ceiling passes", len(FakeSttClient.sent_audio), 1)
    check("and the session is still alive", [m.get("type") for m in messages], ["segment", "done"])

    print("\nthe session keeps working after valid audio")
    FakeSttClient.sent_audio = []
    with TestClient(build_app()) as client:
        with client.websocket_connect("/ws/translate") as ws:
            ws.send_bytes(b"\x00\x00" * 480)
            ws.send_text('{"type":"text","text":"hola","turn":1}')
            messages = [ws.receive_json() for _ in range(2)]
    check("the audio still arrived", len(FakeSttClient.sent_audio), 1)
    check("and the phrase was translated", [m.get("type") for m in messages], ["segment", "done"])

    print()
    if failures:
        print(f"FAILED {len(failures)}: {', '.join(failures)}")
        sys.exit(1)
    print("all OK")


if __name__ == "__main__":
    main()
