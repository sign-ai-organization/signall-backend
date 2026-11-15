# SignAll — backend

Servicio central del proyecto **SignAll**: recibe español (texto o audio) desde la app Android,
lo convierte en glosas de Lengua de Señas Colombiana (LSC) y devuelve las señas que el avatar
tiene que representar, una oración por vez.

Trabajo de grado de Ingeniería de Sistemas, Pontificia Universidad Javeriana (Colombia), con un
corpus fijo de 50 señas (LSC50) para el caso de uso "Registro Básico de Datos".

Este archivo son las reglas que aplican a todo, para una persona o para un agente. El mapa del
sistema, el protocolo del STT y el resto del contexto están enlazados al final, en § Qué cargar
y cuándo.

## El sistema: cuatro repositorios y el avatar

Este repositorio es **una pieza**. El sistema completo:

| Repositorio | Qué es | Puerto |
|---|---|---|
| [signall-android](https://github.com/sign-ai-organization/signall-android) | la app: captura el micrófono, envía por WebSocket y representa las señas | — |
| [signall-backend](https://github.com/sign-ai-organization/signall-backend) | este repositorio: WebSocket, NLP de glosas, catálogo y caché semántico | 8080 |
| [signall-stt](https://github.com/sign-ai-organization/signall-stt) | faster-whisper + WebRTC VAD: audio → texto en tiempo real | 8000 |
| [signall-docs](https://github.com/sign-ai-organization/signall-docs) | los documentos de la tesis: SRS, SDD, memoria, plan de pruebas y plan de administración | — |
| [signall-avatar](https://github.com/sign-ai-organization/signall-avatar) (rama `dev`) | producción de las animaciones: los GLB finales de Juan y Pauline | — |

**Los repos hermanos son fuentes de información, no cajas negras.** Antes de cambiar un frame
del WebSocket, una glosa del catálogo o un nombre de métrica hay que leer el otro lado: el
contrato entre ellos son frames, y ningún compilador avisa cuando se rompe. Un cambio que cruza
el contrato no está terminado hasta que el otro lado lo refleja; si queda pendiente, se dice en
voz alta.

Los cuatro se mantienen actualizados entre sí, y `signall-docs` es el repositorio de
documentación de la tesis y **el que manda para lo escrito**: los documentos formales son suyos
y no hay copia en otro lugar. Cuando el código y un documento no coinciden, no se elige por
cuenta propia: se determina cuál de los dos está mal y se pregunta al owner.

Los comandos de este archivo suponen los clones uno al lado del otro (`../signall-stt`), que es
como se trabaja normalmente. El `docker-compose.yml` construye el servicio de voz desde esa
carpeta hermana.

## Cómo se escribe

El owner es la persona autora de la tesis; lo que se le explica tiene que entenderse en
**español neutro, sin voseo y sin jerga sin explicar**: la idea primero y el detalle técnico
después.

- **El término de la tesis es `representar`**: el avatar *representa* las señas, no "firma" ni
  "signa". Si el texto habla de mandar una frase, es `enviar`. En inglés, `signing` es la
  palabra correcta y se queda.
- **Los números van con su origen**: fecha, corpus, modelo y si la caché estaba caliente. Una
  cifra sin origen no se puede discutir.
- **No se inventa terminología.** Si una palabra no está en los documentos de la tesis, se
  pregunta antes de escribirla.
- **Una decisión, una pregunta.** Cuando algo sea decisión del owner, se presentan las opciones
  con lo que se gana y lo que se pierde, y se para ahí.
- **Se separa lo medido de lo supuesto.**

## Cada cambio se documenta en `signall-docs`

> **Cada cambio no trivial se documenta en `signall-docs`**: en `cambios/` (qué cambió y por
> qué) y, si toca un documento formal, se actualiza el `.tex` y se compila con `make`. Una
> sesión que termina sin dejar rastro ahí no está terminada.

Es un **estándar**, no una sugerencia. Aplica a los cuatro repositorios.

- En `signall-docs/cambios/` va la entrada: qué se cambió, por qué y qué quedó pendiente.
- Si el cambio toca un documento formal (`latex/srs`, `latex/sdd`, `latex/memoria`,
  `latex/plan-pruebas`, `latex/administracion`, `latex/vfp`), se edita el `.tex` y se compila con
  `make <documento>`. Un documento que no compila no es un cambio terminado.
- En este repositorio el rastro de trabajo es además [`docs/sessions/`](docs/sessions/), un
  archivo por sesión.
- Cuando el dato venga de otro repositorio, se deja **de qué repo y de qué commit** salió.

## Arquitectura

Monolito modular en FastAPI con PostgreSQL 16 + pgvector (Neon). El flujo de una frase es
`Controller` (WebSocket) → `Orchestrator` → `NLPService` → `ValidatorService` →
`CatalogRepository`: el controlador recibe el turno, el orquestador lo recorre, el servicio de
NLP corta el texto en oraciones y produce las glosas con un LLM, y el validador comprueba que
cada glosa exista en el catálogo antes de mandarla.

```
app/controller/       WebSocket /ws/translate, cliente del STT y router de administración
app/orchestrator/     el turno completo: audio o texto de entrada, oraciones de salida
app/nlp/              análisis de glosas, cliente del LLM, corte en oraciones y caché semántico
app/validation/       catálogo y validación de que cada glosa exista
app/persistence/      conexión a Neon, migraciones, keep-alive y recuperación
app/domain/           tipos compartidos (Segment, PhraseType, Gloss, ValidatedSegment)
app/observability/    métricas y trazas del pipeline
scripts/              verificaciones ejecutables, mediciones y cliente de traducción manual
deploy/               proxy TLS y archivos para la demostración cifrada
```

- **Persistencia**: dos tablas sin relaciones entre sí, `catalog` y `semantic_cache`. Se usa
  `asyncpg` directo, sin ORM (decisión DEC-15), y las migraciones son `.sql` versionados.
- **Fuente de verdad del diseño**: [`docs/sdd.md`](docs/sdd.md), con los diagramas en
  `docs/diagrams/`. Las decisiones que se van cerrando quedan en
  [`docs/decisions.md`](docs/decisions.md); los requisitos, en `signall-docs`
  (`borradores/requerimientos/`).
- Si el SDD, los diagramas y el código no coinciden, **no se edita el SDD**: se documenta el
  hallazgo en [`docs/sdd-changes.md`](docs/sdd-changes.md) —qué dice cada fuente, cuál parece
  correcta y por qué, y qué se implementó mientras tanto— y decide el owner.

## El contrato con la app

Un único WebSocket, de la app **solo al backend**: `:8080/ws/translate`. La app nunca habla con
el STT ni con Neon. El backend mantiene a su vez un socket saliente al STT (`STT_WS_URL`).

| frame | quién | qué |
|---|---|---|
| audio PCM16 binario | app → backend | se reenvía al STT y vuelve como `transcript` (parciales y `final`). **No se traduce** |
| `{"type":"text","text":"..."}` | app → backend | se divide en oraciones, se traduce, se manda un `segment` por oración con `index`/`total` reales y un `done` |
| `{"type":"end"}` | app → backend | cierra el utterance del STT |
| `transcript`, `segment`, `done`, `error` | backend → app | `trace` solo con `DEBUG_TRACE_ENABLED=true` |

Los cuatro invariantes que no se rompen:

1. **Solo se traduce lo que el cliente manda como `text`.** La transcripción de la voz vuelve
   como `transcript` y **no se traduce**. Si el backend hiciera eco de la frase escrita, la app
   lo tomaría por una frase de voz y la reenviaría: ese bucle existió y quemó el proceso (una
   frase repetida ~2.900 veces, `rt_phrases_total 3731`, 44 % de CPU).
2. **`segment` es una oración, con `index` y `total` reales desde el primero.** No existen
   `stream`, `provisional` ni `source_text`.
3. **El `final` siempre llega**, incluso vacío: el STT responde a todo `end`. Un `final` sin
   texto es "no se escuchó nada", no un error.
4. **Los mismos nombres de métrica en los dos lados** (`rt_*` acá, `SignAllMetrics` en el
   dispositivo): un número que no se instrumentó en las dos partes no se compara con nada.

El contrato completo, campo por campo y con un ejemplo de una frase, está en
[`docs/android-integration.md`](docs/android-integration.md). **Es lo primero que se lee si se
toca el protocolo, y se actualiza en el mismo cambio.** Para cambiar un frame o un nombre de
métrica, se lee además el skill `contrato-websocket` del repositorio de la app (vive en
`signall-android/.opencode/skills/`).

## CPU y GPU

El **default es el entorno del plan de pruebas**: `medium` en una GPU NVIDIA. La elección es
manual y explícita: no hay preguntas ni autodetección. La opción de CPU existe para una PC sin
GPU (o con una que no alcanza).

| Quiero… | Comando |
|---|---|
| **el default** (GPU, `medium`) | `docker compose -f docker-compose.yml -f docker-compose.host.yml up -d` |
| **sin GPU** | `docker compose -f docker-compose.yml -f docker-compose.host.yml -f docker-compose.cpu.yml up -d` |

- El servicio `stt` toma `MODEL_SIZE`, `DEVICE` y `COMPUTE_TYPE` del entorno, con
  `medium`/`cuda`/`float16` por defecto y `deploy.resources.reservations.devices` con driver
  `nvidia`. `docker-compose.cpu.yml` fija `small`/`cpu`/`int8`, quita la reserva con
  `deploy: !reset` y compila el STT con `requirements.txt` (sin las librerías de CUDA).
- El `Dockerfile` del backend instala **siempre** torch desde el índice de CPU, **antes** de
  `requirements.txt`, para que el resolver no baje los 7,5 GB de paquetes `nvidia-*`. El
  contenedor del backend **no recibe la GPU** (`HostConfig.DeviceRequests` es `null`; la reserva
  está solo en `stt`) y `EmbeddingModel` no elige dispositivo, así que los embeddings siempre
  corrieron en CPU: el wheel de CUDA nunca se usó. Si algún día tienen que ir en GPU, es un
  cambio de diseño (reservar el dispositivo y llevar torch con CUDA) y los documentos tienen que
  decirlo.
- Si se pide CUDA y falla al cargar el modelo, el STT cae a CPU como red de seguridad y
  `/health` publica el dispositivo efectivo (`device` y `requested_device`). Eso no elige el
  perfil: el perfil ya quedó declarado en el comando.

## Decisiones de diseño

Trátalas como el punto de partida, no como algo incuestionable: si al implementar una de estas
reglas no tiene sentido, genera un problema real o hay una forma claramente mejor, se dice
explícitamente y se explica por qué antes de decidir, en vez de cambiarla en silencio.

- **`LLMClient` solo devuelve glosas, nunca decide el tipo de frase.** El `phrase_type` siempre
  viene de `GlossAnalyzer` (huella gramatical), tanto al guardar como al consultar
  `SemanticCache`.
- **Sin umbrales numéricos en requisitos o lógica funcional.** Cualquier valor cuantitativo
  (latencia, tamaños, timeouts) pertenece a configuración o a no-funcionales, nunca hardcodeado
  en la lógica de negocio como si fuera parte del contrato funcional.
- **Las señales de colisión de `GlossAnalyzer` nunca se ocultan.** Se reportan siempre
  (`hasCollision`, `secondarySignals`), incluso cuando no afectan el resultado final: son
  instrumentación para validación empírica.
- **`CatalogRepository` carga todo el catálogo en memoria al arrancar** (`load_all()`).
  `ValidatorService` nunca consulta PostgreSQL durante la inferencia, solo el mapa en memoria.
- **El prompt de glosas NO lleva la lista de glosas.** Es la decisión **D-7** (owner,
  2026-10-16): la lista sale del prompt porque va contra el plan de pruebas y no escala.
  `self._prompt` es la constante `PROMPT_TEMPLATE`, sin nada inyectado. Lo que hace el trabajo es
  `_repair_glosses` + `_merge_fragments` (consultan el vocabulario en memoria, O(1)) y el
  validador, que marca como no disponible lo que no está en el catálogo. LSC50 tiene glosas
  **frasales** (`COMO ESTAS`, `BUENOS DIAS`, `MAS O MENOS`), así que la regla de "una glosa = una
  palabra" partía las frases en palabras que no existían en el catálogo y el avatar caía a la
  seña por defecto. El razonamiento completo está en el comentario de `app/nlp/llm_client.py` y
  en [`docs/performance.md`](docs/performance.md) §9.
- **No se usa el patrón Gateway dentro del monolito.** El flujo es Controller → Orchestrator,
  sin una capa intermedia.

## Convenciones de código

- Todo el código y los comentarios van **en inglés**, sin excepción.
- Buenos hábitos de Python/FastAPI: type hints, funciones pequeñas y con una sola
  responsabilidad, nombres descriptivos, sin código muerto ni comentado.
- Los nombres de clases coinciden exactamente con los del SDD (`Controller`, `Orchestrator`,
  `NLPServiceImpl`, `GlossAnalyzer`, `SemanticCache`, `LLMClient`, `ValidatorServiceImpl`,
  `CatalogRepository`, `Segment`, `PhraseType`, `Gloss`, `ValidatedSegment`, `Fingerprint`).
- Los métodos siguen el nombre semántico del SDD pero en `snake_case` (`loadAll()` del SDD se
  implementa como `load_all()`): PEP 8 le gana a la notación UML.
- **La métrica se agrega antes que la feature.** Un número que no se instrumentó no se puede
  afirmar que mejoró.

## Trampas operativas

- **Cambiar el prompt NO invalida `semantic_cache`.** Las glosas viejas siguen en Neon y salen
  por `SemanticCache HIT`, así que el prompt nuevo no se ejecuta y parece que el arreglo no
  sirvió. Después de tocar el prompt o el modelo:

  ```sql
  DELETE FROM semantic_cache;
  ```

  Es un caché derivado, se reconstruye solo con la primera frase de cada una.

- **El catálogo se carga una sola vez al arrancar.** Después de un seed hay que reiniciar el
  servicio: no hay invalidación.
- **El proveedor del LLM es configurable, no fijo.** `LLM_BASE_URL` vacío = OpenAI. Apuntándolo
  a un servidor local (Ollama, LM Studio, vLLM) corre el mismo prompt sin API key ni costo. El
  backend va en la red de Compose, así que el servidor local se alcanza por
  `host.docker.internal` (`extra_hosts` ya está en `docker-compose.yml`) y tiene que escuchar
  fuera de `127.0.0.1` (Ollama: `OLLAMA_HOST=0.0.0.0:11434`). Si el firewall del host filtra el
  tráfico que viene del bridge —con `ufw` activo pasa, medido el 2026-10-26— el camino es
  `docker-compose.host.yml`, que pone el backend en la red del host y deja `127.0.0.1:11434` al
  alcance sin tocar el firewall.
- **El proxy TLS es parte del sistema, no un extra.** Se levanta con los dos archivos de Compose
  (`-f docker-compose.yml -f docker-compose.host.yml`); con uno solo no hay `wss://` y el APK
  `demo` de Android no conecta. La verificación y el significado de cada fallo están en
  [`deploy/README.md`](deploy/README.md).
- **Cambiar de modelo puede no cambiar nada.** Con el prompt de glosas frasales, `gpt-4o-mini` y
  `qwen3:4b-instruct` siguen partiendo algunas frases, y por eso `_repair_glosses` existe: el
  prompt solo no alcanza.
- **La transparencia importa**: los números que se citan llevan su origen (fecha, corpus, si la
  caché estaba caliente). [`docs/performance.md`](docs/performance.md) y
  [`docs/tablas-rendimiento.md`](docs/tablas-rendimiento.md) son el registro.

## Verificación

```bash
pip install -r requirements-dev.txt   # ruff, mypy y coverage
tools/calidad/verificar.sh            # ruff, mypy y gitleaks: toda la verificación local
ruff check app scripts                # solo el análisis estático, por separado
mypy                                  # tipado de app/
scripts/cobertura.sh                  # corre los verify_* bajo coverage y deja coverage.xml

docker compose -f docker-compose.yml -f docker-compose.host.yml config        # default (GPU)
docker compose -f docker-compose.yml -f docker-compose.host.yml \
    -f docker-compose.cpu.yml config                                          # perfil de CPU
docker compose -f docker-compose.yml -f docker-compose.host.yml exec backend \
    python -m scripts.verify_client_frames        # el contrato

curl -s http://localhost:8080/health    # estado, catálogo cargado y configuración del STT
curl -s http://localhost:8080/metrics   # rt_first_sign_ms, rt_phrase_total_ms, ...
```

No hay una suite de `pytest`: las pruebas son los `scripts/verify_*.py`, que se corren **como
módulo**, `python -m scripts.<nombre>` — corridos como `python scripts/x.py`, `sys.path[0]` es
`/app/scripts` y `import app` no resuelve. Salen con código 1 cuando el comportamiento que
vigilan cambió. La mayoría necesita las dependencias del servicio, así que lo práctico es
correrlos dentro de la imagen.

## Commits

- Convención: `tipo(scope): descripción` **en inglés** (Conventional Commits). Tipos usados:
  `feat`, `fix`, `chore`, `docs`, `test`, `infra`.
- **No se hace `git commit` ni `git push` sin que el owner lo pida**: se propone el mensaje y lo
  hace él. Todo el trabajo va a `main`; la rama `develop` no existe desde el 2026-11-11.

## Qué cargar y cuándo

| Si la tarea toca… | Cargar |
|---|---|
| **Un frame del WebSocket o un nombre de métrica** | [`docs/android-integration.md`](docs/android-integration.md) + el skill `contrato-websocket` del repositorio de la app |
| **El diseño, los diagramas o los requisitos** | [`docs/sdd.md`](docs/sdd.md), [`docs/diagrams/`](docs/diagrams/), [`docs/plan-implementacion-backend.md`](docs/plan-implementacion-backend.md); los requisitos en `signall-docs/borradores/requerimientos/` |
| **Una decisión que ya se cerró, o una que está abierta** | [`docs/decisions.md`](docs/decisions.md) |
| **Una inconsistencia entre el SDD, los diagramas y el código** | [`docs/sdd-changes.md`](docs/sdd-changes.md): se anota ahí, no se edita el SDD |
| **Mediciones de latencia o el efecto de una optimización** | [`docs/performance.md`](docs/performance.md) y [`docs/tablas-rendimiento.md`](docs/tablas-rendimiento.md) |
| **El proxy TLS, el certificado o la demo cifrada** | [`deploy/README.md`](deploy/README.md) y [`docs/plan-proxy-tls.md`](docs/plan-proxy-tls.md) |
| **El WiFi, la IP del teléfono o la publicación del APK** | [`docs/plan-wifi.md`](docs/plan-wifi.md) |
| **Qué cambió en el flujo por oraciones y qué falta del otro lado** | [`docs/CAMBIOSBACKEND.md`](docs/CAMBIOSBACKEND.md) |
| **El mapa completo del sistema y el protocolo del STT** | `signall-android/docs/SISTEMA.md` y el `README.md` de `signall-stt` |
