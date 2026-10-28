# Pruebas de rendimiento — tablas

## Backend

### Línea base, frase en caché — `docs/performance.md` §1 · 2026-10-01

| Paso | ms | % del total |
|---|---:|---:|
| fingerprint | 0.2 | 0 % |
| cache.embed | 61.9 | 2 % |
| cache.connect | 1347.1 | 34 % |
| cache.query | 2355.2 | 60 % |
| validation | 0.0 | 0 % |
| **total** | **3929.9** | |

### Línea base, frase nueva — `docs/performance.md` §1 · 2026-10-01

| Paso | ms | % del total |
|---|---:|---:|
| fingerprint | 0.1 | 0 % |
| cache.embed | 14.8 | 0 % |
| cache.connect | 1572.7 | 16 % |
| cache.query | 2046.4 | 20 % |
| llm | 2631.9 | 26 % |
| store.embed | 13.8 | 0 % |
| store.connect | 1448.3 | 15 % |
| store.insert | 1639.9 | 16 % |
| validation | 0.0 | 0 % |
| **total** | **9985.5** | |

### Pool de conexiones, medición aislada — `docs/performance.md` §2 · 2026-10-01

| Llamada | cache.embed | cache.acquire | cache.query |
|---|---:|---:|---:|
| 1 | 28.7 | 0.1 | 529.0 |
| 2 | 11.3 | 0.0 | 391.7 |
| 3 | 12.9 | 0.0 | 296.7 |
| 4 | 12.3 | 0.0 | 247.4 |

### Pool de conexiones, frase en caché — `docs/performance.md` §2 · 2026-10-01

| Paso | Antes (ms) | Con pool (ms) |
|---|---:|---:|
| fingerprint | 0.2 | 0.1 |
| cache.embed | 61.9 | 24.0 |
| cache.connect → cache.acquire | 1347.1 | 0.0 |
| cache.query | 2355.2 | 143.7 |
| cache.release | — | 102.1 |
| validation | 0.0 | 0.0 |
| **total** | **3929.9** | **270.3** |

### Pool de conexiones, frase nueva — `docs/performance.md` §2 · 2026-10-01

| Paso | Antes (ms) | Con pool (ms) |
|---|---:|---:|
| fingerprint | 0.1 | 0.1 |
| cache.embed | 14.8 | 17.0 |
| cache.connect → cache.acquire | 1572.7 | 0.0 |
| cache.query | 2046.4 | 103.3 |
| cache.release | — | 99.9 |
| llm | 2631.9 | 3241.6 |
| store.embed | 13.8 | 14.3 |
| store.connect → store.acquire | 1448.3 | 0.0 |
| store.insert | 1639.9 | 103.2 |
| store.release | — | 101.0 |
| validation | 0.0 | 0.0 |
| **total** | **9985.5** | **3680.8** |

### Pool de conexiones, resumen — `docs/performance.md` §2 · 2026-10-01

| Caso | Antes | Con pool | Mejora |
|---|---:|---:|---:|
| Acierto de caché | 3.93 s | 0.27 s | ≈ 14.5× (−93 %) |
| Fallo de caché (LLM) | 9.99 s | 3.68 s | ≈ 2.7× (−63 %) |
| Base de datos en el fallo de caché | 6.71 s | 0.41 s | ≈ 16× (−94 %) |

### Región de Neon — `docs/performance.md` §3 · 2026-10-01

| Región | Mínimo | Mediana |
|---|---:|---:|
| us-east-1 (Virginia) | 92 ms | 234 ms |
| **us-east-2 (Ohio), actual** | 109 ms | 213 ms |
| sa-east-1 (São Paulo) | 141 ms | 240 ms |
| us-west-2 (Oregon) | 169 ms | 226 ms |
| eu-central-1 (Frankfurt) | 177 ms | 301 ms |

### *Scale-to-zero* — `docs/performance.md` §3 · 2026-10-01

| Paso | Normal (ms) | Tras 5 min (ms) |
|---|---:|---:|
| cache.embed | 24.0 | 15.4 |
| cache.acquire | 0.0 | **3837.6** |
| cache.query | 143.7 | 297.5 |
| cache.release | 102.1 | 296.9 |
| **total** | **270.3** | **4448.0** |

### Límites del plan gratuito de Neon — `docs/performance.md` §3 · 2026-10-01

| Recurso | Límite |
|---|---|
| Cómputo | 100 CU-horas por proyecto al mes |
| Almacenamiento | 1 GB por proyecto |
| *Scale-to-zero* | A los 5 min, no desactivable |
| Al agotar el cómputo | Se suspende hasta el siguiente ciclo (no hay cobro) |

### Alternativas de *keep-alive* evaluadas — `docs/performance.md` §3 · 2026-10-01

| Alternativa | Por qué no / por qué sí |
|---|---|
| Mantener Neon despierto siempre que el backend esté encendido | Olvidar el backend encendido consume cómputo sin uso; dos semanas bastan para suspender la base de datos hasta el mes siguiente. |
| Mantenerlo despierto mientras haya sesiones WebSocket abiertas | Mismo riesgo si se olvida un cliente conectado. Requiere contar sesiones. |
| Desactivar *scale-to-zero* en Neon | Solo en planes pagos. |
| No hacer nada | ~4 s extra en la primera frase de cada atención. |
| **Mantenerlo despierto solo con actividad reciente** | **Elegida.** Gasto acotado en todos los casos, sin depender de apagar nada. |

### Guardar en caché en segundo plano — `docs/performance.md` §6 · 2026-10-01

| Paso | Entrada 2 (ms) | Store en segundo plano (ms) |
|---|---:|---:|
| fingerprint | 0.1 | 0.1 |
| cache.embed | 17.0 | 15.5 |
| cache.acquire | 0.0 | 0.0 |
| cache.query | 103.3 | 189.1 |
| cache.release | 99.9 | 111.4 |
| llm | 3241.6 | 1865.8 |
| store.embed | 14.3 | — |
| store.acquire | 0.0 | — |
| store.insert | 103.2 | — |
| store.release | 101.0 | — |
| validation | 0.0 | 0.0 |
| **total** | **3680.8** | **2182.2** |

### De punta a punta con el STT optimizado, por frase — `docs/performance.md` §7 · 2026-10-01

| Frase | Fuente | Backend (final → resultado) | LLM |
|---|---|---:|---:|
| "Hola, ¿cómo estás?" | cache | 0.36 s | — |
| "un tiempo bastante rápido." | llm | 2.66 s | 2.33 s |
| "Me llamo Julián." | llm | 1.39 s | 1.08 s |
| "¿Y ahora cómo estás?" | llm | 1.68 s | 1.28 s |
| "Hola, ¿cómo estás?" | cache | 0.29 s | — |

### Latencia total para el usuario — `docs/performance.md` §7 · 2026-10-01

| | STT | Backend | Total |
|---|---:|---:|---:|
| Frase en caché | 1.8–2.1 s | 0.3–0.4 s | ~2.1–2.5 s |
| Frase nueva (LLM) | 1.8–2.1 s | 1.4–2.7 s | ~3.2–4.8 s |

### Caché semántico con oraciones cortas — `docs/performance.md` §8 · 2026-10-02

| | Texto original, umbral 0.15 | Texto original, umbral 0.05 | Normalizado, umbral 0.05 |
|---|---:|---:|---:|
| Aciertos buenos | 9 de 10 | 5 de 10 | **7 de 10** |
| Aciertos indebidos | 2 de 12 | 0 de 12 | **0 de 12** |

### Crecimiento del vocabulario en el prompt — `docs/performance.md` §9 · medido el 2026-10-15

| Glosas | Caracteres de vocabulario | Tokens aproximados |
|---|---|---|
| 50 (hoy) | 413 | ~103 |
| 500 | ~4 100 | ~1 000 |
| 5 000 | ~41 000 | ~10 000 |

### Bucle de lectura y sockets del STT — `docs/CAMBIOSBACKEND.md` · 2026-10-16

| | antes | después |
|---|---|---|
| retraso del audio durante la traducción | 991 ms | **0 ms** |
| `rt_read_loop_busy_ms` (p50 / max) | 0,155 / **931** ms | 0,151 / **0,595** ms |
| conexiones al STT que quedan colgadas (10 sesiones) | +18 | **0** |

## STT

### VAD — `sign-ai-stt/docs/performance.md` §1 · 2026-10-01

| | `VAD_AGGRESSIVENESS=0` | `VAD_AGGRESSIVENESS=2` |
|---|---:|---:|
| Frases con pausa cerradas por silencio | 1 de 5 | 8 de 8 |
| Finales vacíos (solo ruido) | 5 | 1 |
| Cortes forzados a los 8 s (`buffer_max`) | 4 | 2 |
| Fin de la habla → final (cierres por silencio) | 1877 ms | 1880–2047 ms |

### Parciales activados y desactivados — `sign-ai-stt/docs/performance.md` §2 · 2026-10-01

| | Con parciales | Sin parciales |
|---|---:|---:|
| Atraso máximo del procesamiento | 5817 ms | ~0 ms |
| Picos de transcripción de 6–8 s | sí | no |
| Fin de la habla → final, peor caso | 7742 ms | 2635 ms |
| Fin de la habla → final, típico | 1880–2047 ms | 2148–2635 ms |

### Parciales en segundo plano — `sign-ai-stt/docs/performance.md` §3 · 2026-10-01

| | Parciales bloqueantes | Sin parciales | Parciales en segundo plano |
|---|---:|---:|---:|
| Texto en vivo (RF-STT-02) | sí | no | **sí** |
| Atraso máximo del procesamiento | 5817 ms | ~0 ms | **~0 ms** |
| Picos de 6–8 s | sí | no | **no** |
| Fin de la habla → final (con voz) | 1880–2047 ms | 2148–2635 ms | **1862 ms** |

### Volúmenes medidos — `sign-ai-stt/docs/performance.md` §6 · 2026-10-01

| Audio | Nivel |
|---|---|
| Ruido de fondo | 0.001–0.004 |
| Voz baja al inicio de la sesión | 0.0086–0.0090 (un tramo en 0.0077) |
| Voz "pasito" | 0.017–0.022 |
| Voz normal o fuerte | 0.025–0.06 |

### Cortes en pausas y filtro de energía — `sign-ai-stt/docs/performance.md` §7 · 2026-10-01

| | Solo corte en pausas | Con filtro de energía por frame |
|---|---:|---:|
| Frases perdidas | varias | 0 de 9 |
| Frases mantenidas abiertas por ruido | 3 | 0 |
| Cortes en pausa / forzados | 5 / 3 | 2 / 0 |
| Fin de la habla → final | — | 1813–2099 ms |

### Perfil de tiempo real frente al flujo por oraciones — `sign-ai-stt/docs/performance.md` §8 · 2026-10-15

| | En el perfil | Ahora |
|---|---|---|
| `SILENCE_TIMEOUT_MS` | 600 ms | **1500 ms**, el del diagrama 6.3 |
| `PARTIAL_INTERVAL_MS` | 250 ms | 400 ms |
| `SPEECH_ONSET_WINDOW_MS` / `_RATIO` | 150 ms / 0.7 | 300 ms / 0.9 |
| `FINAL_TRAILING_SILENCE_KEEP_MS` | 120 ms | 300 ms |
| `MIN_AUDIO_MS_FOR_PARTIAL` | 160 ms | 200 ms |
| Modelos | dos (`medium` + `small`) | uno |
| `WORD_TIMESTAMPS` | `true` | `false` |

## App y avatar

### Primer seña, 28 fixtures — `sign-ai-android/tools/TIEMPO-REAL.md` · 2026-10-15

| | p50 | p95 |
|---|---|---|
| **`rt_first_sign_ms`** (transcripción final → primera oración enviada) | **273 ms** | **422 ms** |
| Ídem con la caché caliente | 1 ms | 4 ms |
| Del primer sample de audio a la primera seña (**lo que percibe el usuario**) | **4010 ms** | — |
| …de los cuales el STT | 3709 ms | — |

### Antes y después de la traducción en tiempo real, 28 fixtures — `openspec/sessions/2026-10-14-traduccion-tiempo-real.md`

| | antes | después |
|---|---|---|
| Primera seña (p50 / p95) | — | **913 ms / 1336 ms** |
| Dejar de hablar → final | 1813 – 2099 ms | **839 ms / 958 ms** (p50 / p95) |
| Inferencia de un parcial | 350 – 630 ms | **92 ms / 172 ms** |
| Inferencia de un final | 246 – 332 ms | 249 – 338 ms |
| Espera por la GPU | picos de 4 – 8 s | **p95 0.8 ms** |

### Rendimiento del WebView en el Redmi Note 9S — `openspec/sessions/2026-10-13-glb-animation-mixer.md`

| | mediana | p99 | jank |
|---|---|---|---|
| antes (dpr sin tope) | 51.1 ms | 75.2 ms | **99.2%** |
| dpr topado a 1.75 | 11.3 ms | 25.7 ms | 10.8% |
| + sin `DoubleSide` | 11.3 ms | 17.9 ms | **6.7%** |

### Fundición entre señas, A/B en el Redmi (`hola gracias`, tres corridas) — `openspec/sessions/2026-10-14-reposo-y-crossfade.md`

| | mediana | |
|---|---|---|
| antes (`TRANSITION_FRAMES = 6`) | 4708 ms | 6 ticks de pose congelada + cola entera |
| crossfade 100 ms | **4522 ms** | −186 ms (−4.0%), contra −200 ms predichos |
| corte seco (reducir animaciones) | 4634 ms | sin congelado, sin solapar |

### Salto entre el final de una seña y el inicio de la siguiente — `openspec/changes/archive/2026-10-17-reposo-y-crossfade/investigacion.md` §4.1

| | |
|---|---|
| salto directo del final de A al inicio de B | **mediana 5.9 cm**, p90 20.3 cm |
| pares que ya son continuos (< 10 cm) | **79%** |
| vuelta por el reposo de hoy | **mediana 46.6 cm** |

### Movimiento real al final y al inicio del clip — `investigacion.md` §4.2

| ventana | movimiento al final del clip | al inicio del siguiente |
|---|---|---|
| 42 ms | 0.8 cm | 0.9 cm |
| 83 ms | 3.3 cm | 3.0 cm |
| 125 ms | 7.1 cm | 5.7 cm |
| 167 ms | 12.3 cm | 8.6 cm |

### Duración de la fundición contra salto máximo — `investigacion.md` §4.4

| configuración | máximo (cm/frame) |
|---|---:|
| hoy | 94.5 |
| reposo nuevo, corte seco | 71.8 |
| crossfade 50 ms | 24.0 |
| crossfade 75 ms | 16.0 |
| **crossfade 100 ms** | **12.1** |
| crossfade 125 ms | 9.7 |
| crossfade 150 ms | 8.8 |
| crossfade 200 ms | 8.8 |

### Duración de la animación por frase — `investigacion.md` §4.5

| frase | hoy | con crossfade 100 ms |
|---|---|---|
| HOLA + BUENOS DIAS + COMO ESTAS | 6.72 s | **6.12 s** |
| BIEN + GRACIAS + TRISTE | 8.01 s | **7.41 s** |
| HOLA + GRACIAS + BIEN + TRISTE + CONTENTO | 12.50 s | **11.50 s** |

### Latencia del LLM por modelo — `openspec/sessions/2026-10-14-conectar-stt-y-backend-real.md` · 2026-10-14

| Modelo | En vocabulario | LLM |
|---|---|---|
| `gpt-4o-mini` | 9/10 | 1248 ms |
| `qwen3:4b-instruct` (local) | 9/10 | **139 ms** |
