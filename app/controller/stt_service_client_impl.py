"""Cliente del servicio STT.

Traduce el protocolo WebSocket a un tipo: `TranscriptUpdate`. El resto del
backend no necesita saber que existen `partial` y `final`, ni que el STT ahora
manda timestamps por palabra — solo recibe actualizaciones y decide qué hacer
con ellas.

Ese `words` es lo que habilita el modo en tiempo real. Ver
`app/realtime/incremental.py`.
"""

import json

import websockets
from websockets.asyncio.client import ClientConnection

from app.controller.stt_service_client import SttServiceClient
from app.realtime.incremental import TranscriptUpdate


class SttServiceClientImpl(SttServiceClient):
    def __init__(self, stt_ws_url: str) -> None:
        self._stt_ws_url = stt_ws_url
        self._connection: ClientConnection | None = None

    async def connect(self) -> None:
        # Disable the client-driven keepalive ping: this is a long-lived
        self._connection = await websockets.connect(self._stt_ws_url, ping_interval=None)

    async def send_audio(self, chunk: bytes) -> None:
        await self._connection.send(chunk)

    async def send_end(self) -> None:
        # The STT protocol asks for this as a bare "end" text frame, not JSON
        # (see sign-ai-stt app/main.py: `text_msg.strip().lower() == "end"`).
        if self._connection is None:
            return
        await self._connection.send("end")

    async def receive_transcript(self) -> TranscriptUpdate | None:
        try:
            message = await self._connection.recv()
        except websockets.ConnectionClosed:
            return None

        payload = json.loads(message)
        return TranscriptUpdate(
            text=payload.get("text", ""),
            final=payload.get("type") == "final",
            words=_parse_words(payload.get("words")),
            audio_ms=float(payload.get("audio_ms") or 0.0),
        )

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()


def _parse_words(raw: object) -> tuple[tuple[str, float, float], ...]:
    """Lee el `words` del STT, ignorando lo que venga raro.

    Un STT viejo no manda este campo y uno nuevo podría mandarlo mal. Ninguno de
    los dos casos vale la pena tumbar la sesión: el peor resultado de no tener
    timestamps es usar la regla más gruesa, que ya está contemplada.
    """
    if not isinstance(raw, list):
        return ()

    parsed: list[tuple[str, float, float]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        text = entry.get("w")
        if not isinstance(text, str):
            continue
        try:
            start = float(entry.get("s") or 0.0)
            end = float(entry.get("e") or 0.0)
        except (TypeError, ValueError):
            continue
        parsed.append((text, start, end))
    return tuple(parsed)