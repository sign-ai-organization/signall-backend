# Bitácora de rendimiento

Mediciones de latencia del pipeline de traducción y efecto de cada
optimización. Cada entrada registra qué se midió, cómo, qué se concluyó
y qué cambio se hizo. Sirve como evidencia de "antes / después" para
cada mejora.

Las mediciones por paso vienen de `PipelineTrace`
(`app/observability/pipeline_trace.py`), visibles en los logs del
backend y, con `DEBUG_TRACE_ENABLED=true`, en
`scripts/manual_translation_client.py`.

Entradas más recientes al final.

---

## 1. Línea base: una conexión nueva a Neon por consulta

**Fecha:** 2026-10-01
**Entorno:** backend local (Windows), Neon PostgreSQL vía pooler
(PgBouncer) en `us-east-2` (AWS Ohio), LLM `gpt-4o-mini`. Medido con
`manual_translation_client` hablando por micrófono.

**Frase en caché** — `'Hola, ¿cómo estás?'` (fuente: cache):

| Paso | ms | % del total |
|---|---:|---:|
| fingerprint | 0.2 | 0 % |
| cache.embed | 61.9 | 2 % |
| cache.connect | 1347.1 | 34 % |
| cache.query | 2355.2 | 60 % |
| validation | 0.0 | 0 % |
| **total** | **3929.9** | |

**Frase nueva** — `'Me llamo Julian.'` (fuente: llm):

| Paso | ms | % del total |
|---|---:|---:|
| fingerprint | 0.1 | 0 % |
| cache.embed | 14.8 | 0 % |
| cache.connect | 1572.7 | 16 % |
| cache.query | 2046.4 | 20 % |
| llm | 2631.9 | 26 % |
| store.embed | 13.8 | 0 % |
| store.connect | 1448.3 | 15 % |
| store.insert | 1639.9 | 16 % |
| validation | 0.0 | 0 % |
| **total** | **9985.5** | |

**Análisis:**

- En el acierto de caché, el **94 %** del tiempo es la base de datos. El
  trabajo propio del backend (huella, embedding, validación) cuesta
  ~62 ms.
- En el fallo de caché, la base de datos suma **~6.7 s (67 %)** frente a
  **2.6 s (26 %)** del LLM. Además, el usuario espera **~3.1 s** del
  `store` (embedding + conexión + INSERT) que no necesita para recibir
  su resultado.
- `connect` (~1.4 s, estable entre llamadas): `asyncpg.connect()` abre
  TCP + TLS + autenticación en cada consulta. Al ser estable, apunta a
  varios viajes de ida y vuelta de red más que a arranques en frío de
  Neon.
- `query` (~2 s para una consulta trivial sobre una tabla pequeña): en
  una conexión nueva, `asyncpg` prepara la sentencia y consulta el
  catálogo de Postgres para resolver el tipo `vector` de pgvector —
  varios viajes de ida y vuelta adicionales que con una conexión
  reutilizada se pagan una sola vez. Lo mismo explica el INSERT.
- El embedding se calcula dos veces en el fallo de caché (`cache.embed`
  y `store.embed`), aunque su costo (~14 ms) es menor.

**Conclusión:** el cuello de botella principal no es el LLM sino abrir
una conexión por consulta. Siguiente paso: pool de conexiones.

---

## 2. Pool de conexiones asyncpg

**Fecha:** 2026-10-01
**Cambio:** un único `asyncpg.Pool` creado al arrancar
(`app/persistence/database.py`), compartido por `SemanticCache` y
`CatalogRepository`. Cada conexión nueva del pool resuelve el tipo
`vector` al abrirse (`init`), para que la primera consulta real no pague
la introspección. Tamaño configurable (`DB_POOL_MIN_SIZE`,
`DB_POOL_MAX_SIZE`).

**Medición aislada** (script, mismo entorno, 4 `lookup` seguidos de
`'Hola, ¿cómo estás?'`, pool de 2 conexiones):

| Llamada | cache.embed | cache.acquire | cache.query |
|---|---:|---:|---:|
| 1 | 28.7 | 0.1 | 529.0 |
| 2 | 11.3 | 0.0 | 391.7 |
| 3 | 12.9 | 0.0 | 296.7 |
| 4 | 12.3 | 0.0 | 247.4 |

- Crear y precalentar el pool al arrancar cuesta ~4.2 s, una sola vez,
  fuera del camino del usuario.
- Latencia de red pura hacia Neon (`SELECT 1` en conexión abierta):
  **~100 ms** por viaje de ida y vuelta.

**Análisis:**

- `cache.acquire` es prácticamente 0: desaparece el ~1.4 s de conexión.
- `cache.query` baja de ~2 s a **~250–530 ms**. Las primeras llamadas
  en cada conexión son más lentas porque `asyncpg` prepara la sentencia
  una vez por conexión; después queda en caché.
- El `lookup` completo pasa de **~3.7 s a ~0.3 s** (≈ 12× más rápido).
- Lo que queda es dominado por la red: ~100 ms por viaje de ida y
  vuelta a `us-east-2`, y la consulta necesita 2–3 viajes. Bajar de ahí
  requiere acercar la base de datos (región de Neon) o reducir viajes.

**Medición de punta a punta** (`manual_translation_client` por
micrófono, mismo entorno):

Frase en caché — `'Hola, como estas?'` (fuente: cache):

| Paso | Antes (ms) | Con pool (ms) |
|---|---:|---:|
| fingerprint | 0.2 | 0.1 |
| cache.embed | 61.9 | 31.1 |
| cache.connect → cache.acquire | 1347.1 | 0.0 |
| cache.query | 2355.2 | 233.4 |
| validation | 0.0 | 0.0 |
| **total** | **3929.9** | **361.2** |

Frase nueva — `'Me llamo Julian.'` antes, `'Me llamo Camilo.'` con
pool (fuente: llm):

| Paso | Antes (ms) | Con pool (ms) |
|---|---:|---:|
| fingerprint | 0.1 | 0.1 |
| cache.embed | 14.8 | 14.7 |
| cache.connect → cache.acquire | 1572.7 | 0.0 |
| cache.query | 2046.4 | 134.1 |
| llm | 2631.9 | 1899.2 |
| store.embed | 13.8 | 12.3 |
| store.connect → store.acquire | 1448.3 | 0.0 |
| store.insert | 1639.9 | 141.4 |
| validation | 0.0 | 0.0 |
| **total** | **9985.5** | **2576.2** |

**Resumen:**

| Caso | Antes | Con pool | Mejora |
|---|---:|---:|---:|
| Acierto de caché | 3.93 s | 0.36 s | ≈ 11× (−91 %) |
| Fallo de caché (LLM) | 9.99 s | 2.58 s | ≈ 3.9× (−74 %) |

**Observaciones:**

- En el fallo de caché, el LLM pasa a ser el paso dominante (**74 %**
  del total). La variación del LLM entre ambas mediciones (2.6 s → 1.9 s)
  es propia del proveedor, no de este cambio.
- La suma de los pasos medidos es menor que el `total`: ~97 ms en el
  acierto y ~374 ms en el fallo. Coincide con ~1 viaje de ida y vuelta
  (~100 ms) por cada `pool.release()`, que no está instrumentado:
  `asyncpg` reinicia el estado de la conexión al devolverla al pool, y
  eso requiere una consulta al servidor. Es candidato a optimizar más
  adelante (devolver la conexión sin esperar, o ajustar la consulta de
  reinicio).
- El `store` todavía suma ~150 ms más su `release` dentro del tiempo que
  espera el usuario; moverlo a segundo plano queda como mejora aparte.
