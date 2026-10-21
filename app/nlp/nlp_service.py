from abc import ABC, abstractmethod

from app.domain.models import Segment


class NLPService(ABC):
    @abstractmethod
    async def transform(self, text: str) -> list[Segment]:
        raise NotImplementedError

    @abstractmethod
    def split(self, text: str) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    async def transform_sentence(self, sentence: str) -> Segment:
        raise NotImplementedError
