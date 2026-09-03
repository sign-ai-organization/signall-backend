from abc import ABC, abstractmethod

from app.domain.models import Segment, ValidatedSegment


class ValidatorService(ABC):
    @abstractmethod
    def validate(self, segments: list[Segment]) -> list[ValidatedSegment]:
        raise NotImplementedError
