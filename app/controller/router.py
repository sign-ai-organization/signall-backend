import asyncio
import json
import logging

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


async def _forward_audio(websocket: WebSocket, controller: Controller) -> None:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            break

        chunk = message.get("bytes")
        if chunk is not None:
            await controller.handle_audio_chunk(chunk)
            continue

        raw = message.get("text")
        if raw is None:
            continue

        frame = _parse_client_frame(raw)
        if frame is None:
            continue

        kind, payload = frame
        if kind == TEXT_FRAME:
            await controller.handle_text(payload)
        else:
            await controller.handle_end()


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

    metrics.gauge("sessions_active", metrics.counter_value("sessions_active") + 1)
    metrics.counter("sessions_total")

    try:
        await stt_client.connect()
    except Exception:
        logger.exception("Could not connect to the STT service")
        await _try_send_error(controller, "El servicio de transcripción no está disponible.")
        metrics.gauge("sessions_active", max(0.0, metrics.counter_value("sessions_active") - 1))
        return

    try:
        await asyncio.gather(
            _forward_audio(websocket, controller),
            _forward_transcripts(controller, db_keep_alive),
        )
    except Exception:
        logger.exception("Translation session failed")
        await _try_send_error(controller, "Ocurrió un error inesperado durante la sesión.")
    finally:
        await stt_client.close()
        metrics.gauge("sessions_active", max(0.0, metrics.counter_value("sessions_active") - 1))


async def _try_send_error(controller: Controller, message: str) -> None:
    try:
        await controller.send_error(message)
    except Exception:
        logger.exception("Could not notify the client about the error")
