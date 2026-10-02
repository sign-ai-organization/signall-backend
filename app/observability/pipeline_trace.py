"""Per-request timing instrumentation for the translation pipeline.

The active trace lives in a ContextVar so components can record steps
without adding instrumentation parameters to their SDD signatures. When no
trace is active, recording is a no-op.
"""

import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator


class PipelineTrace:
    def __init__(self) -> None:
        self.source: str | None = None
        self.steps_ms: dict[str, float] = {}

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        started_at = time.perf_counter()
        try:
            yield
        finally:
            # A step repeats once per sentence: report the total.
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            self.steps_ms[name] = self.steps_ms.get(name, 0.0) + elapsed_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "steps_ms": {name: round(ms, 1) for name, ms in self.steps_ms.items()},
        }


_current_trace: ContextVar[PipelineTrace | None] = ContextVar("pipeline_trace", default=None)


@contextmanager
def start_trace() -> Iterator[PipelineTrace]:
    trace = PipelineTrace()
    token = _current_trace.set(trace)
    try:
        yield trace
    finally:
        _current_trace.reset(token)


@contextmanager
def trace_step(name: str) -> Iterator[None]:
    trace = _current_trace.get()
    if trace is None:
        yield
        return

    with trace.step(name):
        yield


def set_trace_source(source: str) -> None:
    trace = _current_trace.get()
    if trace is None:
        return
    # Sentences of one text may come from different sources (cache and LLM).
    trace.source = source if trace.source in (None, source) else "mixed"
