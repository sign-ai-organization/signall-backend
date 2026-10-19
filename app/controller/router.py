import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket

from app.config.settings import settings
from app.controller.controller import Controller
from app.controller.stt_service_client_impl import SttServiceClientImpl
from app.metrics import metrics
from app.persistence.keep_alive import DatabaseKeepAlive

logger = logging.getLogger(__name__)

router = APIRouter()

TEXT_FRAME = "text"
END_FRAME = "end"


def _parse_client_frame(raw: str) -> tuple[str, str] | None:
    """Classify a text frame from the client, or None when it is not one.

    The Android client sends `{"type":"text","text":"<phrase>"}` for a phrase
    typed instead of spoken, and `{"type":"end"}` when the user releases the
    microphone. Returns `(kind, payload)` where payload is the phrase for
    `text` and empty for `end`.

    Anything else — malformed JSON, a non-object, an unknown type, an empty
    phrase — is ignored rather than turned into an error the user cannot act
    on. The client is free to send whatever it likes; an unknown frame must not
    end the session.
    """
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    kind = payload.get("type")
    if kind == END_FRAME:
        return (END_FRAME, "")
    if kind != TEXT_FRAME:
        return None

    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        return None

    return (TEXT_FRAME, text.strip())


class _PhraseTranslator:
    """Runs each phrase translation on its own task, one at a time and in order.

    Translating inline meant that while the pipeline ran, the read loop was not
    draining the client's socket — and that socket is also the microphone's only
    way in. The audio was not lost, it waited: measured with
    `tools/verificar-bloqueo-lectura.py`, a 1091 ms translation left 991 ms of
    the user's voice invisible to the STT, which then pushes the closing of every
    phrase back by the same amount. `rt_read_loop_busy_ms` is the guard.

    One at a time, and in order, is what the client already assumes: it never
    puts two phrases in flight (`MainScreenState.requestTranslation` and
    `sendLivePhrase` both refuse), so interleaving cannot happen. The lock is
    not an optimisation that is left out for speed — it is the guarantee that a
    second phrase, if one ever arrives, waits its turn instead of reordering the
    sentences' `index` values and making the avatar play the phrase backwards.
    """

    def __init__(self, controller: Controller) -> None:
        self._controller = controller
        self._lock = asyncio.Lock()
        self._tasks: set[asyncio.Task[None]] = set()

    def submit(self, text: str) -> None:
        """Start translating [text] without waiting for it."""
        task = asyncio.create_task(self._translate(text), name="translate-phrase")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _translate(self, text: str) -> None:
        async with self._lock:
            await self._controller.handle_text(text)

    def cancel_all(self) -> list[asyncio.Task[None]]:
        """Cancel every translation still in flight and return the tasks."""
        pending = list(self._tasks)
        for task in pending:
            task.cancel()
        return pending


async def _forward_audio(
    websocket: WebSocket,
    controller: Controller,
    translator: _PhraseTranslator,
) -> None:
    """Drain the client socket: audio to the STT, phrases to the translator.

    This loop is the session's read path **and** the microphone's only way in.
    Anything that runs here is time in which the user's voice is sitting in a
    socket instead of reaching the STT, and the STT closes a phrase by counting
    the silence it receives — so the delay does not go away, it pushes the
    closing of every phrase back by the same amount.

    Phrases go to [translator] instead of being awaited here, so the audio keeps
    flowing while the language model works.

    `rt_read_loop_busy_ms` is the guard: it times the work done per frame —
    forwarding a chunk, parsing a control frame. Forwarding a chunk costs a few
    hundred microseconds, and that is what it should say; the translation, which
    used to land on this number in full, now happens elsewhere.
    """
    while True:
        message = await websocket.receive()
        busy_since = time.perf_counter()

        if message["type"] == "websocket.disconnect":
            break

        chunk = message.get("bytes")
        if chunk is not None:
            await controller.handle_audio_chunk(chunk)
            metrics.histogram(*_busy(busy_since))
            continue

        raw = message.get("text")
        if raw is None:
            metrics.histogram(*_busy(busy_since))
            continue

        frame = _parse_client_frame(raw)
        if frame is None:
            metrics.histogram(*_busy(busy_since))
            continue

        kind, payload = frame
        if kind == TEXT_FRAME:
            translator.submit(payload)
        else:
            await controller.handle_end()
        metrics.histogram(*_busy(busy_since))


def _busy(since: float) -> tuple[str, float, str]:
    return (
        "rt_read_loop_busy_ms",
        (time.perf_counter() - since) * 1000,
        "Trabajo del bucle de lectura por frame, sin contar la espera",
    )


async def _forward_transcripts(controller: Controller, db_keep_alive: DatabaseKeepAlive) -> None:
    while True:
        result = await controller.stt_client.receive_transcript()
        if result is None:
            break

        text, is_final = result
        if is_final:
            db_keep_alive.mark_activity()
        await controller.handle_transcript(text, is_final)


@router.websocket("/ws/translate")
async def translation_session(websocket: WebSocket) -> None:
    await websocket.accept()

    db_keep_alive: DatabaseKeepAlive = websocket.app.state.db_keep_alive
    db_keep_alive.wake_up()

    stt_client = SttServiceClientImpl(settings.stt_ws_url)
    controller = Controller(
        websocket,
        websocket.app.state.orchestrator,
        stt_client,
        debug_trace_enabled=settings.debug_trace_enabled,
    )
    translator = _PhraseTranslator(controller)

    metrics.gauge("sessions_active", metrics.gauge_value("sessions_active") + 1)
    metrics.counter("sessions_total")

    try:
        await stt_client.connect()
    except Exception:
        logger.exception("Could not connect to the STT service")
        await _try_send_error(controller, "El servicio de transcripción no está disponible.")
        metrics.gauge("sessions_active", max(0.0, metrics.gauge_value("sessions_active") - 1))
        return

    # The two halves of a session: the client's socket and the STT's. Neither one
    # can finish on its own — `_forward_audio` only ends when the client goes
    # away, and `_forward_transcripts` blocks in `receive()` waiting for a
    # message from the STT that will never come — so whichever ends first ends
    # the session, and the other is cancelled.
    #
    # `asyncio.gather` waited for *both* and so never returned: the `finally`
    # that closes the STT socket never ran, and every session left its connection
    # open forever. Measured with `tools/verificar-conexiones-stt.py`: 10
    # sessions, 20 connections that never came back.
    audio_task = asyncio.create_task(
        _forward_audio(websocket, controller, translator),
        name="client-audio",
    )
    transcript_task = asyncio.create_task(
        _forward_transcripts(controller, db_keep_alive),
        name="stt-transcripts",
    )

    try:
        await asyncio.wait({audio_task, transcript_task}, return_when=asyncio.FIRST_COMPLETED)
    except Exception:
        logger.exception("Translation session failed")
        await _try_send_error(controller, "Ocurrió un error inesperado durante la sesión.")
    finally:
        translations = translator.cancel_all()
        for task in (audio_task, transcript_task, *translations):
            task.cancel()
        await asyncio.gather(
            audio_task,
            transcript_task,
            *translations,
            return_exceptions=True,
        )
        await stt_client.close()
        metrics.gauge("sessions_active", max(0.0, metrics.gauge_value("sessions_active") - 1))


async def _try_send_error(controller: Controller, message: str) -> None:
    try:
        await controller.send_error(message)
    except Exception:
        logger.exception("Could not notify the client about the error")
