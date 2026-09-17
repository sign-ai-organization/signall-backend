"""Minimal fake STT server for manually testing the Controller's WebSocket
wiring (11.2/11.3/11.4) without needing the real Whisper service running.

Sends back a "final" transcript after receiving 2 audio chunks, and closes
the connection — just enough to exercise the Controller's full round trip.

Usage: python -m scripts.fixtures.fake_stt_server
"""

import asyncio
import json

import websockets


async def handle(websocket) -> None:
    received = 0
    async for message in websocket:
        if isinstance(message, bytes):
            received += 1
            print(f"[fake-stt] received chunk #{received} ({len(message)} bytes)")

            if received == 2:
                await websocket.send(json.dumps({"type": "final", "text": "¿Cuál es su nombre?"}))
                print("[fake-stt] sent final transcript")
                return


async def main() -> None:
    async with websockets.serve(handle, "127.0.0.1", 8000):
        print("[fake-stt] listening on ws://127.0.0.1:8000/ws/transcribe")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
