# Merge de `Correccion-Pruebas` (Fase 2) sobre `fix/fases1-3`

- **Fecha:** 2026-11-06
- **Ramas:** `fix/fases1-3` (`e0ee611`) ← `origin/Correccion-Pruebas` (`28b3d4d`, Samuel Osorio)
- **Puntos de retorno:** `respaldo/fix-fases1-3-2026-11-06` y `respaldo/correccion-pruebas-2026-11-06`

## Qué se juntó

| Rama | Fases |
|---|---|
| `fix/fases1-3` | Fase 1 (índice único, `EMBEDDING_MODEL_NAME`) y Fase 3 (pregunta de contenido sin `?`) |
| `Correccion-Pruebas` | Fase 2 completa: `gloss_lexicon.py` (flexión + pronombre implícito), tabla `catalog_synonym` y su carga en `CatalogRepository`, sinónimos en la llave de `SemanticCache` |

La Fase 4 (Android: cola de turnos, reactivación del micrófono) ya estaba en `fix/fases1-3`
desde `c473956`. La Fase 5 no está en ninguna de las dos ramas.

## Conflictos y decisiones del merge

1. **`app/main.py`**: se auto-fusionó. Quedaron las dos cosas en el constructor de
   `SemanticCache`: `EmbeddingModel(settings.embedding_model_name)` (Fase 3) y
   `synonym_pairs=catalog_repository.synonym_pairs` (Fase 2). El orden importa y se
   respetó: `catalog_repository.load_all()` corre antes, así que `synonym_pairs` ya está
   poblado cuando se construye la caché.

2. **Dos migraciones numeradas `005`**: la rama de Samuel traía
   `005_catalog_synonyms.sql` y la mía `005_catalog_unique_gloss.sql`. El plan de
   implementación nombra la de sinónimos como `006_catalog_synonyms.sql` y la de Fase 1
   como `005_catalog_unique_gloss.sql`, así que se renumeró la de Samuel a `006`.
   No hay tabla de migraciones aplicadas y el script es idempotente
   (`CREATE TABLE IF NOT EXISTS`), así que renombrar el archivo no toca la base: la
   tabla ya existía en Neon con el nombre viejo y sigue igual.

3. **`scripts/verify_catalog_semantic_category.py`**: el doble de `FakePool` devolvía las
   filas del catálogo a cualquier consulta, y `load_all()` ahora hace una segunda consulta
   a `catalog_synonym`; reventaba con `KeyError: 'synonym'`. Se hizo el doble consciente de
   la consulta, como el de `verify_catalog_synonyms.py`. Es el único arreglo de un script
   que pidió el merge.

## Verificación

- `ruff check app scripts`: limpio. `mypy`: 40 archivos, sin errores.
- Backend reconstruido (`docker compose up -d --build backend`) y arriba:
  `/health` da `catalog_glosses: 63` (50 glosas + 13 sinónimos) y `cache_rows: 0`.
- Suite de `scripts/verify_*.py` comparada contra `main`, `fix/fases1-3` y
  `Correccion-Pruebas` por separado, corrida con el mismo image y el código montado:
  - Pasan y quedan pasando: `verify_gloss_lexicon`, `verify_catalog_synonyms`,
    `verify_gloss_analyzer`, `verify_llm_prompt`, `verify_catalog_repository`,
    `verify_nlp_service`, `verify_validator_service`, `verify_orchestrator`,
    `verify_endpoints`, `verify_static_analysis`, `verify_database_resilience`,
    `verify_metrics_sources`, `verify_sentence_segmenter`, `verify_llm_timeout`,
    `verify_dependencies_pinned`, `verify_catalog_normalization`,
    `verify_catalog_semantic_category` (después del arreglo del doble).
  - **Ya fallaban en `main` y siguen fallando igual**, sin sumar ni un fallo:
    `verify_audio_validation` (7), `verify_done_on_error` (9), `verify_turn_id` (2),
    `verify_client_frames` (14), y las excepciones de `verify_cache_upsert`
    (`FakePool.acquire()` no acepta `timeout`) y `verify_semantic_cache`
    (espera HIT donde ya no lo hay). Son dobles de prueba desactualizados respecto del
    código de `main` (frames `capability`, `turn_id`), no regresiones de este merge.
    `verify_llm_client` es interactivo y no corre sin teclado.

## Medición de `PR-INT-02` (30 frases de FR-01)

Método: caché semántica vaciada en Neon (`DELETE FROM semantic_cache`, decisión del
owner), backend reiniciado con `cache_rows: 0`, las 30 frases enviadas como
`{"type":"text"}` por `ws://127.0.0.1:8080/ws/translate`, concatenando las glosas de
todos los `segment` en orden hasta el `done`. Modelo `gpt-4o-mini`, temperatura 0.

Resultado del pipeline mergeado, **antes** del ajuste: **15/30 frases exactas (50 %), 126
glosas devueltas de 112 esperadas (112,5 %)**.

Para separar qué aporta cada regla se repitió la reparación sobre la misma respuesta del
modelo, frase por frase y con el mismo segmentador, con y sin la regla del pronombre:

| Configuración | Exactas |
|---|---|
| Respuesta cruda del modelo | 13-14/30 |
| + flexión + sinónimos (sin pronombre) | **20-21/30** |
| + pronombre implícito, como se mergeó | **15/30** |
| + pronombre con el ajuste (abajo) | **22-23/30** |

La capa de flexión y sinónimos sí funciona y suma **+7** frases exactas. La regla del
pronombre, tal como estaba, **restaba 5-6** porque disparaba sobre casos donde el sujeto
no es el oyente:

| Oración | Agregaba | Problema |
|---|---|---|
| `Mi abuelo nunca trabaja.` | YO | `mi` es posesivo de primera persona, no sujeto; FR-01 dice que `mi`/`su` no pasan a glosa |
| `La mujer es juiciosa.` | TU | el sujeto es la mujer; se disparaba por la cópula `es` |
| `La niña nunca está triste.` | TU | ídem por `está` |
| `¿Quién es el hombre?` | TU | ídem por `es` |
| `Por favor, come poco.` | TU | imperativo; FR-01 no usa TU en órdenes |

Disparaba bien en `¿Estás bien?`, `¿Estás triste?`, `¿Por qué estás triste?`,
`¿cómo estás?` y `¿Tu hermano está aburrido?`.

## Ajuste aplicado a la regla del pronombre (decisión del owner, 2026-11-06)

Se acotó `app/nlp/gloss_lexicon.py` en dos puntos, sin tocar nada más:

1. `mi` y `mis` salen de `_FIRST_PERSON_WORDS`: son posesivos que apuntan a otra persona,
   no marcas de primera persona.
2. La rama ambigua (tercera persona → TU) exige además el reflexivo `se`, que es lo que
   esconde el sujeto. `¿Se siente mal?` y `Se siente muy bien.` siguen agregando TU;
   `La mujer es juiciosa.` y `¿Quién es el hombre?` ya no.

`scripts/verify_gloss_lexicon.py` ganó los dos casos nuevos y pasa completo.

## Medición final de `PR-INT-02` (después del ajuste)

Mismo método: caché vaciada, backend reconstruido y reiniciado, 30 frases por el
WebSocket, `gpt-4o-mini`, temperatura 0.

**22/30 frases exactas (73,3 %), 115 glosas devueltas de 112 esperadas (102,7 %).**

Las 8 que no coinciden son, por origen:

- **Modelo** (6): FR-01-006 omite NIÑO y CON GUSTO; FR-01-011 agrega COMO; FR-01-013
  omite NOMBRE; FR-01-016 cambia el orden; FR-01-027 dice NIÑA donde el corpus pide NIÑO
  (NIÑA es una glosa válida del catálogo, así que la flexión no la toca); FR-01-029
  agrega SENTIR.
- **Decisión del owner** (2): FR-01-010 y FR-01-024 agregan TU por la regla de la persona
  ambigua, que es comportamiento correcto según la decisión 2 pero no coincide con las
  glosas de referencia de FR-01, escritas antes de esa decisión.

Comparado con la línea base del 2026-11-04 (15/30, 99 glosas), la Fase 2 suma **+7 frases
exactas**. El plan preveía 26-28; falta que el modelo acierte esas 6 frases para llegar.


## Estado

- Merge y ajuste commiteados en `fix/fases1-3` y subidos a `origin/fix/fases1-3`.
- El backend quedó corriendo con el código mergeado.
- La caché `semantic_cache` quedó poblada con las 30 frases de la medición.
- La app Android se instaló en el Redmi Note 9S apuntando a `ws://127.0.0.1:8080` con
  `adb reverse tcp:8080 tcp:8080`; una prueba desde la app («Estoy muy cansado») devolvió
  `YO, MUCHO`, primera seña en 982 ms.
