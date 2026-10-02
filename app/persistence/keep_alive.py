import asyncio
import contextlib
import logging
import time

import asyncpg

logger = logging.getLogger(__name__)


class DatabaseKeepAlive:
    """Keeps a scale-to-zero database (Neon) awake only while there has been
    recent activity, so idle backends let it suspend and stop using compute.
    """

    def __init__(self, pool: asyncpg.Pool, interval_seconds: float, idle_window_seconds: float) -> None:
        self._pool = pool
        self._interval_seconds = interval_seconds
        self._idle_window_seconds = idle_window_seconds
        self._last_activity = float("-inf")
        self._loop_task: asyncio.Task | None = None
        self._wake_up_tasks: set[asyncio.Task] = set()

    def start(self) -> None:
        # Startup counts as activity: the client usually connects a while
        # after the backend comes up, and the pool just woke the database.
        self.mark_activity()
        if self._interval_seconds > 0:
            self._loop_task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        tasks = [*self._wake_up_tasks, *([self._loop_task] if self._loop_task else [])]
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task

    def mark_activity(self) -> None:
        self._last_activity = time.monotonic()

    def wake_up(self) -> None:
        """Marks activity and pings right away, without waiting for the result,
        so the database starts resuming while the user begins to speak."""
        self.mark_activity()
        task = asyncio.create_task(self._ping())
        self._wake_up_tasks.add(task)
        task.add_done_callback(self._wake_up_tasks.discard)

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._interval_seconds)
            if self._is_recently_active():
                await self._ping()

    def _is_recently_active(self) -> bool:
        return time.monotonic() - self._last_activity < self._idle_window_seconds

    async def _ping(self) -> None:
        try:
            await self._pool.fetchval("SELECT 1")
        except Exception:
            logger.warning("Database keep-alive ping failed", exc_info=True)
