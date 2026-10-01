import asyncio
import contextvars
import logging

from app.domain.models import Segment
from app.nlp.gloss_analyzer import GlossAnalyzer
from app.nlp.llm_client import LLMClient
from app.nlp.models import Fingerprint
from app.nlp.nlp_service import NLPService
from app.nlp.semantic_cache import SemanticCache
from app.observability.pipeline_trace import set_trace_source, trace_step

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
        self._pending_stores: set[asyncio.Task] = set()

    async def transform(self, text: str) -> list[Segment]:
        with trace_step("fingerprint"):
            fingerprint = self.analyzer.analyze(text)

        glosses = await self.cache.lookup(text, fingerprint)
        if glosses is None:
            logger.info("SemanticCache MISS for %r -> calling LLM", text)
            set_trace_source("llm")
            with trace_step("llm"):
                glosses = await self.llm_client.transform(text)
            self._store_in_background(text, fingerprint, glosses)
        else:
            logger.info("SemanticCache HIT for %r", text)
            set_trace_source("cache")

        return [self._build_segment(fingerprint, glosses)]

    async def wait_for_pending_stores(self) -> None:
        await asyncio.gather(*self._pending_stores, return_exceptions=True)

    def _store_in_background(self, text: str, fingerprint: Fingerprint, glosses: list[str]) -> None:
        # Storing is not part of answering the user, so it runs after the
        # result is returned. A fresh context keeps its timings out of the
        # pipeline trace, which has already been sent by then.
        task = asyncio.create_task(
            self._store(text, fingerprint, glosses),
            context=contextvars.Context(),
        )
        self._pending_stores.add(task)
        task.add_done_callback(self._pending_stores.discard)

    async def _store(self, text: str, fingerprint: Fingerprint, glosses: list[str]) -> None:
        try:
            await self.cache.store(text, fingerprint, glosses)
        except Exception:
            logger.exception("SemanticCache store failed for %r", text)

    def _build_segment(self, fingerprint: Fingerprint, glosses: list[str]) -> Segment:
        return Segment(type=fingerprint.category, glosses=glosses)
