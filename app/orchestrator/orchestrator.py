from app.domain.models import ValidatedSegment
from app.nlp.nlp_service import NLPService
from app.validation.validator_service import ValidatorService


class Orchestrator:
    def __init__(self, nlp_service: NLPService, validator_service: ValidatorService) -> None:
        self.nlp_service = nlp_service
        self.validator_service = validator_service

    async def translate(self, text: str) -> list[ValidatedSegment]:
        segments = await self.nlp_service.transform(text)
        return self.validator_service.validate(segments)
