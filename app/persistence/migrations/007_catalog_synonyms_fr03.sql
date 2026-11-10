-- Sinónimos que faltaban para las variantes de FR-03 (PR-CAC-03).
--
-- La caché semántica compara la oración normalizada después de cambiar cada
-- sinónimo por su glosa canónica. Medido el 2026-11-10 con el umbral 0,04, de
-- las 12 variantes de sinónimo solo 3 acertaban: las otras 9 no compartían
-- clave con su original. Estas filas son las que faltaban.
--
-- Dos detalles del mecanismo que explican las filas raras:
--
--   * el reemplazo es la **glosa**, no la palabra del original, así que una
--     forma flexionada del original ("juiciosa", "niños", "vive") necesita su
--     propia fila para caer también en la glosa ("JUICIOSO", "NIÑO", "VIVIR");
--   * el reemplazo de un sinónimo de varias palabras se busca antes que el de
--     una sola, por eso "UN POQUITO" y "MUY BIEN" se resuelven como frase y no
--     palabra por palabra.
--
-- Idempotente: `ON CONFLICT (synonym) DO UPDATE` deja la fila apuntando a la
-- glosa correcta si ya existía.

INSERT INTO catalog_synonym (synonym, id_sign)
SELECT v.synonym, c.id_sign
FROM (VALUES
    ('REGULAR',     'MAS O MENOS'),
    ('PRUDENTE',    'JUICIOSO'),
    ('JUICIOSA',    'JUICIOSO'),
    ('JAMAS',       'NUNCA'),
    ('DISCULPE',    'PERDON'),
    ('EXCELENTE',   'BIEN'),
    ('MUY BIEN',    'BIEN'),
    ('UN POQUITO',  'POCO'),
    ('CHICOS',      'NIÑO'),
    ('NIÑOS',       'NIÑO'),
    ('RESIDE',      'VIVIR'),
    ('VIVE',        'VIVIR')
) AS v(synonym, gloss)
JOIN catalog c ON c.gloss = v.gloss
ON CONFLICT (synonym) DO UPDATE SET id_sign = EXCLUDED.id_sign;
