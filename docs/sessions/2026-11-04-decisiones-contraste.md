# Decisiones del contraste del backend

- **Fecha:** 2026-11-04
- **Rama:** `develop`
- **Origen:** las 14 decisiones del owner sobre la sección 6 de
  `../signall-android/docs/backend/contraste-backend-2026-11-03.html`, más el reporte
  `../signall-android/docs/CONTRASTE-BACKEND-ARTIFACT-2026-11-03.md`.
- **Sin commit:** los cambios quedan en el árbol de trabajo, como manda `CLAUDE.md`.

---

## Qué se hizo

| Archivo | Qué cambió |
|---|---|
| `app/controller/controller.py` | **RNF-SEC-02.** `handle_audio_chunk` valida el fragmento antes de reenviarlo: vacío, número impar de bytes (PCM16 son dos bytes por muestra) o más de `audio_max_chunk_bytes` (32 768, ~1 s a 16 kHz) devuelve `False` y cuenta `audio_chunks_rejected_total{reason}`. Un fragmento normal de 30 ms pesa 960 bytes |
| `app/controller/router.py` | Cuando el fragmento se rechaza: frame `error`, `websocket.close(code=1008)` y fin de la sesión. El cierre explícito es lo que le dice a un cliente estándar que la sesión terminó a propósito |
| `app/config/settings.py` | `audio_max_chunk_bytes`, `db_connect_timeout_seconds` y `db_acquire_timeout_seconds`; `env_file=(".env", ".env.local")`, con `.env.local` opcional y de desarrollo |
| `app/persistence/database.py` | `connect_timeout_seconds` se pasa a `asyncpg.create_pool(timeout=...)`; `open_pool` lo propaga |
| `app/nlp/semantic_cache.py` | Cada `pool.acquire()` lleva el tope de espera |
| `app/main.py` | `/health` publica `catalog_loaded` y `catalog_glosses`, y responde `status: degraded` si el catálogo está vacío. `/metrics.json` enmascara `llm_base_url` y `stt_ws_url` con `_redact_url` (esquema y ruta, host y puerto ocultos) |
| `.env.example` | `AUDIO_MAX_CHUNK_BYTES`, `DB_CONNECT_TIMEOUT_SECONDS`, `DB_ACQUIRE_TIMEOUT_SECONDS` y la explicación de `.env.local` |
| `.env.local.example` | **Nuevo.** Plantilla del override de desarrollo (Ollama local) |
| `.gitignore` | `.env.local` |
| `docker-compose.yml` | `env_file` incluye `.env.local` con `required: false` |
| `docs/sdd.md` | §7.1: `handleText(text, turn)`, `Gloss` y `CatalogEntry` con `semanticCategory`, `SemanticCache.lookup/store` con glosas, y la validación de audio en la narrativa. §7.2: el `done` también cierra el camino del error. §7.5: etiqueta `source`, los dos tramos de `rt_first_sign_ms`, direcciones enmascaradas y `/health` |
| `docs/sdd-changes.md` | Las entradas del 2026-10-21 (turno, `semanticCategory`, `done` en el error) y la de métricas quedan marcadas como **aplicadas** |
| `scripts/verify_audio_validation.py` | **Nuevo.** Los tres rechazos, el fragmento válido y la sesión que sigue viva |
| `scripts/verify_endpoints.py` | **Nuevo.** Enmascarado de URLs y catálogo en `/health` |
| `scripts/verify_official_config.py` | **Nuevo.** `.env` oficial, `.env.local` de desarrollo, `.gitignore` y compose. Corre en el host porque `.env` no entra a la imagen |
| `scripts/verify_database_resilience.py` | Se agregó la medición contra un servidor TCP que acepta y no contesta, y la comprobación del tope de `acquire` |
| `scripts/measure_cache_lookup.py` | **Nuevo.** Acierto en memoria frente a la consulta a Neon, con la misma frase |

## Configuración oficial y local

- `.env` (no versionado, esta máquina): `LLM_MODEL=gpt-4o-mini`, `LLM_BASE_URL=` vacío,
  `LLM_TIMEOUT_MS=5000`, `LLM_MAX_RETRIES=1`.
- `.env.local` (no versionado, esta máquina): `qwen3:4b-instruct`, Ollama en
  `http://host.docker.internal:11434/v1`, 10 000 ms y 0 reintentos, con `LLM_API_KEY=ollama`
  para no mandar la clave real a un servidor local. **El run local de esta máquina sigue
  usando Qwen**; borrar el archivo deja el backend contra el modelo oficial.

## Qué se midió

| Medición | Valor | Origen |
|---|---|---|
| Acierto del caché en memoria | p50 **10 µs**, p95 12 µs | `scripts/measure_cache_lookup.py`, 20 rondas, 109 filas, misma frase, contenedor del backend |
| Acierto del mismo caché contra Neon | p50 **254 ms**, p95 348 ms | ídem |
| Conexión a una base que acepta TCP y no contesta | **0,50 s** con tope de 0,5 s | `verify_database_resilience.py` |
| Espera por una conexión libre | 5 s | ídem, sobre un pool simulado |
| `/health` con el catálogo cargado | `status: ok`, `catalog_loaded: true`, 50 glosas | backend en marcha en `127.0.0.1:8080` |
| `/metrics.json` | `http://***/v1`, `ws://***/ws/transcribe` | ídem |
| `done` en el camino del error | `error` y `done` con el mismo `turn` (1) | Redmi Note 9S contra el backend en marcha; la app registró `frame 'done' del turno 1 descartado (turno en vuelo=null)` |

## Qué quedó pendiente

- **Commit y PR:** la sesión no commitea. Los cambios están en el árbol de `develop`.
- **Documentos y Overleaf:** el punto 2 (RF-CAT-03), el 7 (correcciones con control de
  cambios) y el 14 (SignAll) van en la sesión de documentos; Overleaf necesita permiso
  explícito y `track_changes_on_for_me`.
- **Texto en los logs:** se queda por ahora; se quita o enmascara antes de una demo con
  personas reales.
- **La caché en memoria:** la medición dice que se queda (10 µs contra 254 ms). No se
  cambió el código.
- **Estático:** `ruff check app scripts` pasa limpio. `mypy` reporta **7 errores previos**
  (`settings.py:109` por `Settings()` sin argumentos, dos en `segmenter/_clauses.py` y dos en
  `llm_client.py`); ninguno está en las líneas tocadas por esta sesión, pero quedan a la
  vista porque el comando los corre sobre todo `app/`.
- **Modelo local desde Docker:** con `ufw` activo, el contenedor no alcanza
  `host.docker.internal:11434` y la llamada al LLM agota los 10 s del `.env.local`. Es la
  trampa ya documentada; `docker-compose.host.yml` es el camino. Las frases que están en
  caché no tocan el modelo y funcionan.
