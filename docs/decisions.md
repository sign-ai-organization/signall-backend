# Decisiones

Registro de las decisiones que se van resolviendo entre las marcadas como
🛑 en `docs/plan-implementacion-backend.md`. Cada entrada es corta: qué se
decidió, por qué, y en qué subfase quedó registrada. No reemplaza al SDD —
si una decisión termina cambiando algo del diseño documentado ahí, ese
cambio se refleja en `docs/sdd.md`, y aquí queda solo el porqué.

Entradas más recientes al final.

---

## 1.3 — Herramienta de acceso a datos (DEC-15)

**Subfase:** 1.3 — Herramienta de acceso a datos (DEC-15)
**Decisión:** `asyncpg` directo, sin ORM. Migraciones como scripts `.sql`
versionados a mano.
**Por qué:** el modelo son dos tablas sin relaciones entre sí (`catalog`,
`semantic_cache`), y `CatalogRepository` carga todo el catálogo en memoria
al arrancar sin volver a consultar por fila — no hay joins, lazy loading
ni N+1 queries que un ORM (SQLAlchemy + Alembic) resuelva mejor aquí. Se
evaluó explícitamente frente a SQLAlchemy por preferencia previa con JPA
en Java; la diferencia de esfuerzo de setup es mínima (~10 min), pero
SQLAlchemy suma dependencias y piezas de configuración (Alembic, engine,
sesiones async) que no aportan valor real dado que no hay complejidad
relacional que gestionar.
**Fecha:** 2026-09-02

---

## 4.1 y 4.2 — Diseño del caché semántico y modelo de embeddings

**Subfase:** 4.1 (Cómo simular similitud semántica) y 4.2 (Modelo de
embeddings local), resueltas juntas.
**Decisión:** No se simula. Se implementa un `EmbeddingModel` real desde
el inicio, corriendo dentro del mismo contenedor del backend (no aparte, como
STT/Whisper), usando `sentence-transformers` con el modelo
`paraphrase-multilingual-MiniLM-L12-v2` (384 dimensiones, coincide con
`semantic_cache.embedding VECTOR(384)` ya definido anteriormente).
**Por qué:** se evaluó explícitamente si aislarlo en un contenedor aparte
(como STT), dado que `sentence-transformers` depende de PyTorch, una
dependencia pesada que infla la imagen Docker y el tiempo de arranque.
Se decidió no separarlo ya que esa razón (peso de imagen/arranque) no es
un problema de recursos en ejecución (a diferencia de STT, que se separa
por consumo real de GPU/VRAM compartida), es solo un costo de build,
aceptable. Separarlo replicaría la
complejidad operativa de STT (protocolo, contenedor, orquestación) sin
necesidad real. Se eligió la variante multilingüe sobre `all-MiniLM-L6-v2`
(inglés) porque todo el texto de entrada del sistema es en español.
**Fecha:** 2026-09-03

---

## 6.1 — Proveedor, modelo y parámetros del LLM externo

**Subfase:** 6.1 — Configuración del LLMClient.
**Decisión:** Proveedor OpenAI, modelo `gpt-4o-mini`, `temperature=0`.
Interfaz vía **LangChain** (`langchain` + `langchain-openai`), no el SDK
de OpenAI directo.
**Por qué:** se evaluó explícitamente LangChain vs. SDK directo — para
una sola llamada (texto → glosas), el SDK directo sería más simple y
liviano, sin capas de más. Se optó por LangChain de todas formas porque
la API key de OpenAI usada hoy es personal y temporal (solo para
pruebas); hay una posibilidad de cambiar de proveedor más adelante
(costos, calidad, o disponibilidad de la key), y LangChain permite ese
cambio sin reescribir `LLMClient` (solo cambia el chat model
subyacente).
**Fecha:** 2026-09-09

> **Actualizado el 2026-10-21.** El timeout ya no es 10 s: son **5 s con un
> reintento**, por la decisión del owner del 2026-10-18 (§6.3 del contraste).
> El motivo es el reloj de 15 s de la app: con tres intentos de 10 s, el
> backend era el último en avisar de una frase que la app ya había cerrado.
> Con 5 s y un reintento, el peor caso son ~10 s. Ver `docs/performance.md`.

---

## 9.3 — Tamaño de modelo Whisper

**Subfase:** 9.3 — Selección de modelo Whisper (usa `faster-whisper`, no
Whisper original).
**Decisión:** `medium` (`MODEL_SIZE=medium`, `DEVICE=cuda`,
`COMPUTE_TYPE=float16`).
**Por qué:** medición ya realizada por un compañero de equipo sobre la
misma RTX 3050 del Demo/Dev Host (repo `sign-ai-stt`), comparando
`tiny/base/small/medium/large-v3`; `medium` resultó el mejor balance de
rendimiento según su informe. Cifras exactas de latencia/VRAM por
tamaño: **por confirmar**, pendientes de que se comparta el informe
completo.
**Fecha:** 2026-09-16

---

## 9.4 — Protocolo de comunicación Controller ↔ STT

**Subfase:** 9.4 — Protocolo Controller-STT.
**Decisión:** El Backend es el único que le habla al contenedor STT. El
Controller recibe audio del cliente Android por el único canal WebSocket
ya definido (app ↔ backend), y por dentro abre su propia conexión
WebSocket hacia `STT: /ws/transcribe` (protocolo ya implementado en
`sign-ai-stt`: frames binarios PCM16LE 16kHz de entrada, mensajes JSON
`{"type": "partial"|"final", "text": ...}` de vuelta). El cliente Android
nunca se conecta directo al STT.
**Por qué:** se evaluó una alternativa (repo `stt-integration-test`) donde
el cliente le habla directo al STT y este reenvía por HTTP al backend
como aviso aparte. Se descartó porque contradice un requerimiento ya
aprobado (**RF-INT-COM-01**, en
`../sign-ai-docs/documentos/requerimientos/SignAI_Requerimientos_Consolidados_v0.16.md:168`):
un único canal WebSocket persistente
entre la app y el backend, que lleva audio en un sentido y el resultado
final en el otro — la alternativa necesitaría una segunda conexión
(app↔STT) que ese requerimiento no contempla.
**Fecha:** 2026-09-16

---

## Nota — Tiempo de silencio para transcripción final

**Decisión:** 1500 ms, tal como ya especifica el SDD (Vista de Procesos).
**Por qué:** el repo `sign-ai-stt` trae `SILENCE_TIMEOUT_MS=600` como
default — hay que ajustarlo a 1500 al configurar el servicio para este
proyecto, no usar su valor por defecto.
**Fecha:** 2026-09-16

---

## Nota — Umbral y normalización del caché semántico

**Decisión:** el embedding del caché se calcula sobre el texto
normalizado (minúsculas, sin tildes salvo la ñ, sin signos), con
`app/nlp/text_normalizer.py`, y el umbral de distancia baja de 0.15 a
0.05. En `semantic_cache.original_text` se sigue guardando el texto
original.
**Por qué:** con el segmentador, el caché compara oraciones cortas y
devolvía glosas de frases distintas: "¿cómo estás?" recibía las de
"Hola, ¿cómo estás?" (HOLA repetido) y "Firme allá" las de "Firme
aquí". Medido con `scripts/measure_cache_threshold.py`: con texto
original, los aciertos buenos y los indebidos se solapan (0.071 frente a
0.076) y ningún umbral los separa. Con texto normalizado y umbral 0.05:
7 de 10 aciertos buenos y 0 de 12 indebidos. Se prioriza que el caché
nunca devuelva glosas equivocadas frente a acertar más: una glosa
equivocada cambia el mensaje del avatar; un fallo solo cuesta una
llamada al LLM, cuyo resultado queda guardado. Normalizar sin bajar el
umbral sería peor que antes ("Vivo en Bogotá" / "Vivo en Medellín" baja
a 0.083).
**Fecha:** 2026-10-02
