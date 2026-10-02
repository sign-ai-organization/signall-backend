from typing import AsyncIterator

from app.domain.models import ValidatedSegment
from app.nlp.nlp_service import NLPService
from app.observability.pipeline_trace import trace_step
from app.validation.validator_service import ValidatorService


class Orchestrator:
    def __init__(self, nlp_service: NLPService, validator_service: ValidatorService) -> None:
        self.nlp_service = nlp_service
        self.validator_service = validator_service

    async def translate(self, text: str) -> list[ValidatedSegment]:
        return [segment async for _, _, segment in self.translate_stream(text)]

    async def translate_stream(self, text: str) -> AsyncIterator[tuple[int, int, ValidatedSegment]]:
        """Yields (index, total, segment) as soon as each sentence is translated, in order."""
        sentences = self.nlp_service.split(text)
        for index, sentence in enumerate(sentences):
            segment = await self.nlp_service.transform_sentence(sentence)
            with trace_step("validation"):
                validated = self.validator_service.validate([segment])[0]
            yield index, len(sentences), validated
