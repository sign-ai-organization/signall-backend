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

---

## 4. Llamada al LLM asíncrona

**Fecha:** 2026-10-01
**Cambio:** `LLMClient.transform` pasa de `invoke` (síncrono) a
`await ainvoke` (asíncrono).

**Problema:** la llamada síncrona dentro de una corrutina congelaba el
event loop de todo el backend durante 2–3 s por cada frase nueva: no se
reenviaba audio al STT, no corría el keep-alive y cualquier otra sesión
quedaba detenida.

**Medición:** una llamada real al LLM (`'¿Cuál es su nombre?'`, 2.06 s)
en paralelo con una tarea que marca cada 100 ms. Durante la llamada la
tarea marcó **18 de ~20** veces posibles; con la versión síncrona habría
marcado 0.

**Efecto en la latencia:** ninguno. El LLM tarda lo mismo y, para una
frase aislada, el total no cambia. El orden de las frases tampoco: los
mensajes del STT se siguen leyendo y traduciendo en serie
(`_forward_transcripts`), así que los parciales siguen llegando al
cliente después de la traducción en curso. El beneficio es que el resto
del sistema sigue funcionando durante la espera, y es requisito para
procesar segmentos en paralelo (segmentador) y para desacoplar la
traducción de la lectura del STT.

---

## 5. Evaluado y descartado: optimizar el cálculo del embedding

**Fecha:** 2026-10-01

**Qué se evaluó:**
- Calcularlo una sola vez por frase nueva: hoy se calcula en `lookup` y
  otra vez en `store` con el mismo texto. Se haría con memoización en
  `EmbeddingModel.embed`, para no cambiar firmas del SDD.
- Ejecutar el `encode` en un hilo (`asyncio.to_thread`) para no
  bloquear el event loop.

**Por qué se descarta:** según la traza, `cache.embed` y `store.embed`
cuestan ~12–17 ms (~25–60 ms la primera vez tras arrancar). Es menos del
1 % de una frase nueva (~2.5–3.5 s, dominada por el LLM) y un bloqueo
de ~15 ms no afecta el reenvío de audio ni el keep-alive. A cambio, la
memoización agregaría un segundo caché, distinto de `SemanticCache`,
con su propio tamaño configurable, consumo de memoria y riesgo de
compartir listas mutables. Tampoco se precalienta el modelo al
arrancar: ahorraría ~40 ms una sola vez por arranque.

**Cuándo reconsiderarlo:** si con el segmentador se procesan varios
segmentos en paralelo y los bloqueos del `encode` empiezan a sumarse en
la traza.

---

## 6. Guardar en caché en segundo plano

**Fecha:** 2026-10-01
**Cambio:** en un fallo de caché, `NLPServiceImpl` ya no espera
`SemanticCache.store`: lo programa como tarea en segundo plano y
devuelve las glosas de inmediato.

**Problema:** según la entrada 2, el usuario esperaba ~220 ms de
`store.embed` + `store.insert` + `store.release` en cada frase nueva,
aunque guardar en caché no es necesario para responderle.

**Detalles de la implementación:**
- `NLPServiceImpl` guarda referencia a las tareas pendientes, para que
  Python no las descarte antes de terminar.
- Los errores del `store` se registran en el log con el texto afectado.
  Si falla, la siguiente vez esa frase vuelve a ir al LLM: el usuario
  nunca recibe un resultado incorrecto.
- Al apagar el backend, `wait_for_pending_stores()` espera los `store`
  pendientes antes de cerrar el pool.
- La tarea corre con un contexto limpio: sus tiempos no se escriben en
  la traza de la frase, que ya se envió. Los pasos `store.*`
  desaparecen de la traza porque ya no forman parte del tiempo que
  espera el usuario.

**Caso límite aceptado:** si la misma frase nueva se repite antes de
que termine su `store` (< ~200 ms), ambas van al LLM y quedan dos filas
iguales en `semantic_cache`. No rompe nada.

**Medición de punta a punta** (`manual_translation_client`, mismo
entorno). Frase nueva, `'Me llamo Julian.'` en la entrada 2 frente a
`'Me llamo Julián.'` ahora (fuente: llm):

| Paso | Entrada 2 (ms) | Store en segundo plano (ms) |
|---|---:|---:|
| fingerprint | 0.1 | 0.1 |
| cache.embed | 17.0 | 15.5 |
| cache.acquire | 0.0 | 0.0 |
| cache.query | 103.3 | 189.1 |
| cache.release | 99.9 | 111.4 |
| llm | 3241.6 | 1865.8 |
| store.embed | 14.3 | — |
| store.acquire | 0.0 | — |
| store.insert | 103.2 | — |
| store.release | 101.0 | — |
| validation | 0.0 | 0.0 |
| **total** | **3680.8** | **2182.2** |

**Análisis:**

- Los pasos `store.*` (**218.5 ms**) desaparecen del tiempo que espera
  el usuario.
- La diferencia en el total (−1.5 s) se debe sobre todo a la variación
  del LLM (3.2 s → 1.9 s), no a este cambio. Sin contar el LLM, el
  resto del pipeline pasa de 439 ms a 316 ms (−123 ms): menos de los
  218 ms esperados porque en esta sesión la red estaba más lenta
  (`cache.query` 189 ms frente a 103 ms).
- En esta sesión la latencia de red varió bastante: entre frases en
  caché, `cache.query` fue de 147 a 646 ms y `cache.release` de 111 a
  306 ms (antes, ~100 ms estables). La primera consulta tras reiniciar
  (646 ms) incluye además preparar la sentencia en esa conexión.

**Comprobación de que el `store` se ejecuta:** la fila
`'Me llamo Julián.'` quedó guardada en `semantic_cache` por la tarea en
segundo plano. Después, `'Me llamo Julian'` (sin tilde ni punto) salió
del caché por similitud semántica con esa fila: distancia coseno
**0.110**, por debajo del umbral de 0.15.

---

## 7. De punta a punta con el STT optimizado

**Fecha:** 2026-10-01
**Contexto:** backend con todos los cambios anteriores y el STT
(`sign-ai-stt`) con sus optimizaciones (ver su `docs/performance.md`):
VAD con filtro de energía, parciales en segundo plano, cortes en pausas
y precalentamiento del modelo.

| Frase | Fuente | Backend (final → resultado) | LLM |
|---|---|---:|---:|
| "Hola, ¿cómo estás?" | cache | 0.36 s | — |
| "un tiempo bastante rápido." | llm | 2.66 s | 2.33 s |
| "Me llamo Julián." | llm | 1.39 s | 1.08 s |
| "¿Y ahora cómo estás?" | llm | 1.68 s | 1.28 s |
| "Hola, ¿cómo estás?" | cache | 0.29 s | — |

**Latencia total para el usuario** (fin de la habla → resultado). El
tramo del STT se toma de sus últimas mediciones (1.8–2.1 s, de los que
1.5 s son el silencio que cierra la frase):

| | STT | Backend | Total |
|---|---:|---:|---:|
| Frase en caché | 1.8–2.1 s | 0.3–0.4 s | ~2.1–2.5 s |
| Frase nueva (LLM) | 1.8–2.1 s | 1.4–2.7 s | ~3.2–4.8 s |

- En la línea base, una frase en caché tardaba ~3.9 s solo en el
  backend, y el STT podía tardar hasta 8 s en cerrar una frase.
- El STT entregó cada frase completa como un único final, con sus
  parciales antes.
- En frases nuevas, el LLM sigue siendo el 78–88 % del tiempo del
  backend (ver Pendientes: evaluar el modelo del LLM).

---

# Pendientes

Trabajo identificado y analizado, pero aplazado. Cada uno queda descrito
con lo necesario para retomarlo sin repetir el análisis.

## Evaluar el modelo del LLM

**Estado:** aplazado por decisión del autor (2026-10-01).

**Por qué importa:** tras las optimizaciones de este documento, el LLM
es el paso dominante en toda frase nueva: **74–88 %** del total (1.9–3.2
s según la medición, entradas 2 y 6). Es la mayor palanca de latencia
que queda en el backend. El resto del pipeline de una frase nueva suma
~0.3 s.

**Contexto:** el proveedor y el modelo son una decisión abierta del
proyecto. Hoy se usa OpenAI `gpt-4o-mini`, `temperature=0`, vía
LangChain (`app/nlp/llm_client.py`). LangChain se eligió precisamente
para poder cambiar de proveedor o modelo sin reescribir `LLMClient`
(ver `docs/decisions.md`, subfase 6.1).

**Qué hacer:**

1. **Elegir los candidatos** al momento de hacerlo, según
   disponibilidad y precio: el modelo actual como referencia, variantes
   más pequeñas o rápidas del mismo proveedor y, opcionalmente, modelos
   de otros proveedores compatibles con LangChain. No fijar la lista
   aquí: cambia rápido.
2. **Armar el conjunto de frases** a partir de
   `scripts/fixtures/oraciones_prueba.md`: unas 5–10 por tipo de frase
   (afirmativa, interrogativa sí/no, interrogativa de contenido,
   negativa, imperativa), priorizando las del dominio de registro de
   datos e incluyendo algunas marcadas con `(*)`. Total sugerido:
   30–50 frases.
3. **Escribir un script** `scripts/compare_llm_models.py` que, para
   cada modelo candidato:
   - Instancie `LLMClient` con ese modelo (mismo `SYSTEM_PROMPT`, misma
     temperatura), sin pasar por el caché semántico.
   - Llame `transform` para cada frase y mida la latencia de cada
     llamada.
   - Repita cada frase al menos 3 veces: la latencia de la API varía
     mucho entre llamadas (en este documento, 1.9–3.2 s para el mismo
     modelo).
   - Guarde los resultados en un CSV o JSON: modelo, frase, glosas,
     latencia.
4. **Métricas a comparar:**
   - **Latencia:** mediana (p50) y p95 por modelo. La mediana sola
     esconde los picos que el usuario sí nota.
   - **Formato válido (automático):** que cada glosa cumpla las reglas
     del prompt: mayúsculas, sin tildes (salvo Ñ), sin puntuación,
     separadas por comas. Hoy `gpt-4o-mini` ya las incumple a veces
     (devuelve `CÓMO` con tilde).
   - **Cobertura del catálogo (automático):** porcentaje de glosas que
     existen en `catalog`. Mide qué tan bien se ajusta el modelo al
     vocabulario disponible.
   - **Calidad (manual):** revisar las glosas de cada modelo frente a
     las del modelo actual en las mismas frases. Para las frases
     principales del caso de uso, idealmente contrastar con una
     referencia validada por alguien que conozca LSC.
   - **Costo:** precio por millón de tokens de entrada y salida de cada
     modelo, multiplicado por los tokens usados en la prueba.
5. **Decidir** con la tabla de resultados: el modelo más rápido cuya
   calidad y formato no empeoren frente al actual. Registrar la
   decisión en `docs/decisions.md` (qué se eligió y por qué) y las
   mediciones aquí, como una entrada nueva.
6. **Aplicar** cambiando `LLM_MODEL` (y el proveedor, si cambia) en
   `.env` y `.env.example`.

**Incluir en el mismo trabajo:** fijar `max_tokens` en `LLMClient`
como setting (`LLM_MAX_TOKENS`). La respuesta son unas pocas glosas,
así que un tope bajo protege contra respuestas desbocadas (costo y
tiempo). Casi no mejora la latencia normal.

**Descartado:** el caché de prompts del proveedor. En OpenAI solo
aplica a prompts de más de 1024 tokens, y el `SYSTEM_PROMPT` actual es
más corto.

## Pruebas pendientes del keep-alive (entrada 3)

1. Frase, pausa de más de 5 min dentro de la ventana de actividad,
   misma frase: se espera ~0.27 s y no ~4.4 s.
2. Pausa de más de 25 min (Neon suspendido): el pool debe recuperarse
   sin errores. Si aparece `[ERROR] No se pudo traducir el texto.`, el
   pool está entregando conexiones cerradas por Neon y hay que agregar
   un reintento al obtener la conexión.

## Confirmación del texto antes de traducir (RF-STT-03)

**Situación:** RF-STT-03 dice que el texto final no se envía al NLP de
forma automática: el usuario lo confirma, y según RF-UI-02 puede
editarlo antes. Hoy el `Controller` traduce cada transcripción final en
cuanto llega del STT.

**Qué hacer:** el backend envía el final al cliente y espera un mensaje
de confirmación del cliente con el texto (posiblemente editado); solo
entonces llama a `Orchestrator.translate`. Cambia el protocolo
WebSocket con Android, así que hay que acordarlo con el cliente y
registrarlo en `docs/sdd-changes.md`. `manual_translation_client`
necesitará una forma de confirmar (por ejemplo, confirmar
automáticamente cada final para las pruebas).

## Desacoplar la traducción y enviar segmentos al estar listos

**Depende de:** el segmentador.

1. **Desacoplar la traducción de la lectura del STT.** Hoy
   `_forward_transcripts` espera a que termine cada traducción antes de
   leer el siguiente mensaje del STT. Lanzar cada traducción como tarea
   y garantizar que los resultados se envíen al cliente en el orden de
   las frases (una frase posterior que sale del caché no puede llegar
   antes que una anterior que fue al LLM).
2. **Enviar cada segmento en cuanto esté listo**, en orden, en lugar de
   un único resultado por frase, para que el avatar empiece a señar
   antes. Cambia el contrato con Android y el SDD: registrar en
   `docs/sdd-changes.md`.

## Limpiar docstrings y comentarios largos

Quitar los docstrings y comentarios explicativos agregados durante estas
optimizaciones (`app/persistence/keep_alive.py`,
`app/observability/pipeline_trace.py`, `app/nlp/nlp_service_impl.py`,
`app/persistence/database.py`): el porqué ya está en este documento.

## Catálogo incompleto

La tabla `catalog` en Neon tiene 3 señas de las 50 del corpus, por eso
casi todas las glosas salen con `available: False`. Cargar el catálogo
completo antes de la demo.

## STT (`sign-ai-stt`)

- **README:** actualizar la descripción del final (ahora las frases
  largas se cortan en pausas y los finales vacíos no se envían).
- **Picos de transcripción:** no aparecieron tras los últimos cambios,
  pero solo hay 2 sesiones de prueba; vigilar los logs `[timing]`.
- **Inicio de frase recortado:** una vez se perdió un "No" inicial
  corto. Si se repite, ajustar `SPEECH_ONSET_WINDOW_MS`.
- **Varias sesiones a la vez:** todo se probó con un solo cliente; con
  varios, comparten la misma GPU.
