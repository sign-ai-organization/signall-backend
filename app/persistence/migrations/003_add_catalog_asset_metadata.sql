-- Asset metadata on `catalog`, matching what production already has.
--
-- `001_create_catalog.sql` creates five columns; the deployed table has nine.
-- These four were added by hand during the dataset work and never got a
-- migration, so a database built by running the migrations in order comes out
-- with a different `catalog` than production. Nothing reads them yet
-- (`CatalogRepository.load_all` still selects gloss and glb_animation_path
-- only) and they stay nullable and without defaults on purpose.
--
-- They are not dropped. Dropping them would be a second migration and a second
-- divergence; the point of this one is that a fresh environment comes out equal
-- to production. If they turn out to be useless, that is a `004` and a note in
-- docs/sdd-changes.md.
--
-- Idempotent on purpose: this migration has to be safe on a database that
-- already has the columns, which is every existing one.
--
-- Verified against Neon on 2026-10-15 (project `sign-ai`): the column names,
-- types, nullability and absence of defaults all match this file.

ALTER TABLE catalog ADD COLUMN IF NOT EXISTS fps INTEGER;
ALTER TABLE catalog ADD COLUMN IF NOT EXISTS total_frames INTEGER;
ALTER TABLE catalog ADD COLUMN IF NOT EXISTS asset_bytes BIGINT;
ALTER TABLE catalog ADD COLUMN IF NOT EXISTS asset_sha256 TEXT;