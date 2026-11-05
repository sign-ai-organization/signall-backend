"""Measures an in-memory cache hit against the same lookup done against Neon.

Decision of the owner (2026-11-03), point 13: measure before deciding whether
the in-memory cache stays, changes or goes. The cache was introduced because a
trip to Neon cost more than the model call it was avoiding; the number in the
docstring of `SemanticCache` came from an earlier round. This script produces
the current pair of numbers on the machine that runs it:

- `lookup()` with the table already loaded (`load_all`): embedding + cosine
  search in memory, no network.
- `_lookup_neon()`: the old path, embedding + a query against pgvector.

Both are timed on the same phrase, taken from the database, so the two runs are
a HIT and not a miss. Run it inside the backend image, which has the
dependencies and the database URL:

    docker compose run --rm --no-deps backend python -m scripts.measure_cache_lookup

The numbers are per machine and per database state; quote them with that origin.
"""

from __future__ import annotations

import asyncio
import statistics
import sys
import time

from app.config.settings import settings
from app.domain.models import PhraseType
from app.nlp.embedding_model import EmbeddingModel
from app.nlp.models import Fingerprint
from app.nlp.semantic_cache import SemanticCache
from app.persistence.database import RetryPolicy, open_pool

ROUNDS = 20


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((pct / 100) * (len(ordered) - 1))))
    return ordered[index]


def format_ms(milliseconds: float) -> str:
    """Milliseconds with the unit that says something: µs below 1 ms."""
    if milliseconds < 1:
        return f"{milliseconds * 1000:.0f} µs"
    return f"{milliseconds:.1f} ms"


async def time_calls(label: str, call, rounds: int = ROUNDS) -> list[float]:
    # Two warm-ups: the first embedding loads the tokenizer and the first query
    # pays the TLS handshake. Timing those would describe the start-up, not the
    # steady state the user lives in.
    for _ in range(2):
        await call()
    samples: list[float] = []
    for _ in range(rounds):
        started = time.perf_counter()
        await call()
        samples.append((time.perf_counter() - started) * 1000)
    print(
        f"  {label}: p50 {format_ms(percentile(samples, 50))}, "
        f"p95 {format_ms(percentile(samples, 95))}, "
        f"media {format_ms(statistics.fmean(samples))}"
    )
    return samples


async def main() -> None:
    # The same helper the service uses, with more patience than the service
    # has: this script is a measurement, not a start-up, and a Neon resuming
    # from scale-to-zero must not turn the measurement into a timeout.
    pool = await open_pool(
        settings.database_url,
        1,
        2,
        0,
        command_timeout_seconds=settings.db_command_timeout_seconds,
        connect_timeout_seconds=15.0,
        policy=RetryPolicy(retries=2, delay_seconds=1.0),
    )
    if pool is None:
        print("No se pudo abrir la base: no hay números que medir.")
        sys.exit(2)
    try:
        row = await pool.fetchrow(
            "SELECT original_text, phrase_type FROM semantic_cache ORDER BY created_at LIMIT 1"
        )
        if row is None:
            print("La tabla semantic_cache está vacía: no hay una frase con la que medir un acierto.")
            sys.exit(2)

        text = row["original_text"]
        category = PhraseType(row["phrase_type"])
        fingerprint = Fingerprint(category=category, secondary_signals=[], has_collision=False)
        print(f"\nfrase de prueba: {text!r} ({category.value})")

        embedding = EmbeddingModel()
        cache = SemanticCache(
            pool,
            embedding,
            settings.semantic_cache_similarity_threshold,
            preload=settings.semantic_cache_preload,
            max_rows=settings.semantic_cache_max_rows,
            retry_policy=RetryPolicy(settings.db_max_retries, settings.db_retry_delay_seconds),
            acquire_timeout_seconds=settings.db_acquire_timeout_seconds,
        )
        await cache.load_all()
        print(f"filas cargadas en memoria: {cache.row_count}")

        print("\nun acierto del caché, dos caminos:")
        in_memory = await time_calls("en memoria  ", lambda: cache.lookup(text, fingerprint))
        over_neon = await time_calls("contra Neon", lambda: cache._lookup_neon(text, category.value))

        extra = percentile(over_neon, 50) - percentile(in_memory, 50)
        print(
            f"\nNeon suma {extra:.0f} ms al p50 frente a la memoria. "
            "Mismo equipo, misma base y la misma frase: la diferencia es el viaje a Neon."
        )
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
