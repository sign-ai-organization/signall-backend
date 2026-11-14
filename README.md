# signall-backend

Backend del proyecto **SignAll**: recibe audio en español desde la app Android, lo manda
a transcribir, lo convierte en glosas de Lengua de Señas Colombiana y devuelve las señas
que el avatar tiene que representar.

Monolito modular en FastAPI: `Controller` (WebSocket) → `Orchestrator` → `NLPService` →
`ValidatorService` → `CatalogRepository`, con PostgreSQL + pgvector (Neon) para el catálogo
y el caché semántico.

## Cómo se corre

Lo normal es Docker, que levanta el backend y el STT juntos:

```bash
cp .env.example .env      # llena DATABASE_URL (Neon, sslmode=require) y LLM_API_KEY
docker compose up -d
```

El STT se compila desde `../signall-stt`, así que los dos repos tienen que estar uno al
lado del otro. Sin GPU NVIDIA se usa el override de host y el STT cae a CPU; ver
[`docs/android-integration.md`](docs/android-integration.md).

Para trabajar en el backend sin Docker:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt      # tarda: trae PyTorch por sentence-transformers
uvicorn app.main:app --reload
```

## Cómo se verifica

```bash
curl -s http://127.0.0.1:8080/health     # {"status":"ok","catalog_glosses":75,...}
curl -s http://127.0.0.1:8080/metrics    # rt_first_sign_ms, rt_phrase_total_ms, ...
ruff check app scripts                   # análisis estático (lo que corre el CI)
mypy
python -m scripts.verify_sentence_segmenter
```

Los scripts de `scripts/` prueban una pieza suelta sin pasar por la API:
`python -m scripts.<nombre>`. Los que necesitan librerías de desarrollo salen de
`requirements-dev.txt`.

## Qué necesita

| Necesitas | Detalle |
|---|---|
| Python 3.12 | o Docker con el compose del repo |
| PostgreSQL 16 + pgvector | Neon; la cadena va en `DATABASE_URL` |
| Clave del LLM | `LLM_API_KEY`; con `LLM_BASE_URL` vacío usa OpenAI |
| STT | `../signall-stt`, en el `8000`; lo levanta el mismo compose |
| Puertos | `8080` (backend) y `8000` (STT) |
| GPU | opcional: el STT corre en CPU con `DEVICE=cpu` |

**El caché semántico no se invalida al cambiar el prompt ni el modelo.** Si el arreglo
parece no surtir efecto, `DELETE FROM semantic_cache;`. El catálogo se carga **una sola
vez** al arrancar: después de un seed hay que reiniciar el backend.

## Adónde ir después

| Si vas a tocar… | Lee |
|---|---|
| Reglas de código, decisiones de diseño, trampas | [`CLAUDE.md`](CLAUDE.md) |
| La arquitectura completa | [`docs/sdd.md`](docs/sdd.md) |
| La integración con la app Android | [`docs/android-integration.md`](docs/android-integration.md) |
| El camino WiFi, TLS y el proxy | [`docs/plan-wifi.md`](docs/plan-wifi.md), [`docs/plan-proxy-tls.md`](docs/plan-proxy-tls.md) |
| Rendimiento y mediciones | [`docs/performance.md`](docs/performance.md) |

El código y los comentarios van **en inglés**, sin excepción, y los nombres de clase
coinciden con los del SDD. Este repo no se commitea sin que el owner lo pida.
