import json

import websockets
from websockets.asyncio.client import ClientConnection

from app.controller.stt_service_client import SttServiceClient


class SttServiceClientImpl(SttServiceClient):
    def __init__(self, stt_ws_url: str) -> None:
        self._stt_ws_url = stt_ws_url
        self._connection: ClientConnection | None = None

    async def connect(self) -> None:
        # Disable the client-driven keepalive ping: this is a long-lived
        self._connection = await websockets.connect(self._stt_ws_url, ping_interval=None)

    async def send_audio(self, chunk: bytes) -> None:
        if self._connection is None:
            return
        await self._connection.send(chunk)

    async def send_end(self) -> None:
        # The STT protocol asks for this as a bare "end" text frame, not JSON
        # (see signall-stt app/main.py: `text_msg.strip().lower() == "end"`).
        if self._connection is None:
            return
        await self._connection.send("end")

    async def receive_transcript(self) -> tuple[str, bool] | None:
        if self._connection is None:
            return None
        try:
            message = await self._connection.recv()
        except websockets.ConnectionClosed:
            return None

        payload = json.loads(message)
        return payload["text"], payload["type"] == "final"

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
