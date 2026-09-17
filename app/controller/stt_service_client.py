from abc import ABC, abstractmethod


class SttServiceClient(ABC):
    @abstractmethod
    async def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def send_audio(self, chunk: bytes) -> None:
        raise NotImplementedError

    @abstractmethod
    async def receive_transcript(self) -> tuple[str, bool] | None:
        """Returns (text, is_final), or None if the connection closed."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError
