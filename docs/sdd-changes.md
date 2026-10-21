# Cambios pendientes al SDD

Registro de inconsistencias encontradas en `docs/sdd.md` (o en sus
diagramas) durante la implementación — casos donde el diagrama, la
narrativa y/o la tabla de persistencia no coinciden entre sí. No se
edita `sdd.md` ni los diagramas directamente al encontrarlas: quedan
documentadas aquí hasta que decidas aplicarlas.

Cada entrada lleva su estado al final. **Aplicado** significa que el
cambio se hizo en el SDD, y en qué fecha; esas entradas se quedan como
historia de lo que se corrigió. Las que todavía tienen trabajo quedan
abiertas.

---

## SemanticCache — tipo de `lookup()` y `store()`

**Dónde:** Figura 5 (`docs/diagrams/sdd-7.1-clases-2-nlp.drawio.png`),
sección 7.1 de `docs/sdd.md`.

**Inconsistencia:** el diagrama de clases dice:
```
+ lookup(text: String, fingerprint: Fingerprint): List<Segment>?
+ store(text: String, fingerprint: Fingerprint, segments: List<Segment>): void
```
Pero la narrativa que explica el mismo diagrama, un par de párrafos
después, dice que el resultado se guarda con
`SemanticCache.store(text, fingerprint, glosses)`, y que
`NLPServiceImpl` arma el `Segment` después, con
`buildSegment(fingerprint, glosses)` — en ambos casos (HIT y MISS).

**Evidencia a favor de la narrativa, no del diagrama:**
- La tabla `semantic_cache` (Figura 8, ya implementada en la Fase 1)
  tiene `glosses TEXT[]`, no una columna que represente un `Segment`
  completo (que incluiría `type`).
- `LLMClient.transform(text)` devuelve `List<String>` (glosas en texto
  plano) — es lo mismo que se guarda en el camino de cache-miss.
- Guardar `Segment` completo duplicaría `type`, que ya vive en la
  columna `phrase_type` de `semantic_cache`, usada además para filtrar
  en el propio `lookup`.

**Cambio propuesto:** `lookup(text, fingerprint) -> list[str] | None` y
`store(text, fingerprint, glosses: list[str]) -> None`. `Segment` se
construye únicamente en `NLPServiceImpl` (Fase 7), combinando
`fingerprint.category` con las `glosses` obtenidas de cualquiera de los
dos caminos.

**Estado:** el **diagrama** ya lo refleja: la Figura 5 tiene
`lookup(text, fingerprint): List<String>?` y
`store(text, fingerprint, glosses: List<String>)`, que es lo que hace el
código (`app/nlp/semantic_cache.py:164` y `:197`). Lo que **no** está
reflejado es la lista de clases de `docs/sdd.md:198-200`, que sigue con la
firma vieja: ver la entrada del 2026-10-21, que trata las dos cosas juntas.
**Fecha:** 2026-09-03

---

## Falta la clase `EmbeddingModel` en el diagrama de NLP

**Dónde:** Figura 5 (`docs/diagrams/sdd-7.1-clases-2-nlp.drawio.png`),
sección 7.1 de `docs/sdd.md`.

**Inconsistencia:** el propio plan de implementación (`docs/plan-implementacion-backend.md`,
subfase 5.1) ya señala que `EmbeddingModel` es una "clase identificada
como faltante en el diagrama de clases de NLP" — el diagrama actual no
la incluye, aunque `SemanticCache` depende de ella para convertir texto
a vector antes de comparar con pgvector.

**Cambio propuesto:** agregar `EmbeddingModel` a la Figura 5, con su
método `embed(text: String): List<Float>` (o el tipo equivalente), y
una relación de dependencia desde `SemanticCache` hacia `EmbeddingModel`.

**Estado:** implementado en código (`app/nlp/embedding_model.py`, Fase
5.1) y **agregado al diagrama**: la Figura 5 tiene `EmbeddingModel` con
`+ embed(text: String): List<Float>` y `SemanticCache` lo tiene como
atributo `embeddingModel`, que es lo que hace el código
(`app/nlp/semantic_cache.py:26` y `:100`). Falta en la lista de clases de
`docs/sdd.md`: ver la entrada del 2026-10-21.
**Fecha:** 2026-09-03

---

## Instrumentación de tiempos del pipeline (`PipelineTrace`)

**Dónde:** no figura en el SDD (ni en las Figuras 4–6 ni en la secuencia
de la Figura 7.2).

**Situación:** para medir la latencia de cada paso (huella, embedding,
conexión y consulta a `semantic_cache`, LLM, inserción, validación) se
agregó `app/observability/pipeline_trace.py`. La traza activa vive en un
`ContextVar`, de modo que **ninguna firma del SDD cambia**:
`Orchestrator.translate(text)`, `NLPService.transform(text)` y
`SemanticCache.lookup/store` conservan sus parámetros. Esto además
reemplaza el callback de debug `on_source`, que sí había agregado un
parámetro fuera del diseño a `translate` y `transform`.

El `Controller` crea la traza por cada transcripción final y la
registra en el log. Si `DEBUG_TRACE_ENABLED=true`, envía al cliente un
`{"type": "sentence_trace", "index", "text", "source", "steps_ms"}`
antes de cada oración y un `{"type": "trace", "steps_ms"}` con los pasos
globales (segmentación, validación, total) al terminar. El mensaje
`{"type": "source"}` se eliminó. (Actualizado el 2026-10-02 con el envío
por oración.)

**Cambio propuesto:** si se decide documentarlo, mencionarlo como
instrumentación no funcional (fuera del contrato funcional del
`Controller` con Android), y agregar el mensaje `trace` al protocolo
WebSocket como mensaje opcional de debug.

**Estado:** **aplicado.** Se decidió reflejarlo y quedó en el SDD: la
sección 7.5 (Instrumentación), nueva el 20/10/2026, describe el
`PipelineTrace`, las métricas `rt_*`, `llm_ms` y `cache_lookup_ms`, y dice
que la traza se escribe en el registro del servidor y, si está activada,
se envía además al cliente como un mensaje de tipo `trace`.
**Fecha:** 2026-10-01

---

## `SemanticCache.store` ya no bloquea la respuesta

**Dónde:** sección 7.2 de `docs/sdd.md` (secuencia del flujo de
traducción), paso 7 del camino de fallo de caché, y la Figura 7.2.

**Situación:** la secuencia muestra `NLPServiceImpl → SemanticCache:
store(text, fingerprint, glosses)` como paso síncrono antes de que
`NLPServiceImpl` devuelva la `List<Segment>` al `Orchestrator`. En el
código, `store` se sigue llamando con los mismos parámetros, pero como
tarea en segundo plano: `NLPServiceImpl` devuelve los segmentos sin
esperar a que termine.

**Por qué:** guardar en caché no es necesario para responder al usuario
y costaba ~220 ms por frase nueva (embedding + INSERT + devolver la
conexión al pool, ver `docs/performance.md`). Si el `store` falla, solo
se pierde la entrada de caché; el resultado entregado no cambia.

**Cambio propuesto:** en la Figura 7.2, marcar la llamada `store` como
asíncrona (flecha de mensaje asíncrono) y reflejarlo en la narrativa
del paso 7.

**Estado:** **aplicado.** La Figura 7.2 marca el paso 14 como
`(asíncrono, no se espera respuesta)` y el paso 14 de la narrativa del
SDD dice lo mismo ("en segundo plano: no se espera la respuesta").
**Fecha:** 2026-10-01

---

## Segmentación de oraciones antes de la huella (`SentenceSegmenter`)

**Dónde:** no figura en el SDD. Afecta la sección 6.3 (Figura 3), la
sección 7.1 (Figura 5, diagrama de clases de NLP) y la sección 7.2
(Figura 7, secuencia del flujo de traducción).

**Situación:** hoy `NLPServiceImpl.transform(text)` trata todo el texto
final del STT como una sola unidad: una huella, un `lookup` en
`SemanticCache` y, si falla, una llamada al LLM, y siempre devuelve un
único `Segment`. Cuando el STT entrega varias oraciones juntas ("me llamo
andrea || tengo veinticinco años || ¿dónde vive?"), la huella mezcla tipos
de frase, el caché casi nunca acierta (la combinación exacta no se repite)
y el LLM recibe un texto largo. El cambio divide el texto en oraciones
antes de la huella, con el método `hibrido_ligero` evaluado en el
laboratorio del segmentador (puntuación → marcadores de discurso →
cláusulas con spaCy `es_core_news_md`, con postproceso que fusiona las
muletillas), y cada oración recorre el camino huella → caché → LLM por su
cuenta.

**Clase nueva:**
- **`SentenceSegmenter`**: `+ segment(text: String): List<String>`.
  Devuelve las oraciones en orden; nunca devuelve una lista vacía para un
  texto no vacío. Carga el modelo local de spaCy una sola vez al
  construirse (al arrancar el backend), con una llamada de calentamiento.
  Clase concreta, sin interfaz, igual que los demás colaboradores de
  `NLPServiceImpl` (`GlossAnalyzer`, `SemanticCache`, `LLMClient`).

`NLPServiceImpl` recibe un cuarto colaborador, `segmenter: SentenceSegmenter`.
La firma `transform(text): List<Segment>` no cambia, así que `Orchestrator`
y `ValidatorService` no se tocan; solo que ahora la lista puede tener más
de un `Segment` (uno por oración, en orden). Las reglas internas del
segmentador (puntuación, marcadores, cláusulas, postproceso) son módulos
privados del paquete `app/nlp/segmenter/` y no se proponen como clases del
SDD.

**Qué habría que cambiar en el SDD:**
1. **Sección 6.3 / Figura 3 (actividades):** en el paso 4, antes de la
   huella, agregar "el texto se divide en oraciones", y envolver la huella,
   el caché y el LLM en "para cada oración". El paso 5 pasa a "se arma un
   segmento por oración, en orden".
2. **Sección 7.1 / Figura 5 (clases de NLP):** agregar la clase
   `SentenceSegmenter` con `+ segment(text: String): List<String>`, el
   atributo `segmenter: SentenceSegmenter` en `NLPServiceImpl` (asociación
   hacia `SentenceSegmenter`) y la nota de que se apoya en un modelo local
   de spaCy. En la narrativa: `NLPServiceImpl` primero llama a
   `segmenter.segment(text)` y luego, por cada oración, hace lo que hoy se
   describe para el texto completo.
3. **Sección 7.2 / Figura 7 (secuencia):** nuevo participante
   `SentenceSegmenter`; nuevo paso `NLPServiceImpl → SentenceSegmenter:
   segment(text)` que devuelve `List<String>`; los pasos 3–7 (huella,
   `lookup`, hit/miss, LLM, `store`) quedan dentro de un fragmento
   `loop [para cada oración]` y reciben `sentence` en vez de `text`. El
   paso 5 devuelve una `List<Segment>` con un segmento por oración.
4. **Sección 7.3 (persistencia):** sin cambios de esquema. Solo precisar
   que `semantic_cache.original_text` guarda una oración, ya no el texto
   final completo del STT (la narrativa ya dice "la oración tal como
   llegó", así que el texto queda más exacto que antes).
5. **Sección 6.2 (vista física):** opcional. Mencionar que el contenedor
   del backend incluye el modelo de spaCy `es_core_news_md` (≈ +440 MB de
   memoria, ≈ 0.7 s de carga al arrancar).
6. **Sección 1 (historial de cambios):** agregar la entrada.

Las secciones 6.1, 8.1, 8.2 y 8.3 no cambian: el segmentador es interno a
NLPService y no agrega contenedores, sistemas externos ni componentes C4.

**Interruptor (solo en el código, no en el SDD):** en el diseño el
segmentador es obligatorio. En el código se mantiene temporalmente
`SENTENCE_SEGMENTER__ENABLED` (por defecto `true`), una opción operativa
como `DEBUG_TRACE_ENABLED`: permite medir el antes/después (tasa de
aciertos del caché, llamadas al LLM, precisión del tipo de frase) con la
misma versión del backend, y apagarlo si falla con transcripciones reales
mientras la validación con casos nuevos del laboratorio sigue pendiente.
Desactivado, `NLPServiceImpl` recibe `segmenter=None` y procesa el texto
completo como antes. Se quita cuando esa validación confirme el método.

**Estado:** confirmado; implementado en código (`app/nlp/segmenter/`) y
**aplicado al SDD el 20/10/2026**. De los seis puntos de la lista de
arriba están hechos el 1 (§6.3), el 3 (§7.2), el 4 (§7.3) y el 6 (la fila
del historial). El 2 (§7.1) quedó a medias: el diagrama y la narrativa
sí lo tienen, la lista de clases no (ver la entrada del 2026-10-21). El 5,
que era opcional, no se hizo: el SDD no menciona el modelo de spaCy ni lo
que carga al contenedor del backend.
**Fecha:** 2026-10-02

---

## Envío de cada oración en cuanto está lista

**Dónde:** sección 7.2 (Figura 7, secuencia), clases de orquestación y
NLP (Figuras 4 y 5), y el contrato WebSocket del `Controller` con
Android.

**Situación:** con el segmentador, el backend esperaba a traducir todas
las oraciones y enviaba una sola lista. Si la última iba al LLM (~1.5–3
s), las anteriores, listas en ~0.2 s, esperaban con ella, y el avatar no
podía empezar a señar.

**Cambio en el código:**
- `NLPService` agrega `split(text): List<String>` y
  `transform_sentence(sentence): Segment`. `transform(text)` se mantiene
  y ahora se implementa con ambos.
- `Orchestrator` agrega `translate_stream(text)`, que entrega
  `(índice, total, ValidatedSegment)` por oración, en orden, en cuanto
  cada una está traducida y validada. `translate(text)` se mantiene y se
  implementa con `translate_stream`.
- El `Controller` envía un mensaje por oración y uno al final:
  `{"type": "segment", "index", "total", "segment": {...}}` y
  `{"type": "done"}`. Antes enviaba una lista JSON con todos los
  segmentos. `total` se conoce tras segmentar, así que el cliente sabe
  cuántas oraciones esperar desde la primera.
- Todas las oraciones se traducen a la vez (una tarea por oración) y se
  envían en el orden en que se dijeron: cada una sale en cuanto está
  lista y todas las anteriores ya se enviaron. Así una oración del caché
  no espera a que termine el LLM de la anterior, y varias llamadas al
  LLM se solapan en lugar de sumarse.

**Qué habría que cambiar en el SDD:**
1. **Figura 7:** el bucle pasa a un fragmento `par [para cada oración]`
   que incluye la validación, seguido del envío en orden de un mensaje
   `Controller → App: segment` por oración; al final,
   `Controller → App: done`.
2. **Figuras 4 y 5:** `translate_stream(text)` en `Orchestrator`;
   `split(text)` y `transform_sentence(sentence)` en `NLPService`.
3. **Contrato con Android:** los mensajes `segment` y `done` reemplazan
   la lista única de resultado.

**Estado:** implementado en código y **aplicado al SDD el 20/10/2026**: la
Figura 7.2 tiene los pasos 22 (`segment`) y 23 (`done`), y la narrativa
describe `translateStream`, `sendSegment(index, total, segment)` y el aviso
de fin. **Con el cliente Android ya está acordado**: el contrato de
`docs/android-integration.md` §3.1 usa `segment` y `done`, con `index` y
`total` reales desde el primero.
**Fecha:** 2026-10-02

---

## Las animaciones GLB viven en la app Android, no en el backend

**Dónde:** Vista física 6.2 y C4 de componentes (el backend agrupa un
"Static GLB Server"), Figura 8 (`catalog.glb_animation_path`), y la
fase 12 del plan de implementación ("Servidor estático de GLB").

**Situación:** el SDD ubica un servidor estático de archivos GLB dentro
del contenedor del backend, y el catálogo guarda rutas servidas por él
(ej. `/static/glb/casa.glb`). Decisión del equipo: las animaciones GLB
se empaquetan en la app Android. El backend solo indica qué seña
reproducir (glosa y `available`); la app resuelve la animación con sus
propios recursos. El servidor estático no se implementó.

**Cambio propuesto:**
1. Quitar el "Static GLB Server" de la Vista 6.2 y del C4 de
   componentes del backend, y ubicar los GLB en el contenedor de la app.
2. Redefinir `catalog.glb_animation_path` como la referencia al recurso
   dentro de la app (formato por acordar con el equipo Android), o
   eliminarlo si la app usa la glosa como clave.
3. Marcar la fase 12 del plan como descartada.

**Estado:** decisión tomada y **aplicada al SDD el 20/10/2026**: el
servidor estático de GLB ya no está en la Vista 6.2 ni en el C4 de
componentes, y `catalog.glb_animation_path` quedó redefinido como la clave
con la que la aplicación encuentra la animación entre las que trae dentro
de sí ("no es una dirección en la red"). Los tres puntos del cambio
propuesto están hechos, y el formato de la referencia quedó resuelto por
esa vía.
**Fecha:** 2026-10-02
---

## Vuelta al flujo documentado: la unidad de traducción es la oración

**Dónde:** Vista de procesos 6.3 (nodo "Divide el texto final en oraciones"),
secuencia 7.2 (`split(text)` → `segment(text)` → por oración), Vista de
componentes 6.1 (`Split(text): sentences`) y este contrato
(`docs/android-integration.md` §3.1).

**Situación:** entre el 13 y el 14 de octubre se implementó en la rama
`develop` un camino que **traducía por fragmentos mientras la persona todavía
hablaba**: `app/realtime/incremental.py` decidía con *timestamps por palabra*
qué palabras ya estaban "representadas" y mandaba un `segment` por cada una, con
`total: 0` y `stream: true`. Eso no aparece en ningún diagrama del SDD ni en
los requisitos. Cuatro documentos del repo de documentos dicen lo contrario:
la unidad es la oración, y el envío al módulo de lenguaje lo decide la persona
(RF-STT-03) o la pausa (modo en vivo), nunca una palabra a medio formar.

**Qué se implementó mientras tanto:** el backend quedó en `flujo-oraciones`,
que sale de `origin/main`, donde el flujo documentado ya estaba entero
(`Orchestrator.translate_stream` con `_translate_sentence`, `index` y `total`
reales, un `Controller` de 90 líneas). Se conservó de `develop` lo que no es
del camino por palabras:

- El prompt con el catálogo como vocabulario cerrado y `_repair_glosses` /
  `_merge_fragments` (`ac013d4`). Con oración sigue siendo necesario: es lo que
  evita que "cómo estás" vuelva como `TÚ, ESTAR, CÓMO`, y las tres glosas son
  irreproducibles. **Ojo:** la parte del **vocabulario cerrado se quita** por la
  decisión **D-7** (owner, 2026-10-16; ver `docs/performance.md` §9): la lista
  de glosas **sale del prompt**. **La reparación y la fusión se quedan**, y el
  validador también.
- El caché semántico en memoria y las métricas, renombradas (§ abajo).
- `docs/performance.md`, `docs/android-integration.md` y las verificaciones.

**Cambio en el contrato, que es lo único que un diagrama no puede mostrar:**

Antes, un `final` del STT disparaba la traducción. Ahora **solo se traduce lo
que el cliente manda como `{"type":"text"}`**; las transcripciones se reenvían
para mostrarse y nada más. Con eso el backend cumple RF-STT-03 por
construcción —no existe forma de que una frase dictada llegue al módulo de
lenguaje sin que la app la mande— y el frame `mode` y el flag `dictation`, que
existían solo para distinguir los modos de captura, dejan de ser necesarios.
Los tres modos de captura quedan como decisión de la app: dictado (espera
confirmación), en vivo (reenvía sola al cerrarse la frase) y en vivo con el
micrófono siempre prendido (`◢◢ TR`).

**Por qué el SDD no cambia:** los diagramas 6.3, 7.2 y 6.1 no dibujan quién
invoca `split(text)`; dibujan el trabajo que se hace desde ahí. Lo único que
cambia es de dónde llega el texto, y eso ya estaba documentado como decisión
de la app en RF-STT-03 y en `trazabilidad.md` §"Modos de envío".

**Métricas renombradas.** Los nombres `rt_utterance_*` y `rt_chunk_*`
describían fragmentos. Ahora:

| Antes | Ahora | Qué mide |
|---|---|---|
| `rt_utterance_ms` | `rt_phrase_total_ms` | última oración enviada − frase recibida |
| `rt_chunk_delay_ms` | `rt_sentence_delay_ms` | cada oración por separado |
| `rt_chunks_total` | `rt_sentences_total` | oraciones enviadas |
| `rt_utterances_total` | `rt_phrases_total` | frases traducidas |
| `rt_utterance_segments` | `rt_phrase_sentences` | oraciones por frase |
| `rt_first_sign_ms` | `rt_first_sign_ms` (igual) | primera oración enviada − frase recibida |

`rt_first_sign_ms` conserva el nombre a propósito: es la latencia de titular y
el número que los documentos del proyecto citan como línea base. Además su
punto de partida pasó a ser el envío del cliente, que es la "confirmación de
envío del usuario" de RNF-DES-01.

**Pendiente:** remedir `rt_first_sign_ms` con las 28 frases de
`../sign-ai-stt/fixtures/audio` (los clips se generan con
`scripts/make_audio_fixtures.py --all` en el repo del STT, y la medición se
corre con `../sign-ai-android/tools/verificar-tiempo-real.sh`). La
cifra publicada de 913 ms p50 / 1336 ms p95 era del camino por palabras y con
oraciones **no es comparable**: ahora se mide al terminar la primera oración y
no a mitad de camino.

**Fecha:** 2026-10-15

---

## 2026-10-16 — La traducción sale del bucle de lectura, y el socket con el STT se suelta al cerrar

Dos cambios en el mismo archivo (`app/controller/router.py`), medidos antes y
después. Ninguno cambia el contrato con la app.

### 1. `handle_text` va a su propia tarea, una a la vez

**Qué dice cada fuente:**

| Documento | Dice |
|---|---|
| `docs/performance.md:676-681` | "Desacoplar la traducción de la lectura del STT. Hoy `_forward_transcripts` espera a que termine cada traducción antes de leer el siguiente mensaje del STT. **Lanzar cada traducción como tarea** y garantizar que los resultados se envíen al cliente en el orden de las frases." |
| `docs/performance.md:331-334` | lo nombra como requisito |
| `../sign-ai-docs/documentos/requerimientos/SignAI_Requerimientos_Consolidados_v0.16.md:160` (RF-INT-SW-04) y `:553` (RNF-REL-01) | no bloquear el hilo principal |
| `app/controller/controller.py:29-36` (docstring) | "The translation now happens on its own task and the read loop keeps draining the STT" — **ya lo afirmaba y no era cierto** |

**Qué se implementó:** `_PhraseTranslator` corre cada frase en su propia tarea
y un `asyncio.Lock` las serializa. El bucle de lectura nunca espera a una
traducción.

**Por qué una a la vez y no todas en paralelo:** el cliente ya prohíbe dos
frases en vuelo (`MainScreenState.requestTranslation` y `sendLivePhrase`
rechazan si hay una en curso), así que el intercalado no puede ocurrir. Y si
ocurriera, el `index` de las oraciones dejaría de corresponder al orden en que
llegaron y el avatar representaría la frase al revés. Ningún documento exige
traducir frases en paralelo.

**Medido** (`tools/verificar-bloqueo-lectura.py`, audio a 1x con un muestreador
independiente del bucle de recepción):

| | antes | después |
|---|---|---|
| retraso del audio durante la traducción | 991 ms (y 8438 ms en la primera corrida) | **0 ms** |
| `rt_read_loop_busy_ms` p50 / max | 0,155 ms / **931 ms** | 0,151 ms / **0,595 ms** |

La métrica es nueva: `rt_read_loop_busy_ms` es el trabajo por frame del bucle
de lectura, sin contar la espera. Es la que convierte el arreglo en algo que se
puede afirmar —sin ella, "ya no se traba" sería una anecdote de una corrida.

### 2. El socket con el STT se cierra al terminar la sesión

**Qué estaba mal:** `asyncio.gather(_forward_audio(...), _forward_transcripts(...))`
esperaba a las dos. `_forward_audio` termina cuando el cliente se va;
`_forward_transcripts` bloquea en `receive()` esperando un mensaje del STT que
no llega nunca. El `gather` no volvía, así que el `finally` que cierra el
socket con el STT no corría.

**Medido** (`tools/verificar-conexiones-stt.py`, contando sockets establecidos
con el puerto del STT desde el host):

| | antes | después |
|---|---|---|
| 5 sesiones | +10 conexiones colgando | 0 |
| 10 sesiones | +18 conexiones colgando | 0 |

**Qué se implementó:** `asyncio.wait(..., return_when=FIRST_COMPLETED)`: la
sesión termina con la primera de las dos mitas y la otra se cancela. Antes de
cerrar se cancelan también las traducciones en vuelo.

**Nota de ciclo de vida:** `docs/sessions/2026-10-15-vuelta-al-flujo-por-oraciones.md:105-113`
advertía que tocar el cierre de sesión es decisión del owner. Queda tomada
(opción B: arreglarlo junto con lo otro, porque toca el mismo archivo).

### 3. `sessions_active` decía siempre 1

No es un cambio de comportamiento sino de una métrica que mentía: leía su
propio valor con `counter_value()`, que mira el mapa de contadores y siempre
devuelve 0, así que el gauge era `0 + 1`. Ahora existe `gauge_value()`. La
misma clase de error estaba en el STT, en `stt_sessions_active` y
`ConcurrencyGauge`, y se corrigió de los dos lados.

### 4. `llm_ms` y `cache_lookup_ms` como métricas de verdad

**Qué decía el pendiente:** `docs/performance.md:756` — "contrastar
`rt_sentence_delay_ms` con la traza por oración: el histograma dice cuándo salió
cada oración pero no por qué se demoró esa".

**Qué estaba mal:** el tiempo del modelo solo existía como paso de
`PipelineTrace`, que necesita `DEBUG_TRACE_ENABLED=true` y un log para
leerse. Ahora son histogramas de `/metrics`: `llm_ms{model}` mide la llamada al
modelo y `cache_lookup_ms` la consulta a la caché semántica.

Las dos juntas porque por separado se prestan a confusión: una corrida con
caché caliente no muestra `llm_ms` en absoluto, y su p50 de `rt_first_sign_ms`
sale de 2 dígitos. Medido con `qwen3:4b-instruct` en Ollama local: `llm_ms`
p50 442 ms / max 881 ms, `cache_lookup_ms` p50 48 ms.

### 5. `silence_timeout_ms` en el `/health` del backend

El STT ya lo publica en su `/health`. La app nunca habla con el STT, así que
para mostrarlo en el overlay de depurar (decisión D-6 del cliente) el valor tiene
que pasar por acá: una tarea relee el `/health` del STT cada
`STT_CONFIG_POLL_SECONDS` (30 s por defecto, configurable) y lo publica en el
`/health` y el `/metrics.json` de este servicio.

**Es aditivo:** un campo más en un endpoint que ya existía. El protocolo del
WebSocket con la app no cambia, así que `docs/android-integration.md` no necesita
cambios por esto.

**Fecha:** 2026-10-16

---

## La lista de clases de la §7.1 no coincide con su propio diagrama

**Dónde:** `docs/sdd.md:192-210` (la lista "Clases y elementos principales"
de la Figura 5), contra
`../sign-ai-docs/diagramas/draw.io/sdd-7.1-clases-2-nlp.drawio` y su PNG,
que es el mismo archivo que se ve en
`docs/diagrams/sdd-7.1-clases-2-nlp.drawio.png`.

**Qué dice cada fuente:**

| Fuente | Dice |
|---|---|
| El diagrama (Figura 5) | `NLPServiceImpl` con **cuatro** atributos: `segmenter`, `analyzer`, `cache`, `llmClient`. `SemanticCache.lookup(text, fingerprint): List<String>?` y `store(text, fingerprint, glosses: List<String>)`. Una clase `EmbeddingModel` con `+ embed(text: String): List<Float>`, de la que `SemanticCache` depende |
| La lista de clases de `docs/sdd.md:192-210` | `NLPServiceImpl` con **tres** atributos (sin `segmenter`); `lookup(...): List<Segment>?` y `store(..., segments: List<Segment>): void`; **no menciona `EmbeddingModel`** |
| La narrativa de la misma §7.1 (`docs/sdd.md:211-213`) | "**cuatro** colaboradores", incluido `segmenter`, y usa `store(text, fingerprint, glosses)` |
| El SDD de Overleaf (`main.tex:318`, `:323`, `:325`) | No tiene lista de firmas: pone la Figura 5 y la narrativa, que ya habla de los cuatro colaboradores y de `store(..., glosses)` |

**Cuál parece correcta:** el diagrama. Es el que describe el código:
`app/nlp/semantic_cache.py:164` devuelve `list[str] | None` y `:197` recibe
`glosses: list[str]`, y `app/nlp/embedding_model.py:10` tiene
`embed(text: str) -> list[float]`.

**Por qué sigue así:** esa lista del Markdown es una transcripción escrita a
mano de la Figura 5. El 20/10/2026 se corrigió el SDD al pasar del flujo por
palabras al flujo por oraciones, y en esa pasada se actualizaron los
diagramas y la narrativa, pero la lista de firmas se quedó atrás.

**Qué habría que cambiar:** tres puntos en `docs/sdd.md:192-210`:
1. Agregar `segmenter: SentenceSegmenter` a los atributos de
   `NLPServiceImpl`.
2. Poner las firmas de `SemanticCache` como las del diagrama:
   `lookup(text, fingerprint): List<String>?` y
   `store(text, fingerprint, glosses: List<String>): void`.
3. Agregar la clase `EmbeddingModel`, con `+ embed(text: String): List<Float>`,
   y la dependencia de `SemanticCache` hacia ella.

**Estado:** documentado; **no se aplicó**, por la regla de que los cambios
del SDD se anotan en este archivo y los aplica el owner.
**Fecha:** 2026-10-21

---

## El identificador de turno y el `done` del error (2026-10-21)

Los nueve cambios de código que faltaban (el §10.3 del contraste) se
implementaron el 2026-10-21. Dos de ellos tocan el SDD, y ninguno toca un
diagrama.

### 1. `handleText` recibe el identificador de turno

**Qué dice cada fuente:**

| Fuente | Dice |
|---|---|
| `docs/sdd.md:166` y la Figura 4 (clases de orquestación) | `+ handleText(text: String): void` |
| `docs/sdd.md:180` (narrativa) | "expose tres métodos de entrada: `handleAudioChunk(chunk)` […] `handleText(text)` […] y `handleEnd()`" |
| El código (`app/controller/controller.py`) | `handle_text(text: str, turn: Any = None)` |

**Por qué cambia:** el cliente manda un identificador de turno en el frame
`text` (§3.2 de `docs/android-integration.md`) y el backend lo copia, sin
interpretarlo, en los frames `segment`, `done` y `error`. El Controller tiene
que saber cuál es para poder ponerlo.

**Qué habría que cambiar:** `docs/sdd.md:166` y `:180`, y la lista de
firmas del §7.1: `handleText(text: String, turn: Integer): void`. El
identificador es **opaco**: el backend no lo parsea, no lo compara y no lo
genera, así que en el SDD conviene decir "el identificador que manda el
cliente" y no "un entero".

**Estado:** documentado; **no se aplicó**, por la regla del repo. El
contrato con la app sí está actualizado, en `docs/android-integration.md`
§3.2 y §4.
**Fecha:** 2026-10-21

### 2. `Gloss` lleva la categoría semántica del catálogo

**Qué dice cada fuente:**

| Fuente | Dice |
|---|---|
| La Figura 8 (persistencia, `docs/sdd.md` §7.3) | La tabla `catalog` tiene la columna `semantic_category` |
| `docs/sdd.md:192-210` (la lista de clases de la §7.1) | `Gloss(text, available, glbPath)` |
| El código (`app/domain/models.py`) | `Gloss(text, available, glb_path, semantic_category)` |

**Por qué cambia:** la decisión del owner para el punto 11 del contraste fue
**leer** la columna, para que el código quede de acuerdo con el diagrama y no
al revés. `CatalogRepository.load_all()` la lee, `CatalogEntry` la guarda y
`ValidatorServiceImpl` la pasa a cada `Gloss`, que es lo que viaja en el
frame `segment`.

**Qué habría que cambiar:** `docs/sdd.md:192-210`: `Gloss(text, available,
glbPath, semanticCategory)`. Y la Figura 8, que ya la tiene: por eso el
diagrama no se toca.

**Nota:** el `segment` lleva un campo más (`semantic_category` en cada
glosa). Es **aditivo**: el parser de la app ignora lo que no conoce, así que
un cliente viejo no se rompe. La app no lo usa todavía.

**Estado:** documentado; **no se aplicó**, por la regla del repo.
**Fecha:** 2026-10-21

### 3. El `done` también se manda cuando la traducción falla

**Qué dice cada fuente:**

| Fuente | Dice |
|---|---|
| La Figura 7.2 (secuencia), paso 23 | `Controller → Android Client: el frame done, cuando ya salió la última oración` |
| `docs/sdd.md:290` (narrativa) | "Cuando ya salió la última, Controller envía el aviso de fin de la traducción" |
| El código | El `done` se manda en los dos caminos: el que salió bien y el que falló |

**Por qué cambia:** el `done` es la señal de "terminé", y el turno se cierra
también cuando la frase falla. Antes el backend mandaba el `error` y nada
más, y la app esperaba su propio reloj de 15 s para reportar como fallida una
frase que ya había fallado (punto 39 del contraste).

**Qué habría que cambiar:** nada. La Figura 7.2 ya tiene el paso 23 al
final del bucle, y el `error` no es un paso del flujo funcional: el SDD
documenta el camino que funciona. Lo que sí hay que escribir es que el `done`
cierra el turno **también en el camino del error**, y eso está en
`docs/android-integration.md` §4.

**Estado:** documentado; **no se aplicó**, por la regla del repo.
**Fecha:** 2026-10-21
