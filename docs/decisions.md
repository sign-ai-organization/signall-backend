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
**Decisión:** Proveedor OpenAI, modelo `gpt-4o-mini`, `temperature=0`, `timeoutMs=10000`.
Interfaz vía **LangChain** (`langchain` + `langchain-openai`), no el SDK
de OpenAI directo.
**Por qué:** se evaluó explícitamente LangChain vs. SDK directo — para
una sola llamada (texto → glosas), el SDK directo sería más simple y
liviano, sin capas de más. Se optó por LangChain de todas formas porque
la API key de OpenAI usada hoy es personal y temporal (solo para
pruebas); hay una posibilidad de cambiar de proveedor más adelante
(costos, calidad, o disponibilidad de la key), y LangChain permite ese
cambio sin reescribir `LLMClient` (solo cambia el chat model
subyacente). El timeout de 10s es un techo de seguridad, no la latencia
esperada (`gpt-4o-mini` normalmente responde en 1-3s para este tipo de
prompt corto).
**Fecha:** 2026-09-09

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
aprobado (`docs/requirements.md`): un único canal WebSocket persistente
entre la app y el backend, que lleva audio en un sentido y el resultado
final en el otro — la alternativa necesitaría una segunda conexión
(app↔STT) que ese requerimiento no contempla.
**Fecha:** 2026-09-16

---

## LLM por defecto en desarrollo — Ollama local (addenda a 6.1)

**Subfase:** 6.1 revisited — el proveedor de la 6.1 sigue siendo OpenAI para
mediciones comparables; esto es cómo se ejecuta en la máquina de desarrollo.
**Decisión:** `LLMBaseURL` permite apuntar `LLMClient` a cualquier endpoint
compatible con OpenAI. Para desarrollo, Ollama local
(`http://localhost:11434/v1`, `qwen3:4b-instruct`) en lugar de la API de pago.
Con la variable vacía, el comportamiento es el de la 6.1 (OpenAI) — no cambia
nada por defecto.
**Por qué:** sin API key ni costo por llamada, y sin enviar el texto de las
frases de prueba a un servicio externo. `ChatOpenAI` ya aceptaba `base_url`:
faltaba exponerlo en `Settings`. LangChain Justifica haberlo elegido en la 6.1
precisamente para este caso. Medido con `qwen3:4b-instruct`: reproduce los tres
ejemplos del prompt de glosado exactamente y responde en ~0.2 s (OpenAI:
1-3 s). Ojo: la primera llamada tras arrancar Ollama carga el modelo en memoria
y puede tardar ~1 min, lo que excede `LLM_TIMEOUT_MS` — hay que calentar el
modelo (`ollama run <model>`) antes de medir.
**Fecha:** 2026-09-30

---

## Nota — Tiempo de silencio para transcripción final

**Decisión:** 1500 ms, tal como ya especifica el SDD (Vista de Procesos).
**Por qué:** el repo `sign-ai-stt` trae `SILENCE_TIMEOUT_MS=600` como
default — hay que ajustarlo a 1500 al configurar el servicio para este
proyecto, no usar su valor por defecto.
**Fecha:** 2026-09-16
