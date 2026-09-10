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
