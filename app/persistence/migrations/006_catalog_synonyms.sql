-- Fase 2 del plan de implementación: tabla de sinónimos del catálogo.
--
-- Cada fila dice "este sinónimo significa la glosa de este id_sign". Una
-- sola glosa canónica puede tener varios sinónimos (MUCHO <- MUY; PERMISO
-- <- CON PERMISO, DAME PASAR). Vive en la base de datos, no en código
-- (decisión 4 del owner), para poder agregar sinónimos sin desplegar.
--
-- Esta tabla nunca se le manda al LLM: solo se consulta después de que el
-- LLM ya respondió (CatalogRepository.load_all -> LLMClient._repair_glosses)
-- o antes de buscar en la caché semántica. Respeta D-7.

CREATE TABLE IF NOT EXISTS catalog_synonym (
    id SERIAL PRIMARY KEY,
    synonym VARCHAR NOT NULL UNIQUE,
    id_sign INTEGER NOT NULL REFERENCES catalog (id_sign)
);

CREATE INDEX IF NOT EXISTS idx_catalog_synonym_id_sign ON catalog_synonym (id_sign);
