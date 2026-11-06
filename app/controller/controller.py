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
from typing import Any

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
        audio_max_chunk_bytes: int = 32768,
    ) -> None:
        self.websocket = websocket
        self.orchestrator = orchestrator
        self.stt_client = stt_client
        self.debug_trace_enabled = debug_trace_enabled
        self.audio_max_chunk_bytes = audio_max_chunk_bytes
        self._audio_bytes = 0
        self._audio_chunks = 0
        self._audio_rms_total = 0.0
        self._phrase_started_at: float | None = None
        self._first_segment_at: float | None = None
        self._sentences_sent = 0
        self._glosses_sent = 0
        # The client's own identifier for the phrase being translated. It is
        # opaque: the backend does not parse it, does not compare it and does
        # not generate it. It only copies it into the frames it sends back.
        self._turn: Any = None

    # ----------------------------------------------------------------- audio

    async def handle_audio_chunk(self, chunk: bytes) -> bool:
        """Forward one chunk of client audio to the STT, untouched.

        The bytes go across exactly as they arrived: no resampling, no header,
        no framing. Reassembling into the 30 ms units the VAD works on is the
        STT's job.

        RNF-SEC-02: the chunk is checked before it is forwarded. An empty
        chunk, an odd number of bytes (PCM16 samples are two bytes each) or a
        chunk bigger than `audio_max_chunk_bytes` is not a capture fragment, and
        forwarding it pushes garbage into the STT or lets one client make the
        backend send an arbitrary amount of data. The caller closes the session
        when this returns False; the reason is counted in
        `audio_chunks_rejected_total`.

        Returns True when the chunk was forwarded.
        """
        reason = self._audio_chunk_rejection(chunk)
        if reason is not None:
            metrics.counter("audio_chunks_rejected_total", labels={"reason": reason})
            logger.warning("Rejected audio chunk: reason=%s bytes=%d", reason, len(chunk))
            return False

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
        return True

    def _audio_chunk_rejection(self, chunk: bytes) -> str | None:
        """The reason a chunk is not acceptable, or None when it is.

        Kept as a separate method so the three rules can be read on their own
        and the reason travels as a metric label instead of a log the operator
        has to count by hand.
        """
        if not chunk:
            return "empty"
        if len(chunk) % 2:
            return "odd_length"
        if len(chunk) > self.audio_max_chunk_bytes:
            return "too_large"
        return None

    def audio_stats(self) -> tuple[int, float]:
        """(bytes, mean rms) captured in this session. For tests and diagnosis."""
        return self._audio_bytes, self._audio_rms_total / max(1, self._audio_chunks)

    # ---------------------------------------------------------------- phrases

    async def handle_text(self, text: str, turn: Any = None) -> None:
        """Translate one phrase. The only translation trigger in the system.

        Whether the phrase was typed, dictated, or dictated in live mode is the
        client's business and makes no difference here: a phrase that arrives as
        `text` is a phrase to translate. It goes through
        `Orchestrator.translate_stream`, which splits it into sentences and
        yields them in order with a real `index` and `total`.

        `turn` is the client's identifier for this phrase. The backend copies it
        into every frame it sends for this phrase and does nothing else with
        it: it never parses it, never compares it and never makes one up. A
        client that does not send one gets frames without it, exactly as
        before.

        **No echoed transcript.** A `transcript` frame means one thing only: the
        STT transcribed audio. Echoing the phrase back as a `final` transcript
        used to be harmless because the backend decided what to translate, but
        now the client does —it re-sends each closed phrase by itself in live
        mode— and an echo is indistinguishable from a voice transcript. The client
        took its own phrase for something the STT had heard, sent it again, and
        the two sides translated the same phrase a few hundred times a minute.
        The client already has the text: it is the one that sent it.
        """
        self._phrase_started_at = time.monotonic()
        self._first_segment_at = None
        self._sentences_sent = 0
        self._glosses_sent = 0
        self._turn = turn

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
                # The turn is closed even when it failed. The client waits for
                # the `done` to know the phrase is over, and without it the app
                # waits out its own timeout and then reports a failure that
                # already happened.
                await self.send_done()
                self._phrase_started_at = None
                self._turn = None
                return

        logger.info("Pipeline trace for %r: %s", text, trace.to_dict())
        if self.debug_trace_enabled:
            await self.websocket.send_json({"type": "trace", "steps_ms": trace.to_dict()["steps_ms"]})
        await self.send_done()
        self._record_phrase_timings(text, trace)
        self._turn = None

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
            # The source says where the answer came from, and it is what turns
            # one latency into the two the SRS asks for: the one of a phrase
            # the cache resolved and the one of a phrase that needed the
            # model. Without it the two scenarios only live apart in the log,
            # and `/metrics` shows their average, which is neither.
            labels = {"source": trace.sentence_source(index) or "unknown"}
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
                    labels,
                )
            metrics.histogram(
                "rt_sentence_delay_ms",
                since_phrase_ms,
                "Oración enviada menos frase recibida",
                labels,
            )
        self._sentences_sent += 1
        self._glosses_sent += len(segment.glosses)

        logger.info("Sending segment %d/%d: %s", index + 1, total, segment)
        if self.debug_trace_enabled:
            await self.websocket.send_json({"type": "sentence_trace", "index": index, **trace.sentence_dict(index)})
        await self.websocket.send_json(
            self._with_turn(
                {"type": "segment", "index": index, "total": total, "segment": segment.model_dump(mode="json")}
            )
        )

    async def send_done(self) -> None:
        """Close the phrase, whether it was translated or it failed."""
        await self.websocket.send_json(self._with_turn({"type": "done"}))

    async def send_error(self, message: str) -> None:
        logger.info("Sending error: %s", message)
        await self.websocket.send_json(self._with_turn({"type": "error", "message": message}))

    async def send_capability(self, audio: bool, reason: str | None = None) -> None:
        """Say what this session can do, without closing it.

        `RNF-AV-03`: when the transcription service is down the client must keep
        translating text. Closing the socket told the app "no connection" and it
        stopped accepting text too, which is the failure this frame replaces.
        The frame is additive: an older client ignores the unknown type, and an
        older backend simply never sends it.
        """
        frame: dict[str, Any] = {"type": "capability", "audio": audio}
        if reason:
            frame["reason"] = reason
        await self.websocket.send_json(frame)

    def _with_turn(self, frame: dict[str, Any]) -> dict[str, Any]:
        """Add the client's turn identifier to a frame, when there is one.

        The identifier travels as it came: the backend does not read it, does
        not compare it and does not generate it. A client that sends none gets
        frames without the field, exactly as before, and a client that sends
        one gets it back on every frame of that phrase.
        """
        if self._turn is None:
            return frame
        return {**frame, "turn": self._turn}

    # -------------------------------------------------------------- metrics

    def _record_phrase_timings(self, text: str, trace: PipelineTrace) -> None:
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
        metrics.histogram(
            "rt_phrase_total_ms",
            total_ms,
            "Ultima oración enviada menos frase recibida",
            {"source": trace.phrase_source()},
        )
        # A histogram, not a gauge: the question it answers is how the
        # sentences are distributed across phrases, and a gauge only holds the
        # last one. The SDD has always described it as a histogram.
        metrics.histogram(
            "rt_phrase_sentences",
            float(self._sentences_sent),
            "Oraciones por frase",
        )

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
