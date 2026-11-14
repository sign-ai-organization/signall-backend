# CAMBIOS — backend (`Correccion-Pruebas`, 2026-11-05/06)

Fase 2 del plan de implementación (artifact "De la propuesta al commit"): la
capa de vocabulario que sube el acierto de `PR-INT-02`. Dos arreglos, los dos
en `signall-backend`; no se tocó `signall-stt` ni `signall-android` porque la
Fase 2 del plan es solo backend.

**Rama:** `Correccion-Pruebas`, desde `origin/main`. El trabajo se publicó como
el commit `28b3d4d` (*"feat: Ajuste realizados de la Fase 2 de las pruebas"*,
Samuel Osorio, 2026-11-06 00:43). Al mergearse con `fix/fases1-3` la migración
se renumeró de `005_catalog_synonyms.sql` a `006_catalog_synonyms.sql`, que es
el número que pide el plan (la `005` es la de Fase 1, el índice único). La
tabla ya existía en Neon con el nombre viejo del archivo: como no hay tabla de
migraciones aplicadas y el script es idempotente, renombrar no toca la base.

---

## 1. Flexión y pronombre implícito — `app/nlp/gloss_lexicon.py` (nuevo)

Dos reglas que se enganchan en `LLMClient._repair_glosses`, antes de que una
glosa sin match se dé por perdida:

- **`resolve_inflection`**: si `NIÑOS` o `BIENVENIDOS` no están en el catálogo
  tal cual, prueba singular, género (A↔O) y variante con/sin Ñ, antes de
  rendirse. Arregla `NINOS→NIÑO`, `BIENVENIDOS→BIENVENIDO`.
- **`insert_implicit_pronoun`**: agrega `TU` o `YO` cuando la oración lo
  implica gramaticalmente (verbo en segunda o primera persona) y el modelo no
  lo dijo. El caso ambiguo usted/él (verbo en tercera persona singular, p. ej.
  "¿Se siente mal?") agrega `TU` por decisión del owner — habla directo a la
  persona en vez de asumir un tercero. Una oración sin ningún marcador de
  persona se deja intacta.

`LLMClient.transform`/`_repair_glosses` cambiaron de firma para recibir el
texto original (lo necesita la regla del pronombre) — es el único cambio de
interfaz de toda la fase, como anticipaba el plan.

## 2. Sinónimos en base de datos — tabla `catalog_synonym`

- `app/persistence/migrations/006_catalog_synonyms.sql` (nuevo; era `005` en la
  rama original): tabla
  `catalog_synonym (synonym UNIQUE, id_sign REFERENCES catalog)`.
- `CatalogRepository.load_all()` la funde en el mismo `self.cache` que ya usan
  `vocabulary()` y `search()` — un sinónimo resuelve automáticamente en
  `LLMClient._repair_glosses`, sin tocar ese archivo para esta regla. Una
  colisión con una glosa real se registra y se ignora (gana el catálogo); un
  sinónimo que apunta a una glosa que no existe también se ignora.
- `SemanticCache` recibe los pares (sinónimo, glosa canónica) de
  `CatalogRepository.synonym_pairs` y los usa para sustituir el texto de la
  frase antes de normalizarla (`text_normalizer.substitute_synonyms`, nuevo),
  así "tengo mucho sueño" y "tengo muy sueño" caen en la misma llave de caché.
- Respeta D-7: la tabla nunca se le manda al LLM, solo se consulta después de
  que ya respondió, o antes de buscar en caché.

---

## 3. Lo que ya se aplicó en Neon (no está en git)

Esto es dato, no código — no hay commit que lo registre, solo este archivo:

- **Migración de sinónimos aplicada** (2026-11-06, como `005_catalog_synonyms.sql`; hoy es `006_catalog_synonyms.sql`). La tabla
  existe en producción con sus 0 filas iniciales, antes de la carga de abajo.
- **13 sinónimos cargados**:

  | Sinónimo | → Glosa canónica |
  |---|---|
  | MUY, BASTANTE | MUCHO |
  | UN POCO | POCO |
  | CON PERMISO, DAME PASAR | PERMISO |
  | DISCULPA, LO SIENTO | PERDON |
  | CHAO, HASTA LUEGO | ADIOS |
  | QUE TAL, COMO TE VA | COMO ESTAS |
  | SEÑOR | HOMBRE |
  | SEÑORA | MUJER |

  Se dejaron fuera a propósito los que `gloss_lexicon.py` ya resuelve solo sin
  tabla (singular/plural, género, Ñ): por ejemplo `ABUELA→ABUELO` o
  `NIÑOS→NIÑO` no necesitan un sinónimo.
- **`semantic_cache` se vació** (2026-11-06, 40 filas borradas) para que la
  prueba no diera HIT con respuestas de antes del cambio. Es caché derivada,
  se reconstruye sola con la primera frase de cada una.

## 4. Verificación hecha en esta sesión

- `scripts/verify_gloss_lexicon.py` y `scripts/verify_catalog_synonyms.py`
  (nuevos): lógica aislada, con vocabulario falso, sin Neon ni LLM. Cubren los
  casos límite (colisión con glosa real, sinónimo a una glosa inexistente,
  frase sin marcador de persona).
- `ruff` + `mypy` sobre los archivos tocados: cero errores nuevos sobre la
  base de `main`.
- **Prueba real** contra Neon y OpenAI, con el backend levantado
  (`docker compose up -d --build backend`) y 4 frases por el WebSocket
  `/ws/translate`, el mismo contrato que usa el cliente Android:

  | Frase | Glosas obtenidas | Qué confirma |
  |---|---|---|
  | "Estoy muy cansado" | `YO, MUCHO` | sinónimo `MUY→MUCHO`; pronombre `YO` |
  | "Con permiso, ¿puedo pasar?" | `PERMISO` / `PUEDO, PASAR` (no disp.) | sinónimo `CON PERMISO→PERMISO`; `PODER`/`PASAR` no están en el corpus de 50 señas, esperado |
  | "Estoy contento" | `YO, CONTENTO` | pronombre implícito (primera persona) |
  | "Los niños comen" | `NIÑO, COMER` | flexión `NIÑOS→NIÑO` |

  `/health` tras el reinicio con caché vacía: `{"cache_rows":0,
  "catalog_glosses":63}` — 50 glosas + 13 sinónimos, confirma que
  `load_all()` los plegó bien en memoria.

  El backend se paró después (`docker compose stop backend`); no quedó
  corriendo.

## 5. Pendiente

1. **Reproducir `PR-INT-02` completo** (las 30 frases de
   `signall-docs/borradores/plan-pruebas/02-datos/FR-01-frases-dominio.md`),
   no solo las 4 de esta sesión — eso sí se decidió no correrlo todavía para
   no llenar `semantic_cache` de producción con datos de prueba sin que el
   owner lo decidiera primero.
2. Las Fases 1, 3, 4 y 5 del mismo plan siguen sin implementar.
