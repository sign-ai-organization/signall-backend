import asyncio
import logging

from fastapi import APIRouter, WebSocket

from app.config.settings import settings
from app.controller.controller import Controller
from app.controller.stt_service_client_impl import SttServiceClientImpl
from app.persistence.keep_alive import DatabaseKeepAlive

logger = logging.getLogger(__name__)

router = APIRouter()


async def _forward_audio(websocket: WebSocket, controller: Controller) -> None:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            break

        chunk = message.get("bytes")
        if chunk is not None:
            await controller.handle_audio_chunk(chunk)


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

    try:
        await stt_client.connect()
    except Exception:
        logger.exception("Could not connect to the STT service")
        await _try_send_error(controller, "El servicio de transcripción no está disponible.")
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


async def _try_send_error(controller: Controller, message: str) -> None:
    try:
        await controller.send_error(message)
    except Exception:
        logger.exception("Could not notify the client about the error")
