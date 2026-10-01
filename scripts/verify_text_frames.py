"""Verification of the client text frames on /ws/translate.

A client may send `{"type": "text", "text": "<phrase>"}` instead of audio, so
the Android app can translate a phrase the user typed (RF-UI-02) without
speaking it. The frame is parsed and routed to `Controller.handle_text`, which
shares the pipeline with the spoken path.

This checks parsing and routing only — no STT, no database, no LLM.

Usage: python -m scripts.verify_text_frames
"""

import asyncio
import json

from app.controller.router import _forward_audio, _parse_text_frame


class _FakeController:
    def __init__(self) -> None:
        self.audio_chunks: list[bytes] = []
        self.texts: list[str] = []

    async def handle_audio_chunk(self, chunk: bytes) -> None:
        self.audio_chunks.append(chunk)

    async def handle_text(self, text: str) -> None:
        self.texts.append(text)


class _FakeWebSocket:
    """Replays a fixed list of WebSocket messages, then reports a disconnect."""

    def __init__(self, messages: list[dict]) -> None:
        self._messages = list(messages)

    async def receive(self) -> dict:
        if not self._messages:
            return {"type": "websocket.disconnect"}
        return self._messages.pop(0)


def check_parsing() -> None:
    cases: list[tuple[str, str | None]] = [
        ('{"type": "text", "text": "quiero ir a la universidad"}', "quiero ir a la universidad"),
        ('{"type":"text","text":"  hola  "}', "hola"),
        ('{"type": "translate", "text": "hola"}', None),
        ('{"type": "text", "text": "   "}', None),
        ('{"type": "text", "text": 123}', None),
        ('{"type": "text"}', None),
        ("not json", None),
        ("[1, 2]", None),
    ]

    for raw, expected in cases:
        actual = _parse_text_frame(raw)
        assert actual == expected, f"{raw!r}: expected {expected!r}, got {actual!r}"

    print(f"[ok] _parse_text_frame: {len(cases)} cases")


async def check_routing() -> None:
    controller = _FakeController()
    websocket = _FakeWebSocket(
        [
            {"type": "websocket.receive", "bytes": b"\x01\x02"},
            {
                "type": "websocket.receive",
                "text": json.dumps(
                    {"type": "text", "text": "quiero ir a la universidad"}
                ),
            },
            {"type": "websocket.receive", "text": json.dumps({"type": "text", "text": "  "})},
            {"type": "websocket.receive", "text": "not json"},
        ]
    )

    await _forward_audio(websocket, controller)

    assert controller.audio_chunks == [b"\x01\x02"], controller.audio_chunks
    assert controller.texts == ["quiero ir a la universidad"], controller.texts
    print("[ok] _forward_audio: audio forwarded, 1 phrase translated, 2 bad frames ignored")


def main() -> None:
    check_parsing()
    asyncio.run(check_routing())
    print("\nText frames work end to end (parse + route).")


if __name__ == "__main__":
    main()
