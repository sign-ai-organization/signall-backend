# signall-backend

Servicio central del proyecto **SignAll**: recibe español (texto o audio) desde la app
Android, lo convierte en glosas de Lengua de Señas Colombiana (LSC) y devuelve las señas
que el avatar tiene que representar.

## Qué es

Un monolito modular en FastAPI con PostgreSQL 16 y pgvector. El flujo de una frase es
`Controller` (WebSocket) → `Orchestrator` → `NLPService` → `ValidatorService` →
`CatalogRepository`: el controlador recibe el turno, el orquestador lo recorre, el servicio de
NLP corta el texto en oraciones y produce las glosas con un LLM, y el validador comprueba que
cada glosa exista en el catálogo antes de mandarla. La base guarda el catálogo de glosas de
LSC50 y el caché semántico de frases ya traducidas. La arquitectura completa, con los
diagramas y las decisiones, está en [`docs/sdd.md`](docs/sdd.md).

## Enfoque

**Hace:** mantiene el WebSocket con el cliente, transcribe el audio que le llega (delegando
en el STT), traduce el texto a glosas, valida el resultado contra el catálogo y devuelve cada
oración con su índice y su total. También expone `/health`, `/metrics` y `/metrics.json`.

**No hace:** no captura audio del dispositivo, no ejecuta el modelo de voz y no dibuja nada.
El reconocimiento de voz es de
[signall-stt](https://github.com/sign-ai-organization/signall-stt) y la representación es de
[signall-android](https://github.com/sign-ai-organization/signall-android). Tampoco traduce
la transcripción por su cuenta: solo se traduce lo que el cliente manda como `text`, para que
la voz no entre en un bucle.

## Cómo se usa

El sistema completo —backend, servicio de voz y **proxy TLS**— se levanta con **dos archivos
de Compose**:

```bash
cp .env.example .env                                    # completar DATABASE_URL y LLM_API_KEY
git clone https://github.com/sign-ai-organization/signall-stt ../signall-stt
docker compose -f docker-compose.yml -f docker-compose.host.yml up -d
```

El `docker-compose.yml` construye el servicio de voz desde un clon de `signall-stt` en la
carpeta hermana (`../signall-stt`, la ruta que declara el propio archivo), así que el clon va
ahí. El `docker-compose.host.yml` es un **override** que pone el backend en la red del host y
agrega el proxy.

| Servicio | Qué es | Queda en |
|---|---|---|
| `backend` | este repositorio | `http://localhost:8080` |
| `stt` | el servicio de voz del clon hermano | `http://localhost:8000` |
| `caddy` | el proxy TLS de `deploy/` | `https://127.0.0.1/` (443) y `wss://…/ws/translate` |

### CPU o GPU: se elige, no se detecta

El **default es el entorno del plan de pruebas**: Whisper `medium` en una GPU NVIDIA. El modelo
y el dispositivo del servicio de voz se eligen con `MODEL_SIZE`, `DEVICE` y `COMPUTE_TYPE`. Para
una PC **sin GPU** (o con una que no alcanza) está `docker-compose.cpu.yml`: fija
`small`/`cpu`/`int8`, quita la reserva de la tarjeta y compila la imagen del STT sin las
librerías de CUDA. La elección es **manual y explícita**: no hay preguntas, no hay
autodetección y no hay un segundo Dockerfile.

| Quiero… | Comando |
|---|---|
| **el default** (GPU, `medium`) | `docker compose -f docker-compose.yml -f docker-compose.host.yml up -d` |
| **sin GPU** | `docker compose -f docker-compose.yml -f docker-compose.host.yml -f docker-compose.cpu.yml up -d` |
| solo el STT, default | `cd ../signall-stt && docker compose up --build` |
| solo el STT, sin GPU | `cd ../signall-stt && docker compose -f docker-compose.yml -f docker-compose.cpu.yml up --build` |

| Archivo | `MODEL_SIZE` | `DEVICE` | `COMPUTE_TYPE` | Reserva NVIDIA | Librerías CUDA del STT |
|---|---|---|---|---|---|
| `docker-compose.yml` (base, default) | `${MODEL_SIZE:-medium}` | `${DEVICE:-cuda}` | `${COMPUTE_TYPE:-float16}` | sí, driver `nvidia` | `requirements-gpu.txt` |
| `docker-compose.cpu.yml` (override) | `small` | `cpu` | `int8` | no (`!reset`) | `requirements.txt` |

El perfil de GPU necesita NVIDIA Container Toolkit (o Docker Desktop con soporte GPU
habilitado). **La imagen del backend siempre instala torch desde el índice de CPU**: el modelo
de embeddings corre en CPU aunque la máquina tenga GPU, y el wheel de PyPI para Linux traería
7,5 GB de paquetes `nvidia-*` inútiles para este servicio. El perfil de GPU es del STT, que vive
en el repositorio hermano.

**El proxy es parte del sistema, no un extra.** Sin él solo existe `ws://` en claro, y el APK
`demo` de Android —el que demuestra el cifrado— apunta a `wss://` y no conecta. Por eso el
`caddy` vive en el segundo archivo: necesita compartir la red del host para alcanzar al
backend por `127.0.0.1:8080`, y el archivo base se mantiene portable (red de Compose, la misma
configuración en Linux, macOS y Windows).

La consecuencia práctica se confunde con un error del backend: `docker compose up -d` **a
secas no levanta Caddy**. El backend responde en el 8080 y la app `demo` no conecta. Si se
levantó así, alcanza con volver a correr el comando de dos archivos; no hay que reconstruir
nada.

Antes del primer arranque del proxy hace falta el certificado de laboratorio, una vez por
máquina: son tres archivos en `deploy/certs/` que no están en git y se emiten con `mkcert`
según [`deploy/README.md`](deploy/README.md). Sin `lab.pem` y `lab-key.pem` el contenedor de
Caddy no arranca, y eso es a propósito: un proxy sin certificado no debe levantar en claro en
silencio.

### Comprobar que el sistema completo está arriba

```bash
scripts/verify_proxy.sh
```

Ese script falla con código 1 y un mensaje distinto según lo que falte: el certificado, el
contenedor de Caddy o la respuesta por TLS. También se puede mirar a mano:

```bash
docker compose -f docker-compose.yml -f docker-compose.host.yml ps caddy
curl --cacert deploy/certs/lab-ca.crt https://127.0.0.1/health
```

El primero tiene que listar `signall-backend-caddy-1` con estado `Up`. El segundo tiene que
devolver el mismo JSON de `/health` que el backend, porque el proxy solo reenvía. Si algo
falla, cada síntoma significa una cosa distinta:

| Síntoma | Qué significa | Qué hacer |
|---|---|---|
| `The file '…/lab-ca.crt' provided to --cacert does not exist` | el certificado no se emitió en esta máquina, o se borró | emitir los tres archivos con [`deploy/README.md`](deploy/README.md) |
| `curl: (60) SSL certificate problem` **sin** `--cacert` | normal: la CA de laboratorio no está en el almacén del sistema | usar `--cacert`, o instalar la CA si se quiere evitar |
| `curl: (7) Failed to connect … port 443` | Caddy no está arriba: se levantó con un solo archivo de Compose, o el contenedor se cayó porque falta el certificado | `docker compose -f docker-compose.yml -f docker-compose.host.yml up -d`, y si sigue, `… logs caddy` |
| `502 Bad Gateway` | el proxy está arriba y el backend no | `curl -s http://localhost:8080/health` y `docker compose … ps backend` |
| `ps caddy` no lista nada | el proxy nunca se levantó | el comando de dos archivos, no el de uno |

El backend por el 8080 sigue respondiendo igual que siempre: `curl -s
http://localhost:8080/health` sirve para separar "el backend está bien" de "el proxy falta".

Si no se quiere ese clon, se puede levantar el STT desde su propio repositorio y correr el
backend contra él:

```bash
# en signall-stt (default: GPU y medium; `-f docker-compose.cpu.yml` para CPU)
docker compose up --build

# en signall-backend, con STT_WS_URL=ws://localhost:8000/ws/transcribe en .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt      # trae PyTorch, spaCy y el modelo de embeddings
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

La primera vez tarda alrededor de un minuto: carga los modelos de NLP y el catálogo completo
desde Neon. Si la base no está disponible al arrancar, el servicio levanta igual y `/health`
responde `degraded`; en ese estado toda seña sale como no disponible. El STT solo hace falta
para el camino por voz: el texto escrito se traduce aunque no esté.

`DATABASE_URL` (PostgreSQL con pgvector, por ejemplo Neon con `sslmode=require`) y
`LLM_API_KEY` son obligatorias. `LLM_BASE_URL` vacía significa OpenAI; con una URL apunta a
cualquier endpoint compatible, como Ollama o LM Studio.

Dos avisos que cuestan tiempo: el caché semántico **no** se invalida al cambiar el prompt ni
el modelo (`DELETE FROM semantic_cache;` lo vacía), y el catálogo se carga **una sola vez** al
arrancar, así que después de un seed hay que reiniciar el servicio.

## Requisitos

| Necesitas | Detalle |
|---|---|
| Python 3.12 | solo si se corre sin Docker; con Compose la imagen lo trae |
| PostgreSQL 16 + pgvector | la cadena de conexión va en `DATABASE_URL` |
| Clave de LLM | `LLM_API_KEY`; `LLM_BASE_URL` vacía usa OpenAI |
| Servicio de voz | [signall-stt](https://github.com/sign-ai-organization/signall-stt) en `ws://…:8000/ws/transcribe`; sin él no hay voz |
| Certificado de laboratorio | `deploy/certs/` con la CA, el certificado y la clave; sin él el proxy no arranca (ver [`deploy/README.md`](deploy/README.md)) |
| Puertos | `8080` para el backend, `8000` para el STT y `443` para el proxy |
| GPU | el default es el del plan de pruebas (`medium`/`float16` en GPU); sin GPU se usa `docker-compose.cpu.yml` (`small`/`cpu`/`int8`) |

## Estructura

```
app/controller/       WebSocket /ws/translate, cliente del STT y router de administración
app/orchestrator/     el turno completo: audio o texto de entrada, oraciones de salida
app/nlp/              análisis de glosas, cliente del LLM, corte en oraciones y caché semántico
app/validation/       catálogo y validación de que cada glosa exista
app/persistence/      conexión a Neon, migraciones, keep-alive y recuperación
scripts/              verificaciones ejecutables, mediciones y cliente de traducción manual
deploy/               proxy TLS y archivos para la demostración cifrada
```

## Cómo se verifica

```bash
pip install -r requirements-dev.txt            # ruff, mypy y coverage
tools/calidad/verificar.sh                     # ruff, mypy y gitleaks: toda la verificación local
ruff check app scripts                         # solo el análisis estático, por separado
mypy                                           # tipado de app/
scripts/cobertura.sh                           # corre los verify_* bajo coverage y deja coverage.xml

curl -s http://localhost:8080/health     # estado, catálogo cargado y configuración del STT
curl -s http://localhost:8080/metrics    # rt_first_sign_ms, rt_phrase_total_ms, ...
```

El proyecto no tiene una suite de `pytest`: las pruebas son los `scripts/verify_*.py`, que se
pueden correr de a uno con `python -m scripts.<nombre>` y salen con código 1 cuando el
comportamiento que vigilan cambió. La mayoría necesita las dependencias del servicio, así que
lo práctico es correrlos dentro de la imagen con `scripts/cobertura.sh`.

## El resto del sistema

Este repositorio es **una pieza** de un sistema de cuatro, más la producción de las
animaciones:

| Repositorio | Qué aporta |
|---|---|
| [signall-stt](https://github.com/sign-ai-organization/signall-stt) | audio → texto en tiempo real |
| [signall-android](https://github.com/sign-ai-organization/signall-android) | la app que captura, envía y representa las señas |
| [signall-docs](https://github.com/sign-ai-organization/signall-docs) | los documentos de la tesis; **es el que manda para lo escrito** |
| [signall-avatar](https://github.com/sign-ai-organization/signall-avatar) | los GLB finales de los dos avatares (rama `dev`) |

Los repos hermanos son **fuentes de información**, no cajas negras: antes de cambiar un frame
del WebSocket, una glosa del catálogo o un nombre de métrica hay que leer el otro lado, porque
el contrato no lo verifica ningún compilador. La referencia cruzada está en
[`docs/android-integration.md`](docs/android-integration.md).

Cada cambio no trivial se documenta en `signall-docs`: en `cambios/` queda qué cambió y por
qué, y si toca un documento formal se actualiza el `.tex` y se compila con `make`.

## Licencia

Este proyecto se distribuye bajo la licencia que defina la Pontificia Universidad Javeriana (pendiente de confirmación; por ahora, todos los derechos reservados). Ver [LICENSE](LICENSE).

## Trabajo de grado

SignAll es un trabajo de grado de la Pontificia Universidad Javeriana (Colombia). Para
citarlo: el equipo del trabajo de grado (2026). *SignAll: español hablado a Lengua de Señas Colombiana con un
avatar 3D*.
