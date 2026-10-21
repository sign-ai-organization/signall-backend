import logging

import spacy

from app.config.sentence_segmenter import SentenceSegmenterSettings
from app.nlp.segmenter._clauses import split_by_clauses
from app.nlp.segmenter._discourse_markers import split_by_markers
from app.nlp.segmenter._post_processing import post_process
from app.nlp.segmenter._punctuation import split_by_punctuation
from app.nlp.text_normalizer import normalized_words
from app.observability.pipeline_trace import trace_step

logger = logging.getLogger(__name__)

# Only POS tags and morphology are needed.
_EXCLUDED_PIPES = ["parser", "ner", "lemmatizer", "senter"]
_SENTENCE_MARKS = set(".?!¿¡…")
_WARM_UP_TEXT = "hola cómo está me llamo carlos y tengo treinta años"


class SentenceSegmenter:
    def __init__(self, config: SentenceSegmenterSettings) -> None:
        self._config = config
        self._nlp = spacy.load(config.spacy_model, exclude=_EXCLUDED_PIPES)
        # The first call is much slower than the rest: pay it at startup.
        self.segment(_WARM_UP_TEXT)

    def segment(self, text: str) -> list[str]:
        with trace_step("segmentation"):
            sentences = post_process(self._split(text), self._config)
        logger.info("Segmented %r into %d sentence(s)", text, len(sentences))
        return sentences

    def _split(self, text: str) -> list[str]:
        if not any(c in _SENTENCE_MARKS for c in text):
            return self._split_unpunctuated(text)

        fragments: list[str] = []
        for fragment in split_by_punctuation(text, self._config):
            if len(normalized_words(fragment)) >= self._config.reprocess_min_words:
                fragments.extend(self._split_unpunctuated(fragment))
            else:
                fragments.append(fragment)
        return fragments

    def _split_unpunctuated(self, text: str) -> list[str]:
        by_markers = split_by_markers(text, self._config)
        return [
            clause
            for fragment in by_markers
            for clause in split_by_clauses(fragment, self._nlp, self._config)
        ]
