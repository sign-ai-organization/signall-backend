-- Figura 8 (docs/sdd.md, 7.3): tabla catalog.
CREATE TABLE catalog (
    id_sign SERIAL PRIMARY KEY,
    gloss VARCHAR NOT NULL,
    semantic_category VARCHAR NOT NULL,
    glb_animation_path VARCHAR NOT NULL,
    modified_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_catalog_gloss ON catalog (gloss);
