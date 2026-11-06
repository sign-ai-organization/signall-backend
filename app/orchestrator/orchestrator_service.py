"""The contract the controller depends on, not the class that implements it.

`Controller` used to import `Orchestrator` directly, because there was no other
option: `NLPService` and `ValidatorService` are abstract bases and the
orchestrator — the one that glues them — was not. That is fase 5 of the
implementation plan (TRA-01), and it is a mechanical change: the behaviour
stays exactly where it was.

Why it is worth the indirection at all: the controller is the WebSocket's own
code, and importing a concrete class from it makes the socket depend on how a
sentence is split and on which cache answered. With the interface in between,
the tests that replace the orchestrator with a double (`verify_client_frames`,
`verify_turn_id`, `verify_done_on_error`) describe the same thing the
production code asks for, instead of something shaped like one particular
implementation.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.domain.models import ValidatedSegment


class OrchestratorService(ABC):
    @abstractmethod
    async def translate(self, text: str) -> list[ValidatedSegment]:
        """Every sentence of `text`, translated and validated, in order."""
        raise NotImplementedError

    @abstractmethod
    def translate_stream(self, text: str) -> AsyncIterator[tuple[int, int, ValidatedSegment]]:
        """`(index, total, segment)` as each sentence is ready, in sentence order.

        Declared with `def` and not `async def` because the implementation is an
        async generator: what it returns is the iterator, not a coroutine that
        produces one.
        """
        raise NotImplementedError
