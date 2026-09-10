from abc import ABC, abstractmethod

from app.domain.models import Segment


class NLPService(ABC):
    @abstractmethod
    async def transform(self, text: str) -> list[Segment]:
        raise NotImplementedError
