# CAMBIOS — backend (`flujo-oraciones`, 2026-10-15)

Qué cambió en este repo para pasar del flujo **por fragmentos** al flujo **por
oraciones**, y qué tiene que hacer el resto del sistema con esto.

**Rama:** `flujo-oraciones`, desde `origin/main`. **Sin mergear.**

> **Base de la rama, y es deliberada.** `origin/main` de este repo es **anterior**
> a todo el trabajo de tiempo real, que vive en `origin/develop` (8 commits:
> `app/realtime/incremental.py`, `app/metrics.py` con las métricas de fragmento, el
> modo dictado del controller, `scripts/verify_incremental.py`,
> `verify_voice_modes.py`, `verify_realtime_latency.py`). Volver a `main` y
> **dejar atrás** ese camino es decisión del owner, escrita en `Revisión de develop.md`
> (nota en la raíz de `sign-ai-android`, 2026-10-15):
>
> > **Base recomendada.** `origin/main` del backend ya contiene lo útil
> > (normalización del catálogo y frames `text`/`end`), sin nada de tiempo real.
>
> Por eso esta rama no tiene nada que borrar del camino por frases: en `main` no
> estaba. **No rebasar sobre `develop` sin preguntar** — reintroduce
> `app/realtime/` y las métricas de fragmento, que es justo lo que vino a
> desarmar.

---

## 1. El contrato cambió: **el backend solo traduce lo que llega como `text`**

Antes el backend tenía dos modos de entrega y él decidía cuál:

- recibir audio → transcribir → mandar fragmentos de glosas (`stream: true`,
  `total: 0`, `provisional`, `source_text`), sin esperar a que la frase terminara
- recibir `text` → traducir la frase entera y mandar un `segment` por oración

Ahora hay **un solo modo de entrega**, y el cliente decide cuándo usarlo:

| frame del cliente | qué hace el backend |
|---|---|
| audio PCM16 binario | lo reenvía al STT y devuelve `transcript` (parciales y `final`). **No traduce.** |
| `{"type":"text","text":"..."}` | divide en oraciones, traduce, manda un `segment` por oración con `index`/`total` reales, y un `done` |
| `{"type":"end"}` | cierra el utterance del STT |
| `{"type":"mode",...}` | **ya no existe** |

Lo que ya **no** está en este repo: el modo por fragmentos, `REALTIME_ENABLED`, los
flags `mode` / `dictation` / `capture_mode`, el latch por utterance, y
`app/realtime/incremental.py`.

`docs/android-integration.md` §3.1 documenta el contrato nuevo.

### El bug del eco (corregido, y fue serio)

`handle_text` respondía a cada `{"type":"text"}` con un `transcript` con
`final: true`. Venía de `main` y era inofensivo mientras el backend decidía qué
traducir. Al mover el disparador al cliente, el eco se volvió indistinguible de
algo que el STT había oído: **la app tomaba su propia frase por una transcripción
de voz y la reenviaba**.

```
frase #2875 y subiendo · 44 % de CPU · rt_phrases_total 3731
```

Corregido en `9e0f4b7`. `verify_client_frames.py` lo fija: una frase escrita de
dos oraciones produce **exactamente tres** frames (`segment`, `segment`, `done`),
leídos de una sola vez con `read_exactly(ws, 3)`.

---

## 2. Métricas: nombres honestos

`app/metrics.py` se conserva pero las de fragmento pasan a hablar de oraciones.

| antes | ahora | qué mide |
|---|---|---|
| `rt_first_sign_ms` | `rt_first_sign_ms` | frase recibida → primera oración enviada |
| `rt_utterance_ms` | **`rt_phrase_total_ms`** | frase recibida → última oración enviada |
| `rt_chunk_delay_ms` | **`rt_sentence_delay_ms`** | por oración |
| `rt_fragments_total` | **`rt_sentences_total`** | oraciones entregadas |
| — | **`rt_phrases_total`**, **`rt_glosses_total`**, **`rt_phrase_sentences`** | frases, glosas, y el histograma de oraciones por frase |

`rt_first_sign_ms` **conserva el nombre** aunque cambiara lo que mide. Es
deliberado: la línea base publicada (p50 913 ms / p95 1336 ms) es del camino por
palabras, y con el mismo nombre la comparación es visible — pero **no es
comparable**. La cifra nueva, medida el 2026-10-15 con `qwen3:4b-instruct` en
Ollama local y la caché semántica vacía, es **p50 273 ms / p95 422 ms**.

> Los nombres de métrica tienen que coincidir con los del lado del teléfono
> (`SignAiMetrics`): un número que no se instrumentó en las dos partes no se puede
> comparar con nada.

---

## 3. NLP: una oración, una clave de caché

El `||` de dos barras —la clave compuesta que el camino por palabras necesitaba
para partir la frase en trozos traducibles— **desaparece**: la unidad es la
oración, así que la clave es una oración limpia, la misma en los dos modos.

También viene `db1fa69` (cherry-pick de `ac013d4`, que estaba en `develop`): el
LLM partía glosas nominales en palabras sueltas que no se pueden representar.
**Ojo:** de ese cherry-pick, la parte del **vocabulario cerrado en el prompt se
quita** por la decisión D-7 (owner, 2026-10-16; ver `docs/performance.md` §9).
La reparación (`_repair_glosses`, `_merge_fragments`) y el validador se quedan.

`semantic_cache` se vació en Neon (619 filas, 201 con `||`). Es caché derivada y
se reconstruye sola con la primera frase de cada entrada. `catalog` quedó intacta
con sus 50 glosas.

---

## 4. Migración de catálogo

`db/migrations/003_add_catalog_asset_metadata.sql` agrega las cuatro columnas que
producción ya tenía y el repo no: verified contra producción — las nueve columnas
quedan idénticas.

---

## 5. Lo que este repo necesita de los otros dos

| repo | qué tiene que hacer |
|---|---|
| `sign-ai-stt` | seguir mandando `transcript` con `final`, y **responder a todo `end`, incluso vacío**. El backend no puede asumir que un `end` produce un `final`: si no llega, la frase queda colgada. |
| `sign-ai-android` | decidir **cuándo** mandar el `text`: el client es quien dispara. En el cliente, el auto-envío en vivo **no debe poder dispararse por un frame que no venga del STT** — es el modo en que se manifestó el bug del eco. |

---

## 6. Cómo verificar

```bash
docker compose up -d --build
docker compose exec backend python -m scripts.verify_client_frames      # contrato
docker compose exec backend python -m scripts.verify_sentence_segmenter  # divisor
```

Los dos se corren **como módulo**: corridos como `python scripts/x.py`,
`sys.path[0]` es `/app/scripts` y `import app` no resuelve.

El `Dockerfile` ahora copia `scripts/` a la imagen, porque los tests corren
**dentro** del contenedor (necesitan `spacy` y `httpx2`) y sin el `COPY` no
estaban.

Desde el repo de Android, todo junto:

```bash
tools/verificar-tiempo-real.sh contrato
tools/medir-primera-sena.py
tools/medir-retraso.py
```
---

## 2026-10-16 — El bucle de lectura deja de traducir, y el socket con el STT se suelta

El detalle y las citas están en `docs/sdd-changes.md`. Resumen de lo medido:

| | antes | después |
|---|---|---|
| retraso del audio durante la traducción | 991 ms | **0 ms** |
| `rt_read_loop_busy_ms` (p50 / max) | 0,155 / **931** ms | 0,151 / **0,595** ms |
| conexiones al STT que quedan colgadas (10 sesiones) | +18 | **0** |

También se arregló `scripts/verify_orchestrator.py`, que construía el `LLMClient`
sin `settings.llm_base_url` y por lo tanto llamaba a la API de OpenAI de verdad
(404 `model not found` con `qwen3:4b-instruct`). Y `verify_client_frames.py` fijó
dos regresiones nuevas del cierre de sesión: que cerrar el cliente cierre el socket
con el STT una vez, y que si el STT se cae la sesión también termine.

Herramientas nuevas, que son las pruebas de regresión de cada punto:

- `tools/verificar-bloqueo-lectura.py` (vive en `sign-ai-android/tools`) —
  falla si el bucle de lectura se traba más de 500 ms.
- `tools/verificar-conexiones-stt.py` — falla si alguna sesión deja su socket
  con el STT abierto.

Tres métricas nuevas: `rt_read_loop_busy_ms` (trabajo por frame del bucle de
lectura), `llm_ms{model}` (la llamada al modelo, que antes solo se veía en el
log con `DEBUG_TRACE_ENABLED`) y `cache_lookup_ms`. Más `gauge_value()` en el
registro, porque `sessions_active` leía su propio valor del mapa de contadores
y por eso decía siempre 1.

`/health` ahora incluye `silence_timeout_ms`, copiado del STT cada 30 s, para
que la app lo muestre en su overlay de depurar.

---

## Pendiente

1. **Falta remedir `rt_first_sign_ms` con el LLM de producción.** Los 273 ms son
   de `qwen3:4b-instruct` en Ollama local, no de OpenAI. Con OpenAI la cifra es
   otra y esa es la que va a la tesis.
2. **El divisor de oraciones** (`verify_sentence_segmenter.py`) reproduce
   exactamente la salida del laboratorio en los 191 casos, pero solo coincide con
   el corte esperado en 156. Los 35 restantes están documentados como
   "info only": la diferencia está en dónde corta una abreviatura o un
   participio, y el corte del laboratorio es el que manda.