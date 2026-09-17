"""Minimal fake STT server for manually testing the Controller's WebSocket
wiring (11.2/11.3) without needing the real Whisper service running.

Usage: python -m scripts.fixtures.fake_stt_server
"""

import asyncio

import websockets


async def handle(websocket) -> None:
    received = []
    async for message in websocket:
        if isinstance(message, bytes):
            received.append(message)
            print(f"[fake-stt] received chunk #{len(received)} ({len(message)} bytes)")


async def main() -> None:
    async with websockets.serve(handle, "127.0.0.1", 8000):
        print("[fake-stt] listening on ws://127.0.0.1:8000/ws/transcribe")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
