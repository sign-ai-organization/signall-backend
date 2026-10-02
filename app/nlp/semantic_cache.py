import asyncpg

from app.nlp.embedding_model import EmbeddingModel
from app.nlp.models import Fingerprint
from app.observability.pipeline_trace import trace_step


def _format_vector(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


class SemanticCache:
    def __init__(
        self,
        pool: asyncpg.Pool,
        embedding_model: EmbeddingModel,
        similarity_threshold: float,
    ) -> None:
        self._pool = pool
        self._embedding_model = embedding_model
        self._similarity_threshold = similarity_threshold

    async def lookup(self, text: str, fingerprint: Fingerprint) -> list[str] | None:
        with trace_step("cache.embed"):
            embedding = self._embedding_model.embed(text)

        with trace_step("cache.acquire"):
            conn = await self._pool.acquire()
        try:
            with trace_step("cache.query"):
                row = await conn.fetchrow(
                    """
                    SELECT glosses, embedding <=> $1::vector AS distance
                    FROM semantic_cache
                    WHERE phrase_type = $2
                    ORDER BY embedding <=> $1::vector
                    LIMIT 1
                    """,
                    _format_vector(embedding),
                    fingerprint.category.value,
                )
        finally:
            with trace_step("cache.release"):
                await self._pool.release(conn)

        if row is None or row["distance"] > self._similarity_threshold:
            return None

        return list(row["glosses"])

    async def store(self, text: str, fingerprint: Fingerprint, glosses: list[str]) -> None:
        with trace_step("store.embed"):
            embedding = self._embedding_model.embed(text)
        secondary_signals = [signal.value for signal in fingerprint.secondary_signals]

        with trace_step("store.acquire"):
            conn = await self._pool.acquire()
        try:
            with trace_step("store.insert"):
                await conn.execute(
                    """
                    INSERT INTO semantic_cache
                        (original_text, embedding, phrase_type, glosses, secondary_signals, had_collision)
                    VALUES
                        ($1, $2::vector, $3, $4, $5, $6)
                    """,
                    text,
                    _format_vector(embedding),
                    fingerprint.category.value,
                    glosses,
                    secondary_signals,
                    fingerprint.has_collision,
                )
        finally:
            with trace_step("store.release"):
                await self._pool.release(conn)
