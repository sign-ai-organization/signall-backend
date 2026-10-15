"""Session translation: the Android client WebSocket and the STT WebSocket.

One translation trigger, and it is not speech
---------------------------------------------

The backend translates **only** what the client sends as a phrase:

    {"type": "text", "text": "hola, como estas"}

Everything the STT says is echoed back and nothing else. A `final` transcript
means "the phrase closed", not "translate this". That single rule is what
RF-STT-03 asks for and it holds structurally: there is no way for speech to
reach the language model without the client having sent it, so a dictated
phrase cannot be signed before the user confirms it.

The client is what makes each mode a mode, and it needs no flag to do it:

- **Dictation**: the client streams audio, receives the transcripts, leaves the
  phrase in the input bar and sends it as `text` when the user presses
  Translate.
- **Live**: the client streams audio and re-sends each closed phrase as `text`
  on its own, with no button press.
- **Live with the mic held open** (`◢◢ TR`): the same thing for every phrase,
  without turning the microphone off in between.

None of those three is a backend concept. The backend sees audio and text
frames, and that is the whole protocol.

Why the translation used to run inside the read loop
----------------------------------------------------

Translating inline meant that while the pipeline ran, the next message from the
STT was not read. With an LLM in the middle a `final` could sit unread in the
socket while the avatar waited for it. The translation now happens on its own
task and the read loop keeps draining the STT.
"""

import array
import logging
import math
import time

from fastapi import WebSocket

from app.controller.stt_service_client import SttServiceClient
from app.domain.models import ValidatedSegment
from app.metrics import metrics
from app.observability.pipeline_trace import PipelineTrace, start_trace, trace_step
from app.orchestrator.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


def _pcm16_rms(chunk: bytes) -> float:
    """RMS level of one PCM16 chunk, 0..32767.

    The client's own volume meter cannot tell "the user spoke" from "the room
    was loud", because it measures the phone's output stage. This measures the
    bytes that actually reached the server, which is what the STT will try to
    transcribe.

    Written out rather than using `audioop`, which was removed in Python 3.13:
    the same arithmetic in four lines keeps the helper working on every version
    the backend might be run with.
    """
    if len(chunk) < 2:
        return 0.0
    samples = array.array("h")
    samples.frombytes(chunk[: len(chunk) - (len(chunk) % 2)])
    if not samples:
        return 0.0
    return math.sqrt(sum(value * value for value in samples) / len(samples))


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
        self._audio_bytes = 0
        self._audio_chunks = 0
        self._audio_rms_total = 0.0
        self._phrase_started_at: float | None = None
        self._first_segment_at: float | None = None
        self._sentences_sent = 0
        self._glosses_sent = 0

    # ----------------------------------------------------------------- audio

    async def handle_audio_chunk(self, chunk: bytes) -> None:
        """Forward one chunk of client audio to the STT, untouched.

        The bytes go across exactly as they arrived: no resampling, no header,
        no framing. Reassembling into the 30 ms units the VAD works on is the
        STT's job.
        """
        await self.stt_client.send_audio(chunk)
        self._audio_bytes += len(chunk)
        self._audio_chunks += 1
        metrics.counter("audio_bytes_total", len(chunk))
        metrics.counter("audio_chunks_total")
        metrics.gauge("session_audio_bytes", self._audio_bytes)

        rms = _pcm16_rms(chunk)
        # Running mean: a chunk is 30 ms and many arrive per second, so the mean
        # over the session is the sustained level, which is the interesting one.
        self._audio_rms_total += rms
        metrics.gauge("session_audio_rms", self._audio_rms_total / self._audio_chunks)
        metrics.histogram("audio_rms", rms, "Nivel RMS por fragmento de audio entrante")

    def audio_stats(self) -> tuple[int, float]:
        """(bytes, mean rms) captured in this session. For tests and diagnosis."""
        return self._audio_bytes, self._audio_rms_total / max(1, self._audio_chunks)

    # ---------------------------------------------------------------- phrases

    async def handle_text(self, text: str) -> None:
        """Translate one phrase. The only translation trigger in the system.

        Whether the phrase was typed, dictated, or dictated in live mode is the
        client's business and makes no difference here: a phrase that arrives as
        `text` is a phrase to translate. It goes through
        `Orchestrator.translate_stream`, which splits it into sentences and
        yields them in order with a real `index` and `total`.
        """
        self._phrase_started_at = time.monotonic()
        self._first_segment_at = None
        self._sentences_sent = 0
        self._glosses_sent = 0
        await self.send_transcript(text, True)

        logger.info("Phrase received: %r -> translating", text)
        with start_trace() as trace:
            try:
                with trace_step("total"):
                    async for index, total, segment in self.orchestrator.translate_stream(text):
                        await self.send_segment(index, total, segment, trace)
            except Exception:
                logger.exception("orchestrator.translate_stream failed for %r", text)
                logger.info("Pipeline trace for %r: %s", text, trace.to_dict())
                metrics.counter("rt_phrase_errors_total")
                await self.send_error("No se pudo traducir el texto.")
                self._phrase_started_at = None
                return

        logger.info("Pipeline trace for %r: %s", text, trace.to_dict())
        if self.debug_trace_enabled:
            await self.websocket.send_json({"type": "trace", "steps_ms": trace.to_dict()["steps_ms"]})
        await self.websocket.send_json({"type": "done"})
        self._record_phrase_timings(text)

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
        """Echo one STT transcript to the client. Never translates.

        A `final` here means the STT closed the phrase. What happens next is the
        client's decision: it either re-sends the phrase as `text` right away
        (live mode) or holds it for the user to confirm (dictation).

        **An empty `final` is an answer, not a lost phrase.** The STT closed the
        utterance and its drop filter found no words in the audio, which is what
        releasing the microphone over noise does. The transcript goes out anyway,
        empty, so the client can stop waiting: a client that only closes a phrase
        on a non-empty transcript waits out its own timeout and then reports a
        failure for a phrase that never existed. The empty `final` carries no
        glosses, so there is nothing to translate here anyway.
        """
        await self.send_transcript(text, is_final)

    # ------------------------------------------------------------- outgoing

    async def send_transcript(self, text: str, is_final: bool) -> None:
        await self.websocket.send_json({"type": "transcript", "text": text, "final": is_final})

    async def send_segment(self, index: int, total: int, segment: ValidatedSegment, trace: PipelineTrace) -> None:
        if self._phrase_started_at is not None:
            since_phrase_ms = (time.monotonic() - self._phrase_started_at) * 1000
            if self._first_segment_at is None:
                self._first_segment_at = time.monotonic()
                # Kept under its old name on purpose: this is the headline
                # latency of the system, the one the project's own docs quote as
                # the baseline, and a sentence is what the avatar starts
                # signing. `rt_sentence_delay_ms` below is the same clock read
                # for every sentence.
                metrics.histogram(
                    "rt_first_sign_ms",
                    since_phrase_ms,
                    "Primera oración enviada menos frase recibida",
                )
            metrics.histogram(
                "rt_sentence_delay_ms",
                since_phrase_ms,
                "Oración enviada menos frase recibida",
            )
        self._sentences_sent += 1
        self._glosses_sent += len(segment.glosses)

        logger.info("Sending segment %d/%d: %s", index + 1, total, segment)
        if self.debug_trace_enabled:
            await self.websocket.send_json({"type": "sentence_trace", "index": index, **trace.sentence_dict(index)})
        await self.websocket.send_json(
            {"type": "segment", "index": index, "total": total, "segment": segment.model_dump(mode="json")}
        )

    async def send_error(self, message: str) -> None:
        logger.info("Sending error: %s", message)
        await self.websocket.send_json({"type": "error", "message": message})

    # -------------------------------------------------------------- metrics

    def _record_phrase_timings(self, text: str) -> None:
        """Close the phrase's metrics and publish them.

        The reference point is when the client sent the phrase, which is RNF-DES-01's
        "user's send confirmation": the clock starts when the order was given, not
        when some internal stage happened to notice it.
        """
        if self._phrase_started_at is None:
            return

        total_ms = (time.monotonic() - self._phrase_started_at) * 1000
        metrics.counter("rt_phrases_total")
        metrics.counter("rt_sentences_total", self._sentences_sent)
        metrics.counter("rt_glosses_total", self._glosses_sent)
        metrics.histogram("rt_phrase_total_ms", total_ms, "Ultima oración enviada menos frase recibida")
        metrics.gauge("rt_phrase_sentences", self._sentences_sent)

        logger.info(
            "phrase done: text=%r sentences=%d glosses=%d total=%.0fms",
            text,
            self._sentences_sent,
            self._glosses_sent,
            total_ms,
        )
        self._phrase_started_at = None
        self._first_segment_at = None
        self._sentences_sent = 0
        self._glosses_sent = 0