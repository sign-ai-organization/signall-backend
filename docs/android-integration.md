# Integración del cliente Android con el backend

Guía para conectar la app Android al backend de SignAI. La app habla
**solo con el backend**, por un único WebSocket: le envía el audio del
micrófono y recibe la transcripción y las glosas para el avatar. La app
nunca se conecta directo al servicio STT.

---

## 1. Levantar el backend

Se necesitan el backend y el servicio STT (`sign-ai-stt`, requiere GPU
NVIDIA). Los dos repos deben estar en la misma carpeta, uno al lado del
otro:

```
sign-ai-organization/
├── sign-ai-backend/
└── sign-ai-stt/
```

### Opción recomendada: Docker, un solo comando

En `sign-ai-backend/.env` debe estar
`STT_WS_URL=ws://stt:8000/ws/transcribe` (`stt` es el nombre del
servicio dentro de Docker; `localhost` no funciona aquí). Luego:

```bash
sign-ai-backend> docker compose up --build
```

Este comando levanta los dos servicios: el backend (puerto **8080**) y el
STT (puerto 8000), que se construye desde `../sign-ai-stt`. Esperar a que
ambos muestren `Application startup complete`. La primera vez tarda
varios minutos (instala dependencias y descarga el modelo de Whisper).

- No correr al mismo tiempo el STT desde su propio repo: ocupan el mismo
  puerto 8000.
- Tras cambiar código de cualquiera de los dos repos, volver a usar
  `--build`.

### Alternativa: sin Docker para el backend

1. STT desde su repo:

   ```bash
   sign-ai-stt> docker compose up --build
   ```

2. Backend con el entorno virtual activado (ver `README.md`), con
   `STT_WS_URL=ws://localhost:8000/ws/transcribe` en `.env`:

   ```bash
   sign-ai-backend> uvicorn app.main:app --host 0.0.0.0 --port 8080
   ```

   `--host 0.0.0.0` es necesario para que el teléfono lo alcance.

### Conectar el teléfono
- El teléfono y el computador deben estar en la misma red.
- Usar la IP del computador, no `localhost`:
  `ws://<IP-del-computador>:8080/ws/translate`.
- Si no conecta, revisar que el firewall de Windows permita el puerto
  8080.

Comprobar desde el navegador del teléfono:
`http://<IP-del-computador>:8080/health` → `{"status": "ok"}`.

---

## 2. Conexión

```
ws://<host>:8080/ws/translate
```

- Una conexión por sesión de conversación. Se abre al activar el
  micrófono y se mantiene mientras se habla.
- Si al conectar el STT no está disponible, el backend envía un mensaje
  `error` (sección 4) y cierra la sesión.

---

## 3. Enviar audio (app → backend)

Mensajes **binarios** con audio crudo, de forma continua mientras el
micrófono esté activo:

| Parámetro | Valor |
|---|---|
| Formato | PCM 16 bits, little-endian, sin cabecera WAV |
| Canales | 1 (mono) |
| Frecuencia | 16 000 Hz |
| Tamaño de cada envío | Libre; se recomienda ~30 ms (480 muestras = 960 bytes) |

En Android, `AudioRecord` con `AudioFormat.ENCODING_PCM_16BIT`,
`CHANNEL_IN_MONO` y `16000` Hz entrega exactamente este formato.

No hay que avisar cuándo termina una frase: el sistema lo detecta por
el silencio (~1.5 s) y responde solo.

---

## 4. Mensajes que envía el backend (backend → app)

Todos son JSON de texto. Se distinguen por el campo `type`.

### `transcript`: texto de lo que se está diciendo

```json
{"type": "transcript", "text": "Hola, ¿cómo estás?", "final": false}
```

- `final: false`: transcripción parcial; llega varias veces mientras la
  persona habla, cada una reemplaza a la anterior. Es el texto que se
  muestra en la barra de transcripción en vivo (RF-STT-02).
- `final: true`: la frase terminó; es el texto definitivo. Puede venir
  vacío (`""`): ignorarlo.

En modo tiempo real (`REALTIME_ENABLED=true`, el default) los parciales ya
disparan `segment`: **no hay que esperar al `final` para empezar a señar**.

### `segment`: un fragmento traducido, listo para el avatar

Es el mismo frame para los dos modos, y lo que los distingue es `stream`.

**Modo fragmentado** (`stream: true`, el default). El backend traduce
apenas el STT confirma que esas palabras ya se dijeron y lo manda en el
acto. `total` es `0`: en una frase todavía abierta nadie sabe cuántas
van a ser.

```json
{
  "type": "segment",
  "index": 0,
  "total": 0,
  "stream": true,
  "provisional": true,
  "source_text": "hola",
  "segment": {
    "type": "AFFIRMATIVE",
    "glosses": [{"text": "HOLA", "available": true, "glb_path": "signs/0030_0000_0000.glb"}]
  }
}
```

**Modo frase completa** (`stream` ausente o `false`). El backend divide
el texto en oraciones y manda una por mensaje, en orden, sin esperar a
las demás.

```json
{
  "type": "segment",
  "index": 0,
  "total": 2,
  "segment": {
    "type": "CONTENT_QUESTION",
    "glosses": [
      {"text": "HOLA", "available": true, "glb_path": "signs/0030_0000_0000.glb"},
      {"text": "TU", "available": false, "glb_path": ""},
      {"text": "COMO", "available": true, "glb_path": "signs/0044_0000_0000.glb"}
    ]
  }
}
```

| Campo | Significado |
|---|---|
| `index` | Posición, desde 0. Siempre en orden. |
| `total` | Cuántos fragmentos tiene la frase. **`0` significa "todavía no se sabe"**, que es lo normal mientras la frase está abierta. Solo en modo fragmentado. |
| `stream` | `true` si el fragmento se envió sin esperar el final. Un backend más viejo que la app no lo manda, y la app cae en el camino de frase completa, que es el default seguro. |
| `provisional` | `true` si el fragmento salió de una hipótesis que el STT todavía puede corregir. Solo informativo: la app lo muestra como texto provisional, no cambia lo que firma. |
| `source_text` | El texto del STT del que salió este fragmento. Es lo que la app registra en el historial. |
| `segment.type` | Tipo de frase: `AFFIRMATIVE`, `YES_NO_QUESTION`, `CONTENT_QUESTION`, `NEGATIVE` o `IMPERATIVE`. Sirve para los marcadores no manuales del avatar. |
| `glosses` | Señas en el orden en que se deben reproducir. |
| `glosses[].available` | `true` si la seña está en el catálogo del backend. |
| `glosses[].glb_path` | Valor de `glb_animation_path` del catálogo para esa seña. |

**Qué tiene que hacer la app con `stream: true`.** No esperar: anexar el
fragmento a la cola de reproducción y firmarlo ya. `total: 0` no es un
error ni un total pendiente de resolver: es la señal de que la cola
puede seguir creciendo.

`glb_path` es **siempre un path same-origin dentro del APK**
(`signs/<id>.glb`), nunca una URL. Las animaciones viven en la app, no en
el backend; el backend solo dice qué seña reproducir. Si una glosa no
está disponible, la app decide qué hacer (omitirla, deletrear, mostrar el
texto).

### `done`: terminó la frase

```json
{"type": "done"}
```

Llega después del último `segment` de la frase. En modo fragmentado
significa "el backend dejó de mandar", **no** "terminó la animación": la
app sigue firmando lo que quede en la cola y recién ahí cierra el turno.

### `error`

```json
{"type": "error", "message": "No se pudo traducir el texto."}
```

El mensaje está en español y se puede mostrar al usuario. Si llega en
medio de una frase, descartar los `segment` que hayan llegado de esa
frase.

### Mensajes de depuración: ignorar

`sentence_trace` y `trace` solo se envían si el backend tiene
`DEBUG_TRACE_ENABLED=true` (tiempos internos para pruebas). La app debe
ignorar cualquier `type` que no conozca.

---

## 5. Implementación en Android

### Configuración obligatoria

**Permisos** en `AndroidManifest.xml` (`RECORD_AUDIO` además se pide en
tiempo de ejecución):

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
```

**Permitir `ws://` sin cifrar.** Desde Android 9 el tráfico sin cifrar
está bloqueado por defecto y la conexión falla. Para desarrollo contra el
backend local, crear `res/xml/network_security_config.xml`:

```xml
<network-security-config>
    <base-config cleartextTrafficPermitted="true" />
</network-security-config>
```

y referenciarlo en `<application android:networkSecurityConfig="@xml/network_security_config" ...>`.
En producción se usaría `wss://` y esto no haría falta.

### Esqueleto (Kotlin, OkHttp)

```kotlin
val client = OkHttpClient()
val request = Request.Builder().url("ws://<IP>:8080/ws/translate").build()

val socket = client.newWebSocket(request, object : WebSocketListener() {
    override fun onMessage(webSocket: WebSocket, text: String) {
        val message = JSONObject(text)
        when (message.getString("type")) {
            "transcript" -> showTranscript(message.getString("text"), message.getBoolean("final"))
            "segment" -> enqueueForAvatar(message.getInt("index"), message.getJSONObject("segment"))
            "done" -> onSentenceFinished()
            "error" -> showError(message.getString("message"))
            // sentence_trace / trace / cualquier otro: ignorar
        }
    }

    override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
        stopRecording()
        showError("Sin conexión con el servidor")
    }
})

// Captura: 16 kHz, mono, PCM 16 bits; enviar bloques de ~30 ms
val minBuffer = AudioRecord.getMinBufferSize(16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
val recorder = AudioRecord(
    // VOICE_RECOGNITION, no MIC: es la fuente afinada para reconocimiento, así
    // el STT escucha la voz en vez del AGC bombeando.
    MediaRecorder.AudioSource.VOICE_RECOGNITION, 16000,
    AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, maxOf(minBuffer, 960 * 4)
)
recorder.startRecording()
val chunk = ByteArray(960) // 30 ms
while (isRecording) { // en un hilo o corrutina en segundo plano, nunca en el hilo principal
    val read = recorder.read(chunk, 0, chunk.size)
    if (read > 0) socket.send(chunk.toByteString(0, read))
}
recorder.stop()
recorder.release()
```

`AudioRecord` ya entrega PCM 16 bits little-endian, así que los bytes se
envían tal cual. Los callbacks de OkHttp llegan en un hilo de fondo:
pasar al hilo principal antes de tocar la interfaz o el avatar.

### Reproducción en el avatar

Modo fragmentado (el default): **anexar** cada `segment` a la cola y
firmarlo ya. El primero arranca la cola; los siguientes se encadenan
detrás de lo que esté sonando. Es indispensable que elappen en orden:
resolver una glosa puede suspender (bajar un asset remoto), así que si
dos fragmentos compiten y se anexan desordenados el avatar firma la
frase al revés.

Modo frase completa (`stream` ausente o `false`): encolar por `index` y
reproducirlos en ese orden. Ya llegan ordenados, pero la cola permite
empezar el primero mientras llegan los demás.

Dentro de cada segmento, reproducir `glosses` en el orden de la lista.

### Al detener el micrófono

**Ya no hace falta mandar silencio.** Al soltar el micrófono, la app
manda `{"type":"end"}` y el backend lo reenvía al STT como el frame
`end` del protocolo, que fuerza la transcripción final del segmento en
curso. Antes había que mandar ~2 s de bytes en cero, porque el segmento
solo se cerraba oyendo silencio.

El hangover de silencio del STT bajó de 1500 ms a 600 ms
(`SILENCE_TIMEOUT_MS`, perfil de tiempo real). Ese es el piso por debajo
del cual una pausa natural entre palabras parte la frase en dos, que
para señas encadenables es el trade-off correcto.

Cerrar la conexión con `socket.close(1000, null)` cuando termine la
conversación.

---

## 6. Ejemplo de una frase completa (modo fragmentado)

```
app → backend   [audio binario continuo...]
backend → app   {"type":"transcript","text":"Hola","final":false}
backend → app   {"type":"segment","index":0,"total":0,"stream":true,"provisional":true,
                 "source_text":"hola","segment":{"glosses":[{"text":"HOLA",...}]}}
                       ↑ el avatar ya empieza a firmar HOLA mientras la persona sigue hablando
backend → app   {"type":"transcript","text":"Hola, ¿cómo estás?","final":false}
backend → app   {"type":"segment","index":1,"total":0,"stream":true,"provisional":true,
                 "source_text":"como estas","segment":{"glosses":[{"text":"COMO ESTAS",...}]}}
                (silencio ~0.6 s)
backend → app   {"type":"transcript","text":"Hola, ¿cómo estás?","final":true}
backend → app   {"type":"done"}   ← el avatar sigue firmando lo que le queda en la cola
```

Medido sobre los 28 fixtures de audio del repo `sign-ai-stt`, reproducidos
por el socket a velocidad real: **primera seña p50 913 ms / p95 1336 ms**,
contada desde el primer sample de audio. El modo anterior esperaba al
`final`: 2.4–4.8 s después de que la persona dejaba de hablar.

## 6bis. Ejemplo de una frase completa (modo `REALTIME_ENABLED=false`)

```
app → backend   [audio binario continuo...]
backend → app   {"type":"transcript","text":"Hola, ¿cómo estás? Me llamo Ana.","final":true}
backend → app   {"type":"segment","index":0,"total":2,"segment":{...}}
backend → app   {"type":"segment","index":1,"total":2,"segment":{...}}
backend → app   {"type":"done"}
```

Mientras tanto la app sigue enviando audio: la siguiente frase se
procesa igual.

---

## 7. Limitaciones actuales (importante)

- **18 de las 50 glosas no tienen animación.** El catálogo de Neon
  anuncia las 50 con `available: true`, pero el APK solo trae 32 `.glb`
  (`0000`–`0031`). Las 18 restantes (`0032`–`0049`: POR FAVOR, CON GUSTO,
  NUNCA, YO, TU, USTEDES, QUE, CUANDO, DONDE, COMO, POR QUE, QUIEN,
  DIFERENTE, TODOS, MUCHO, BIENVENIDO, PERDÓN, PERMISO) llegan como un
  path propio que nadie va a servir. La app lo detecta y no intenta
  bajarlo por HTTP.
- **Glosas fuera de LSC50 se traducen a algo aproximando.** "estudiante" no
  está en el vocabulario cerrado y el LLM puede devolver algo que no
  significa lo mismo. Lo correcto sería que la frase se quedara sin firmar
  y quedara en el caption.
- **Confirmación del texto (RF-STT-03 / RF-UI-02) no implementada.** Los
  requisitos dicen que el usuario confirma (y puede editar) el texto
  final antes de traducirlo. Hoy el backend traduce cada fragmento
  automáticamente, que es incompatible con confirmar: para cuando llegara
  el `final` el avatar ya firmó media frase. Cuando se implemente, la
  app tendrá que enviar un mensaje de confirmación con el texto; **este
  contrato va a cambiar** y
  se acordará antes con el equipo.
- El protocolo de esta guía todavía no está reflejado en el SDD (ver
  `docs/sdd-changes.md`).

---

## 8. Probar sin la app

Hay tres formas, de menos a más realista.

### Cliente de referencia, con micrófono

`scripts/manual_translation_client.py` hace lo mismo que la app
(micrófono → WebSocket → imprime los mensajes) e imprime la latencia de
cada mensaje. Sirve para comparar comportamientos a ojo:

```bash
pip install -r requirements-dev.txt
python -m scripts.manual_translation_client ws://<IP-del-computador>:8080/ws/translate
```

### Reproducir un WAV, sin micrófono ni voz

`scripts/verify_realtime_latency.py` manda un WAV por el socket a
velocidad real y cronometra desde el primer sample. Es la forma
reproducible: el mismo archivo da siempre el mismo resultado.

```bash
# una frase
python scripts/verify_realtime_latency.py --phrase "hola" --phrase "cómo estás"

# línea de tiempo de un audio
python scripts/verify_realtime_latency.py \
    --replay-audio ../sign-ai-stt/fixtures/audio/conversacion_2.wav

# los 28 fixtures, con tabla y p50/p95 al final
python scripts/verify_realtime_latency.py --all-fixtures
```

Los WAV se generan en el repo del STT:

```bash
cd ../sign-ai-stt
python3 -m venv .venv-tts && .venv-tts/bin/pip install piper-tts numpy
.venv-tts/bin/python scripts/make_audio_fixtures.py --all
```

### Sin nada corriendo

```bash
# qué seña se firma y cuál no: 31 aserciones, sin red ni base de datos
docker compose exec backend python scripts/verify_incremental.py

# el protocolo del WebSocket, en los dos modos
docker compose exec backend python scripts/verify_client_frames.py
```

### Todo junto, con el teléfono incluido

En el repo de la Android:

```bash
tools/verificar-tiempo-real.sh
```

---

## 9. Métricas

Los dos servicios exponen `/metrics` (Prometheus) y `/metrics.json`.

```bash
curl -s 127.0.0.1:8080/metrics | less
curl -s 127.0.0.1:8000/metrics.json | python3 -m json.tool
```

Del backend, las que importan para el modo fragmentado:

| Métrica | Qué es |
|---|---|
| `rt_first_sign_ms` | del primer texto del STT a la primera seña enviada. **La que decide si se siente en tiempo real.** |
| `rt_utterance_ms` | del primer texto a la última seña. |
| `rt_chunk_delay_ms` | cada fragmento por separado, para ver si se entregan espaciados o de golpe al final. |
| `audio_bytes_total` | audio reenviado al STT. El único tramo que no produce salida: si el micrófono se rompe, esto es lo único que se mueve. |
