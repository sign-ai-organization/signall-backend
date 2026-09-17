import asyncio

from fastapi import APIRouter, WebSocket

from app.config.settings import settings
from app.controller.controller import Controller
from app.controller.stt_service_client_impl import SttServiceClientImpl

router = APIRouter()


async def _forward_audio(websocket: WebSocket, controller: Controller) -> None:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            break

        chunk = message.get("bytes")
        if chunk is not None:
            await controller.handle_audio_chunk(chunk)


async def _forward_transcripts(controller: Controller) -> None:
    while True:
        result = await controller.stt_client.receive_transcript()
        if result is None:
            break

        text, is_final = result
        await controller.handle_transcript(text, is_final)


@router.websocket("/ws/translate")
async def translation_session(websocket: WebSocket) -> None:
    await websocket.accept()

    stt_client = SttServiceClientImpl(settings.stt_ws_url)
    await stt_client.connect()
    controller = Controller(websocket, websocket.app.state.orchestrator, stt_client)

    try:
        await asyncio.gather(
            _forward_audio(websocket, controller),
            _forward_transcripts(controller),
        )
    finally:
        await stt_client.close()
