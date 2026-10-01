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

El `Controller` crea la traza por cada transcripción final, la registra
en el log y, si `DEBUG_TRACE_ENABLED=true`, envía al cliente un mensaje
`{"type": "trace", "source": ..., "steps_ms": {...}}` después del
resultado. El mensaje `{"type": "source"}` se eliminó.

**Cambio propuesto:** si se decide documentarlo, mencionarlo como
instrumentación no funcional (fuera del contrato funcional del
`Controller` con Android), y agregar el mensaje `trace` al protocolo
WebSocket como mensaje opcional de debug.

**Estado:** implementado en código, pendiente de decidir si se refleja
en el SDD.
**Fecha:** 2026-10-01
