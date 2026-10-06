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

    async def handle_text(self, text: str) -> None:
        """Translate a phrase the client typed instead of spoke.

        Goes through `handle_transcript` with `is_final=True`, so a typed phrase
        and a spoken one share one pipeline: echo the transcript, translate,
        send the segments.
        """
        await self.handle_transcript(text, is_final=True)

    async def handle_end(self) -> None:
        """Close the utterance the STT has open.

        The STT ends a segment when it hears silence. A client that stops
        capturing — the Android mic toggle — never sends that silence, so the
        segment would stay open and no final transcript would ever arrive.
        The STT protocol has a frame for exactly this case.

        Failures are logged, not raised: this runs on the session's read path,
        and letting it throw would take down a session that is otherwise fine.
        """
        try:
            await self.stt_client.send_end()
        except Exception:
            logger.exception("could not forward end-of-utterance to the STT service")

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
