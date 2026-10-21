from app.domain.models import Gloss, Segment, ValidatedSegment
from app.validation.catalog_repository import CatalogRepository
from app.validation.validator_service import ValidatorService


class ValidatorServiceImpl(ValidatorService):
    def __init__(self, catalog_repository: CatalogRepository) -> None:
        self.catalog_repository = catalog_repository

    def validate(self, segments: list[Segment]) -> list[ValidatedSegment]:
        return [self._validate_segment(segment) for segment in segments]

    def _validate_segment(self, segment: Segment) -> ValidatedSegment:
        glosses = [self._validate_gloss(gloss) for gloss in segment.glosses]
        return ValidatedSegment(type=segment.type, glosses=glosses)

    def _validate_gloss(self, gloss: str) -> Gloss:
        entry = self.catalog_repository.search(gloss)
        if entry is None:
            return Gloss(text=gloss, available=False)
        return Gloss(
            text=gloss,
            available=True,
            glb_path=entry.glb_path,
            semantic_category=entry.semantic_category,
        )
