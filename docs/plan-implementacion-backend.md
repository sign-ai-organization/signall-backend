# Plan de Implementación — Backend SignAI

**Base de este plan:** SDD (Vistas 6.1–6.3, Diagramas de Clases 7.1, Secuencia 7.2, Persistencia 7.3, C4 Niveles 1–3)
**Alcance:** Backend monolito (`signall-backend`) + servicio STT. No cubre el cliente Android.
**Unidad de trabajo:** cada subfase corresponde a un commit (o, en subfases de decisión, a una actualización documental — ver convenciones).

---

## Convenciones del plan

**Etiquetas por subfase:**
- 🔧 **Código** — produce un commit en el repositorio del backend.
- 🗂️ **Infraestructura / fuera de código** — una tarea manual (crear un recurso en la nube, configurar una cuenta). Puede no generar commit, o generar uno de configuración (ej. `.env.example`).
- 🛑 **Decisión requerida** — un punto donde el plan se detiene porque depende de una decisión (ADR/DEC) que hoy sigue abierta. No se avanza a la subfase siguiente sin resolverla. El "commit" de una decisión es la actualización del ADR correspondiente en `signall-docs`, no código.
- ✅ **Verificación** — no es un test formal (eso vive en la Fase 14), sino una comprobación rápida y manual de que el componente hace lo que el diagrama dice, antes de construir lo siguiente encima.

**Formato de mensajes de commit:** convención tipo Conventional Commits — `tipo(scope): descripción`. Tipos usados en este plan: `feat`, `fix`, `chore`, `docs`, `test`, `infra`.

**Nota sobre el orden de las fases:** el plan no sigue estrictamente el orden top-down del diagrama de secuencia (Controller → Orchestrator → NLP → Validación). En su lugar, prioriza primero los componentes que el SDD ya especifica por completo y sin decisiones pendientes (persistencia, catálogo, validación, análisis gramatical), dejando para más adelante los componentes que dependen de decisiones aún abiertas (caché semántico, LLM, protocolo STT). Esto evita bloquear todo el desarrollo detrás de una sola decisión y da avances verificables desde temprano.

---

## Supuestos y notas de consistencia (léelas antes de empezar)

1. **ADR-011 en el ADR Log todavía dice "microservicios", no monolito.** El documento `SignAI_ADR_Log.pdf` (v0.10) registra ADR-011 como "Decidida (el enfoque)" a favor de microservicios. El SDD, que es la base de este plan por instrucción explícita, ya implementa el monolito modular con STT como único contenedor separado. Este plan sigue al SDD. La actualización formal de ADR-011 en el ADR Log (y su aprobación por Andrea) sigue pendiente — esto ya estaba identificado como uno de los tres puntos abiertos de la SRS v0.15 y no es un hallazgo nuevo, solo lo dejo explícito aquí para que no se pierda de vista mientras se construye.
2. **DEC-15 (ORM, migraciones y carga inicial del corpus) sigue "En análisis"** en el Architecture Backlog — no tiene ADR propio todavía. La Fase 1 la trata como una decisión ligera dentro de la autoridad técnica del equipo (no requiere a Andrea ni al intérprete), con una recomendación mía a validar en su momento.
3. **El corpus real hoy tiene 24 de 50 filas** (según ADR-002 y tu estado actual de `señas.xlsx`), con la entrada #31 faltante y dos pares de duplicados sin resolver (#2/#24, #13/#14). La Fase 1 siembra el catálogo con lo que existe hoy; completar las 50 señas es responsabilidad de TSK-01/TSK-02 (intérprete), no bloquea la construcción del backend.
4. **Seguridad del backend (DEC-14) y definición de sesión (DEC-20) no aparecen como fases bloqueantes.** El diagrama de secuencia y los diagramas de componentes del SDD no incluyen autenticación ni control de gasto del LLM — es una decisión pendiente y de menor prioridad para un entorno de demo/tesis (Demo/Dev Host, según la Vista 6.2). Aparecen como una nota al final (Fase 14) en vez de una fase propia, para no inflar el plan con algo que el SDD mismo no modela todavía.
5. **El formato exacto de serialización del mensaje WebSocket** (camelCase vs snake_case, envoltorio del mensaje) no es una fase aparte, tal como ya acordamos — aparece como una nota puntual dentro de la Fase 11 (Controller).
6. **Gestor de dependencias de Python:** este plan asume `pip` + entorno virtual + `requirements.txt` por simplicidad para un equipo pequeño, no `poetry`. Es una decisión dentro de la autoridad técnica del equipo, ajustable sin impacto en el resto del plan — dímelo si prefieres otra herramienta antes de empezar la Fase 0.

---

## Resumen de fases

| Fase | Nombre | Tipo de bloqueo |
|---|---|---|
| 0 | Fundamentos y setup del proyecto | Ninguno |
| 1 | Infraestructura de datos (persistencia) | Decisión ligera (DEC-15) |
| 2 | Validación y catálogo | Ninguno |
| 3 | NLP — Análisis gramatical (GlossAnalyzer) | Ninguno (ya validado en Python) |
| 4 | Decisión — Diseño del caché semántico simulado | 🛑 Bloqueante |
| 5 | NLP — Caché semántico (SemanticCache) | Depende de Fase 4 |
| 6 | Decisión — Configuración del LLM externo | 🛑 Bloqueante |
| 7 | NLP — LLMClient y flujo completo de NLPService | Depende de Fase 6 |
| 8 | Orquestación (Orchestrator) | Ninguno (glue code) |
| 9 | Decisión + medición — Modelo Whisper y protocolo STT (ADR-006) | 🛑 Bloqueante |
| 10 | Servicio STT (contenedor Whisper) | Depende de Fase 9 |
| 11 | Controller y canal WebSocket | Ninguno |
| 12 | Servidor estático de GLB | Ninguno |
| 13 | Integración end-to-end | Depende de todas las anteriores |
| 14 | Testing formal y cierre | Depende de Fase 13 |

---

## Fase 0 — Fundamentos y Setup del Proyecto

Objetivo: tener un proyecto FastAPI ejecutable, vacío de lógica de negocio, pero con la estructura, configuración y contenedores listos para recibir el código de las fases siguientes.

### 0.1 — Estructura de carpetas del repositorio 🔧
Crear la estructura de `signall-backend` reflejando 1:1 los componentes del diagrama C4 nivel 3: `app/controller/`, `app/orchestrator/`, `app/nlp/`, `app/validation/`, `app/persistence/`, `app/static_glb/`, `app/config/`.
**Commit:** `chore(setup): estructura inicial de carpetas del backend`

### 0.2 — Entorno virtual y dependencias base 🔧
`requirements.txt` inicial con FastAPI, uvicorn, pydantic. Sin librerías de NLP/STT todavía (esas llegan en sus fases).
**Commit:** `chore(setup): entorno virtual y dependencias base`

### 0.3 — Esqueleto de la aplicación FastAPI 🔧
`main.py` con instancia de FastAPI y un endpoint `/health` que responde 200. Nada más.
**Commit:** `feat(setup): esqueleto de aplicación FastAPI con healthcheck`
**Verificación ✅:** levantar el servidor local y confirmar que `/health` responde.

### 0.4 — Configuración centralizada 🔧
`config/settings.py` usando `pydantic-settings`, leyendo variables de entorno (connection string de Neon, API key del LLM, parámetros del modelo). `.env.example` con las claves sin valores reales.
**Commit:** `feat(setup): configuración centralizada vía pydantic-settings`

### 0.5 — Logging básico 🔧
Configuración mínima de logging estructurado (nivel, formato), sin integración con ninguna herramienta externa todavía.
**Commit:** `feat(setup): logging básico`

### 0.6 — Dockerfile del backend 🔧
Dockerfile para el contenedor del backend (según Vista 6.2: agrupa Controller, Orchestrator, NLPService, ValidatorService, CatalogRepository, Static GLB Server).
**Commit:** `infra(docker): Dockerfile del contenedor backend`

### 0.7 — docker-compose.yml esqueleto 🔧
`docker-compose.yml` con el servicio `backend` y un placeholder para el servicio `stt` (se completa en la Fase 10). Neon y el LLM externo no entran aquí por ser servicios en la nube.
**Commit:** `infra(docker): esqueleto de docker-compose con backend y placeholder stt`

---

## Fase 1 — Infraestructura de Datos (Persistencia)

Objetivo: tener las dos tablas del modelo relacional (Figura 8 del SDD) creadas en Neon y el catálogo sembrado con las señas disponibles hoy.

### 1.1 — Crear instancia de Neon PostgreSQL 16 🗂️
Tarea fuera de código. Crear el proyecto en Neon, obtener el connection string, guardarlo (sin exponerlo) como referencia para `.env`.
**Commit:** ninguno de código; actualizar `.env.example` si cambia alguna clave esperada.

### 1.2 — Habilitar la extensión pgvector 🗂️
Ejecutar `CREATE EXTENSION IF NOT EXISTS vector;` en la instancia de Neon. Verificar que la extensión quedó activa.
**Commit:** ninguno de código.

### 1.3 — Decisión: herramienta de acceso a datos (DEC-15) 🛑
DEC-15 sigue "En análisis" en el Architecture Backlog — no hay ADR que la resuelva todavía. Opciones:
- **SQLAlchemy (async) + Alembic:** más código de configuración inicial, pero migraciones versionadas y manejo de tipos maduro. Facilita evolucionar el esquema si el catálogo crece más allá de 50 señas.
- **SQL directo con `asyncpg`:** menos capas, más rápido de escribir para dos tablas simples sin relaciones entre sí (como ya señala el propio SDD en 7.3). Las migraciones se manejan como scripts `.sql` versionados a mano.

Mi recomendación: dado que el modelo son solo dos tablas sin relaciones (el propio SDD lo dice explícitamente en 7.3), y que CatalogRepository carga todo en memoria al arrancar sin volver a consultar por fila, `asyncpg` directo es proporcional a la complejidad real del problema. SQLAlchemy sería sobre-ingeniería aquí. Valida esto conmigo cuando lleguemos a esta subfase antes de escribir código.
**Commit al resolverse:** `docs(adr): decisión de acceso a datos (DEC-15)` en `signall-docs`.

### 1.4 — Esquema de las tablas 🔧
Script de creación de `catalog` y `semantic_cache` exactamente como en la Figura 8: `catalog(id_sign PK, gloss indexed, semantic_category, glb_animation_path, modified_at)`, `semantic_cache(id PK, original_text, embedding VECTOR(384), phrase_type, glosses TEXT[], secondary_signals TEXT[], had_collision BOOLEAN, created_at)`.
**Commit:** `feat(persistence): esquema de tablas catalog y semantic_cache`

### 1.5 — Migraciones iniciales 🔧
Según lo decidido en 1.3: migración inicial versionada (Alembic) o script `.sql` numerado.
**Commit:** `feat(persistence): migración inicial del esquema`

### 1.6 — Script de carga del corpus (seed) 🔧
Script que lee `señas.xlsx` y siembra la tabla `catalog` con las 24 filas disponibles hoy. La entrada #31 y los duplicados #2/#24, #13/#14 quedan explícitamente fuera hasta que el intérprete los resuelva — el script no debe inventar valores para completarlos.
**Commit:** `feat(persistence): script de carga del corpus desde señas.xlsx`

### 1.7 — Verificación de conexión ✅
Script o test manual que hace un `SELECT count(*) FROM catalog` y confirma que devuelve 24 y que la extensión pgvector responde a una consulta trivial de similitud.

---

## Fase 2 — Validación y Catálogo

Objetivo: implementar el camino de validación completo (Figura 6), que no depende de ninguna decisión pendiente y puede probarse de forma aislada con datos falsos.

### 2.1 — Modelos de dominio compartidos 🔧
`Segment`, `PhraseType`, `Gloss`, `ValidatedSegment`, `CatalogEntry` como dataclasses o modelos pydantic, exactamente con los atributos de las Figuras 5 y 6 (`PhraseType`: afirmativa, interrogativa_si_no, interrogativa_contenido, negativa, imperativa).
**Commit:** `feat(domain): modelos de dominio Segment, PhraseType, Gloss, ValidatedSegment`

### 2.2 — CatalogRepository 🔧
`cache: Dict[str, CatalogEntry]`, `loadAll()` (carga única al arrancar, lee de `catalog`), `search(gloss)` (resuelve contra el mapa en memoria, sin tocar PostgreSQL).
**Commit:** `feat(validation): CatalogRepository con carga en memoria`

### 2.3 — ValidatorService y ValidatorServiceImpl 🔧
Interfaz `ValidatorService.validate(segments)`, implementación que recorre cada glosa de cada segmento, llama a `CatalogRepository.search(gloss)`, y arma `Gloss(available=True/False, glbPath=...)` según exista o no.
**Commit:** `feat(validation): ValidatorServiceImpl`

### 2.4 — Verificación ✅
Con una lista de `Segment` construida a mano (sin pasar por NLP todavía), confirmar que `validate()` devuelve `ValidatedSegment` con `available` y `glbPath` correctos para glosas que sí y que no están en el catálogo sembrado en la Fase 1.

---

## Fase 3 — NLP: Análisis Gramatical (GlossAnalyzer)

Objetivo: portar la lógica ya validada de `analizador_huella.py` (96/100 en el set de prueba) al backend, sin reescribirla desde cero.

### 3.1 — Fingerprint como modelo de dominio 🔧
`Fingerprint(category: PhraseType, secondarySignals: List[PhraseType], hasCollision: bool)`.
**Commit:** `feat(nlp): modelo Fingerprint`

### 3.2 — Portar GlossAnalyzer 🔧
Migrar las cinco categorías y la prioridad de colisión (interrogativa > imperativa > negativa > afirmativa) de `analizador_huella.py` a una clase `GlossAnalyzer.analyze(text) -> Fingerprint` dentro del backend.
**Commit:** `feat(nlp): GlossAnalyzer portado desde analizador_huella.py`

### 3.3 — Verificación de regresión ✅
Correr el mismo set de 100 frases de prueba contra el `GlossAnalyzer` ya integrado y confirmar que el resultado se mantiene en 96/100 (o mejor) tras el port. Si baja, es una señal de que algo se perdió al migrar, no que el modelo original estaba mal.

---

## Fase 4 — Decisión: Diseño del Caché Semántico Simulado 🛑

Esta fase es enteramente de decisión, sin código, tal como ya acordamos que debía tratarse como un punto de parada explícito.

### 4.1 — Cómo simular similitud semántica sin una API de embeddings real 🛑
Pendiente de discutir contigo, como ya quedó anotado en tu contexto de proyecto: no hay todavía una decisión de cómo `SemanticCache.lookup` compara embeddings cuando aún no hay integración con un proveedor real de embeddings.
**Commit al resolverse:** `docs(adr): diseño del caché semántico simulado`

### 4.2 — Qué modelo de embeddings locales se usará en la versión real 🔧-futuro
El SDD (7.3) ya asume "un modelo de embeddings local" para producir el vector de 384 dimensiones que se guarda en `semantic_cache.embedding`. Falta elegir cuál (ej. un modelo tipo `sentence-transformers` que produzca vectores de esa dimensión). Esta subfase decide el modelo concreto; no bloquea 4.1, pero sí bloquea el `EmbeddingModel` real de la Fase 5.
**Commit al resolverse:** `docs(adr): selección del modelo de embeddings local`

*No se avanza a la Fase 5 sin resolver al menos 4.1 (puede resolverse con una simulación explícita y documentada, no necesariamente con el modelo final de 4.2).*

---

## Fase 5 — NLP: Caché Semántico (SemanticCache)

Bloqueada por la Fase 4. El contenido exacto de estas subfases depende de lo que se decida ahí; lo siguiente es la estructura esperada según el SDD.

### 5.1 — EmbeddingModel 🔧
Clase identificada como faltante en el diagrama de clases de NLP (Diagrama 2) — se agrega aquí. Responsable de convertir texto a vector, según lo decidido en 4.2 (o su versión simulada de 4.1).
**Commit:** `feat(nlp): EmbeddingModel`

### 5.2 — SemanticCache.lookup 🔧
Compara `embedding` (similitud por pgvector) y `phrase_type` (proveniente de `Fingerprint.category`, nunca del LLM) contra lo ya guardado en `semantic_cache`.
**Commit:** `feat(nlp): SemanticCache.lookup con búsqueda pgvector`

### 5.3 — SemanticCache.store 🔧
Guarda `original_text`, `embedding`, `phrase_type`, `glosses`, `secondary_signals`, `had_collision` — las señales de colisión siempre se registran, nunca se ocultan, tal como ya está establecido como principio del proyecto.
**Commit:** `feat(nlp): SemanticCache.store`

### 5.4 — Verificación de cache HIT y MISS ✅
Con datos de prueba, confirmar que una segunda consulta con texto semánticamente similar y el mismo `phrase_type` produce HIT, y que un `phrase_type` distinto (aun con texto similar) produce MISS.

---

## Fase 6 — Decisión: Configuración del LLM Externo 🛑

### 6.1 — Proveedor, modelo y parámetros del LLM 🛑
Falta decidir qué proveedor de LLM se usa a través de LangChain, y fijar `model`, `temperature` y `timeoutMs` de `LLMClient`. Nota: el Architecture Backlog (LIM-06) ya recomienda temperatura 0 para que el LLM sea determinista en la sustentación de tesis — es un dato a favor, no una decisión completa por sí sola.
**Commit al resolverse:** `docs(adr): configuración del LLMClient (proveedor, modelo, parámetros)`

### 6.2 — Manejo de la API key 🗂️
Definir cómo se inyecta la API key del proveedor elegido (variable de entorno vía `.env`, sin commitear el valor real). Relacionado con DEC-14 (seguridad), aunque no es necesario resolver DEC-14 completa para esta subfase puntual.
**Commit:** `chore(config): variable de entorno para API key del LLM`

*No se avanza a la Fase 7 sin resolver 6.1.*

---

## Fase 7 — NLP: LLMClient y Flujo Completo de NLPService

Bloqueada por la Fase 6.

### 7.1 — LLMClient 🔧
`transform(text) -> List[str]` (glosas en texto plano). Su responsabilidad se limita a devolver glosas — nunca decide el tipo de frase, eso siempre viene de `GlossAnalyzer`.
**Commit:** `feat(nlp): LLMClient`

### 7.2 — NLPServiceImpl 🔧
Orquesta `analyzer`, `cache`, `llmClient`: llama `analyze(text)`, luego `cache.lookup`; si hay HIT reutiliza las glosas, si hay MISS llama `llmClient.transform(text)` y guarda con `cache.store`. En ambos caminos arma el segmento con `buildSegment(fingerprint, glosses)`.
**Commit:** `feat(nlp): NLPServiceImpl con flujo cache HIT/MISS`

### 7.3 — Verificación del flujo completo de NLP ✅
Contra los pasos 2–11 del diagrama de secuencia: confirmar que un texto nuevo dispara LLM y guarda en caché, y que repetir el mismo texto (mismo `phrase_type`) reutiliza el caché sin llamar al LLM de nuevo.

---

## Fase 8 — Orquestación (Orchestrator)

Objetivo: el "pegamento" entre NLP y Validación. No depende de ninguna decisión pendiente por sí misma, pero sí requiere que las Fases 2 y 7 estén terminadas.

### 8.1 — Interfaces NLPService y ValidatorService 🔧
Definidas como interfaces (no implementaciones concretas), tal como especifica la Figura 4.
**Commit:** `feat(orchestrator): interfaces NLPService y ValidatorService`

### 8.2 — Orchestrator.translate(text) 🔧
Llama `nlpService.transform(text)`, pasa el resultado a `validatorService.validate(segments)`, devuelve la lista de `ValidatedSegment`.
**Commit:** `feat(orchestrator): Orchestrator.translate`

### 8.3 — Verificación end-to-end sin WebSocket ✅
Llamar `Orchestrator.translate("texto de prueba")` directamente (sin pasar por Controller todavía) y confirmar que el resultado final coincide con lo esperado según el diagrama de secuencia completo (pasos 1–16), incluyendo glosas validadas contra el catálogo real sembrado en la Fase 1.

---

## Fase 9 — Decisión + Medición: Modelo Whisper y Protocolo STT (ADR-006) 🛑

El diagrama de contenedores marca explícitamente "protocolo pendiente — ADR-006" en la conexión Backend↔STT Container. Esta fase resuelve tanto el protocolo como el tamaño de modelo Whisper a usar, porque ambos requieren medir sobre la RTX 3050 real antes de decidir.

### 9.1 — Setup mínimo de Whisper para medición 🔧
Instalar Whisper en el entorno del STT (sin integrarlo aún al pipeline del backend), solo para poder medir.
**Commit:** `chore(stt): setup mínimo de Whisper para medición`

### 9.2 — Medir latencia y consumo de VRAM por tamaño de modelo 🗂️
Correr audio real en español contra los tamaños de modelo candidatos (base/small, medium, large-v3) sobre la RTX 3050 y registrar latencia y uso de VRAM de cada uno.
**Commit:** `docs(measurement): resultados de medición de Whisper en RTX 3050`

### 9.3 — Decisión: tamaño de modelo Whisper 🛑
Con el dato de 9.2, elegir el modelo. Sin esta medición, cualquier elección es una apuesta, no una decisión informada.
**Commit al resolverse:** `docs(adr): selección de modelo Whisper`

### 9.4 — Decisión: protocolo Controller ↔ STT Container 🛑
Definir cómo viaja el audio y el texto transcrito entre ambos contenedores (WebSocket interno, streaming HTTP, gRPC, etc.), y el formato exacto de los mensajes parciales/finales.
**Commit al resolverse:** `docs(adr): protocolo de comunicación Controller-STT (ADR-006)`

*No se avanza a la Fase 10 sin resolver 9.3 y 9.4.*

---

## Fase 10 — Servicio STT (Contenedor Whisper)

Bloqueada por la Fase 9.

### 10.1 — Setup del proyecto STT 🔧
Estructura y dependencias propias del servicio STT (distintas del monolito: Whisper, PyTorch/CUDA).
**Commit:** `chore(stt): estructura y dependencias del servicio STT`

### 10.2 — SttServiceClient (lado servidor) 🔧
Implementación de `transcribe(audio): text` según el modelo y protocolo decididos en la Fase 9.
**Commit:** `feat(stt): implementación de transcripción con Whisper`

### 10.3 — Streaming continuo y detección de silencio 🔧
Transcripción en fragmentos hasta detectar 1.5 segundos de silencio, momento en el que se marca la transcripción como final (`isFinal=True`), según el diagrama de actividades (Vista 6.3).
**Commit:** `feat(stt): detección de silencio y marcado de transcripción final`

### 10.4 — Dockerfile del contenedor STT 🔧
Imagen separada del backend, con soporte GPU.
**Commit:** `infra(docker): Dockerfile del contenedor STT`

### 10.5 — Verificación manual ✅
Enviar un audio de prueba real y confirmar que se recibe texto parcial durante la grabación y texto final tras el silencio.

---

## Fase 11 — Controller y Canal WebSocket

### 11.1 — Endpoint WebSocket 🔧
Sesión de traducción en FastAPI, según la Vista de Contenedores (`«interfaz» Translation Session (WebSocket)`).
**Commit:** `feat(controller): endpoint WebSocket de sesión de traducción`

### 11.2 — handleAudioChunk(chunk) 🔧
Recibe cada fragmento de audio del cliente y lo reenvía a `SttServiceClient`.
**Commit:** `feat(controller): handleAudioChunk`

### 11.3 — handleTranscript(text, isFinal) 🔧
Recibe la transcripción parcial o final desde el STT. Cuando `isFinal=True`, llama a `Orchestrator.translate(text)`.
**Commit:** `feat(controller): handleTranscript con disparo de traducción al marcar final`

### 11.4 — sendResult(segments) 🔧
Envía el resultado final al cliente Android. **Nota puntual, no bloqueante:** el formato exacto de serialización (camelCase/snake_case, envoltorio del mensaje) se acuerda con Juan Diego en este punto del desarrollo, tal como ya quedamos — la estructura de campos ya está definida por `ValidatedSegment`/`Gloss`/`PhraseType`.
**Commit:** `feat(controller): sendResult`

### 11.5 — Manejo de errores hacia el cliente 🔧
Si falla STT, NLP o el LLM, el Controller debe enviar un mensaje de error identificable, para que Android pueda transicionar a su estado `Error` (según el diagrama de estados de UI, con retorno automático a `Inactivo` en ≤2s del lado del cliente).
**Commit:** `feat(controller): manejo de errores de STT/NLP/LLM`

### 11.6 — Verificación ✅
Simular una sesión completa (audio de prueba → texto final → resultado) a través del WebSocket real, no solo llamando a `Orchestrator` directamente como en la Fase 8.

---

## Fase 12 — Servidor Estático de GLB

### 12.1 — Endpoint HTTPS de descarga 🔧
Sirve archivos estáticos desde una carpeta del propio repo (ej. `/static/glb/`), según la decisión ya tomada de que el catálogo referencia rutas dentro del propio backend.
**Commit:** `feat(static-glb): endpoint de descarga de archivos GLB`

### 12.2 — Poblar la carpeta de GLB 🗂️
Copiar al repo los archivos GLB que Samuel ya haya producido, nombrados de forma consistente con `glb_animation_path` en la tabla `catalog`.
**Commit:** `feat(static-glb): archivos GLB iniciales del corpus`

### 12.3 — Verificación ✅
Descargar un archivo GLB de prueba vía HTTPS y confirmar que la ruta coincide con la registrada en `catalog`.

---

## Fase 13 — Integración End-to-End

### 13.1 — Cablear todo en docker-compose 🔧
Backend + STT Container corriendo juntos, apuntando a Neon real y (si ya está resuelta la Fase 6) al LLM real.
**Commit:** `infra(docker): docker-compose completo backend + stt`

### 13.2 — Prueba manual end-to-end ✅
Audio real → transcripción → NLP (cache o LLM) → validación contra catálogo → resultado por WebSocket → descarga de GLB. Este es el primer momento en que se ejecuta el flujo completo de la Figura 7 de punta a punta, con todos los componentes reales.

### 13.3 — Ajustes post-integración 🔧
Correcciones puntuales de manejo de errores, timeouts o formato de mensajes que solo aparecen al integrar todo (es normal que surjan aquí, no es un síntoma de mal diseño previo).
**Commit(s):** `fix(integration): ...` (uno por cada ajuste real que surja)

---

## Fase 14 — Testing Formal y Cierre

### 14.1 — Setup de pytest 🔧
Fixtures de base de datos de prueba y mocks del LLM externo.
**Commit:** `test(setup): configuración de pytest y fixtures`

### 14.2 — Tests unitarios: GlossAnalyzer, CatalogRepository, ValidatorService 🔧
Componentes sin dependencias externas bloqueantes — los más baratos de cubrir con tests reales.
**Commit:** `test(unit): GlossAnalyzer, CatalogRepository, ValidatorService`

### 14.3 — Tests unitarios: SemanticCache, LLMClient (mockeado) 🔧
**Commit:** `test(unit): SemanticCache y LLMClient con mocks`

### 14.4 — Tests de integración: Orchestrator 🔧
Flujo completo `translate()` con catálogo real y LLM mockeado.
**Commit:** `test(integration): Orchestrator.translate`

### 14.5 — Test de integración: Controller vía WebSocket 🔧
Usando el `TestClient` de FastAPI para simular una sesión completa.
**Commit:** `test(integration): sesión WebSocket completa`

### 14.6 — Nota de cierre: seguridad y control de gasto (no bloqueante) 📝
DEC-14 (seguridad del backend, control de gasto del LLM) y DEC-20 (definición de sesión) siguen abiertas y no están cubiertas por este plan porque el SDD, en su estado actual, no las modela. Quedan como trabajo futuro explícito antes de exponer el backend fuera del entorno de demo — no se implementan aquí para no inventar diseño que el SDD no respalda todavía.

---

## Qué sigue después de este plan

Este documento no incluye: el cliente Android, el JSON contract formal (documentado aparte, ya resuelto en su mayoría por los diagramas), ni las decisiones de UX/lingüísticas que dependen del intérprete (deletreo, corpus completo). Cuando quieras, podemos usar esta misma estructura de fases/subfases para planear alguno de esos frentes por separado.
