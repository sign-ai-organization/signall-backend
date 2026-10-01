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
`DB_POOL_MAX_SIZE`). La traza mide por separado obtener la conexión
(`acquire`), la consulta y devolverla al pool (`release`).

**Medición aislada** (script, mismo entorno, 4 `lookup` seguidos de
`'Hola, ¿cómo estás?'`, pool de 2 conexiones, sin medir `release`):

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
- Las primeras consultas en cada conexión son más lentas porque
  `asyncpg` prepara la sentencia una vez por conexión; después queda en
  caché.

**Medición de punta a punta** (`manual_translation_client` por
micrófono, mismo entorno):

Frase en caché — `'Hola, ¿cómo estás?'` (fuente: cache):

| Paso | Antes (ms) | Con pool (ms) |
|---|---:|---:|
| fingerprint | 0.2 | 0.1 |
| cache.embed | 61.9 | 24.0 |
| cache.connect → cache.acquire | 1347.1 | 0.0 |
| cache.query | 2355.2 | 143.7 |
| cache.release | — | 102.1 |
| validation | 0.0 | 0.0 |
| **total** | **3929.9** | **270.3** |

Frase nueva — `'Me llamo Julian.'` (fuente: llm):

| Paso | Antes (ms) | Con pool (ms) |
|---|---:|---:|
| fingerprint | 0.1 | 0.1 |
| cache.embed | 14.8 | 17.0 |
| cache.connect → cache.acquire | 1572.7 | 0.0 |
| cache.query | 2046.4 | 103.3 |
| cache.release | — | 99.9 |
| llm | 2631.9 | 3241.6 |
| store.embed | 13.8 | 14.3 |
| store.connect → store.acquire | 1448.3 | 0.0 |
| store.insert | 1639.9 | 103.2 |
| store.release | — | 101.0 |
| validation | 0.0 | 0.0 |
| **total** | **9985.5** | **3680.8** |

**Resumen:**

| Caso | Antes | Con pool | Mejora |
|---|---:|---:|---:|
| Acierto de caché | 3.93 s | 0.27 s | ≈ 14.5× (−93 %) |
| Fallo de caché (LLM) | 9.99 s | 3.68 s | ≈ 2.7× (−63 %) |
| Base de datos en el fallo de caché | 6.71 s | 0.41 s | ≈ 16× (−94 %) |

**Análisis:**

- `acquire` es prácticamente 0: desaparece el ~1.4 s de abrir conexión.
- Con la conexión reutilizada, cada operación contra Neon (`query`,
  `insert`, `release`) cuesta **un viaje de ida y vuelta, ~100 ms**. Lo
  que queda en la base de datos es latencia de red hacia `us-east-2`,
  no trabajo de Postgres.
- La suma de los pasos coincide con el `total` (diferencia < 1 ms en
  ambos casos): la traza cubre todo el pipeline.
- En el fallo de caché, el LLM pasa a ser el paso dominante (**88 %**
  del total). Su variación entre mediciones (1.9 s – 3.2 s en las
  pruebas de este día) es propia del proveedor, no de este cambio; por
  eso la mejora del fallo de caché se lee mejor en la fila "base de
  datos" del resumen.
- El `store` (embedding + INSERT + `release` ≈ 220 ms) sigue dentro del
  tiempo que espera el usuario, aunque no lo necesita para recibir su
  resultado.

### Evaluado y descartado por ahora: desactivar la limpieza del `release`

Al devolver una conexión al pool, `asyncpg` la limpia con una consulta
de reinicio (`pg_advisory_unlock_all()`, `CLOSE ALL`, `UNLISTEN *`,
`RESET ALL`) y espera la respuesta: un viaje de ida y vuelta, ~100 ms.
En el acierto de caché es el **38 %** del total (102 de 270 ms).

Se podría eliminar sobrescribiendo `Connection.get_reset_query()` para
que devuelva una cadena vacía. Sería seguro hoy: el código no deja
estado de sesión (no usa `SET`, `LISTEN`, bloqueos consultivos ni
cursores) y, con PgBouncer en modo transacción, el estado de sesión no
se mantiene de forma confiable de todos modos.

**Por qué no se hace por ahora:**

- El costo existe solo por la distancia a Neon. Con el backend
  desplegado en la misma región que la base de datos, un viaje de ida y
  vuelta cuesta 1–5 ms y el `release` deja de importar.
- El impacto es pequeño frente al resto: el STT espera 1500 ms de
  silencio para emitir el final y el LLM tarda 2–3 s.
- Desactiva una protección que la librería trae por defecto e introduce
  una regla implícita ("no usar `SET`/`LISTEN`") fácil de olvidar.
- Mover el `store` a segundo plano ya saca uno de los dos `release` del
  camino del usuario sin desactivar nada.

**Cuándo reconsiderarlo:** si, con el segmentador, los segmentos se
procesan en serie y los ~100 ms se acumulan por segmento sin poder
cambiar la región, o si la demo debe correr contra una base de datos
lejana.
