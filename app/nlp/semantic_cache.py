"""Semantic cache of phrase -> glosses, resident in memory.

Why it changed
--------------

The previous version asked Neon on every `lookup`. Measured in this project, a
trip to Neon costs ~100 ms and the whole `lookup` took ~200 ms with the acquire
and the release: **the cache was slower than the LLM it was avoiding.** That has
nothing to do with how fast the avatar is supposed to move — a cache that costs
more than a miss is a cache that is never worth consulting, whatever else is
happening in the pipeline.

So the table is loaded whole at start-up and the search is cosine distance in
memory. Neon is written to, and only in the background.

The cache is derived: it rebuilds itself from the first occurrence of each
phrase. Losing it loses no information, it only means calling the LLM again.
"""

import asyncio
import logging

import asyncpg
import numpy as np

from app.metrics import metrics
from app.nlp.embedding_model import EmbeddingModel
from app.nlp.models import Fingerprint
from app.nlp.text_normalizer import normalize, substitute_synonyms
from app.observability.pipeline_trace import trace_step
from app.persistence.database import RetryPolicy, run_with_retry

logger = logging.getLogger(__name__)


def _format_vector(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


def _unit(vector: np.ndarray) -> np.ndarray:
    """The vector scaled to length 1. A null vector is left as it is."""
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-12:
        return vector.astype(np.float32)
    return (vector / norm).astype(np.float32)


class _PhraseTypeIndex:
    """Rows of a single `phrase_type`, with the embedding matrix alongside.

    Partitioned by type because the original query filtered on `phrase_type`:
    mixing types would let "cómo estás" (a question) find "bien" (affirmative)
    close by on lexical resemblance alone.

    All vectors are stored **normalized to length 1**. This is not optional: the
    original query used pgvector's `<=>`, which normalizes on its own, and
    `SentenceTransformer.encode` returns unnormalized vectors. Without it, the
    dot product of a short phrase can exceed 1, the distance comes out negative
    and *everything* is a HIT.
    """

    __slots__ = ("vectors", "glosses", "exact")

    def __init__(self) -> None:
        self.vectors: np.ndarray = np.zeros((0, 0), dtype=np.float32)
        self.glosses: list[list[str]] = []
        # normalized text -> row. The exact shortcut avoids even computing the
        # embedding, which is 12-25 ms of CPU.
        self.exact: dict[str, int] = {}

    def add(self, normalized: str, vector: np.ndarray, glosses: list[str]) -> None:
        unit = _unit(vector)
        if normalized in self.exact:
            row = self.exact[normalized]
            self.glosses[row] = glosses
            self.vectors[row] = unit
            return

        row = len(self.glosses)
        self.exact[normalized] = row
        self.glosses.append(glosses)
        if self.vectors.size == 0:
            self.vectors = unit.reshape(1, -1)
        else:
            self.vectors = np.vstack([self.vectors, unit])

    def nearest(self, vector: np.ndarray) -> tuple[list[str], float] | None:
        if not self.glosses:
            return None

        # With both sides normalized, the dot product is cosine similarity and
        # the distance is 1 - dot, the same thing pgvector's `<=>` computes.
        similarity = self.vectors @ _unit(vector)
        best = int(np.argmax(similarity))
        return self.glosses[best], float(1.0 - similarity[best])


class SemanticCache:
    def __init__(
        self,
        pool: asyncpg.Pool | None,
        embedding_model: EmbeddingModel,
        similarity_threshold: float,
        preload: bool = True,
        max_rows: int = 20000,
        retry_policy: RetryPolicy | None = None,
        acquire_timeout_seconds: float = 5.0,
        synonym_pairs: list[tuple[str, str]] | None = None,
    ) -> None:
        # None means the database was unreachable at start-up: the cache then
        # lives only in memory and nothing is persisted.
        self._pool = pool
        self._embedding_model = embedding_model
        self._similarity_threshold = similarity_threshold
        self._preload = preload
        self._max_rows = max_rows
        self._retry_policy = retry_policy or RetryPolicy()
        self._acquire_timeout_seconds = acquire_timeout_seconds
        # `catalog_synonym`, folded into this cache's own normalization so
        # "tengo mucha hambre" and "tengo muy hambre" (MUY is a synonym of
        # MUCHO) land on the same key. CatalogRepository hands display
        # spellings; this is the layer that knows how its own keys are built.
        self._synonyms = {
            normalize(synonym): normalize(canonical) for synonym, canonical in (synonym_pairs or [])
        }
        self._indexes: dict[str, _PhraseTypeIndex] = {}
        self._lock = asyncio.Lock()
        self._rows = 0
        self._loaded = False

    async def load_all(self) -> None:
        """Load the table into memory. Best-effort: on failure, keep using Neon.

        Start-up deliberately does not depend on this. An empty cache costs one
        LLM call per phrase; a start-up that does not start costs the whole
        session.
        """
        if not self._preload:
            logger.info("SemanticCache preload disabled; lookups go to Neon")
            return

        pool = self._pool
        if pool is None:
            logger.warning("No database pool: the semantic cache starts empty and is not persisted")
            return

        started = asyncio.get_running_loop().time()
        try:
            rows = await self._fetch_rows(pool)
        except Exception:
            logger.exception("could not preload semantic_cache; falling back to per-lookup queries")
            return

        self._indexes, self._rows = self._build_indexes(rows)
        self._loaded = True
        logger.info(
            "SemanticCache preloaded %d rows in %.0f ms",
            self._rows,
            (asyncio.get_running_loop().time() - started) * 1000,
        )

    async def reload(self) -> int:
        """Rebuild the in-memory index from `semantic_cache` and return how many rows it holds.

        `load_all` runs once, at start-up, and until now nothing called it
        again: an `UPDATE` or a `DELETE` run by hand on Neon stayed invisible
        until the container restarted, and a restart drops every open session.
        This is the body of the admin endpoint of fase 5 of the plan — the
        explicit call instead of `LISTEN/NOTIFY`, which is the option that fits
        an occasional manual edit.

        The rows are fetched **before** the index is touched, so a database
        that fails halfway leaves the previous cache serving; that is the same
        best-effort rule the start-up follows, and the endpoint reports the
        failure instead of pretending it worked. The swap itself is one
        assignment, so no lookup can see a half-built index.

        A `store` that lands while the fetch is in flight is not lost — it is
        already in Neon — but its row can be missing from the new index until
        the next reload. That costs one extra LLM call, never a wrong answer.

        Returns 0 when `semantic_cache_preload` is off: in that mode every
        lookup goes to Neon and there is no in-memory index to rebuild.
        """
        if not self._preload:
            logger.info("SemanticCache reload ignored: preload is disabled")
            return 0

        pool = self._pool
        if pool is None:
            raise RuntimeError("no hay pool de base de datos: no se puede recargar la cache")

        rows = await self._fetch_rows(pool)
        indexes, loaded = self._build_indexes(rows)
        async with self._lock:
            self._indexes = indexes
            self._rows = loaded
            self._loaded = True
        logger.info("SemanticCache reloaded %d rows", loaded)
        return loaded

    async def _fetch_rows(self, pool: asyncpg.Pool) -> list[asyncpg.Record]:
        """Every row of `semantic_cache`, exactly as `load_all` reads them."""
        return await run_with_retry(
            lambda: pool.fetch(
                """
                SELECT original_text, phrase_type, glosses, embedding::text AS embedding
                FROM semantic_cache
                ORDER BY id
                """
            ),
            self._retry_policy,
            "could not load the semantic cache",
        )

    def _build_indexes(self, rows: list[asyncpg.Record]) -> tuple[dict[str, _PhraseTypeIndex], int]:
        """The in-memory index for these rows, built apart from the live one.

        Built off to the side on purpose: `reload` swaps the finished dictionary
        in, so building it never mutates what lookups are reading, and a row
        that does not parse does not leave a half-reloaded cache behind.
        """
        indexes: dict[str, _PhraseTypeIndex] = {}
        loaded = 0
        for row in rows:
            try:
                vector = np.asarray(row["embedding"].strip("[]").split(","), dtype=np.float32)
            except ValueError:
                logger.warning("skipping malformed embedding for %r", row["original_text"])
                continue
            index = indexes.setdefault(row["phrase_type"], _PhraseTypeIndex())
            normalized = substitute_synonyms(normalize(row["original_text"]), self._synonyms)
            index.add(normalized, vector, list(row["glosses"]))
            loaded += 1
        return indexes, loaded

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def row_count(self) -> int:
        return self._rows

    async def lookup(self, text: str, fingerprint: Fingerprint) -> list[str] | None:
        """Glosses for `text`, or None when the LLM has to be asked.

        The 0.05 threshold is calibrated for whole phrases, where "cómo estás"
        and "¿cómo estás?" really are the same sign.

        Where the answer came from is counted, because that is what turns one
        latency into the two the SRS asks for: a phrase the cache resolved and
        a phrase that needed the model. It only existed as a line in the log,
        so `/metrics` could not tell the two scenarios apart and could only
        publish their average, which is neither of them.
        """
        glosses, source = await self._lookup(text, fingerprint)
        metrics.counter("rt_cache_total", labels={"source": source})
        return glosses

    async def _lookup(self, text: str, fingerprint: Fingerprint) -> tuple[list[str] | None, str]:
        """The answer and where it came from: `exact`, `semantic` or `miss`.

        `exact` is the normalized text already in the cache, which costs no
        embedding at all; `semantic` is a close enough phrase, which costs the
        embedding and the similarity search. The difference is two orders of
        magnitude, so both are worth counting apart.
        """
        normalized = substitute_synonyms(normalize(text), self._synonyms)
        category = fingerprint.category.value

        if self._loaded:
            with trace_step("cache.exact"):
                index = self._indexes.get(category)
                if index is not None:
                    row = index.exact.get(normalized)
                    if row is not None:
                        return list(index.glosses[row]), "exact"

            with trace_step("cache.embed"):
                embedding = await self._embed_async(normalized)
            vector = np.asarray(embedding, dtype=np.float32)

            with trace_step("cache.similarity"):
                index = self._indexes.get(category)
                match = index.nearest(vector) if index is not None else None

            if match is not None:
                glosses, distance = match
                if distance <= self._similarity_threshold:
                    return list(glosses), "semantic"
            return None, "miss"

        if self._pool is None:
            # No database: nothing to look up. The phrase goes to the model.
            return None, "miss"

        found = await self._lookup_neon(normalized, category)
        return found, "semantic" if found is not None else "miss"

    async def store(self, text: str, fingerprint: Fingerprint, glosses: list[str]) -> None:
        if not glosses:
            # An empty answer is not a translation. Storing it would poison the
            # cache: the next lookup of the same phrase would hit an entry with
            # no signs in it, and the avatar would have nothing to play.
            logger.warning("Not storing an empty answer for %r", text)
            return

        normalized = substitute_synonyms(normalize(text), self._synonyms)
        category = fingerprint.category.value

        with trace_step("store.embed"):
            embedding = await self._embed_async(normalized)
        vector = np.asarray(embedding, dtype=np.float32)

        if self._loaded:
            async with self._lock:
                if self._rows < self._max_rows:
                    index = self._indexes.setdefault(category, _PhraseTypeIndex())
                    is_new = normalized not in index.exact
                    index.add(normalized, vector, list(glosses))
                    if is_new:
                        self._rows += 1
                else:
                    logger.warning(
                        "semantic_cache in memory is at the %d row cap; new phrases will miss until restart",
                        self._max_rows,
                    )

        secondary_signals = [signal.value for signal in fingerprint.secondary_signals]

        pool = self._pool
        if pool is None:
            logger.warning("No database pool: the answer for %r is not persisted", text)
            return

        await run_with_retry(
            lambda: self._write_to_neon(
                pool,
                text,
                category,
                embedding,
                glosses,
                secondary_signals,
                fingerprint.has_collision,
            ),
            self._retry_policy,
            f"could not store the cache row for {text!r}",
        )

    async def _write_to_neon(
        self,
        pool: asyncpg.Pool,
        text: str,
        category: str,
        embedding: list[float],
        glosses: list[str],
        secondary_signals: list[str],
        had_collision: bool,
    ) -> None:
        """Write one row, replacing the one the same phrase already has.

        The write is an UPSERT on `(original_text, phrase_type)`: the same
        phrase translated again replaces the old answer instead of piling a
        second copy of it next to it, which is what the plain INSERT used to
        do. The table has a unique index over that pair to conflict against
        (migration 004).
        """
        with trace_step("store.acquire"):
            conn = await pool.acquire(timeout=self._acquire_timeout_seconds)
        try:
            with trace_step("store.query"):
                await conn.execute(
                    """
                    INSERT INTO semantic_cache (original_text, embedding, phrase_type, glosses, secondary_signals, had_collision)
                    VALUES ($1, $2::vector, $3, $4, $5, $6)
                    ON CONFLICT (original_text, phrase_type) DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        glosses = EXCLUDED.glosses,
                        secondary_signals = EXCLUDED.secondary_signals,
                        had_collision = EXCLUDED.had_collision,
                        created_at = now()
                    """,
                    text,
                    _format_vector(embedding),
                    category,
                    glosses,
                    secondary_signals,
                    had_collision,
                )
        finally:
            with trace_step("store.release"):
                await pool.release(conn)

    async def _embed_async(self, text: str) -> list[float]:
        """Embed off the event loop.

        `SentenceTransformer.encode` is 12-25 ms of pure CPU. Blocking the loop
        for that delays the incoming audio of every other connection too, not
        just the phrase being translated.
        """
        return await asyncio.to_thread(self._embedding_model.embed, text)

    async def _lookup_neon(self, normalized: str, category: str) -> list[str] | None:
        """The old path against the database, for when preload did not happen."""
        with trace_step("cache.embed"):
            embedding = await self._embed_async(normalized)

        pool = self._pool
        if pool is None:
            return None

        row = await run_with_retry(
            lambda: self._fetch_nearest(pool, embedding, category),
            self._retry_policy,
            "could not look the phrase up in the semantic cache",
        )

        if row is None or row["distance"] > self._similarity_threshold:
            return None
        return list(row["glosses"])

    async def _fetch_nearest(
        self,
        pool: asyncpg.Pool,
        embedding: list[float],
        category: str,
    ) -> asyncpg.Record | None:
        with trace_step("cache.acquire"):
            conn = await pool.acquire(timeout=self._acquire_timeout_seconds)
        try:
            with trace_step("cache.query"):
                return await conn.fetchrow(
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
                await pool.release(conn)
