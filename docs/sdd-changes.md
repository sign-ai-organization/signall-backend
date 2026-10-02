# Cambios pendientes al SDD

Registro de inconsistencias encontradas en `docs/sdd.md` (o en sus
diagramas) durante la implementación — casos donde el diagrama, la
narrativa y/o la tabla de persistencia no coinciden entre sí. No se
edita `sdd.md` ni los diagramas directamente al encontrarlas: quedan
documentadas aquí hasta que decidas aplicarlas.

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

**Estado:** implementado en código así (Fase 5), pendiente de reflejar
en el diagrama/texto del SDD.
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
5.1), pendiente de agregar al diagrama.
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

**Estado:** implementado en código, pendiente de decidir si se refleja
en el SDD.
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

**Estado:** implementado en código, pendiente de reflejar en el SDD.
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

**Estado:** confirmado; implementado en código (`app/nlp/segmenter/`),
pendiente de reflejar en el SDD.
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
- Las oraciones se procesan en serie, en el orden en que se dijeron. El
  procesamiento en paralelo (más rápido cuando varias van al LLM, pero
  con reordenamiento antes de enviar) queda como paso posterior.

**Qué habría que cambiar en el SDD:**
1. **Figura 7:** el bucle `loop [para cada oración]` incluye la
   validación y un mensaje `Controller → App: segment` por iteración;
   tras el bucle, `Controller → App: done`.
2. **Figuras 4 y 5:** `translate_stream(text)` en `Orchestrator`;
   `split(text)` y `transform_sentence(sentence)` en `NLPService`.
3. **Contrato con Android:** los mensajes `segment` y `done` reemplazan
   la lista única de resultado.

**Estado:** implementado en código, pendiente de reflejar en el SDD y de
acordar con el cliente Android.
**Fecha:** 2026-10-02
