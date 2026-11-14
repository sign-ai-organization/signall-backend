# Plan de implementación — Todo por Wi-Fi, sin cable

**Estado:** en ejecución. Fase 1 y fase 2 hechas el 2026-10-27; falta que el teléfono
instale el APK publicado y siga la fase 3.
**Fecha:** 2026-10-27.
**Alcance:** `../signall-android` (la app, casi todo), `../signall-backend` (el endpoint
de métricas del teléfono y el APK servido por Caddy) y la documentación que lo describe.
**Requisito que cierra:** RF-INT-COM-06 se sigue cumpliendo, y además el equipo deja de
depender del cable para instalar, medir y depurar.

Etiquetas, igual que en `plan-proxy-tls.md`:

- 🔧 **Código o configuración** — produce un commit.
- 🗂️ **Infraestructura o tarea manual** — puede no producir commit.
- 🛑 **Decisión requerida** — el plan se detiene hasta que el owner decida.
- ✅ **Verificación** — comprobación manual de que la pieza hace lo que dice.

---

## 1. La idea

Hoy el teléfono habla con el backend por el cable: `adb reverse` convierte
`127.0.0.1` en la máquina, y `adb` es también como se instala el APK y como se leen
las métricas (`adb logcat -s SignAiMetrics`). El enlace cifrado ya existe y ya se
probó, pero por USB.

El objetivo es que el cable desaparezca de las cuatro cosas que hoy dependen de él:

| Qué | Hoy | Con este plan |
|---|---|---|
| La app llega al backend | `adb reverse tcp:8443 tcp:443` | `wss://192.168.80.49/ws/translate` por la red local |
| Instalar o actualizar el APK | `./gradlew installDemo` (adb) | se baja de `https://192.168.80.49/apk/` en el navegador del teléfono |
| Saber qué build corre | `adb shell dumpsys package` | la app lo reporta en su primer latido |
| Leer las métricas del teléfono | `adb logcat -s SignAiMetrics` | `tools/wifi/metricas.sh`, que lee el reporte de la app |
| Leer un error | `adb logcat -s SignAiNet SignAiState` | el último error viaja en el reporte |

```
Antes
  [Teléfono] ── USB ── adb reverse ──► [PC: 127.0.0.1:8443 → Caddy :443]
  [Teléfono] ◄── adb logcat ── [PC]

Después
  [Teléfono 192.168.80.19] ══ Wi-Fi ══► [PC 192.168.80.49 :443 Caddy] ──► [backend :8080]
                                   └──► [APK]  ──► instalar
                                   └──► [POST /device/metrics] ──► métricas
```

**Lo que se gana:** el teléfono se puede dejar en la mesa, lejos de la PC; la medición
se puede repetir sin que nadie conecte nada; y el APK que se mide es el mismo que se
demuestra (si se elige el build `demo`, ver §4).

**Lo que se pierde:** la red local agrega un tramo que el cable no tiene. Está medido
en §2 y es la razón por la que la latencia del teléfono **no** es comparable con la de
USB. Los números del backend no cambian, porque se miden desde que la frase llega.

---

## 2. Lo que se midió hoy (2026-10-27)

Todo verificado en la máquina de la tesis, con el teléfono todavía por USB.

| Qué | Valor |
|---|---|
| PC en la red local | `192.168.80.49/24`, `wlan0`, DHCP |
| Teléfono en la red local | `192.168.80.19/24`, Redmi Note 9S, Android 11 (API 30) |
| Misma subred | sí, `/24`, sin aislamiento de clientes |
| `ping` teléfono → PC (10 paquetes) | min 7,4 ms · **media 38,4 ms** · max 227,2 ms · mdev 63,6 ms |
| TCP 443 desde el teléfono | **timeout** |
| TCP 8080 desde el teléfono | **timeout** |
| `ufw` | activo (`systemctl is-active ufw`); las reglas necesitan `sudo` |
| Backend y Caddy | red de host; escuchan en `0.0.0.0:8080` y `*:443` |
| Certificado de laboratorio | SAN `127.0.0.1`, `localhost`, `192.168.80.49` |
| CA de laboratorio en el teléfono | instalada (sesión del 2026-10-27) |
| APK `demo` | 40,8 MB; APK `debug` 50,0 MB |
| `versionCode` de la app | `1` en los tres build types |

**El bloqueo número uno es el cortafuegos, no la app.** El `ping` responde y el TCP no:
eso es un `DROP` en el `INPUT` del host, y coincide con lo que `plan-proxy-tls.md` §2.2
ya había anotado. Hasta que no se abra el 443 para la subred, ninguna app puede
conectar por Wi-Fi.

**El `ping` es malo para ser una LAN.** 38 ms de media y 227 ms de máximo no son la
red del cable. Es lo que va a separar la latencia del teléfono de la del backend, y por
eso la medición se hace con la pantalla encendida y la app en primer plano (el ahorro
de energía del Wi-Fi es la causa más probable). Se anota en `performance.md`.

---

## 3. Las cuatro piezas que hay que construir

1. **La red abierta.** Una regla de `ufw` para el 443, limitada a la subred. Es lo
   único que hoy impide que el teléfono hable con la PC.
2. **El APK servido por el mismo 443.** Caddy ya está delante del backend; se le agrega
   una ruta estática. No hace falta otro servidor ni otro puerto.
3. **La dirección editable desde la app.** Hoy la IP entra por
   `-Psignai.backendWsUrl` y eso obliga a recompilar cada vez que el DHCP cambia.
   Pasa a ser un campo en AVANZADO, guardado en preferencias.
4. **El reporte de métricas del teléfono.** La app manda su `SignAiMetrics` por HTTP al
   mismo origen, y el backend lo publica junto a las suyas en `/metrics.json` y
   `/metrics`. Es lo que reemplaza `adb logcat`.

---

## 4. Decisiones que el plan asume 🛑

| # | Decisión | Motivo | Si se cambia |
|---|---|---|---|
| 1 | **Un solo APK: `demo` (solo `wss://`)**, para medir y para demostrar. **Decidida por el owner el 2026-10-27.** | Es el único build que prohíbe el texto en claro y confía en la CA de laboratorio. Medir con el build que se demuestra evita el "esto anda pero aquello no" | `debug` + `ws://`: más simple, pero el número publicado sale de un build que no cumple RF-INT-COM-06, y hay que abrir el 8080 |
| 2 | **Las métricas viajan por HTTP `POST /device/metrics`**, no por un frame nuevo del WebSocket | El reporte tiene que llegar **también cuando el socket está caído**, que es justo cuando se necesita. No toca el contrato del WebSocket ni el invariante de "solo se traduce el `text`" | Un frame `client_metrics`: reusa el socket, pero se pierde el reporte en las desconexiones y hay que versionar el contrato |
| 3 | **La dirección se cambia en la app**, en AVANZADO, y se aplica reiniciando | Sin recompilar y sin reinstalar. El build type decide qué esquemas acepta | Solo `-Psignai.backendWsUrl`: menos código, pero cada IP nueva es un build nuevo |
| 4 | **Se mide por Wi-Fi y se publica con esa condición** | Es lo que pidió el owner: todo por Wi-Fi. El número del backend no cambia; el del teléfono sí, y se declara | Medir por USB y demostrar por Wi-Fi (lo que decía `plan-proxy-tls.md`): comparable con la línea base vieja, pero deja el cable en la medición |

**Por qué el `demo` y no el `debug`.** `demo` es `release` en lo que hace al enlace:
`cleartextTrafficPermitted="false"` y `trust-anchors` con `system` + `user`. Está firmado
con la clave de debug y es `isDebuggable`, así que se instala y se depura igual. El
`debug` acepta `ws://` y por eso no puede demostrar que el enlace va cifrado.

**Consecuencia de la decisión 1:** el 8080 **no se abre** para la LAN. El `debug` queda
para el emulador y para el desarrollo con cable, no para el camino Wi-Fi. El APK que se
publica en `/apk/` es siempre el `demo`.

**Una precisión sobre el canal.** `AGENTS.md` dice que la app y el backend hablan por un
solo WebSocket. Eso ya no es literal: la app **ya** descarga assets por HTTP desde el
mismo origen (`SignAssetRepository`). El reporte de métricas es el mismo tipo de canal:
HTTP al mismo origen, sin tocar el WebSocket. La frase de `AGENTS.md` se ajusta en la
fase 4 en vez de dejar una regla que el código ya no cumple.

---

## 5. Qué se toca, archivo por archivo

### `../signall-backend`

| Archivo | Acción | Qué |
|---|---|---|
| `deploy/Caddyfile` | editar | `handle_path /apk/*` con `file_server` antes del `reverse_proxy` |
| `docker-compose.host.yml` | editar | volumen `./deploy/apk:/srv/apk:ro` en el servicio `caddy` |
| `.gitignore` | editar | `deploy/apk/` (son artefactos de build, no van al repo) |
| `app/observability/device_metrics.py` | **nuevo** | Registro en memoria por dispositivo, validación y render de Prometheus |
| `app/main.py` | editar | `POST /device/metrics`; `devices` en `/metrics.json`; las series del teléfono en `/metrics` |
| `docs/android-integration.md` | editar | El endpoint, el payload y los nombres; y que el contrato del WebSocket no cambia |
| `docs/performance.md` | editar | Línea base por Wi-Fi, con las condiciones de la corrida |
| `AGENTS.md` | editar | La frase del canal: WebSocket para el tiempo real, HTTP para assets y telemetría |
| `docs/plan-wifi.md` | **nuevo** | Este archivo |
| `docs/sessions/2026-10-27-wifi.md` | **nuevo** | Log de la ejecución (fase 7) |

**No se toca:** el WebSocket, `app/realtime/` (no existe y no vuelve), el STT, Neon, el
Dockerfile ni el protocolo de los frames.

### `../signall-android`

| Archivo | Acción | Qué |
|---|---|---|
| `app/build.gradle.kts` | editar | `GIT_SHA` en `BuildConfig`; `versionCode` desde la cantidad de commits; `ALLOW_CLEARTEXT_BACKEND` por build type |
| `app/src/main/java/.../data/SignAiBackendConfig.kt` | editar | La URL sale de las preferencias si hay una guardada; validación por build type |
| `app/src/main/java/.../data/SettingsRepository.kt` | editar | Clave `server_url` (`null` = la del build) |
| `app/src/main/java/.../domain/Settings.kt` | editar | `serverUrl: String?` |
| `app/src/main/java/.../ui/screens/settings/SettingsSidebar.kt` | editar | Campo "Servidor", botón "Probar" y "Guardar", solo en AVANZADO |
| `app/src/main/java/.../data/DeviceMetricsReporter.kt` | **nuevo** | El POST periódico con el estado y las métricas |
| `app/src/main/java/.../ui/state/SignAiMetrics.kt` | editar | `snapshotData()` tipado, además del `snapshot()` de texto; `session_id` al reiniciar |
| `app/src/main/java/.../ui/state/MainScreenState.kt` | editar | Engancha el reporte: al terminar un turno, al reiniciar las métricas y en `fail()` |
| `tools/wifi/publicar-apk.sh` | **nuevo** | Compila, publica en `deploy/apk/` y muestra la URL y el QR |
| `tools/wifi/estado.sh` | **nuevo** | Salud del camino Wi-Fi y último latido del teléfono |
| `tools/wifi/metricas.sh` | **nuevo** | Backend + teléfono en una sola tabla |
| `tools/wifi/abrir.sh` | **nuevo** | QR de las URLs para el navegador del teléfono |
| `tools/verificar-tiempo-real.sh` | editar | El bloque del dispositivo deja de usar `adb` |
| `AGENTS.md`, `docs/SISTEMA.md` | editar | El camino Wi-Fi como camino normal |

**No se toca:** `SignAiWebSocketClient` (ya soporta `wss://`), el puente Kotlin ↔ JS,
`AndroidManifest.xml`, los `network_security_config.xml`, ni el catálogo de señas.

### `../signall-docs` y Overleaf

| Archivo | Acción | Qué |
|---|---|---|
| `diagramas/draw.io/sdd-6.2-vista-fisica-despliegue.drawio` | redibujar | La flecha Android → Caddy pasa de `«WSS por USB»` a `«WSS por Wi-Fi»`, y aparece la ruta del APK |
| `plan-pruebas/...` | editar | La prueba de conexión se hace en el navegador del teléfono, no con `adb` |
| Overleaf (SRS/SDD) | proponer texto | El teléfono habla WSS por la red local; las métricas del dispositivo viajan por HTTPS al mismo origen; no hay cable |

---

## 6. Los scripts permanentes

Van en `../signall-android/tools/wifi/` y se pueden correr desde cualquier lado. Todos
toman `SIGNAI_HOST` (por defecto, la IP de la PC en la red local) y `SIGNAI_CACERT` (por
defecto, `../signall-backend/deploy/certs/lab-ca.crt`).

| Script | Qué hace | Uso |
|---|---|---|
| `publicar-apk.sh` | `assembleDemo` con la IP actual inyectada en `-Psignai.backendWsUrl=wss://<IP>/ws/translate`, copia el APK a `deploy/apk/signai-demo.apk`, escribe un `index.html` con la versión y el SHA, imprime la URL y un QR | `tools/wifi/publicar-apk.sh` |
| `estado.sh` | IP del host, `/health` por la red, último latido, versión y SHA que reporta la app, URL en uso, estado del socket, último error y antigüedad del reporte | `tools/wifi/estado.sh` |
| `metricas.sh` | Tabla única: latencias del backend y latencias del teléfono, con `n`, p50, p95 y max | `tools/wifi/metricas.sh [--watch] [--json]` |
| `abrir.sh` | QR en la terminal de la URL que hay que abrir en el teléfono | `tools/wifi/abrir.sh [apk\|salud]` |

`qrencode` ya está instalado en la máquina, así que el QR no agrega dependencias.

`verificar-tiempo-real.sh` cambia en un solo bloque: `check_device` pasa a
`check_device_network` y deja de llamar a `adb`. El resto (servicios, contrato,
fixtures, latencia, métricas) ya funciona sin teléfono.

---

## 7. Fases

### Fase 0 — Decisiones (15 min) 🛑

Cerrar las cuatro de §4. Sin eso, las fases 2 a 5 pueden quedar para atrás: si se elige
`debug` + `ws://`, hay que abrir el 8080 y el APK que se mide no es el que se demuestra.

**Terminado cuando:** hay una respuesta por cada fila de §4.

### Fase 1 — Abrir la red (15 min) 🗂️

```bash
ip -4 -o addr show scope global
sudo ufw status numbered

# Solo el 443, solo la subred. Es el único puerto que hace falta si se usa wss.
sudo ufw allow from 192.168.80.0/24 to any port 443 proto tcp comment 'SignAI WSS'
sudo ufw reload
sudo ufw status numbered

# Desde la PC, con la CA del laboratorio
curl -sS --cacert deploy/certs/lab-ca.crt https://192.168.80.49/health
```

Con la decisión 1 el 8080 **no se abre**: el `debug` se usa solo en el emulador. Si
alguna vez hace falta un smoke test en claro con el teléfono, se abre solo para su IP y
se cierra enseguida:

```bash
sudo ufw allow from 192.168.80.19 to any port 8080 proto tcp comment 'SignAI ws (temporal)'
sudo ufw delete <número de la regla>
```

Reservar la IP `192.168.80.49` en el router (si el router lo permite) para que el
certificado siga coincidiendo. Si no se puede, la reemisión del certificado es el
recurso: `mkcert -cert-file deploy/certs/lab.pem -key-file deploy/certs/lab-key.pem
127.0.0.1 localhost <IP nueva>`.

**Terminado cuando:** el navegador del teléfono abre `https://192.168.80.49/health` y
muestra `{"status":"ok",...}`, sin cable conectado.

### Fase 2 — El APK llega por Wi-Fi (1 h) 🔧

1. `deploy/Caddyfile`: una ruta estática y el `reverse_proxy` actual dentro de un
   `handle` comodín. Los dos van como bloques `handle` para que Caddy los ordene por
   especificidad de la ruta; un `reverse_proxy` suelto al mismo nivel se comería el
   `/apk/*` y el 404 sería difícil de leer.

   ```
   handle_path /apk/* {
       root * /srv/apk
       file_server
   }

   handle {
       reverse_proxy 127.0.0.1:8080
   }
   ```

   La URL del índice lleva barra final (`/apk/`): `handle_path` matchea `/apk/*`, no
   `/apk`.

2. `docker-compose.host.yml`: `- ./deploy/apk:/srv/apk:ro` en el servicio `caddy`.
3. `mkdir -p deploy/apk` y `deploy/apk/` al `.gitignore`.
4. `app/build.gradle.kts`: `GIT_SHA` con `git rev-parse --short HEAD` (y `-dirty` si hay
   cambios sin commitear), y `versionCode` desde `git rev-list --count HEAD`. Sin eso,
   dos APK distintos se llaman igual y no se sabe cuál está instalado.
5. `tools/wifi/publicar-apk.sh`: compila `assembleDemo` pasando
   `-Psignai.backendWsUrl=wss://<IP actual>/ws/translate` (así el APK recién instalado
   conecta sin tocar nada), copia, escribe el índice y muestra la URL con el QR. La IP
   se puede forzar con `SIGNAI_HOST`.
6. `docker compose -f docker-compose.yml -f docker-compose.host.yml up -d
   --force-recreate caddy` y `curl -sI --cacert deploy/certs/lab-ca.crt
   https://192.168.80.49/apk/`.

En el teléfono: abrir `https://192.168.80.49/apk/`, bajar el APK y aceptar "instalar
apps desconocidas" para el navegador. El APK `demo` reemplaza al `debug` (mismo
`applicationId` y misma clave) sin borrar los datos.

**Terminado cuando:** el teléfono tiene instalada la versión publicada y la pantalla
Acerca de muestra el SHA de ese build, sin haber usado el cable.

### Fase 3 — La dirección, sin recompilar (2 h) 🔧

1. `SettingsRepository` guarda `server_url` (`null` = la del build).
2. `SignAiBackendConfig` lee primero la preferencia, valida y normaliza: acepta
   `wss://host`, `wss://host/puerto` o la URL completa, y agrega `/ws/translate` si
   falta. El build type decide: `demo` y `release` solo `wss://`; `debug` también
   `ws://`.
3. En AVANZADO, un campo "Servidor" con "Probar" y "Guardar". "Probar" hace
   `GET httpOrigin/health` con 3 s de tope y muestra `status`, `cache_loaded` y el
   `silence_timeout_ms` del STT.
4. Al guardar, un aviso: "Reiniciar la app para aplicar", con el botón que reinicia.
   `MainActivity` arma el cliente, el repositorio de assets y la salud una sola vez al
   arrancar; reiniciar es más honesto que fingir que se puede cambiar en caliente.

**Terminado cuando:** con el APK ya instalado, se cambia la IP desde la app, se reinicia
y conecta, sin compilar ni reinstalar.

### Fase 4 — Las métricas del teléfono por la red (3 h) 🔧

**En la app:**

- `DeviceMetricsReporter`: OkHttp (ya está), `POST {httpOrigin}/device/metrics`, cada
  5 s mientras la app está en primer plano, y una vez al terminar cada turno.
- Identidad: `Settings.Secure.ANDROID_ID` como `device_id`, más modelo, versión de
  Android y SDK.
- Build: `versionName`, `versionCode`, build type y `GIT_SHA`.
- Estado: `ws` (`connected`/`disconnected`/`connecting`), `mic`, `playback`, `last_error`
  y `session_id` (cambia cuando `metrics.reset()`).
- Números: los contadores y los cuatro resúmenes de `SignAiMetrics` (p50, p95, max, n).
- Se apaga solo en `release` (`BuildConfig.DEBUG` es `false` ahí).

**En el backend:**

- `POST /device/metrics`: valida, guarda el último reporte por `device_id` y responde
  `{"ok": true}`. Sin autenticación: es una red de laboratorio y se declara.
- `/metrics.json`: un bloque `devices` con el reporte y `age_s`.
- `/metrics`: `device_*_p50`, `_p95`, `_max`, `_n` y `device_*_total`, con la etiqueta
  `device`, más `device_last_seen_seconds` y `device_info{modelo,android,build,sha,url}`.
- El backend **no recalcula** percentiles: el teléfono es el único que tiene las
  muestras. Se publica lo que el teléfono ya calculó, y el método se documenta.

**Nombres**, para que se puedan comparar con los del backend y con los logs de la app:

| En la app (log) | En el reporte | En `/metrics` |
|---|---|---|
| `envío→primera seña` | `first_sign_ms` | `device_first_sign_ms_*` |
| `frase` | `turn_ms` | `device_turn_ms_*` |
| `representado` | `playback_ms` | `device_playback_ms_*` |
| `oración→avatar` | `sign_start_ms` | `device_sign_start_ms_*` |
| `frases`, `oraciones`, `glosas` | `phrases`, `sentences`, `glosses` | `device_*_total` |

**Terminado cuando:** `tools/wifi/metricas.sh` muestra las latencias del teléfono sin
`adb` y con una antigüedad menor a 10 s.

### Fase 5 — Verificar sin `adb` (1 h) 🔧

1. `verificar-tiempo-real.sh`: `check_device` → `check_device_network`. Comprueba
   `/health` por la IP de la red, que haya un latido reciente, la versión y el SHA que
   reporta la app, la URL en uso, y que `rt_phrases_total` se haya movido después de
   hablar. Ya no llama a `adb`.
2. `tools/wifi/estado.sh` y `tools/wifi/abrir.sh`.
3. El resumen del script dice "sin cable" y no "dispositivo conectado".

**Terminado cuando:** con el cable desconectado y `adb kill-server` corrido,
`tools/verificar-tiempo-real.sh todo` pasa entero salvo los pasos de voz, que son
manuales por definición.

### Fase 6 — Opcional: más señal, menos cable (1–2 h) 🔧

- `last_phrase` en el reporte: texto, glosas, ms y de dónde salió (caché o LLM), para
  no tener que mirar la conversación en el teléfono.
- `ws_reconnects` y `last_error` con hora.
- Un panel "Métricas" en AVANZADO con los mismos números, para leerlos en el teléfono
  durante una demo.

**Terminado cuando:** un error de conexión se puede diagnosticar con `estado.sh` y sin
tocar el teléfono.

### Fase 7 — Medición y documentos (2–3 h) 🗂️

1. Caché semántica vacía (`DELETE FROM semantic_cache;` y reiniciar el backend) y
   `tools/verificar-tiempo-real.sh latencia` para el lado del backend: los 28 fixtures.
2. Diez frases habladas por el teléfono, con la app en primer plano, pantalla encendida y
   la misma red. n ≥ 10 para el teléfono y se anota que no es el mismo n que el backend.
3. `docs/performance.md`: la línea base por Wi-Fi, con router, banda, RTT medido, modelo,
   SHA del build y la advertencia de que no es comparable con USB.
4. `docs/android-integration.md`: el endpoint y los nombres.
5. `AGENTS.md` de los dos repos y `docs/SISTEMA.md` de la app.
6. Texto para el owner en Overleaf: el camino por Wi-Fi y el canal de telemetría.
7. `docs/sessions/2026-10-27-wifi.md`.

**Terminado cuando:** los documentos dicen Wi-Fi y los números traen su condición.

### Fase 8 — Cierre (30 min) 🔧

Commits propuestos (los hace el owner):

- backend: `feat(deploy): serve the APK from the TLS proxy`
- backend: `feat(metrics): device metrics endpoint over HTTP`
- app: `feat(settings): backend URL editable at runtime`
- app: `feat(metrics): report device metrics to the backend`
- app: `chore(tools): wifi scripts and verification without adb`

---

## 8. Riesgos y cómo se tratan

| Riesgo | Impacto | Tratamiento |
|---|---|---|
| `ufw` sigue bloqueando el 443 | nada conecta, y el error parece de la app | regla por subred; probar primero en el navegador del teléfono |
| El teléfono cambia de IP por DHCP | el certificado deja de coincidir y el TLS falla | reservar la IP; si no, reemitir; el campo en la app resuelve el `ws`, no el certificado |
| El navegador o MIUI no dejan instalar el APK | no hay forma de actualizar sin cable | habilitar "instalar apps desconocidas"; plan B: `adb pair` por Wi-Fi una vez |
| MIUI congela la app en segundo plano | el latido se corta y parece una caída | mantener la app abierta durante la medición; el script dice "sin latido hace N s" |
| El Wi-Fi agrega jitter (hasta 227 ms medidos) | la latencia del teléfono sube y no es comparable con USB | medir con pantalla encendida, n ≥ 10, y publicar con la condición |
| `/device/metrics` sin autenticación | cualquiera en la LAN puede escribir métricas | red de laboratorio; se documenta y no se expone fuera |
| El reporte cada 5 s gasta batería | una demo larga se queda sin teléfono | solo en `debug`/`demo` y con la app en primer plano |
| Caddy sin el volumen nuevo | `/apk/` da 404 | `up -d --force-recreate caddy` y `curl -I` antes del teléfono |
| El APK de 40 MB tarda en bajar | parece que el navegador se colgó | mostrar el índice con tamaño y SHA; es una sola vez por build |
| Se mide con un APK y se demuestra con otro | conclusiones que no aplican | descartado por la decisión 1: un solo APK `demo` |

---

## 9. Deuda que queda declarada

1. **`/device/metrics` no tiene autenticación.** En una red de laboratorio alcanza; si
   el backend se expone, hace falta un token.
2. **El latido depende de que la app esté abierta.** No hay servicio en primer plano; si
   MIUI la congela, el reporte se detiene y el script lo dice.
3. **El certificado es de una IP.** Sin IP reservada, el Wi-Fi se rompe cuando el DHCP
   cambia, y hay que reemitir.
4. **Los logs completos no viajan.** Solo el estado y el último error. `adb logcat` sigue
   siendo la herramienta de rescate, no un requisito.
5. **El APK sigue siendo de laboratorio:** clave de debug, CA instalada a mano. El
   `release` sigue apuntando a `wss://backend.invalid`.
6. **La latencia del teléfono por Wi-Fi no es comparable con la de USB.** Se publica con
   la condición escrita al lado del número.

---

## 10. Lo que este plan no hace

- No cambia el protocolo del WebSocket ni agrega frames.
- No agrega un segundo socket ni un servidor en el teléfono.
- No toca el STT, Neon ni el catálogo.
- No despliega a internet: sigue siendo la red local.
- No elimina `adb` del mundo, solo del camino normal. Queda como rescate.
- No cambia la v0.16 de los requerimientos.

---

## 11. Estimación

| Fase | Trabajo |
|---|---|
| 0–1 | 30 min |
| 2 | 1 h |
| 3 | 2 h |
| 4 | 3 h |
| 5 | 1 h |
| 6 (opcional) | 1–2 h |
| 7 | 2–3 h |
| 8 | 30 min |
| **Total** | **~10–11 h**, en dos o tres sesiones |

Las fases 1 y 2 se pueden hacer de corrido y dejan el teléfono actualizándose solo. La 3
y la 4 son las de código. La 7 depende del owner para los documentos.

---

## 12. Checklist de cierre

- [x] `ufw` permite el 443 desde la subred y el navegador del teléfono ve `/health`.
- [ ] La IP está reservada o el certificado se reemite cuando cambia.
- [x] `https://<IP>/apk/` sirve el APK con su SHA.
- [ ] El teléfono instala y actualiza sin cable.
- [ ] La dirección se cambia en AVANZADO y se aplica al reiniciar.
- [ ] `tools/wifi/estado.sh` dice versión, SHA, URL y antigüedad del latido.
- [ ] `tools/wifi/metricas.sh` muestra las cuatro latencias del teléfono.
- [ ] `verificar-tiempo-real.sh todo` pasa con `adb kill-server` y el cable desconectado.
- [ ] `docs/performance.md` tiene la línea base por Wi-Fi con sus condiciones.
- [ ] `docs/android-integration.md` describe el endpoint.
- [ ] Los diagramas y el texto de Overleaf están propuestos.
- [ ] Log de sesión en los dos repos.
- [ ] Commits: los propone la sesión, los hace el owner.
