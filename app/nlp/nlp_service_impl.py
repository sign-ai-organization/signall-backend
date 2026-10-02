import asyncio
import contextvars
import logging

from app.domain.models import Segment
from app.nlp.gloss_analyzer import GlossAnalyzer
from app.nlp.llm_client import LLMClient
from app.nlp.models import Fingerprint
from app.nlp.nlp_service import NLPService
from app.nlp.segmenter import SentenceSegmenter
from app.nlp.semantic_cache import SemanticCache
from app.observability.pipeline_trace import set_trace_source, trace_sentence, trace_step

logger = logging.getLogger(__name__)


class NLPServiceImpl(NLPService):
    def __init__(
        self,
        analyzer: GlossAnalyzer,
        cache: SemanticCache,
        llm_client: LLMClient,
        segmenter: SentenceSegmenter | None,
    ) -> None:
        self.analyzer = analyzer
        self.cache = cache
        self.llm_client = llm_client
        # None = segmenter disabled: the whole text is translated as one sentence.
        self.segmenter = segmenter
        self._pending_stores: set[asyncio.Task] = set()

    async def transform(self, text: str) -> list[Segment]:
        return [await self.transform_sentence(sentence) for sentence in self.split(text)]

    def split(self, text: str) -> list[str]:
        return self.segmenter.segment(text) if self.segmenter else [text]

    async def transform_sentence(self, sentence: str) -> Segment:
        with trace_sentence(sentence):
            return await self._transform_sentence(sentence)

    async def wait_for_pending_stores(self) -> None:
        await asyncio.gather(*self._pending_stores, return_exceptions=True)

    async def _transform_sentence(self, sentence: str) -> Segment:
        with trace_step("fingerprint"):
            fingerprint = self.analyzer.analyze(sentence)

        glosses = await self.cache.lookup(sentence, fingerprint)
        if glosses is None:
            logger.info("SemanticCache MISS for %r -> calling LLM", sentence)
            set_trace_source("llm")
            with trace_step("llm"):
                glosses = await self.llm_client.transform(sentence)
            self._store_in_background(sentence, fingerprint, glosses)
        else:
            logger.info("SemanticCache HIT for %r", sentence)
            set_trace_source("cache")

        return self._build_segment(fingerprint, glosses)

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
