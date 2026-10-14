import asyncio
import logging
from typing import AsyncIterator

from app.domain.models import ValidatedSegment
from app.nlp.nlp_service import NLPService
from app.observability.pipeline_trace import trace_step
from app.realtime.incremental import IncrementalTranslator
from app.validation.validator_service import ValidatorService

logger = logging.getLogger(__name__)


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

    def incremental_translator(self, **kwargs: int) -> IncrementalTranslator:
        """Un `IncrementalTranslator` ligado a la traducción de una oración.

        Se construye por sesión WebSocket, no por proceso: su estado (qué
        palabras ya se firmaron) es de la conversación que está teniendo esa
        conexión. Compartirlo haría que dos clientes se pisen las decisiones.
        """
        return IncrementalTranslator(self.translate_fragment, **kwargs)

    async def translate_fragment(self, text: str, context: str = "") -> ValidatedSegment:
        """Traduce y valida un fragmento, sin segmentar por oraciones.

        A diferencia de `translate_stream`, aquí no hay division de oraciones:
        el fragmento ya viene delimitado por la lógica incremental, y volver a
        partirlo con el segmentador produciría un `total` que no significa nada
        en un flujo donde el total se desconoce hasta el final.

        `context` es lo ya traducido del mismo utterance; ver
        `NLPService.transform_with_context`.
        """
        with trace_step("fragment.nlp"):
            # Siempre por `transform_with_context`, incluso sin contexto: esa
            # ruta usa coincidencia literal en el caché, que es lo único
            # defendible para un fragmento de una o dos palabras. Reusar
            # `transform_sentence` dejaría el primer fragmento del utterance
            # subjecto al matching por similitud, que con textos cortos produce
            # signs equivocados.
            segment = await self.nlp_service.transform_with_context(text, context)
        with trace_step("fragment.validation"):
            return self.validator_service.validate([segment])[0]