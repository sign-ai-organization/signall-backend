from app.controller.stt_service_client import SttServiceClient


class Controller:
    def __init__(self, stt_client: SttServiceClient) -> None:
        self.stt_client = stt_client

    async def handle_audio_chunk(self, chunk: bytes) -> None:
        await self.stt_client.send_audio(chunk)
