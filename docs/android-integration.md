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

### `segment`: una oración traducida, lista para el avatar

Tras cada `transcript` final, el backend divide el texto en oraciones y
envía **una por mensaje, en orden, en cuanto cada una está lista**. No
hay que esperar a las demás: el avatar puede empezar a señar la primera
mientras se traducen las siguientes.

```json
{
  "type": "segment",
  "index": 0,
  "total": 2,
  "segment": {
    "type": "CONTENT_QUESTION",
    "glosses": [
      {"text": "HOLA", "available": true, "glb_path": "/static/glb/hola.glb"},
      {"text": "TU", "available": false, "glb_path": ""},
      {"text": "COMO", "available": true, "glb_path": "/static/glb/como.glb"}
    ]
  }
}
```

| Campo | Significado |
|---|---|
| `index` | Posición de la oración (empieza en 0). Siempre llegan en orden. |
| `total` | Cuántas oraciones tiene la frase. Se conoce desde la primera. |
| `segment.type` | Tipo de frase: `AFFIRMATIVE`, `YES_NO_QUESTION`, `CONTENT_QUESTION`, `NEGATIVE` o `IMPERATIVE`. Sirve para los marcadores no manuales del avatar. |
| `glosses` | Señas en el orden en que se deben reproducir. |
| `glosses[].available` | `true` si la seña está en el catálogo del backend. |
| `glosses[].glb_path` | Valor de `glb_animation_path` del catálogo para esa seña. Vacío si `available` es `false`. |

Las animaciones GLB viven en la app, no en el backend. La app usa
`text` (la glosa) o `glb_path` para encontrar la animación en sus
propios recursos; el catálogo del backend y los archivos de la app
tienen que usar los mismos nombres. Si una glosa no está disponible, la
app decide qué hacer (omitirla, deletrear, mostrar el texto).

### `done`: terminó la frase

```json
{"type": "done"}
```

Llega después del último `segment` de la frase.

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
    MediaRecorder.AudioSource.MIC, 16000,
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

- Encolar los `segment` por `index` y reproducirlos en ese orden; ya
  llegan ordenados, pero la cola permite empezar el primero mientras
  llegan los demás.
- Dentro de cada segmento, reproducir `glosses` en el orden de la lista.

### Al detener el micrófono

**Limitación actual:** una frase solo se cierra tras ~1.5 s de
silencio. Si la app deja de enviar audio a mitad de una frase, esa frase
no se transcribe. Mientras se corrige en el backend, al detener el
micrófono enviar ~2 s de silencio (bloques de bytes en cero) antes de
cerrar el WebSocket:

```kotlin
repeat(67) { socket.send(ByteArray(960).toByteString()) } // ~2 s de silencio
```

Cerrar la conexión con `socket.close(1000, null)` cuando termine la
conversación.

---

## 6. Ejemplo de una frase completa

```
app → backend   [audio binario continuo...]
backend → app   {"type":"transcript","text":"Hola","final":false}
backend → app   {"type":"transcript","text":"Hola, ¿cómo estás? Me llamo Ana.","final":false}
                (silencio ~1.5 s)
backend → app   {"type":"transcript","text":"Hola, ¿cómo estás? Me llamo Ana.","final":true}
backend → app   {"type":"segment","index":0,"total":2,"segment":{...}}   ~0.3 s después
backend → app   {"type":"segment","index":1,"total":2,"segment":{...}}   ~1.5–2.5 s si va al LLM
backend → app   {"type":"done"}
```

Mientras tanto la app sigue enviando audio: la siguiente frase se
procesa igual.

---

## 7. Limitaciones actuales (importante)

- **Falta acordar el formato de `glb_path`.** Hoy el catálogo guarda
  rutas como `/static/glb/casa.glb`, pensadas para un servidor del
  backend que ya no se usará. Hay que definir con el equipo qué valor
  guarda el catálogo (por ejemplo, el nombre del archivo dentro de la
  app) para que la app lo encuentre.
- **Detener el micrófono a mitad de una frase la pierde**, salvo que la
  app envíe ~2 s de silencio antes de cerrar (sección 5). Se corregirá
  en el backend para que la app pueda pedir el cierre de la frase.
- **El catálogo tiene 3 de las 50 señas.** Casi todas las glosas llegan
  con `available: false` hasta que se cargue el catálogo completo.
- **Confirmación del texto (RF-STT-03 / RF-UI-02) no implementada.** Los
  requisitos dicen que el usuario confirma (y puede editar) el texto
  final antes de traducirlo. Hoy el backend traduce cada final
  automáticamente. Cuando se implemente, la app tendrá que enviar un
  mensaje de confirmación con el texto; **este contrato va a cambiar** y
  se acordará antes con el equipo.
- El protocolo de esta guía todavía no está reflejado en el SDD (ver
  `docs/sdd-changes.md`).

---

## 8. Probar sin la app

`scripts/manual_translation_client.py` es un cliente de referencia que
hace lo mismo que debe hacer la app (micrófono → WebSocket → imprime los
mensajes). Útil para comparar comportamientos:

```bash
pip install -r requirements-dev.txt
python -m scripts.manual_translation_client ws://<IP-del-computador>:8080/ws/translate
```
