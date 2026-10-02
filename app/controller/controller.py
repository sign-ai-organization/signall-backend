import logging

from fastapi import WebSocket

from app.domain.models import ValidatedSegment
from app.controller.stt_service_client import SttServiceClient
from app.observability.pipeline_trace import PipelineTrace, start_trace, trace_step
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
                with trace_step("total"):
                    async for index, total, segment in self.orchestrator.translate_stream(text):
                        await self.send_segment(index, total, segment, trace)
            except Exception:
                logger.exception("orchestrator.translate_stream failed for %r", text)
                logger.info("Pipeline trace for %r: %s", text, trace.to_dict())
                await self.send_error("No se pudo traducir el texto.")
                return

        logger.info("Pipeline trace for %r: %s", text, trace.to_dict())
        if self.debug_trace_enabled:
            await self.websocket.send_json({"type": "trace", "steps_ms": trace.to_dict()["steps_ms"]})
        await self.websocket.send_json({"type": "done"})

    async def send_transcript(self, text: str, is_final: bool) -> None:
        await self.websocket.send_json({"type": "transcript", "text": text, "final": is_final})

    async def send_segment(self, index: int, total: int, segment: ValidatedSegment, trace: PipelineTrace) -> None:
        logger.info("Sending segment %d/%d: %s", index + 1, total, segment)
        if self.debug_trace_enabled:
            await self.websocket.send_json({"type": "sentence_trace", "index": index, **trace.sentence_dict(index)})
        await self.websocket.send_json(
            {"type": "segment", "index": index, "total": total, "segment": segment.model_dump(mode="json")}
        )

    async def send_error(self, message: str) -> None:
        logger.info("Sending error: %s", message)
        await self.websocket.send_json({"type": "error", "message": message})
