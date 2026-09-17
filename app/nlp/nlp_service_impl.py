import logging

from app.domain.models import Segment
from app.nlp.gloss_analyzer import GlossAnalyzer
from app.nlp.llm_client import LLMClient
from app.nlp.models import Fingerprint
from app.nlp.nlp_service import NLPService
from app.nlp.semantic_cache import SemanticCache

logger = logging.getLogger(__name__)


class NLPServiceImpl(NLPService):
    def __init__(
        self,
        analyzer: GlossAnalyzer,
        cache: SemanticCache,
        llm_client: LLMClient,
    ) -> None:
        self.analyzer = analyzer
        self.cache = cache
        self.llm_client = llm_client

    async def transform(self, text: str) -> list[Segment]:
        fingerprint = self.analyzer.analyze(text)

        glosses = await self.cache.lookup(text, fingerprint)
        if glosses is None:
            logger.info("SemanticCache MISS for %r -> calling LLM", text)
            glosses = self.llm_client.transform(text)
            await self.cache.store(text, fingerprint, glosses)
        else:
            logger.info("SemanticCache HIT for %r", text)

        return [self._build_segment(fingerprint, glosses)]

    def _build_segment(self, fingerprint: Fingerprint, glosses: list[str]) -> Segment:
        return Segment(type=fingerprint.category, glosses=glosses)
