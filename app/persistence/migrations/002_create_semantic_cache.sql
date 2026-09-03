-- Figura 8 (docs/sdd.md, 7.3): tabla semantic_cache.
CREATE TABLE semantic_cache (
    id SERIAL PRIMARY KEY,
    original_text TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    phrase_type VARCHAR NOT NULL,
    glosses TEXT[] NOT NULL,
    secondary_signals TEXT[] NOT NULL,
    had_collision BOOLEAN NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
