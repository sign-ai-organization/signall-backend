"""Caché semántico de frases -> glosas, resident en memoria.

Por qué cambió
--------------

La versión anterior preguntaba a Neon en cada `lookup`. Medido en este proyecto,
un viaje a Neon cuesta ~100 ms y el `lookup` completo se llevaba ~200 ms con el
acquire y el release: **el caché era más lento que el LLM que estaba evitando**.
Para el modo frase-por-frase eso se tolera; para tiempo real, donde el objetivo
es que el avatar empiece aSigning dentro del primer medio segundo, no.

Ahora la tabla se carga completa al arrancar y la búsqueda es distancia coseno
en memoria. En Neon solo se escribe, y en segundo plano.

El caché es derivado: se reconstruye con la primera frase de cada una. Perderlo
no pierde información, solo obliga a volver a llamar al LLM.
"""

import asyncio
import logging

import asyncpg
import numpy as np

from app.nlp.embedding_model import EmbeddingModel
from app.nlp.models import Fingerprint
from app.nlp.text_normalizer import normalize
from app.observability.pipeline_trace import trace_step

logger = logging.getLogger(__name__)


def _format_vector(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


class _PhraseTypeIndex:
    """Filas de un solo `phrase_type`, con la matriz de embeddings al lado.

    Se particiona por tipo porque la consulta original filtraba por
    `phrase_type`: mezclar tipos haría que "cómo estás" (pregunta) encontrara
    cerca "bien" (afirmativo) solo por parecido léxico.
    """

    __slots__ = ("vectors", "glosses", "exact")

    def __init__(self) -> None:
        self.vectors: np.ndarray = np.zeros((0, 0), dtype=np.float32)
        self.glosses: list[list[str]] = []
        # texto normalizado -> índice de fila. El atajo exacto evita incluso
        # calcular el embedding, que son 12-25 ms de CPU.
        self.exact: dict[str, int] = {}

    def add(self, normalized: str, vector: np.ndarray, glosses: list[str]) -> None:
        if normalized in self.exact:
            row = self.exact[normalized]
            self.glosses[row] = glosses
            self.vectors[row] = vector
            return

        row = len(self.glosses)
        self.exact[normalized] = row
        self.glosses.append(glosses)
        if self.vectors.size == 0:
            self.vectors = vector.reshape(1, -1)
        else:
            self.vectors = np.vstack([self.vectors, vector])

    def nearest(self, vector: np.ndarray) -> tuple[list[str], float] | None:
        if not self.glosses:
            return None

        # Los embeddings de sentence-transformers ya vienen normalizados, así que
        # el producto punto es la similitud del coseno y la distancia 1 - punto.
        similarity = self.vectors @ vector
        best = int(np.argmax(similarity))
        return self.glosses[best], float(1.0 - similarity[best])


class SemanticCache:
    def __init__(
        self,
        pool: asyncpg.Pool,
        embedding_model: EmbeddingModel,
        similarity_threshold: float,
        preload: bool = True,
        max_rows: int = 20000,
    ) -> None:
        self._pool = pool
        self._embedding_model = embedding_model
        self._similarity_threshold = similarity_threshold
        self._preload = preload
        self._max_rows = max_rows
        self._indexes: dict[str, _PhraseTypeIndex] = {}
        self._lock = asyncio.Lock()
        self._rows = 0
        self._loaded = False

    async def load_all(self) -> None:
        """Carga la tabla en memoria. Best-effort: si falla, se sigue con Neon.

        Que el arranque no dependa de esto es deliberado. Un caché vacío solo
        cuesta una llamada al LLM por frase; un arranque que no arranca cuesta la
        sesión entera.
        """
        if not self._preload:
            logger.info("SemanticCache preload disabled; lookups go to Neon")
            return

        started = asyncio.get_running_loop().time()
        try:
            rows = await self._pool.fetch(
                """
                SELECT original_text, phrase_type, glosses, embedding::text AS embedding
                FROM semantic_cache
                ORDER BY id
                """
            )
        except Exception:
            logger.exception("could not preload semantic_cache; falling back to per-lookup queries")
            return

        loaded = 0
        for row in rows:
            try:
                vector = np.asarray(row["embedding"].strip("[]").split(","), dtype=np.float32)
            except ValueError:
                logger.warning("skipping malformed embedding for %r", row["original_text"])
                continue
            index = self._indexes.setdefault(row["phrase_type"], _PhraseTypeIndex())
            index.add(normalize(row["original_text"]), vector, list(row["glosses"]))
            loaded += 1

        self._rows = loaded
        self._loaded = True
        logger.info(
            "SemanticCache preloaded %d rows in %.0f ms", loaded, (asyncio.get_running_loop().time() - started) * 1000
        )

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def row_count(self) -> int:
        return self._rows

    async def lookup(self, text: str, fingerprint: Fingerprint) -> list[str] | None:
        """Glosas para `text`, o None si hay que preguntarle al LLM."""
        normalized = normalize(text)
        category = fingerprint.category.value

        if self._loaded:
            with trace_step("cache.exact"):
                index = self._indexes.get(category)
                if index is not None:
                    row = index.exact.get(normalized)
                    if row is not None:
                        return list(index.glosses[row])

            with trace_step("cache.embed"):
                embedding = await self._embed_async(normalized)
            vector = np.asarray(embedding, dtype=np.float32)

            with trace_step("cache.similarity"):
                index = self._indexes.get(category)
                match = index.nearest(vector) if index is not None else None

            if match is not None:
                glosses, distance = match
                if distance <= self._similarity_threshold:
                    return list(glosses)
            return None

        return await self._lookup_neon(normalized, category)

    async def store(self, text: str, fingerprint: Fingerprint, glosses: list[str]) -> None:
        normalized = normalize(text)
        category = fingerprint.category.value

        with trace_step("store.embed"):
            embedding = await self._embed_async(normalized)
        vector = np.asarray(embedding, dtype=np.float32)

        if self._loaded:
            async with self._lock:
                if self._rows < self._max_rows:
                    index = self._indexes.setdefault(category, _PhraseTypeIndex())
                    index.add(normalized, vector, list(glosses))
                    self._rows += 1
                else:
                    logger.warning(
                        "semantic_cache in memory is at the %d row cap; new phrases will miss until restart",
                        self._max_rows,
                    )

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
                    category,
                    glosses,
                    secondary_signals,
                    fingerprint.has_collision,
                )
        finally:
            with trace_step("store.release"):
                await self._pool.release(conn)

    async def _embed_async(self, text: str) -> list[float]:
        """Embebe fuera del bucle de eventos.

        `SentenceTransformer.encode` son 12-25 ms de CPU puro. En el modo frase
        completa eso era ruido; translating un fragmento cada 300 ms, bloquear el
        bucle 25 ms retarda también el audio entrante de todas las demás
        conexiones.
        """
        return await asyncio.to_thread(self._embedding_model.embed, text)

    async def _lookup_neon(self, normalized: str, category: str) -> list[str] | None:
        """Ruta vieja contra la base, para cuando no se pudo precargar."""
        with trace_step("cache.embed"):
            embedding = await self._embed_async(normalized)

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
                    category,
                )
        finally:
            with trace_step("cache.release"):
                await self._pool.release(conn)

        if row is None or row["distance"] > self._similarity_threshold:
            return None
        return list(row["glosses"])