from abc import ABC, abstractmethod
from typing import Awaitable, Callable

from app.domain.models import Segment

# Optional debug hook: reports "cache" or "llm" once the source of the glosses is known.
SourceCallback = Callable[[str], Awaitable[None]]


class NLPService(ABC):
    @abstractmethod
    async def transform(self, text: str, on_source: SourceCallback | None = None) -> list[Segment]:
        raise NotImplementedError
