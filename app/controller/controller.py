import logging

from fastapi import WebSocket

from app.domain.models import ValidatedSegment
from app.controller.stt_service_client import SttServiceClient
from app.observability.pipeline_trace import PipelineTrace, start_trace
from app.orchestrator.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


class Controller:
    def __init__(
        self,
        websocket: WebSocket,
        orchestrator: Orchestrator,
        stt_client: SttServiceClient,
        debug_trace_enabled: bool = False,
    ) -> None:
        self.websocket = websocket
        self.orchestrator = orchestrator
        self.stt_client = stt_client
        self.debug_trace_enabled = debug_trace_enabled

    async def handle_audio_chunk(self, chunk: bytes) -> None:
        await self.stt_client.send_audio(chunk)

    async def handle_transcript(self, text: str, is_final: bool) -> None:
        await self.send_transcript(text, is_final)

        if not is_final or not text.strip():
            return

        logger.info("Final transcript: %r -> translating", text)
        with start_trace() as trace:
            try:
                validated_segments = await self.orchestrator.translate(text)
            except Exception:
                logger.exception("orchestrator.translate failed for %r", text)
                logger.info("Pipeline trace for %r: %s", text, trace.to_dict())
                await self.send_error("No se pudo traducir el texto.")
                return

        logger.info("Pipeline trace for %r: %s", text, trace.to_dict())
        await self.send_result(validated_segments)
        if self.debug_trace_enabled:
            await self.send_trace(trace)

    async def send_transcript(self, text: str, is_final: bool) -> None:
        await self.websocket.send_json({"type": "transcript", "text": text, "final": is_final})

    async def send_trace(self, trace: PipelineTrace) -> None:
        await self.websocket.send_json({"type": "trace", **trace.to_dict()})

    async def send_result(self, segments: list[ValidatedSegment]) -> None:
        logger.info("Sending result: %s", segments)
        await self.websocket.send_json([segment.model_dump() for segment in segments])

    async def send_error(self, message: str) -> None:
        logger.info("Sending error: %s", message)
        await self.websocket.send_json({"type": "error", "message": message})
