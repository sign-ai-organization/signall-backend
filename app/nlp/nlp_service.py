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

    @abstractmethod
    async def transform_with_context(self, text: str, context: str) -> Segment:
        """Translate `text` knowing what came before it in the same utterance.

        The real-time path sends short fragments that are not sentences on their
        own ("estudiante", "vivo en"). Given to the model alone, it answers them
        as if they were: "estudiante" came out as NIÑO, a wrong sign the avatar
        would happily play. With context it keeps the meaning and still returns
        only the new part.
        """
        raise NotImplementedError