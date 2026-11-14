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

La forma normal es Docker, que levanta el backend y el servicio de voz juntos. El
`docker-compose.yml` construye ese servicio desde un clon de `signall-stt` en la carpeta
hermana (`../signall-stt`, la ruta que declara el propio archivo), así que el clon va ahí:

```bash
cp .env.example .env                                    # completar DATABASE_URL y LLM_API_KEY
git clone https://github.com/sign-ai-organization/signall-stt ../signall-stt
docker compose up -d
```

El backend queda en `http://localhost:8080`. Si no se quiere ese clon, se puede levantar el
STT desde su propio repositorio y correr el backend contra él:

```bash
# en signall-stt
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
| Puertos | `8080` para el backend; el STT publica `8000` |
| GPU | opcional; el STT cae a CPU con `DEVICE=cpu` y `COMPUTE_TYPE=int8` |

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
ruff check app scripts                         # análisis estático, lo mismo que corre el CI
mypy                                           # tipado de app/
scripts/cobertura.sh                           # corre los verify_* bajo coverage y deja coverage.xml

curl -s http://localhost:8080/health     # estado, catálogo cargado y configuración del STT
curl -s http://localhost:8080/metrics    # rt_first_sign_ms, rt_phrase_total_ms, ...
```

El proyecto no tiene una suite de `pytest`: las pruebas son los `scripts/verify_*.py`, que se
pueden correr de a uno con `python -m scripts.<nombre>` y salen con código 1 cuando el
comportamiento que vigilan cambió. La mayoría necesita las dependencias del servicio, así que
lo práctico es correrlos dentro de la imagen con `scripts/cobertura.sh`.

## Licencia

Este proyecto se distribuye bajo la licencia {{LICENCIA}}. Ver [LICENSE](LICENSE).

## Trabajo de grado

SignAll es un trabajo de grado de la Pontificia Universidad Javeriana (Colombia). Para
citarlo: {{AUTOR}} ({{AÑO}}). *SignAll: español hablado a Lengua de Señas Colombiana con un
avatar 3D*.
