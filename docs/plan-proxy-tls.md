# Plan de implementación — Proxy inverso y cifrado del enlace

**Estado:** ejecutado el 2026-10-27 (fases 0 a 6). Queda sin commit: el trabajo está
en el árbol de los tres repos y las propuestas de commit están en §11.
**Fecha:** 2026-10-26
**Alcance:** despliegue de demo (`../signall-backend` + `../signall-android`) y la
documentación que lo describe (`../signall-docs` y el Overleaf de la tesis).
**Requisito que cierra:** RF-INT-COM-06, que hasta el 2026-10-27 estaba marcado como
"No implementado" en `../signall-docs/plan-pruebas/00-bases/trazabilidad.md` y que ahora
aparece en la tabla de lo implementado.

Etiquetas usadas, igual que en `plan-implementacion-backend.md`:

- 🔧 **Código o configuración** — produce un commit.
- 🗂️ **Infraestructura o tarea manual** — puede no producir commit.
- 🛑 **Decisión requerida** — el plan se detiene hasta que el owner decida.
- ✅ **Verificación** — comprobación manual de que la pieza hace lo que dice.

---

## 1. La idea

Hoy la aplicación habla con el backend por un WebSocket **sin cifrar**: la frase que
la persona escribe, el audio que manda y la transcripción que vuelve viajan en claro
por la red. El SRS pide lo contrario desde la v0.16, y el requisito está sin cumplir.

La solución no es reescribir el backend. Es poner **una pieza delante**: un proxy
inverso (Caddy) que escucha en el 443 con un certificado, termina ahí el TLS y
reenvía en claro al backend por `127.0.0.1:8080`, que no se toca. El teléfono deja
de hablar `ws://` y habla `wss://`; desde el punto de vista de la app el cambio es
una dirección, y desde el punto de vista del backend no hay cambio ninguno.

```
Antes
  [Teléfono] ── ws://8080 (texto en claro) ──► [backend 0.0.0.0:8080]

Después
  [Teléfono] ── wss://443 (TLS) ──► [Caddy :443] ── http/ws 127.0.0.1:8080 ──► [backend]
```

Lo que se gana es exactamente lo que pide el requisito: el tramo que sale del
dispositivo y cruza la red va cifrado, y se puede **demostrar** con una captura de
tráfico, no solo afirmar en un documento. Lo que queda en claro es el tramo interno,
que es loopback dentro del mismo equipo y no sale de la máquina; eso se declara en
el SRS en lugar de esconderse.

---

## 2. Lo que se requiere

### 2.1 Del sistema

- Una pieza que termine TLS delante del backend.
- Un certificado válido para la **identidad** que usa el teléfono: `127.0.0.1` si va
  por USB con `adb reverse`, `192.168.80.49` si va por Wi-Fi. El certificado no es
  "del proxy": es de la identidad, y el proxy solo lo presenta.
- La app apuntando a `wss://` y **sin** poder degradar a `ws://` en el APK que se
  demuestra.

### 2.2 Del entorno

| Necesidad | Estado hoy |
|---|---|
| Caddy | **no instalado**; está en `cachyos-extra` (`2.11.7-1.1`) |
| mkcert | **no instalado**; está en `cachyos-extra` (`1.4.4-3.1`) |
| Puerto 443 libre en la máquina | sí, verificado |
| Backend y STT levantados | sí, con `docker-compose.host.yml` |
| Teléfono en la misma red | sí: `192.168.80.19`, PC `192.168.80.49`, misma `/24`, ping ~12 ms |
| Aislamiento de clientes en el router | no (verificado con `ping` desde el teléfono) |
| Cortafuegos de la máquina | **activo y bloqueando el entrante**: desde el teléfono, `curl http://192.168.80.49:8080/health` da `000` mientras el `ping` responde |

### 2.3 De las personas

- Una pantalla de bloqueo en el teléfono: Android 11 la exige para instalar una CA
  de usuario.
- Aplicar los cambios de `.tex` en Overleaf y de `.drawio` en `../signall-docs`:
  **los edita el owner**, la sesión solo propone el texto exacto.

---

## 3. Decisiones que el plan asume

| # | Decisión | Motivo | Si se cambia |
|---|---|---|---|
| 1 | Caddy **como contenedor en red de host**, declarado en `docker-compose.host.yml` | El backend ya corre en red de host; un Caddy en la red de compose no lo alcanza (`host.docker.internal` está filtrado por `ufw`). El comando de arranque no cambia | Tres archivos de compose, o Caddy en el host fuera de Docker; el diagrama diría "dos contenedores y un proceso" |
| 2 | **mkcert** con `127.0.0.1`, `localhost` y `192.168.80.49` | Un solo certificado sirve para USB y para Wi-Fi, sin reemitir al cambiar de camino | `tls internal` de Caddy: menos comandos, pero la CA queda en el volumen del contenedor y hay que exportarla con `docker cp` |
| 3 | **Build type `demo`** en la app | Único que puede a la vez prohibir texto en claro y confiar en la CA de laboratorio; `debug` permite `ws://` y por eso no puede demostrar el rechazo | Demostrar con `debug` y renunciar a la prueba de rechazo |

**Por qué hace falta el build `demo`:** desde la API 24, Android **no confía en las
CA instaladas por el usuario** salvo que el `network_security_config` de la app lo
declare. Hoy ni `debug` ni `release` lo declaran, así que instalar la CA en el
teléfono no alcanza: el handshake falla con `Trust anchor for certification path not
found`. Y `debug` permite texto en claro, así que sirve para la demo del cifrado
pero no para probar que la app rechaza `ws://`.

---

## 4. Qué se toca, archivo por archivo

### `../signall-backend`

| Archivo | Acción | Qué |
|---|---|---|
| `deploy/Caddyfile` | **nuevo** | Sitio en `:443` con `tls` por archivo y `reverse_proxy 127.0.0.1:8080`; `admin off` y `auto_https off` |
| `deploy/certs/` | **nuevo, fuera de git** | `lab.pem`, `lab-key.pem`, `lab-ca.crt`. Va al `.gitignore`: la clave privada no entra al repositorio |
| `docker-compose.host.yml` | editar | Servicio `caddy` con `network_mode: host`, volúmenes y `restart`; volúmenes nombrados `caddy-data` y `caddy-config` |
| `.gitignore` | editar | `deploy/certs/` |
| `docs/sdd.md` | editar | §6.2 (`:105`, `:114`) y §C4-2 (`:396`): de **dos** contenedores a **tres** y quién termina el TLS. El origen del certificado **no** entra acá: es un dato de despliegue del SRS (decisión del 2026-10-27) |
| `docs/sdd-changes.md` | editar | Entrada con fecha |
| `docs/CONTRASTE-BACKENDvsDOCUMENTOS.md` | editar | Cerrar el punto 34 y actualizar §10.2 |
| `deploy/README.md` | **nuevo, no estaba en el plan** | Un clon limpio trae `deploy/certs/` vacío y Caddy no arranca: el archivo dice cómo reemitir, levantar y probar |
| `docs/android-integration.md` | editar | Nota de `wss://` en §2 |
| `docs/performance.md` | editar | Entrada del cierre: el TLS no mueve la latencia por frase |
| `docs/sessions/2026-10-27-proxy-tls.md` | **nuevo** | Log de sesión (fase 7) |

**No se toca:** `Dockerfile`, `app/`, el protocolo del WebSocket, `uvicorn`. El
backend sigue escuchando en `0.0.0.0:8080` sin saber que existe un proxy.

### `../signall-android`

| Archivo | Acción | Qué |
|---|---|---|
| `app/src/demo/res/xml/network_security_config.xml` | **nuevo** | `cleartextTrafficPermitted="false"` y `trust-anchors` con `system` + `user` |
| `app/build.gradle.kts` | editar | `buildTypes { create("demo") { … } }` con `initWith(release)`, firma de `debug`, `isDebuggable = true` y `BACKEND_WS_URL` en `wss://` |
| `tools/verificar-tiempo-real.sh` | editar | El chequeo del teléfono (`:271-273`) sigue midiendo `8080`; agregar la variante `https://…:8443` |
| `AGENTS.md`, `docs/SISTEMA.md` | editar | Comando de demo con `wss://`, `adb reverse tcp:8443 tcp:443` y el nombre del certificado |
| `docs/CONTRASTE-APPvsDOCUMENTOS.md` | editar | A3 (`:106`): nueva redacción y nuevo hook de verificación |

**No se toca:** `SignAiBackendConfig.kt`, `SignAiWebSocketClient.kt`,
`AndroidManifest.xml` (ya apunta a `@xml/network_security_config`) ni el puente
Kotlin ↔ JS. El manifiesto y el cliente ya soportan `wss://`; el cambio es de build.

### `../signall-docs`

| Archivo | Acción | Qué |
|---|---|---|
| `diagramas/draw.io/sdd-6.2-vista-fisica-despliegue.drawio` | redibujar | Nodo **Caddy :443**, flecha `«WSS»` de Android al proxy, flecha nueva proxy→backend `«HTTP/WS»` por loopback, el host pasa de dos a **tres** entornos |
| `diagramas/draw.io/sdd-c4-2-contenedores.drawio` | redibujar | Contenedor **Reverse Proxy (Caddy)** y la arista partida: `«WSS»` afuera, `«HTTP/WS»` adentro |
| `diagramas/draw.io/sdd-c4-1-contexto.drawio` | etiqueta | Solo la arista a `[Android, WSS]`. **No** nodo nuevo: en nivel 1 el sistema es una caja |
| `diagramas/png/*.png` | regenerar | Las dos PNG editadas |
| `plan-pruebas/01-diseno/seguridad/pruebas.md` | editar | `:22`, `:36`, `:41`: "que el **proxy** acepte conexiones cifradas"; quitar "se espera que falle"; el rechazo de `ws://` se comprueba en `demo` |
| `plan-pruebas/00-bases/trazabilidad.md` | editar | `:142`: RF-INT-COM-06 deja de estar "No implementado" |

**No se toca:** la v0.16 del documento de requerimientos. RF-INT-COM-06
(`SignAI_Requerimientos_Consolidados_v0.16.md:208`) ya está bien escrito y el proxy
lo hace cumplir; exceptuar el tramo interno sería debilitarlo.

### Overleaf (lectura desde la sesión, escritura del owner)

| Documento | Ubicación | Qué se propone |
|---|---|---|
| SRS | `main.tex:1158-1171` | Párrafo del proxy: la app habla WSS por 443, el proxy termina el TLS y reenvía por HTTP/WS a 8080 en loopback; el tramo interno no sale del equipo |
| SRS | `main.tex:2156-2160` | Tabla de puertos: **443 externo, 8080 interno** |
| SRS | `main.tex:1348-1372` | Despliegue: Caddy, el certificado y la CA de laboratorio instalada en el teléfono |
| SDD | `:242` y `:481-485` | Tres contenedores, el proxy en la lista, quién termina el TLS |
| SDD | carpeta `images/` | Las dos PNG regeneradas |

---

## 5. Fases

### Fase 0 — Preparación (30 min) 🗂️

1. `sudo pacman -S caddy mkcert` (Caddy solo por comodidad de CLI; el servicio no
   se usa).
2. `mkdir -p deploy/certs` y agregarlo al `.gitignore`.
3. Confirmar que el 443 sigue libre: `ss -ltn | grep ':443'`.

**Terminado cuando:** `caddy version` y `mkcert -version` responden y
`deploy/certs/` está ignorado.

### Fase 1 — Certificado de laboratorio (20 min) 🔧

1. `mkcert -install` (crea la CA local).
2. Emitir un solo certificado para `127.0.0.1 localhost 192.168.80.49` en
   `deploy/certs/lab.pem` y `lab-key.pem`.
3. Copiar la CA raíz a `deploy/certs/lab-ca.crt` (es el archivo que va al teléfono).

**Terminado cuando:** `openssl verify -CAfile deploy/certs/lab-ca.crt
deploy/certs/lab.pem` responde `OK` y el SAN lista la IP y los dos nombres.

**Riesgo:** `192.168.80.49` es DHCP. Si cambia, se reemite (un comando) o se reserva
la IP en el router.

### Fase 2 — Caddy delante del backend (45 min) 🔧

1. Escribir `deploy/Caddyfile`.
2. Agregar el servicio `caddy` a `docker-compose.host.yml` con red de host.
3. `docker compose -f docker-compose.yml -f docker-compose.host.yml up -d`.

**Terminado cuando:**

- `curl --cacert deploy/certs/lab-ca.crt https://127.0.0.1/health` devuelve
  `{"status":"ok",…}`.
- `curl http://127.0.0.1:8080/health` sigue funcionando: el backend no se tocó.
- `openssl s_client -connect 127.0.0.1:443 -CAfile deploy/certs/lab-ca.crt` termina
  en `Verify return code: 0 (ok)`.

**Riesgo:** Caddy en red de host toma el 443 de la máquina. Hoy está libre, pero si
otro servicio lo toma, Caddy no arranca y lo dice en el log.

### Fase 3 — La app apunta a `wss://` (1 h) 🔧

1. Crear el `network_security_config` del build `demo`.
2. Agregar el build type `demo` en `app/build.gradle.kts`, con la dirección
   `wss://127.0.0.1:8443/ws/translate` (USB) o `wss://192.168.80.49/ws/translate`
   (Wi-Fi). Igual que `release`, solo acepta `wss://` en la propiedad de build.
3. `./gradlew assembleDemo` y `./gradlew installDemo`.

**Terminado cuando:** el APK instala y arranca, y en `adb logcat -s SignAllNet`
aparece `sesión abierta: wss://… (TLS)` una vez instalada la CA (fase 4).

**Por qué el 8443:** en el teléfono, `adb reverse tcp:443 tcp:443` **falla**
(`cannot bind listener: Permission denied`, verificado); se mapea
`tcp:8443 → 443` del host. El certificado no depende del puerto.

**Riesgo:** el APK `demo` tiene el mismo `applicationId` que `debug` y lo reemplaza.
Para volver atrás se reinstala `debug`.

### Fase 4 — Instalar la CA en el teléfono (20 min + reinicio) 🗂️

1. `adb push deploy/certs/lab-ca.crt /sdcard/Download/`.
2. **Antes de instalar**, abrir la app y guardar la evidencia del fallo de
   handshake (sin CA tiene que fallar).
3. Ajustes → Seguridad → Cifrado y credenciales → Instalar un certificado →
   **Certificado de CA** → `lab-ca.crt`.

**Terminado cuando:** la app abre sesión `wss://` sin error de certificado.

**Riesgos:** Android 11 exige pantalla de bloqueo para instalar una CA de usuario; y
MIUI a veces no muestra el archivo si la extensión no es `.crt`.

### Fase 5 — Verificación de punta a punta y evidencia (45 min) ✅

```bash
adb reverse tcp:8443 tcp:443     # si la demo va por USB
```

| Qué se prueba | Cómo | Esperado |
|---|---|---|
| El enlace va cifrado | `adb logcat -s SignAllNet` | `wss://… (TLS)` |
| El contenido no se puede leer | `sudo tcpdump -i lo -n -A 'tcp port 443'` mientras se envía una frase | el texto **no** aparece |
| La app rechaza `ws://` | probar el APK `demo` contra el 8080 en claro | `CLEARTEXT communication … not permitted` |
| El tramo interno sí va en claro | `sudo tcpdump -i lo -n -A 'tcp port 8080'` | ahí **sí** se lee: es la limitación declarada |
| El backend no cambió | `curl http://127.0.0.1:8080/health` | `status: ok` |

**Por Wi-Fi, además:** agregar la regla de cortafuegos solo para la subred
(`sudo ufw allow from 192.168.80.0/24 to any port 443 proto tcp`) y abrir
`https://192.168.80.49/health` en el navegador del teléfono. Si eso funciona y la
app falla, el problema es de la app o del certificado, no de la red.

### Fase 6 — Documentación (2–3 h) 🗂️

1. Redibujar 6.2 y C4-2; ajustar solo la etiqueta de C4-1.
2. Regenerar las PNG y copiarlas a los **tres** destinos: `../signall-docs/diagramas/png/`,
   `../signall-backend/docs/diagrams/` y la carpeta `images/` del SDD en Overleaf.
3. Aplicar los cambios de texto de §4 en el orden: SDD local → `sdd-changes.md` →
   plan de pruebas → trazabilidad → contrastes.
4. Entregar al owner el texto exacto para el SRS y el SDD de Overleaf.

**Terminado cuando:** los cinco documentos y las dos PNG dicen lo mismo que el
sistema, y no queda ninguna frase que afirme "dos contenedores".

### Fase 7 — Cierre (30 min) 🔧

1. Repetir la medición del 26/10 con `wss://` y comparar contra la línea base
   (caché 86 ms, LLM 345 ms, 2 señas en 3.797 s). El TLS agrega un handshake: si
   mueve el p50 de forma visible, se reporta con el número.
2. Log de sesión en `openspec/sessions/` de los dos repos tocados.
3. Commits: `feat(deploy): proxy Caddy con TLS de laboratorio` en el backend,
   `feat(build): variante demo con wss://` en la app.

---

## 6. Línea base medida (2026-10-26, Redmi Note 9S por USB)

Sirve para comparar después del cambio. Todo medido con el enlace **sin cifrar**,
así que no es comparable con la línea base de 913 ms p50 del camino por palabras.

| Qué | Valor |
|---|---|
| Escena con Pauline lista (`avatarReady`) | 2.836 s |
| Frase en caché ("Hola, como estas") | 86 ms, 2 glosas |
| Frase nueva por LLM ("Permiso, por favor") | LLM 307,9 ms, total 345 ms |
| Envío → primera seña | 417 ms |
| Representación de 2 señas | 3.797 s |
| Filas de caché semántico | 56 → 58 |

### 6.1 La misma medición, con `wss://` (2026-10-27)

Mismo teléfono (Redmi Note 9S) por USB, mismo LLM (`qwen3:4b-instruct` en Ollama
local), APK `demo` hablando `wss://127.0.0.1:8443/ws/translate` por
`adb reverse tcp:8443 tcp:443`. Los números del teléfono son de
`adb logcat -s SignAllMetrics`; los del NLP, del `Pipeline trace` del backend.

| Qué | Sin cifrar (2026-10-26) | Con TLS (2026-10-27) |
|---|---|---|
| Frase en caché ("hola gracias") | 86 ms | **40 y 41 ms** (la primera tras abrir la app: 161 ms) |
| Frase nueva por LLM, total | 345 ms (`llm` 307,9 ms) | **325,3 y 370,3 ms** (`llm` 291,2 y 272,7 ms) |
| Envío → primera seña, caché | 417 ms (frase nueva) | **80 y 88 ms** |
| Envío → primera seña, LLM | 417 ms | **358 y 406 ms** |
| Representación de 2 señas | 3.797 s (HOLA + COMO ESTAS) | 4.136 / 4.096 / 4.107 s (HOLA + GRACIAS) |
| Filas de caché semántico | 56 → 58 | 61 → 64 |
| Handshake TLS | — | 3,4–6,5 ms medido con `curl` en la máquina; ~73 ms desde el teléfono en la captura |

**El TLS no mueve el p50.** Lo que cambió está dentro del ruido de la corrida
anterior, y en la caché incluso salió más bajo. La razón es que el handshake ocurre
**una vez por sesión**, al abrir la app, y no entra en ninguna frase; por mensaje
solo se cifran unos cientos de bytes. El handshake tampoco se nota al usuario:
cae debajo del splash del avatar.

**Lo que sí hay que anotar de esta corrida:** la representación de las dos señas
subió ~0,3 s porque es **otro par de señas** (HOLA 2,12 s + GRACIAS 2,42 s contra
HOLA 2,12 s + COMO ESTAS 2,08 s). El descuento del fundido es el mismo en las dos
(−0,40 s), así que la diferencia es del clip y no del enlace.

**Un hallazgo que no es del TLS:** la primera frase por LLM después de un rato sin
tráfico tardó **6.778 ms** (de los cuales 6.400 ms fueron el modelo). Ollama había
descargado el modelo de memoria y lo estaba recargando, y el embedder de la caché
también estaba frío (`cache.embed` 317,8 ms contra 23–43 ms en caliente). Es el
mismo efecto que la entrada del 2026-10-26 de `../signall-backend` ya había medido
como *warm-up* del LLM, y en una demo se ve como "la primera frase se colgó".

---

## 7. Riesgos y cómo se tratan

| Riesgo | Impacto | Tratamiento |
|---|---|---|
| `ufw` bloquea el 443 | la app no conecta por Wi-Fi | regla explícita, limitada a la subred; se puede quitar |
| Android no confía en la CA de usuario | handshake falla en todo build | build `demo` con `trust-anchors` `user` |
| El teléfono no tiene pantalla de bloqueo | no se puede instalar la CA | poner PIN o patrón |
| La IP DHCP cambia | el certificado deja de coincidir | reservar la IP o reemitir |
| Caddy no alcanza el backend | 502 en el 443 | Caddy en red de host por loopback; verificar con `curl` antes del teléfono |
| El 443 queda expuesto a toda la LAN | exposición innecesaria | limitar la regla del cortafuegos a la IP del teléfono |
| La latencia por Wi-Fi no es comparable con USB | conclusiones falsas | demostrar por Wi-Fi, **medir por USB** y decirlo |
| El certificado de mkcert vence (~2 años) | la demo deja de funcionar | anotarlo; se reemite con el mismo comando |
| El `demo` reemplaza al `debug` en el teléfono | confusión al volver a medir | reinstalar `debug` al terminar la demo |

---

## 8. Deuda que queda declarada

1. **El tramo proxy → backend va en claro.** Es loopback dentro del mismo equipo y
   no sale de la máquina, pero se escribe en el SRS.
2. **El APK de release no sirve todavía.** `release` sigue apuntando a
   `wss://backend.invalid`. La CA de laboratorio es un artefacto de demo; para un
   release con certificado real y sin instalar CA en el teléfono hace falta un
   túnel con certificado público o un dominio. Es otra decisión, no está en este
   plan.
3. **Un solo certificado para una sola máquina.** No hay renovación automática ni
   dominio: si el proyecto se despliega de verdad, esto se reemplaza por
   Let's Encrypt o por el certificado del proveedor del túnel.

---

## 9. Lo que este plan no hace

- No modifica el backend en código ni el protocolo del WebSocket.
- No cifra el tramo interno.
- No habilita el APK de release.
- No toca el túnel público (Cloudflare Tunnel, ngrok, Tailscale Funnel): queda como
  alternativa si el owner prefiere no instalar una CA en el teléfono.
- No cambia la v0.16 de los requerimientos.

---

## 10. Estimación

| Fase | Trabajo |
|---|---|
| 0–2 | 1 h 35 min |
| 3–4 | 1 h 20 min |
| 5 | 45 min |
| 6 | 2–3 h (la mitad del total) |
| 7 | 30 min |
| **Total** | **~6 h**, en dos o tres sesiones |

Las fases 0 a 5 se pueden hacer de corrido con el teléfono conectado. La fase 6
depende del owner, porque los `.tex` y los `.drawio` los aplica él.

---

## 11. Checklist de cierre

- [x] `mkcert` y `caddy` instalados; `deploy/certs/` fuera de git.
- [x] Certificado verificado con `openssl verify`.
- [x] `https://127.0.0.1/health` responde con la CA.
- [x] `http://127.0.0.1:8080/health` sigue respondiendo: backend intacto.
- [x] APK `demo` instala, prohíbe texto en claro y confía en la CA de usuario.
- [x] CA instalada en el teléfono.
- [x] Log `SignAllNet` dice `(TLS)`.
- [x] Captura de `tcpdump` sin texto legible en el 443.
- [x] Intento de `ws://` rechazado por el APK `demo`.
- [x] Dos diagramas redibujados y las PNG en los tres destinos.
- [x] SDD, plan de pruebas, trazabilidad y contrastes actualizados.
- [x] Texto para el SRS y el SDD de Overleaf entregado al owner.
- [x] Medición después del cambio comparada con la línea base (§6.1).
- [x] Log de sesión en los dos repos.
- [ ] Commits: los propone la sesión, los hace el owner.

**Propuestas de commit (no ejecutadas):**

| Repo | Mensaje |
|---|---|
| `signall-backend` | `feat(deploy): proxy Caddy con TLS de laboratorio` |
| `signall-android` | `feat(build): variante demo con wss://` |
| `signall-docs` | `docs(diagramas): el proxy inverso en 6.2 y en C4-2` |
