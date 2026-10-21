# SignAI Backend

SignAI traduce audio hablado en español a Lengua de Señas Colombiana (LSC)
mediante un avatar 3D, para que usuarios sordos o usuarios de LSC puedan
seguir una conversación hablada en tiempo real. El usuario oyente habla,
el sistema transcribe, interpreta el texto y lo traduce a una secuencia de
señas que el avatar reproduce. Es un proyecto de tesis (Ingeniería de
Sistemas, Pontificia Universidad Javeriana), con un corpus fijo de 50 señas
para el caso de uso "Registro Básico de Datos".

Este repositorio es solo el backend monolítico. El cliente Android (avatar
3D) y el servicio de transcripción (STT/Whisper) viven en repositorios
separados; este backend se comunica con ambos pero no los contiene.

## Arquitectura

- **Monolito modular**: Controller, Orchestrator, NLPService, ValidatorService,
  CatalogRepository y el servidor estático de GLB, todos en un solo
  contenedor Docker.
- El backend recibe audio del cliente Android por WebSocket, se comunica
  con el servicio STT externo para obtener texto transcrito, transforma
  ese texto a glosas de LSC, valida las glosas contra el catálogo, y
  devuelve el resultado al cliente junto con las rutas a las animaciones
  GLB correspondientes.
- Persistencia: PostgreSQL 16 + pgvector (Neon). Dos tablas sin relaciones
  entre sí: `catalog` y `semantic_cache`.
- Fuente de verdad de la arquitectura: `docs/sdd.md` (diagramas en
  `docs/diagrams/`). Requisitos: `../sign-ai-docs/documentos/requerimientos/SignAI_Requerimientos_Consolidados_v0.16.md`.
  Plan de implementación por fases: `docs/plan-implementacion-backend.md`.

## Estructura de carpetas

```
app/
├── controller/      # Canal WebSocket con Android
├── orchestrator/     # Orchestrator.translate(text)
├── nlp/               # GlossAnalyzer, SemanticCache, LLMClient, NLPServiceImpl
├── validation/        # ValidatorService, CatalogRepository
├── persistence/        # Esquema, migraciones, acceso a datos
├── static_glb/          # Servidor estático de archivos GLB
└── config/                # Settings, logging
```

## Decisiones de diseño actuales

Lo siguiente refleja el diseño ya documentado en `docs/sdd.md`. Trátalo
como el punto de partida, no como algo incuestionable: si al implementar
algo notas que una de estas reglas no tiene sentido, genera un problema
real, o hay una forma claramente mejor de resolverlo, dilo explícitamente
y explica por qué antes de decidir qué hacer — no lo cambies en silencio,
pero tampoco lo sigas ciegamente si crees que está mal.

No edites `docs/sdd.md` ni los diagramas directamente al encontrar una
inconsistencia (diagrama vs. narrativa vs. tabla de persistencia). En su
lugar, documenta el hallazgo en `docs/sdd-changes.md` (qué dice cada
fuente, cuál parece correcta y por qué, qué se implementó en el código
mientras tanto) y sigue con la implementación según lo que decidiste con
el usuario. Es él quien decide cuándo y cómo aplicar el cambio al SDD.

- **LLMClient solo devuelve glosas, nunca decide el tipo de frase.** El
  `phrase_type` siempre viene de `GlossAnalyzer` (huella gramatical), tanto
  al guardar como al consultar `SemanticCache`.
- **Sin umbrales numéricos en requisitos o lógica funcional.** Cualquier valor
  cuantitativo (latencia, tamaños, timeouts) pertenece a configuración o a
  no-funcionales, nunca hardcodeado en la lógica de negocio como si fuera
  parte del contrato funcional.
- **Las señales de colisión de `GlossAnalyzer` nunca se ocultan.** Se reportan
  siempre (`hasCollision`, `secondarySignals`), incluso cuando no afectan el
  resultado final — son instrumentación para validación empírica futura.
- **`CatalogRepository` carga todo el catálogo en memoria al arrancar**
  (`loadAll()`). `ValidatorService` nunca hace consultas a PostgreSQL durante
  la inferencia, solo contra el mapa en memoria.
- **El prompt de glosas NO lleva la lista de glosas.** Es la decisión **D-7**
  (owner, 2026-10-16): la lista sale del prompt, porque va contra el plan de
  pruebas y no escala. El código ya lo cumple (implementado el 2026-10-21):
  `self._prompt` es la constante `PROMPT_TEMPLATE`, sin nada inyectado. Lo
  que hace el trabajo es `_repair_glosses` + `_merge_fragments` (que consultan
  el vocabulario en memoria y son O(1)) y el validador, que marca como no
  disponible lo que no está en el catálogo.
  LSC50 tiene glosas **frasales** (`COMO ESTAS`,
  `BUENOS DIAS`, `MAS O MENOS`), así que la regla de "una glosa = una palabra"
  partía las frases en palabras sueltas que no existían en el catálogo y el avatar
  caía a la seña por defecto. El razonamiento completo está en el comentario de
  `app/nlp/llm_client.py`. Ver `docs/performance.md` §9.
- **No se usa el patrón Gateway dentro del monolito.** El flujo es
  Controller → Orchestrator, sin una capa de gateway intermedia.

## Trampas operationales

- **Cambiar el prompt NO invalida `semantic_cache`.** Las glosas viejas siguen
  en Neon y salen por `SemanticCache HIT`, así que el prompt nuevo no se ejecuta
  y parece que el arreglo no sirvió. Después de tocar el prompt o el modelo:

  ```sql
  DELETE FROM semantic_cache;
  ```

  Es un caché derivado, se reconstruye solo con la primera frase de cada una.
- **El proveedor del LLM es configurable, no fijo.** `LLM_BASE_URL` vacío =
  OpenAI. Apuntándolo a un servidor local (Ollama, LM Studio, vLLM) corre el
  mismo prompt sin API key ni costo. Desde Docker en Linux el servicio
  necesita `extra_hosts: ["host.docker.internal:host-gateway"]` (ya está en
  `docker-compose.yml`) y el servidor local tiene que escuchar fuera de
  `127.0.0.1` (Ollama: `OLLAMA_HOST=0.0.0.0:11434`).
- **Cambiar de modelo puede no cambiar nada.** Con el prompt de glosas frasales
  ambos modelos (`gpt-4o-mini` y `qwen3:4b-instruct`) siguen partiendo algunas
  frases, y por eso `_repair_glosses` existe: el prompt solo no alcanza.


## Convenciones de código

- Todo el código y los comentarios van **en inglés**, sin excepción.
- Seguir buenas prácticas generales de Python/FastAPI: type hints, funciones
  pequeñas y con una sola responsabilidad, nombres descriptivos, evitar
  código muerto o comentado.
- Los nombres de clases deben coincidir exactamente con los del SDD
  (`Controller`, `Orchestrator`, `NLPServiceImpl`, `GlossAnalyzer`,
  `SemanticCache`, `LLMClient`, `ValidatorServiceImpl`, `CatalogRepository`,
  `Segment`, `PhraseType`, `Gloss`, `ValidatedSegment`, `Fingerprint`).
- Los métodos siguen el mismo nombre semántico del SDD pero en snake_case
  (ej. `loadAll()` del SDD se implementa como `load_all()`), no camelCase
  literal — se prioriza PEP8 sobre la notación UML del diagrama.

## Verificación mientras se avanza

Todavía no hay suite de tests formal (eso llega en la última fase del plan).
Mientras tanto, cada subfase debe ser verificable de forma ligera y rápida:
un script simple, una llamada manual, o una colección de peticiones HTTP/WS
de prueba (por ejemplo con la extensión REST Client de VS Code) para
confirmar que el componente hace lo que dice el SDD antes de seguir. No
hace falta que sea elaborado.

## Commits

- Convención: `tipo(scope): descripción` en inglés (Conventional Commits).
  Tipos usados en este proyecto: `feat`, `fix`, `chore`, `docs`, `test`,
  `infra`.
- Al terminar cada subfase del plan (`docs/plan-implementacion-backend.md`),
  sugiere el mensaje de commit correspondiente. **Nunca ejecutes `git commit`
  ni `git push` — eso lo hace el usuario manualmente.**

## Decisiones todavía abiertas (no asumir una resolución)

Si el trabajo actual depende de alguna de estas, dilo y espera antes de
avanzar:

- Cómo simular similitud semántica en el caché sin una API de embeddings
  real todavía disponible.
- Proveedor, modelo y parámetros del LLM externo.
- Tamaño de modelo Whisper y protocolo de comunicación con el servicio STT
  (vive en otro repo).
- Herramienta de acceso a datos (ORM vs. SQL directo) — recomendación
  actual: `asyncpg` directo, dado que son dos tablas sin relaciones, pero
  sin confirmar todavía.
