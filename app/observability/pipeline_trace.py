import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any


class PipelineTrace:
    def __init__(self) -> None:
        self.steps_ms: dict[str, float] = {}
        self.sentences: list[dict[str, Any]] = []

    def record(self, name: str, elapsed_ms: float) -> None:
        sentence = _current_sentence.get()
        steps = sentence["steps_ms"] if sentence is not None else self.steps_ms
        steps[name] = steps.get(name, 0.0) + elapsed_ms

    def sentence_dict(self, index: int) -> dict[str, Any]:
        sentence = self.sentences[index]
        return {"text": sentence["text"], "source": sentence["source"], "steps_ms": _rounded(sentence["steps_ms"])}

    def sentence_source(self, index: int) -> str | None:
        """Where the translation of sentence `index` came from.

        `cache` when the semantic cache answered it, `llm` when the language
        model did. The index is the one the orchestrator yields, and the
        sentences are appended in the order their tasks start, which is the
        order the tasks were created.

        A mismatch returns None instead of raising: a metric must never be the
        thing that breaks a translation.
        """
        if 0 <= index < len(self.sentences):
            return self.sentences[index]["source"]
        return None

    def phrase_source(self) -> str:
        """Where the phrase as a whole came from.

        A phrase is `llm` as soon as one of its sentences needed the model.
        That is the scenario the SRS asks to be measured apart from the cached
        one: a phrase whose first sentence came from the cache and whose second
        one did not still waited for the model to answer.
        """
        if any(sentence["source"] == "llm" for sentence in self.sentences):
            return "llm"
        return "cache"

    def to_dict(self) -> dict[str, Any]:
        return {
            "steps_ms": _rounded(self.steps_ms),
            "sentences": [self.sentence_dict(index) for index in range(len(self.sentences))],
        }


def _rounded(steps_ms: dict[str, float]) -> dict[str, float]:
    return {name: round(ms, 1) for name, ms in steps_ms.items()}


_current_trace: ContextVar[PipelineTrace | None] = ContextVar("pipeline_trace", default=None)
_current_sentence: ContextVar[dict[str, Any] | None] = ContextVar("pipeline_trace_sentence", default=None)


@contextmanager
def start_trace() -> Iterator[PipelineTrace]:
    trace = PipelineTrace()
    token = _current_trace.set(trace)
    try:
        yield trace
    finally:
        _current_trace.reset(token)


@contextmanager
def trace_sentence(text: str) -> Iterator[None]:
    trace = _current_trace.get()
    if trace is None:
        yield
        return

    sentence: dict[str, Any] = {"text": text, "source": None, "steps_ms": {}}
    trace.sentences.append(sentence)
    token = _current_sentence.set(sentence)
    try:
        yield
    finally:
        _current_sentence.reset(token)


@contextmanager
def trace_step(name: str) -> Iterator[None]:
    trace = _current_trace.get()
    if trace is None:
        yield
        return

    started_at = time.perf_counter()
    try:
        yield
    finally:
        trace.record(name, (time.perf_counter() - started_at) * 1000)


def set_trace_source(source: str) -> None:
    sentence = _current_sentence.get()
    if sentence is not None:
        sentence["source"] = source
