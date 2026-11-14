# La red de compose pasa a ser el default; el modo host queda como override

- **Fecha:** 2026-10-26
- **Rama:** `develop`, desde `78006a5`
- **Decisión del owner:** el requisito RNF-POR-02 ya preveía quitar `network_mode: host`, así
  que el default tenía que ser la red de compose, y el modo host un archivo aparte "para quien
  use Ollama".

---

## Qué se hizo

`docker-compose.yml` corría el backend con `network_mode: host`, y eso era lo único que hacía
faltaba para que el requisito de portabilidad se cumpliera. El cambio no es de una línea:
el modo host resolvía **dos** direcciones que en la red de compose no existen.

| Archivo | Qué cambió |
|---|---|
| `docker-compose.yml` | Fuera `network_mode: host`. El backend va en la red de compose, con `ports: ["8080:8080"]` y `extra_hosts: ["host.docker.internal:host-gateway"]`. Comentario reescrito con la razón y con la salida cuando el firewall filtra |
| `docker-compose.host.yml` | **Nuevo.** El override: `network_mode: host`, `ports: !reset []` y `extra_hosts: !reset []` (son incompatibles con la red del host), y `STT_WS_URL` / `LLM_BASE_URL` en `127.0.0.1`, donde el nombre del servicio no resuelve |
| `.env` | `STT_WS_URL` vuelve al default `ws://stt:8000/ws/transcribe`; `LLM_BASE_URL` pasa a `host.docker.internal`. El override pisa las dos cuando se usa |
| `.env.example` | Los dos bloques reescritos: el default del STT ahora resuelve, y el LLM documenta las dos direcciones con el comando de cada una |
| `AGENTS.md` | La trampa de `STT_WS_URL` se reemplaza por la nueva realidad, más la trampa del firewall |
| `CLAUDE.md` | La nota del proveedor del LLM decía que `extra_hosts` "ya está en `docker-compose.yml`" y no estaba: ahora sí |
| `docs/android-integration.md` | El comando del override, para cuando el modelo corre en el host |
| `docs/CONTRASTE-BACKENDvsDOCUMENTOS.md` | Punto 33 de **B** a **A**, §2.3 reescrita, las dos tablas de resumen y la fila del proxy Caddy |

## La medición que obligó al override

En esta máquina (Linux, Docker 29.9.2, `ufw` activo) un contenedor en el bridge por defecto
**no alcanza el host**:

| Desde un contenedor en el bridge | Resultado |
|---|---|
| `host.docker.internal:11434` (Ollama) | timeout |
| `172.17.0.1:11434` | timeout |
| `172.17.0.1:5672` (puerto publicado de otro contenedor) | timeout |
| `1.1.1.1:80` | OK |

Ollama escucha en `*:11434`, así que el bind no era la causa: es `ufw`. Por eso el default
funciona en Docker Desktop y en Linux con el firewall abierto, y en esta máquina el camino
diario es el override.

## Qué se verificó, con la salida real

| Prueba | Resultado |
|---|---|
| `docker compose config` (base y override) | Válido en los dos, y la precedencia hace lo que se buscaba: base `stt` + `host.docker.internal`, override `127.0.0.1` |
| Base: puertos publicados | `0.0.0.0:8080->8080`, `0.0.0.0:8000->8000` |
| Base: `/metrics` desde el host | `200`, y el log lo registra desde `172.18.0.1` (el gateway del bridge) |
| Base: STT por nombre | `STT SILENCE_TIMEOUT_MS is 1500 ms` — lo lee `app/main.py:170-178` de `http://stt:8000`, o sea que el nombre resuelve |
| Base: LLM del host | `OpenAITimeoutError` y `LLM warm-up took 10413 ms`: es el timeout esperado de `ufw` |
| Override: puertos | Ninguno publicado en el contenedor (red de host), y `/metrics` responde `200` en `127.0.0.1:8080` |
| Override: STT | `STT SILENCE_TIMEOUT_MS is 1500 ms` |
| Override: LLM del host | `LLM warm-up took 132 ms` |
| Frase real por el socket | `{"type":"text","text":"hola, como estas"}` → `segment 1/1`, glosas `HOLA` y `COMO ESTAS` con `available: true` y `glb_path`, `total=478ms`; y `"mi mama esta enferma, necesito ayuda"` → 3 glosas, `total=471ms` |

Las dos frases se probaron con el **override**. La segunda devolvió `available: false` en las
tres glosas porque `MAMA`, `ENFERMA` y `AYUDA NECESITO` no están en el catálogo de LSC50: el
log lo dice (`No gloss of [...] is in the catalog`), no es un fallo del cambio.

## Lo que falta, y de quién es

| Qué | De quién |
|---|---|
| RNF-POR-02 dice *"hoy el backend usa la red del equipo anfitrión … se prevé quitar esa condición"*. La condición ya está quitada, así que la frase quedó falsa: hay que borrar esa cláusula | **Owner**, en `signall-docs` y en el Overleaf |
| Commit y PR contra `develop` | **Owner**: en este repo no se commitea sin que lo pida |
| Ollama como servicio opcional con perfil `local`, para no depender del firewall ni del host | Opcional. El punto 33 se cierra sin esto, y evita duplicar un modelo de 2,5 GB |

## Nota de entorno

La verificación estuvo bloqueada un rato porque el disco estaba al 100 % (473 GB, 471 MB
libres): el backend no podía bajar el modelo de embeddings de 470 MB. Se liberó con la
papelera del usuario y cachés de paquetes. No tenía relación con el cambio.
