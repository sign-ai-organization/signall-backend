import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator


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

    sentence = {"text": text, "source": None, "steps_ms": {}}
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
