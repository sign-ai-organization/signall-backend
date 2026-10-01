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

---

## 3. Región de Neon y *scale-to-zero*

**Fecha:** 2026-10-01

### Región: se mantiene `us-east-2`

Latencia TCP desde el entorno de desarrollo (Colombia) a endpoints de
AWS en las regiones donde Neon ofrece proyectos, 20 muestras por región:

| Región | Mínimo | Mediana |
|---|---:|---:|
| us-east-1 (Virginia) | 92 ms | 234 ms |
| **us-east-2 (Ohio), actual** | 109 ms | 213 ms |
| sa-east-1 (São Paulo) | 141 ms | 240 ms |
| us-west-2 (Oregon) | 169 ms | 226 ms |
| eu-central-1 (Frankfurt) | 177 ms | 301 ms |

- Virginia y Ohio son equivalentes (~15 ms de diferencia en el mínimo,
  a favor de Ohio en la mediana). São Paulo es peor pese a la cercanía
  geográfica.

  **No se cambia.**
- La mediana duplica el mínimo en todas las regiones: la variación de
  la red local pesa más que la región elegida.

### *Scale-to-zero*: el problema

Misma frase en caché, `'Hola, ¿cómo estás?'`, inmediatamente y tras
~5 minutos sin actividad (backend encendido):

| Paso | Normal (ms) | Tras 5 min (ms) |
|---|---:|---:|
| cache.embed | 24.0 | 15.4 |
| cache.acquire | 0.0 | **3837.6** |
| cache.query | 143.7 | 297.5 |
| cache.release | 102.1 | 296.9 |
| **total** | **270.3** | **4448.0** |

Dos mecanismos cierran las conexiones a los 5 minutos:

1. Neon suspende el cómputo tras 5 min de inactividad. En el plan
   gratuito **no se puede desactivar**.
2. El pool de `asyncpg` cierra las conexiones inactivas tras 300 s
   (`max_inactive_connection_lifetime`, valor por defecto).

La siguiente consulta paga abrir una conexión nueva (TCP + TLS +
autenticación), despertar Neon y el precalentamiento del tipo `vector`
(~3.8 s), y las primeras consultas sobre el cómputo recién despierto
son más lentas. El pool se recupera solo: no hubo errores.

En el caso de uso (registro de datos en ventanilla) es normal que pasen
más de 5 minutos entre una atención y la siguiente, así que **la
primera frase de cada atención** pagaría este costo.

### Límites del plan gratuito de Neon

| Recurso | Límite |
|---|---|
| Cómputo | 100 CU-horas por proyecto al mes |
| Almacenamiento | 1 GB por proyecto |
| *Scale-to-zero* | A los 5 min, no desactivable |
| Al agotar el cómputo | Se suspende hasta el siguiente ciclo (no hay cobro) |

Con el cómputo mínimo (0.25 CU), 100 CU-horas equivalen a ~400 horas
encendida (~16 días seguidos). Mantener Neon despierto mientras el
backend esté encendido arriesga agotarlo si se olvida encendido.

### Alternativas evaluadas

| Alternativa | Por qué no / por qué sí |
|---|---|
| Mantener Neon despierto siempre que el backend esté encendido | Olvidar el backend encendido consume cómputo sin uso; dos semanas bastan para suspender la base de datos hasta el mes siguiente. |
| Mantenerlo despierto mientras haya sesiones WebSocket abiertas | Mismo riesgo si se olvida un cliente conectado. Requiere contar sesiones. |
| Desactivar *scale-to-zero* en Neon | Solo en planes pagos. |
| No hacer nada | ~4 s extra en la primera frase de cada atención. |
| **Mantenerlo despierto solo con actividad reciente** | **Elegida.** Gasto acotado en todos los casos, sin depender de apagar nada. |

### Cambio implementado

`DatabaseKeepAlive` (`app/persistence/keep_alive.py`), iniciado y
detenido con la app:

- Guarda la marca de tiempo de la **última actividad**: arranque del
  backend, apertura de una sesión WebSocket o llegada de una
  transcripción final.
- El arranque cuenta como actividad porque al encender el backend el
  pool ya despierta Neon (crea y precalienta las conexiones y carga el
  catálogo antes de aceptar clientes), y lo habitual es conectar el
  cliente un rato después. Sin esto, si pasan más de 5 min entre
  encender el backend y la primera sesión, Neon se dormiría de nuevo.
  Así queda despierto los primeros 20 min tras el arranque.
- Cada `DB_KEEPALIVE_INTERVAL_SECONDS` (240 s, por debajo de los 5 min
  de Neon) hace un `SELECT 1`, **solo si** la última actividad fue hace
  menos de `DB_KEEPALIVE_IDLE_WINDOW_SECONDS` (1200 s = 20 min). Fuera
  de esa ventana no hace nada y Neon se duerme solo.
- Al abrir una sesión WebSocket lanza un `SELECT 1` inmediato en
  segundo plano: si Neon estaba dormido, despierta mientras el usuario
  empieza a hablar y el STT espera el silencio que cierra la frase.
- El pool deja de cerrar conexiones inactivas por su cuenta
  (`DB_POOL_MAX_INACTIVE_CONNECTION_LIFETIME_SECONDS=0`): cuándo puede
  quedar inactiva la base de datos lo decide el keep-alive.

**Peor caso de consumo:** con todo olvidado encendido (con o sin
cliente conectado), Neon se mantiene despierto como mucho 20 min de
ventana desde la última actividad + 5 min hasta suspenderse ≈ 0.1
CU-horas.

**Pendiente:** medir de punta a punta:
1. Frase, pausa de más de 5 min **dentro** de la ventana, misma frase:
   se espera ~0.27 s y no ~4.4 s.
2. Pausa de más de 25 min (fuera de la ventana, Neon suspendido): se
   espera que el pool se recupere sin errores, con la primera frase más
   lenta.
