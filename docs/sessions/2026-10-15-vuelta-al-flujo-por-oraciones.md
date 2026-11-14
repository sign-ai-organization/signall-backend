# Vuelta al flujo documentado: la oración es la unidad

- **Fecha:** 2026-10-15
- **Rama:** `flujo-oraciones`, desde `origin/main` (`979e99d`)
- **Plan:** `signall-docs/auditoria-flujo-2026-10-15.md` §6.1
- **Decisiones del owner:** §5 punto 1 (base `origin/main` + cherry-pick),
  punto 4 (el caché en memoria se conserva), punto 6 (se vacía
  `semantic_cache`), y las dos que se tomaron en la sesión: **salida 1** para el
  disparador de traducción y **conservar y renombrar** para las métricas `rt_*`.

---

## Qué se hizo

`main` ya tenía el flujo documentado entero. El trabajo fue traer de `develop`
lo que no pertenece al camino por palabras, y **cambiar una sola cosa** que no
se puede dejar como estaba: quién dispara la traducción.

### Lo que se trajo de `develop`

| Qué | De dónde | Por qué |
|---|---|---|
| Prompt con el catálogo como vocabulario cerrado, `_repair_glosses`, `_merge_fragments`, `CatalogRepository.vocabulary()`, `ORDER BY id_sign`, `LLM_BASE_URL` | `ac013d4` (cherry-pick limpio) | El prompt lo pide y con oración sigue haciendo falta: es lo que evita que "cómo estás" vuelva `TÚ, ESTAR, CÓMO`. **Después, la decisión D-7 (owner, 2026-10-16) quitó el vocabulario cerrado del prompt**; la reparación y la fusión se quedan |
| `app/metrics.py` (registro Prometheus, `/metrics` y `/metrics.json`) | `d5c6570` | `marco.md` §6.1 lo pone como **criterio de entrada** a las rondas de prueba |
| Caché semántico en memoria | `d5c6570` + `fa045f2` | Decisión del owner. Un viaje a Neon son ~100 ms y el `lookup` completo ~200 ms: más caro que el LLM que evita |
| Precalentado del LLM | `d5c6570` | Sin esto la primera frase paga 6,2 s de carga del modelo y solo esa |
| Métricas de nivel de audio (`audio_rms`, `audio_bytes_total`, …) | `d5c6570` | No son del perfil de tiempo real: son salud del micrófono |

### Lo que se descartó

`app/realtime/` (334 líneas), el frame `mode`, el flag `dictation`, todo
`_utterance_*`, `transform_with_context`, `search_word`, los cuatro settings
`realtime_*`, `exact_only`, y `scripts/verify_incremental.py`,
`verify_realtime_latency.py`, `verify_voice_modes.py`.

### El cambio de contrato: solo se traduce lo que llega como `text`

Antes, un `final` del STT disparaba la traducción y el backend distinguía modos
con el flag `dictation`. Ahora:

| Entrada | Qué hace el backend |
|---|---|
| Audio | Lo reenvía al STT y devuelve cada transcripción. No traduce. |
| `{"type":"text"}` | Divide en oraciones y devuelve un `segment` por oración. |
| `{"type":"end"}` | Cierra el utterance en el STT. No traduce. |

Con eso **RF-STT-03 se cumple por construcción**: no hay forma de que una frase
dictada llegue al módulo de lenguaje sin que la app la mande. Los tres modos
de captura quedan como decisión de la app —dictado (espera confirmación),
en vivo (reenvía sola al cerrarse la frase) y en vivo con el micrófono siempre
prendido (`◢◢ TR`)— y el backend no necesita saber en cuál está.

**Por qué se descartó `13c7ac4`:** el arreglo de `handle_text()` no hizo falta.
`main` ya tenía `Orchestrator._translate_sentence` y `translate_stream` yieldendo
`(index, total, segment)` reales, así que el botón Traducir ya pasaba por el
divisor. El commit arreglaba un bug que había introducido `d5c6570`, que no está
en la base.

### Métricas renombradas

`rt_utterance_*` y `rt_chunk_*` describían fragmentos. Ahora `rt_phrase_total_ms`,
`rt_sentence_delay_ms`, `rt_sentences_total`, `rt_phrases_total`,
`rt_phrase_sentences`. **`rt_first_sign_ms` conserva el nombre** a propósito: es
la latencia de titular y la cifra que los documentos citan como línea base; su
punto de partida pasó a ser el envío del cliente, que es la confirmación de
RNF-DES-01.

### Migración `003`

`app/persistence/migrations/003_add_catalog_asset_metadata.sql`: las cuatro
columnas de metadatos del asset (`fps`, `total_frames`, `asset_bytes`,
`asset_sha256`) que existen en producción y no tenían migración. Idempotente.

---

## Verificación

- `python -m scripts.verify_client_frames`: **34 checks, todos OK**, tres
  sesiones nuevas que fijan el invariante nuevo (un `final` de voz no se
  traduce; un `final` vacío sí se reenvía; el frame `mode` no existe).
- `verify_catalog_normalization`, `verify_catalog_repository`,
  `verify_gloss_analyzer`, `verify_validator_service`: OK.
  `verify_llm_client`, `verify_nlp_service`, `verify_orchestrator` y
  `verify_sentence_segmenter` **no corren fuera del contenedor**: el venv local
  no tiene `langchain_openai`, `sentence_transformers` ni `spacy`.
- Migración `003` contra una base vacía (Postgres 15 local) + Neon de
  producción: `information_schema.columns` de `catalog` **coincide en los nueve**
  — mismo orden, tipos, nulabilidad y defaults. Correrla dos veces no falla.
- Pila completa con **Ollama local** (`qwen3:4b-instruct` en
  `http://127.0.0.1:11434/v1`):

  ```
  >>> Hola, ¿cómo estás? Me llamo Julian y vivo en Bogotá. Buenos días.
    segment 0/4  tipo=AFFIRMATIVE      glosas=[HOLA]
    segment 1/4  tipo=CONTENT_QUESTION glosas=[COMO ESTAS]
    segment 2/4  tipo=AFFIRMATIVE      glosas=[NOMBRE, YO]
    segment 3/4  tipo=AFFIRMATIVE      glosas=[BUENOS DIAS]
  ```

  `index`/`total` reales, sin `stream`, sin `provisional`, sin `total: 0`, y las
  cuatro glosas con animación disponible. `rt_first_sign_ms` 131,7 ms,
  `rt_phrase_total_ms` 810 ms. Caché en memoria: 618 filas al arrancar, 619
  después de la frase (el `store` también actualiza el índice).

## Hallazgo que no se arregló

`sessions_active` queda en 1 después de que el cliente cierre. En
`_forward_audio` el `gather` espera a **las dos** tareas y
`_forward_transcripts` sigue bloqueada en `receive_transcript()` del STT: el
`finally` (que cierra el cliente del STT) no corre hasta que el STT conteste.
Es una fuga de recursos **preexistente en `main`**, no la introduce este
cambio, y tocarlo cambia el ciclo de vida de la sesión. Queda anotado para que
lo decida el owner.

## Autorización de commit para esta rama

El 15 de octubre el owner autorizó commitear **sin pedir permiso** en la rama
`flujo-oraciones` de los tres repos, mientras el trabajo siga siendo local y en
esa rama. Choca con dos reglas escritas, así que vale dejarlasAspuestas:

- `CLAUDE.md`: "nunca hacer `git commit` ni `git push` sin que lo pida el owner".
- `AGENTS.md` del repo de Android: "nada de commits en los hermanos sin que el
  owner lo pida (PR contra `develop`)".

La excepción es acotada a este trabajo y a esa rama. `main` no se toca, y
cualquier otro cambio en este repo sigue la regla de `CLAUDE.md`: se sugiere el
mensaje y lo manda el owner.

## Lo que se hizo después

- `semantic_cache` vaciada en Neon: 619 filas borradas (618 de la tabla más una
  que credo la frase de prueba), 201 con el `||` del camino por palabras.
  `catalog` intacta con las 50 glosas.
- Cuatro commits en `flujo-oraciones`:
  `db1fa69` (cherry-pick de `ac013d4`), `294efae` (el cambio de contrato),
  `39210a1` (métricas y caché en memoria), `9cd2199` (migración 003 y docs).

## Lo que queda pendiente

1. **Remedir `rt_first_sign_ms`** con las 28 frases de `fixtures/audio/`. La
   cifra de 913 ms p50 / 1336 ms p95 es del camino por palabras y **no es
   comparable** con la de ahora: con oraciones la primera seña se representa al
   terminar la primera oración y no a mitad de camino, así que el número sube
   por construcción y no por una regresión.
2. **El frame `mode` se ignora**, no rompe: una app vieja que lo mande sigue
   funcionando, pero sus frases dictadas se representarán solas. Hay que actualizar la
   app antes de probar contra este backend.
3. **`sessions_active` se queda en 1** después de que el cliente cierre (el
   `gather` espera las dos tareas y `_forward_transcripts` sigue bloqueada en el
   STT, así que el `finally` no corre). Preexistente en `main`, no lo introduce
   este cambio y tocarlo cambia el ciclo de vida de la sesión.
