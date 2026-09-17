from fastapi import WebSocket

from app.domain.models import ValidatedSegment
from app.controller.stt_service_client import SttServiceClient
from app.orchestrator.orchestrator import Orchestrator


class Controller:
    def __init__(
        self,
        websocket: WebSocket,
        orchestrator: Orchestrator,
        stt_client: SttServiceClient,
    ) -> None:
        self.websocket = websocket
        self.orchestrator = orchestrator
        self.stt_client = stt_client

    async def handle_audio_chunk(self, chunk: bytes) -> None:
        await self.stt_client.send_audio(chunk)

    async def handle_transcript(self, text: str, is_final: bool) -> None:
        if not is_final:
            return

        validated_segments = await self.orchestrator.translate(text)
        await self.send_result(validated_segments)

    async def send_result(self, segments: list[ValidatedSegment]) -> None:
        await self.websocket.send_json([segment.model_dump() for segment in segments])
