-- One row per phrase and phrase type, so the cache can be written with an
-- UPSERT.
--
-- `SemanticCache.store` used to do a plain INSERT. The same phrase stored
-- twice left two rows that no lookup could tell apart, and the table grew
-- with copies of answers that were already there. The UPSERT needs a
-- constraint to conflict against, and the table had none.
--
-- The unique index is over `(original_text, phrase_type)`: the same phrase
-- translated as a different kind of phrase is a different row, because the
-- lookup filters by phrase type before it compares embeddings.
--
-- Idempotent on purpose: this migration has to be safe on a database that
-- already has the index, which is every database this runs on a second time.

-- Rows that no lookup can use: an empty answer is not a translation, and it
-- would be served as a hit with nothing in it.
DELETE FROM semantic_cache WHERE cardinality(glosses) = 0;

-- Keep the newest row of every duplicated pair and drop the rest, so the
-- unique index can be created.
DELETE FROM semantic_cache older
USING semantic_cache newer
WHERE older.id < newer.id
  AND older.original_text = newer.original_text
  AND older.phrase_type = newer.phrase_type;

CREATE UNIQUE INDEX IF NOT EXISTS idx_semantic_cache_phrase
    ON semantic_cache (original_text, phrase_type);
