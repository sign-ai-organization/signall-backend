from fastapi import APIRouter, WebSocket

from app.config.settings import settings
from app.controller.controller import Controller
from app.controller.stt_service_client_impl import SttServiceClientImpl

router = APIRouter()


@router.websocket("/ws/translate")
async def translation_session(websocket: WebSocket) -> None:
    await websocket.accept()

    stt_client = SttServiceClientImpl(settings.stt_ws_url)
    await stt_client.connect()
    controller = Controller(stt_client)

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break

            chunk = message.get("bytes")
            if chunk is not None:
                await controller.handle_audio_chunk(chunk)
    finally:
        await stt_client.close()
