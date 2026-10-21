import asyncio
from collections.abc import AsyncIterator

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
        """Translates all sentences concurrently; yields (index, total, segment) in sentence order."""
        sentences = self.nlp_service.split(text)
        tasks = [asyncio.create_task(self._translate_sentence(sentence)) for sentence in sentences]
        try:
            for index, task in enumerate(tasks):
                yield index, len(tasks), await task
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
                elif not task.cancelled():
                    task.exception()

    async def _translate_sentence(self, sentence: str) -> ValidatedSegment:
        segment = await self.nlp_service.transform_sentence(sentence)
        with trace_step("validation"):
            return self.validator_service.validate([segment])[0]
