import asyncpg

from app.nlp.embedding_model import EmbeddingModel
from app.nlp.models import Fingerprint


def _format_vector(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


class SemanticCache:
    def __init__(
        self,
        database_url: str,
        embedding_model: EmbeddingModel,
        similarity_threshold: float,
    ) -> None:
        self._database_url = database_url
        self._embedding_model = embedding_model
        self._similarity_threshold = similarity_threshold

    async def lookup(self, text: str, fingerprint: Fingerprint) -> list[str] | None:
        embedding = self._embedding_model.embed(text)

        conn = await asyncpg.connect(self._database_url)
        try:
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
            await conn.close()

        if row is None or row["distance"] > self._similarity_threshold:
            return None

        return list(row["glosses"])
