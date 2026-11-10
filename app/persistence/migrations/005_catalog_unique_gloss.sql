-- One row per gloss, enforced by the database.
--
-- `001_create_catalog.sql` created `idx_catalog_gloss` as a plain index, so
-- inserting the same gloss with a different `id_sign` was accepted. That is
-- exactly what `PR-VAL-02` reported (2026-11-05): a second HAMBRE with a new
-- id landed without error and the in-memory map silently kept one of the two.
--
-- `CatalogRepository.load_all()` already keys the catalog by
-- `normalize_gloss(gloss)`, so two rows that fold to the same key overwrite
-- each other and the winner depends on the read order. A unique constraint on
-- the stored spelling closes the door at the source; it does not replace the
-- folding done in memory, which still resolves accents and punctuation.
--
-- Idempotent on purpose, like `003` and `004`: it has to be safe on a database
-- that already has the constraint. The `DO` block is what makes
-- `ADD CONSTRAINT` repeatable, because PostgreSQL has no
-- `ADD CONSTRAINT IF NOT EXISTS`.
--
-- A database that already holds duplicates makes this migration fail instead
-- of deleting rows on its own. Duplicated glosses are a data decision, not a
-- schema one: the operator has to say which `id_sign` wins.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_catalog_gloss'
          AND conrelid = 'catalog'::regclass
    ) THEN
        ALTER TABLE catalog ADD CONSTRAINT uq_catalog_gloss UNIQUE (gloss);
    END IF;
END $$;
