# Contraste Backend ↔ Documentos

**Fecha:** 2026-10-18 · **Backend:** `sign-ai-backend`, rama `flujo-oraciones`, commit
`0363546` (sin mergear) · **Estado del árbol:** 15 archivos modificados y 2 sin
trackear del trabajo del 2026-10-15, que **no son de este documento**.

**Fuentes leídas, enteras, el 2026-10-18:**

| Fuente | Qué se leyó | Sello |
|---|---|---|
| **El código** | `app/` completo, `scripts/verify_*.py`, `tools/`, migraciones, `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `.env` | `flujo-oraciones` @ `0363546` |
| **Los documentos del proyecto** | `../sign-ai-docs`: Requerimientos v0.15 (701 líneas), `modificaciones/requerimientos.md`, `auditoria-flujo-2026-10-15.md`, `plan-pruebas/00-bases/` (3) y `plan-pruebas/01-diseno/*/general.md` (6), y los **12 `.drawio` con sus PNG** | `main` |
| **Overleaf — SDD** | proyecto `6a85c9a632974414503d9b82`, `main.tex`, **540 líneas**, versión **159**, editado el **2026-08-30**, más las **12 PNG de `images/`** | v159 |
| **Overleaf — SRS** | proyecto `6a122a19bb9a5dd9d390ba3d`, `main.tex`, **1370 líneas**, versión **436**, editado el **2026-10-18 05:02** | v436 |
| **La app** | `../sign-ai-android/docs/CONTRASTE-APPvsDOCUMENTOS.md` y `.opencode/skills/contrato-websocket/SKILL.md`, **solo lectura** | `flujo-oraciones` |

> **Su gemelo para la app es `../sign-ai-android/docs/CONTRASTE-APPvsDOCUMENTOS.md`.**
> Los dos se citan por ruta relativa, nunca con la ruta absoluta de una máquina.
>
> **Overleaf es de solo lectura.** Si un `.tex` está mal, lo corrige el owner.

---

## ⚠ Orden de trabajo de la sesión siguiente

Este documento es el registro de las decisiones. **La sesión siguiente es la de ejecutar.**
Y lo primero que se hace es la **documentación y los diagramas**, en los dos sitios donde
viven:

| # | Qué | Dónde |
|---|---|---|
| 1 | **Copiar las 12 imágenes** del juego viejo al juego nuevo. No es redibujar: es subir el archivo que ya existe | De `../sign-ai-docs/diagramas/png/` a `images/` del SDD en Overleaf, y a `docs/diagrams/` de este repo |
| 2 | **Editar el C4-2**: cambiar "Filament" por Three.js. Regenerar su PNG y volver a subirla | `../sign-ai-docs/diagramas/draw.io/sdd-c4-2-contenedores.drawio` |
| 3 | **Editar el 7.4**: agregar el estado *Texto listo* con sus tres transiciones, y quitar el "≤2s" de la salida de *Error*. Regenerar su PNG y volver a subirla | `../sign-ai-docs/diagramas/draw.io/sdd-7.4-diagrama-estados-ui.drawio` |
| 4 | **Solo después**, corregir el texto del SDD §6.1, §6.2, §6.3, §7.1, §7.2 y §7.3 | SDD de Overleaf y `docs/sdd.md` de este repo |

El orden importa: si se empieza por el texto se cambian veinte frases y después aparecen
las imágenes y hay que revisarlo todo otra vez. Al revés, primero las imágenes y después
el texto dice exactamente qué cambiar.

Los tres pasos de arriba dejan resueltos, de un solo movimiento, los puntos **1, 2, 3, 5,
6, 7, 8, 9, 10, 11, 12, 22** y parte del **33** de §3. Los puntos **23** y **26**van a
trabajo futuro, y el **34** depende de la decisión del proxy.

**Nunca se commitea nada sin que el owner lo pida**, y Overleaf no se escribe desde acá.

---

## Resumen

Al contrastar el backend de `flujo-oraciones` contra el SRS, el SDD y los documentos del
repo de documentos, aparecen 43 contrastes. **Lo primero que hay que sacar de dudas es lo
que más preocupaba: casi ninguno toca un diagrama.** Diez de los doce diagramas ya están
correctos y lo único que hay que hacer con ellos es **subir el archivo de imagen correcto**
—los `.drawio` de `../sign-ai-docs/diagramas/` ya son la versión nueva, y lo que está
mal son las copias de Overleaf y las de `docs/diagrams/` de este repo—. De los dos que sí
hay que editar, uno es **cambiar la palabra "Filament" por "Three.js"**. El otro es
agregar el estado *Texto listo* al diagrama 7.4, que hoy tiene seis estados y el SRS
tiene siete. Eso es todo. **El trabajo pesado es de prosa, no de dibujo**, y está
repartido en §2 y §5.

Sobre el fondo: el desfase de diseño está casi todo del lado del documento. El SDD
publicado en Overleaf —su texto **y** sus imágenes— describe el flujo viejo, el de una
llamada única `Orchestrator.translate(text)` que devuelve la lista completa de oraciones,
con un "Static GLB Server" que nunca existió. El código ya hace otra cosa: divide la frase
en oraciones, las traduce todas en paralelo y manda un `segment` por oración con
`index`/`total` reales y un `done` al final. El desfase de requisitos está del lado del
código: no hay límite de solicitudes, no se valida el audio recibido, no hay reintentos
hacia la base, y si Neon no contesta al arrancar el backend no levanta.

Sobre el que decide: el modelo de lenguaje oficial ya quedó cerrado (`gpt-4o-mini`), junto
con vaciar el caché antes de remedir y con no autenticar las métricas. **Quedan dos
puntos abiertos** —el límite de solicitudes por cliente y la concurrencia de sesiones— y
cuatro temas de fondo en §6, cada uno con sus dos salidas.

Una nota que atraviesa todo el documento: **la línea base publicada de `rt_first_sign_ms`
(913 ms p50 / 1336 ms p95) es del camino por palabras y con oraciones no es comparable.**
La del flujo por oraciones es **p50 273 ms / p95 422 ms**, medida el **2026-10-15** con
`qwen3:4b-instruct` en Ollama local y la caché semántica vacía. Ninguna de las dos es la
de la tesis.

---

## 1. Cuál está desactualizado, y cómo se sabe

El owner preguntó esto primero, así que va primero.

### 1.1 El veredicto

| Cosa | ¿Al día? | Evidencia |
|---|---|---|
| **`../sign-ai-docs/diagramas/*.drawio`** (las fuentes) | **Sí, casi todo.** Diez de doce correctas | Los métodos que contienen coinciden con el código, uno por uno. Ver §1.3 |
| **`../sign-ai-docs/diagramas/png/*.png`** (los render) | **Sí**, son la exportación de esas fuentes | Salen de los `.drawio` de al lado |
| **Overleaf SDD `images/*.png`** | **No.** Es el juego anterior | **Idénticas byte a byte** a `sign-ai-backend/docs/diagrams/*.png`. Ver §1.2 |
| **`sign-ai-backend/docs/diagrams/*.png`** | **No.** Es el mismo juego anterior | Ver §1.2 |
| **Overleaf SDD `main.tex` (v159)** | **No.** El texto es del flujo viejo | Habla de `sendResult(segments)`, de `translate(text)` como único método y del Static GLB Server |
| **`sign-ai-backend/docs/sdd.md`** | **No.** Es el mismo texto viejo que el `.tex` | Copia del Overleaf |
| **Overleaf SRS `main.tex` (v436)** | **Sí**, salvo la §3 vacía y las filas de §5 | Editado el 2026-10-18 |
| **`../sign-ai-docs/documentos/requerimientos` v0.15** | **Es la fuente de los RF/RNF**; su lista de cambios pendientes ya recoge varios de estos ítems | 11 de agosto de 2026 |

En una frase: **`sign-ai-docs` está al día y Overleaf no.** El SDD de Overleaf es el que
se quedó atrás, y `docs/sdd.md` del backend es una copia suya, así que arrastra lo mismo.

### 1.2 Cómo se sabe — método 1: los archivos son idénticos

Se calculó un hash del contenido de las PNG de las tres copias. **Las de Overleaf y las
de `docs/diagrams/` del backend son el mismo archivo, byte por byte**, y ninguna se parece
a la de `sign-ai-docs`:

| Diagrama | Overleaf SDD | `sign-ai-backend/docs/diagrams/` | `sign-ai-docs/diagramas/png/` |
|---|---|---|---|
| 6.1 Vista lógica | `ad8f17c6` | `ad8f17c6` **= igual** | `653d225e` |
| 6.2 Vista física | `af77dd8e` | `af77dd8e` **= igual** | `c901131b` |
| 7.1-2 NLP | `e9ec7ae0` | `e9ec7ae0` **= igual** | `c7ace436` |
| 7.2 Secuencia | `e4499f14` | `e4499f14` **= igual** | `e832b49d` |
| 7.4 Estados UI | `932e5740` | `932e5740` **= igual** | `112ec56b` |

(Hash FNV-1a de 32 bits, calculado el 2026-10-18. Coinciden los cinco probados, con el
tamaño en bytes idéntico también.)

### 1.3 Cómo se sabe — método 2: qué dicen los `.drawio` y qué dice el código

Un `.drawio` es un XML con el texto de cada caja. Leyéndolo y comparándolo con el código,
no hay interpretación posible. Esto es lo que dice el juego de `sign-ai-docs`:

| Lo que el `.drawio` de `sign-ai-docs` nombra | ¿Está en el código? |
|---|---|
| `+ sendSegment(index, total, segment)`, `+ sendTranscript`, `+ sendError` | Sí, `controller.py` |
| `+ translateStream(text): AsyncIterator<(index, total, segment)>` | Sí, `orchestrator.py:18` |
| `+ split(text): List<String>` y `+ transformSentence(sentence): Segment` | Sí, `nlp_service_impl.py:36, :39` |
| `NLPServiceImpl` con **cuatro** colaboradores: `analyzer`, **`segmenter`**, `cache`, `llmClient` | Sí, `nlp_service_impl.py:24-27` |
| Las clases `GlossAnalyzer`, **`EmbeddingModel`**, **`SentenceSegmenter`** | Sí, las tres |
| `lookup(...): List<String>?` y `store(text, fingerprint, glosses: List<String>)` | Sí, `semantic_cache.py:164, :197` |
| `buildSegment(fingerprint, glosses): Segment` | Sí, `nlp_service_impl.py:87` |
| 7.2 con pasos `split` → `segment` → `transformSentence` → `analyze` → `lookup` → `store` (asíncrono) → `validate` → `(index, total, ValidatedSegment)` → `segment` → `done` | Sí, en el mismo orden |
| 6.3 con `Divide el texto final en oraciones`, `Para cada oración, en paralelo`, `Envía la oración al Android Client (en orden)`, `Envía aviso de fin` | Sí |
| 6.2 y C4-2 **sin** Static GLB Server y **sin** canal HTTPS de GLB | Sí: `app/static_glb/` está vacío |
| 6.2 con `External LLM API «cloud service» OpenAI (gpt-4o-mini)` | Coincide con la decisión del owner |

Y esto es lo que dice el juego de Overleaf (abriendo las imágenes):

| Lo que se ve en la PNG de Overleaf | Por qué está viejo |
|---|---|
| 7.2 arranca en `1. translate(text)` → `2. transform(text)` | No hay `split` ni `translateStream` |
| 6.1 tiene una caja `Static GLB Server` y una interfaz `Download(path): GLB file` | Ese servidor nunca existió |
| 6.1 rotula `«interface» Translate(text): result` y `Validate(glosses): validated glosses + paths` | El código manda una oración a la vez y valida una lista de segmentos |

### 1.4 Cómo se sabe — método 3: el texto

El `main.tex` del SDD en Overleaf (540 líneas, v159, editado el 2026-08-30) describe lo
mismo que el juego viejo de imágenes: `sendResult(segments)` (`:308`), `translate(text)`
como **único** método público (`:308`), el Static GLB Server (`:215`, `:238`, `:240`,
`:471`, `:507`). El SRS de Overleaf (v436, editado el 2026-10-18) sí está al día en su
prosa.

---

## 2. Explicaciones de cuatro puntos que no se entendieron

### 2.1 El punto 2 — `Controller.sendResult(segments)`

**Qué dice el documento hoy.** El SDD, en §7.1 (Overleaf `main.tex:308`), hace esta
descripción del Controller:

> *"Controller mantiene una referencia a Orchestrator y a SttServiceClient, y expone tres
> métodos: `handleAudioChunk (chunk)` recibe cada fragmento de audio que llega del cliente
> Android y lo reenvía a SttServiceClient; `handleTranscript (text, isFinal)` recibe la
> transcripción, ya sea parcial o final, de vuelta desde el servicio de STT; y
> `sendResult (segments)` envía el resultado final de la traducción al cliente."*

O sea: el documento dice que el backend, cuando termina de traducir una frase, manda **un
solo mensaje al teléfono, con todas las oraciones adentro**.

**Qué hay en el código.** No existe ningún método con ese nombre. Lo que hay son cinco
formas de mandar algo al teléfono, todas en `app/controller/controller.py`:

| En el código | Qué manda |
|---|---|
| `send_transcript(text, is_final)` (`:202`) | La transcripción del STT, parcial o final |
| `send_segment(index, total, segment, trace)` (`:205`) | **Una oración**, con su número y cuántas son en total |
| `send_error(message)` (`:235`) | Un error |
| sin método propio, en `handle_text` (`:164`) | Un `{"type":"done"}`, o sea "terminé la frase" |
| sin método propio, solo con `DEBUG_TRACE_ENABLED` | `trace` y `sentence_trace`, que son de depuración |

La diferencia que importa es una sola: **`send_segment` se llama una vez por oración,
dentro de un bucle.** El backend no junta las oraciones y las manda juntas.

**Un ejemplo con números.** Una frase con dos oraciones: la primera está en la caché
(~30 ms) y la segunda tiene que ir al modelo (~1,5 s).

| | Cuándo ve el usuario la primera seña |
|---|---|
| Como lo describe el documento viejo | A los ~1,5 s, cuando el modelo termina, y ve las dos oraciones de golpe |
| Como funciona hoy | A los ~30 ms ve la primera oración, y la segunda llega 1,5 s después |

Eso es el cambio de todo el trabajo de octubre. Es lo que hace que el avatar pueda estar
representando mientras la persona todavía está hablando.

**Opción A — cambiar el backend.** No aplica, y además no conviene: volver a mandar todo
junto es perder justamente lo que la tesis va a mostrar.

**Opción B — cambiar el documento.** Dos cosas:

| Dónde | Qué |
|---|---|
| SDD §7.1 (`main.tex:308`) | El párrafo que lista los tres métodos del Controller |
| SDD §6.1, el rótulo de la interfaz | La versión vieja dice `«interface» Translate(text): result` |

**Y acá está lo importante: el diagrama ya está bien.** La versión de 6.1 que está en
`../sign-ai-docs/diagramas/` **no dice** `Translate(text): result`: dice
`«interface» TranslateStream(text): validated segments`. O sea, la imagen correcta ya
existe y hay que subirla (es el punto 1). Lo único viejo es el texto de la página de al
lado.

**Riesgo para los diagramas: ninguno.**

**Recomiendo B.** Es reescribir un párrafo. Y mientras se hace, conviene escribir en el
mismo párrafo las cinco cosas que el Controller manda, porque el día que alguien lea el
SDD tiene que encontrar el protocolo completo ahí.

**Decisión del owner (2026-10-18): B.** Solo texto. No rompe ningún diagrama.

### 2.1 bis Decisiones tomadas el 2026-10-18

**Punto 2 — `sendResult(segments)`: B.** Solo texto. No rompe ningún diagrama.

**Punto 3 — `translate` contra `translateStream`: B.** Los tres diagramas que nombran esto
(7.1-1, 7.2 y C4-3) **ya están correctos** en `sign-ai-docs`: muestran los dos métodos y
marcan `translateStream` como el paso 2 de la secuencia. El texto del SDD es lo único
viejo. Un detalle que hay que cuidar al escribir: como el diagrama 7.1-1 muestra los dos
métodos, el texto tiene que decir los dos. Si el texto dijera "solo hay uno", el documento
se contradiría a sí mismo.

**Punto 5 — `SentenceSegmenter` y `EmbeddingModel` en la Figura 5: B.** Solo texto. El
diagrama de `sign-ai-docs` ya tiene las dos clases y el cuarto colaborador `segmenter`. Este
pendiente ya estaba anotado el **2026-09-03** en `docs/sdd-changes.md` y nunca se aplicó
al SDD.

**Punto 7 — el `store` en segundo plano: B.** Solo texto. El paso 14 del diagrama 7.2 de
`sign-ai-docs` **ya dice** "store(sentence, fingerprint, glosses) (asíncrono, no se espera
respuesta)": es el único de los 23 pasos con ese comentario. Lo único viejo es el texto.

Un detalle que hay que añadir al escribir el SDD, porque hoy no está en ningún documento y
un evaluador lo va a preguntar: **qué pasa al apagar el backend con una frase a medio
guardar.** La respuesta es que hay una espera explícita antes de cerrar
(`app/main.py:104`, `wait_for_pending_stores()`), así que no se pierden guardados. Y que si
un guardado falla se pierde esa entrada del caché, no la traducción que ya se mandó al
usuario: está en el docstring de `_store_in_background`.

**Punto 23 — RNF-SEC-01, límite de solicitudes por cliente: B, con medición.** No se
implementa el bloqueo. Se reescribe el requisito para que diga lo que el sistema realmente
hace, que es **medir** el uso del LLM y publicarlo, en vez de **bloquearlo**; y el bloqueo
queda anotado como trabajo futuro con la razón.

La razón que el owner dio el 2026-10-18: *"No existe nada de inicio de sesión en la app, ni
tipos de usuario, ni registro, tampoco hay administración. Es una app abierta."* Eso
coincide con el SRS: `main.tex:1196-1199` dice que no hay registro ni inicio de sesión, y
`:1201` que no hay modo de administración. Sin identificación de cliente, el límite no tiene
a quién aplicarse, y el propio RNF-SEC-01 lo admite: *"el mecanismo de identificación del
cliente… quedan pendientes de la definición de sesión (DEC-20)"*.

**Lo que hace que "B con medición" no sea bajar el requisito a nada:** el dato que
RNF-SEC-01 quiere controlar **ya está medido y publicado**. Cada llamada al modelo se
registra como `llm_ms{model}`, y ese histograma trae su propio contador
(`llm_ms{model}_count`). La ronda de pruebas puede reportar "se hicieron N llamadas al LLM"
sin escribir una línea de código.

**Punto 26 — RNF-REL-01 y RNF-DES-04, concurrencia y cola de sesiones: B, con la
justificación escrita.** No se implementa la cola. Se reescribe RNF-REL-01 para **dejar la
mitad que sí se cumple** y quitar la de la cola:

| Lo que pide RNF-REL-01 | Qué se hace |
|---|---|
| "recibir y procesar el flujo continuo de audio mediante un mecanismo asíncrono que **no bloquee el hilo principal**" | **Se queda.** Se cumple: todo el backend es asíncrono, la traducción salió del bucle de lectura el 2026-10-16, y `rt_read_loop_busy_ms` lo demuestra con 0,595 ms de máximo |
| "encolando el excedente de sesiones cuando se supere un número máximo" | **Se quita.** Y se anota como trabajo futuro, con la razón de abajo |

**La razón, para que quede escrita en el requisito:**

1. **El criterio del requisito no se puede cumplir con esta arquitectura.** Pide encolar
   *"sin pérdida de datos de audio"*, y en el backend eso no es posible: el audio se
   reenvía al STT de inmediato y no hay búfer que lo retenga. Para cumplirlo, la cola
   tendría que estar **dentro del STT**, que es donde está el búfer de 8 segundos. Eso es
   otro repo y otro requerimiento.
2. **La cola no mejoraría la escalabilidad real.** Lo que limita las sesiones simultáneas
   hoy no es el backend: es la GPU del STT, que hace una inferencia a la vez, y la base de
   datos. Una cola en el backend no arregla eso, solo cambia dónde se espera.
3. **Es un prototipo de tesis sobre un equipo personal**, no un servicio. El plan de
   pruebas ya pone "escalabilidad a muchos usuarios" en **fuera de alcance**
   (`plan-pruebas/00-bases/alcance.md` §2.1), así que una cola nunca se va a probar ni a
   demostrar.
4. **Una cola agrega una espera no acotada**, y eso haría imposible medir con honestidad el
   número que sí importa para la tesis, `rt_first_sign_ms`: si una frase puede esperar un
   tiempo que depende de cuántas sesiones haya, ese número deja de significar nada. Con dos
   o tres sesiones y sin cola, la latencia que se reporta es real.

**Salvedad honesta que también queda escrita:** `trazabilidad.md` §2.2 anota que *"el
cálculo de embeddings y el segmentador bloquean unas decenas de milisegundos, y no se ha
probado con varios clientes a la vez"*. La parte asíncrona está; con más de un cliente a la
vez, no está medida. Eso es material para la ronda de pruebas, no un defecto.

**Punto 33 — RNF-POR-02 y `network_mode: host`: B, y el requisito se cumple completo.**

> **Corrección de esta sesión.** Una primera versión de este análisis decía que
> `network_mode: host` "no es confiable en Windows y macOS". **Eso era incorrecto.** Las
> versiones recientes de Docker Desktop lo soportan. Queda registrado porque el error iba en
> la dirección contraria a la que llegó el punto, y porque la versión buena de la respuesta es
> la que importa.

**El hecho.** Docker Desktop corre los contenedores dentro de una máquina virtual (WSL2 en
Windows). Desde **Docker Desktop 4.34 (enero de 2025)** soporta redes de host, con una
opción que hay que activar en *Settings → Resources → Network*.

| ¿Dónde? | ¿Funciona con `network_mode: host`? |
|---|---|
| Linux | **Sí**, en cualquier versión del motor de contenedores |
| Windows con WSL2 + Docker Desktop 4.34+ | **Sí**, con la opción activada |
| macOS con Docker Desktop 4.34+ | **Sí**, con la opción activada |

**Pendiente de verificar en la máquina del equipo:** que la versión instalada tenga esa
opción. No se midió.

**Lo único que se rompe en Windows y macOS** es el acceso al modelo local. Con red de host,
el `127.0.0.1` del contenedor apunta al interior de la máquina virtual, no a Windows ni a
macOS. Y **tiene solución limpia:** poner Ollama como un servicio opcional del mismo
`docker-compose.yml`, activado por perfil, para que viva en el mismo espacio de nombres que
el backend y sea alcanzable en las tres plataformas:

```yaml
# Solo se levanta cuando se llama: docker compose --profile local up
ollama:
  image: ollama/ollama
  profiles: ["local"]
  ports: ["11434:11434"]
```

El STT no sufre esto: su puerto `8000` está publicado en el mismo espacio de nombres, así que
`127.0.0.1:8000` funciona igual en las tres plataformas. Y el puerto 8080 del backend también
sale publicado.

**Lo que hay que hacer** (nada de esto toca diagramas):

| # | Qué | Dónde |
|---|---|---|
| 1 | Documentar la condición de la versión: "cualquier motor de contenedores en su versión que soporte redes de host; Docker Desktop 4.34 o posterior en Windows y macOS" | RNF-POR-02, criterio de aceptación |
| 2 | Cambiar "no dependa de un proveedor de nube o **sistema operativo de host específico**" por "no dependa de un proveedor de nube ni de un **entorno de desarrollo** concreto: el repositorio documenta la configuración necesaria" | RNF-POR-02, descripción |
| 3 | Escribir la dirección del STT en el `.env.example`, con un comentario que diga que en este despliegue es `127.0.0.1:8000` y no el nombre del servicio | `.env.example` |
| 4 | Meter Ollama como servicio opcional del compose, con perfil | `docker-compose.yml` |

**Por qué los puntos 1 y 2 no bajan la vara.** El punto 2 es una corrección de una premisa
que nunca fue cierta: el problema real de `docker-compose.yml` no es el sistema operativo,
es que el repositorio no documenta qué tiene que poner el usuario. Eso sí se arregla, y con
una línea. El punto 1 agrega una condición que el motor de contenedores cumple en las tres
plataformas.

**Punto 34 — TLS / WSS y el proxy inverso: B.**

> **🔶 TODO del owner — pendiente de revisar, 2026-10-18.**
> Marcar en el SRS que el proxy inverso **no existe hoy** y que hay que decidir cuándo se
> pone. Si algún día hay dominio y hay despliegue real, hay que agregarlo **y entonces sí
> tocar tres diagramas: 6.2, C4-2 y C4-1.** Queda anotado acá para que no se pierda.

**Lo que se hace:** en el SRS §Interfaces de Comunicación, cambiar la frase que dice que la
conexión es WSS por una que diga:

> "El canal viaja cifrado con TLS cuando el despliegue termina el cifrado delante del
> backend, con un proxy inverso. En el entorno de demostración del proyecto, que corre en la
> red del equipo de desarrollo, el backend sirve HTTP en claro y el enlace viaja sin cifrar."

Y **una línea más**, en §Adaptación del Sitio: para un despliegue real hay que poner un proxy
inverso delante del backend.

**Por qué A no era viable hoy.** No es que sea mala idea: es que **no hay dominio** (decisión
del owner del 2026-10-17, "no hay dominio y no se va a tener, porque es un prototipo"). Sin
dominio no hay certificado, y sin certificado no hay nada que un proxy pueda terminar.

**Lo que B deja dicho con honestidad:** el requisito **no lo cumple el software, lo cumple el
despliegue**. Es una arquitectura legítima y común (es lo que se hace entre la app y la base
de datos: no se cifra el tramo interno porque la red lo protege), pero RF-INT-COM-03 dice
literalmente "toda comunicación", y con B eso no se cumple por sí solo. Por eso la frase
nueva dice las dos cosas.

**Lo que dice el análisis de diagramas, para que no se repita:** ninguno de los doce tiene
una caja de proxy. El `«WSS»` está en las **flechas** de 6.2, C4-1 y C4-2, no en un nodo.
Los diagramas piden que el canal se llame WSS, que es una etiqueta; lo que falta es **quién
termina el cifrado**, y eso no está dibujado en ninguna parte.

**Punto 36 — RF-CAT-03, "Seña no disponible": B.**

> **🔶 TODO del owner — al escribir esto en Overleaf, dejar marcado que hay que decidir si
> se quiere que el sistema (el backend) sea quien detecte el segundo caso, o si sigue
> siendo la aplicación. Pendiente, 2026-10-18.**

**Lo que se hace:** corregir el SRS para que diga las dos cosas, en dos lugares:

| Dónde | Qué agregar |
|---|---|
| §Alcance, final del ítem *Validación contra el catálogo de señas* (`main.tex:202`) | "Si la glosa existe en el catálogo pero su animación no puede cargarse, la aplicación omite esa seña y continúa representando las demás." |
| Tabla de estados, fila *Reproduciendo* (`main.tex:747`) | "Cuando la animación de una glosa no puede cargarse, esa seña se omite, el resto de la frase se sigue representando y la pantalla muestra el mismo mensaje." |

Ese texto **ya está escrito** en `../sign-ai-android/docs/CONTRASTE-APPvsDOCUMENTOS.md`
§6 punto 7. No hay que redactarlo de nuevo.

**El problema que se corrige, en dos partes:**

| | Lo que dice hoy | Lo que hace el sistema |
|---|---|---|
| Quién muestra el mensaje | "el **sistema** responde con el mensaje" | El backend marca `available: false`; el mensaje lo pone la **aplicación** |
| Cuántos casos | **uno**: la glosa no está en el catálogo | **dos**: la glosa no está, **o** la glosa está pero su animación no se puede cargar |

**Por qué A no era la mejor.** Meter una columna nueva en el catálogo para decir "esta seña no
tiene animación" **no arregla el problema real**: los 18 archivos siguen sin existir. La
animación se exporta, y el catálogo se ajusta cuando esa exista. Por eso, si algún día se
quiere que el backend lo diga, el lugar natural es el catálogo, y se hace junto con las 18
señas, no antes.

**Lo que sí está resuelto y no se toca:** la app ya omite la seña que no carga, sigue con las
demás y avisa (contraste de la app, punto A5 y punto 21 de su §9). Y el SRS dice 50 y el
objetivo es 50: exportar las 18 que faltan es trabajo de las señas.

**Lo importante para los diagramas.** El 6.3 tiene dibujado `Glosa existe en el catalogo?`
con dos salidas —"Marca la glosa como disponible" y "Marca la glosa como 'seña no
disponible'"— y **las dos siguen siendo ciertas**. El segundo caso lo detecta la aplicación,
que no es un paso del backend, así que no aparece en el diagrama de procesos. Con A habría
que agregar un tercer caso.

> **Cómo se manejan los TODO.** Los que van marcados con 🔶 en este documento se escriben
> **en los propios documentos de Overleaf, en el texto**, cuando se arreglen en la sesión
> siguiente. No son Serious para el entregable: es un documento en construcción, y la
> anotación existe para revisitarlos con el equipo. El owner lo decidió el 2026-10-18.

**Punto 37 — el nombre `rt_first_sign_ms`: B, y el SRS se escribe con los dos tramos.**

**El problema.** RNF-DES-01 y el SRS (`main.tex:843-844`) miden *"desde que el texto se envía
a traducir […] hasta que el avatar ejecuta la primera seña"*. Pero el backend **no sabe
cuándo el avatar se mueve**: eso lo sabe la app. Lo que el backend mide es desde que recibe
la frase hasta que **manda la primera oración por el cable**.

| Tramo | Quién lo mide | Con qué nombre |
|---|---|---|
| Frase recibida → primera oración **enviada** | El backend | `rt_first_sign_ms` |
| Oración **enviada** → el avatar **se mueve** | La app | `SignAiMetrics.onFirstSign` |

La suma de los dos es lo que pide el SRS, y **los dos tramos existen**: el invariante 4 del
contrato pide que los dos lados midan, y los dos miden.

**Lo que hay que escribir en el SRS**, §Aspectos de medición (`main.tex:836-849`): que el
número tiene dos tramos, que el backend mide el primero y lo publica en `rt_first_sign_ms`,
que la aplicación mide el segundo, y que **la suma es el tiempo hasta la primera seña**.

**Por qué no A.** Renombrar obligaría a rehacer la línea base vieja con un nombre que ya no
existe, **y esa línea base además no es comparable**, porque es del camino por palabras. Y
`rt_first_sign_ms` aparece en `docs/performance.md`, en `tools/` del repo de la app, en el
skill del contrato y en sesiones ya escritas.

**Las tres líneas bases que hay que distinguir** (esto es donde se pueden meter los pies):

| Número | Qué es | ¿Sirve? |
|---|---|---|
| 913 ms p50 / 1336 ms p95 | Del **camino por palabras**, el que se desarmó en octubre | **No es comparable.** El nombre se conserva a propósito para que la comparación se vea |
| 273 ms p50 / 422 ms p95 | Del **flujo por oraciones**, medido el **2026-10-15** con Qwen local y la caché vacía | Es el número real del sistema actual, **pero con un modelo que no es el oficial** |
| — | Con `gpt-4o-mini`, que ya es el oficial | **Todavía no medido** |

**Riesgo para los diagramas: ninguno.** Ninguno de los doce muestra métricas.

**Punto 40 — la instrumentación: B, y va en el SDD, no en el SRS.**

> **El owner dejó claro el 2026-10-18 que la parte de mediciones del proyecto no está
> terminada.** Lo que se escriba ahora es el texto de arranque, y lo que falte lo terminan los
> compañeros en otra oportunidad. No es un pendiente de este documento: es que el proyecto
> todavía está midiendo.

**Por qué en el SDD y no en el SRS.** Son documentos de cosas distintas. El SRS dice *qué
debe hacer el sistema*, y `/metrics` no es una funcionalidad: es un instrumento de medición.
Meterlo ahí sería documentar una cinta métrica en el manual de uso. El SDD dice *cómo está
construido*, y ahí sí va.

**Por qué no es opcional.** Dos documentos del proyecto ya lo decidieron:

| Documento | Qué dice |
|---|---|
| `plan-pruebas/00-bases/marco.md` §6.1 | *"La instrumentación de tiempos funciona"* es **criterio de entrada** a las rondas de prueba |
| `modificaciones/requerimientos.md` §5 | *"Medición de tiempos por paso en el backend — Es instrumentación. **Se documenta en el diseño** y en el plan de pruebas"* |

Y `docs/sdd-changes.md` (2026-10-01) **ya tiene escrita la propuesta**, que nunca se aplicó:
*"mencionarlo como instrumentación no funcional (fuera del contrato funcional del Controller
con Android), y agregar el mensaje `trace` al protocolo WebSocket como mensaje opcional de
debug"*.

**Qué escribir:**

| Sí | No |
|---|---|
| Que existe una traza por oración (`PipelineTrace`) que mide cada paso, y que **no cambia ninguna firma** de las clases del SDD porque usa un `ContextVar`. Esa es una buena decisión de diseño y conviene decirla | Cómo está hecho `metrics.py` por dentro. A nadie le interesa |
| Que existen `/metrics` y `/metrics.json`, y que **no llevan autenticación** (decisión del owner) | — |
| Una tabla corta con qué mide cada métrica `rt_*` | — |
| Que todo esto está **fuera del contrato funcional** con la app | — |

**El pedazo que sí toca el SRS** son los dos mensajes de depuración (`trace` y
`sentence_trace`), que **no están** en la lista de lo que el servidor manda a la app
(`main.tex:1107-1117`). Hay que agregarlos ahí, aclarando que solo salen con
`DEBUG_TRACE_ENABLED=true`. Eso **ya está cubierto por el punto 16**, que salió B: no es
trabajo nuevo, es añadirlo a la lista de ese punto.

**Riesgo para los diagramas: ninguno**, y con una razón que conviene decir: la instrumentación
**no es un paso del flujo**. No aparece en el diagrama de procesos ni en la secuencia, y no
debería aparecer. Meterla en la 7.2 sería un error, porque ese diagrama muestra el camino
funcional.

### 2.2 El punto 3 — `translate` contra `translateStream`

**Qué dice el SDD.** En §7.1 y §7.2 (`main.tex:308`, `:310`, `:359`): `Orchestrator` tiene
`translate(text)` y el Controller lo llama cuando el STT marca la transcripción como
final.

**Qué hay en el código.** `app/orchestrator/orchestrator.py` tiene las dos:

| Método | Qué devuelve | Cuándo se usa |
|---|---|---|
| `translate(text)` (`:15`) | La lista **completa**, cuando termina todo | Casi nadie. Queda por comodidad |
| `translate_stream(text)` (`:18`) | Las oraciones **una por una, en orden, en cuanto cada una está lista** | El que usa el protocolo con la app |

La analogía: `translate` es "esperar el plato completo y servirlo de una vez";
`translate_stream` es "servir cada plato en cuanto sale". Con la segunda, una oración que
está en la caché sale en ~30 ms y no espera a que la otra termine de ir al modelo.

`translate()` **no se borra**: la usa `scripts/verify_orchestrator.py` y es cómodo para
probar. Lo que cambia es que el SDD diga cuál de los dos es el camino real del protocolo.

### 2.3 El punto 33 — `network_mode: host`

**Qué es.** Docker normalmente mete cada contenedor en su propia red privada, y se hablan
por nombre (`stt`, `backend`). Este repo **no hace eso**: `docker-compose.yml:20` pone el
backend directamente en la red de la máquina, con `network_mode: host`.

**Qué se gana.** El backend alcanza cualquier cosa de la máquina del desarrollador sin
configurar nada: un Ollama en `127.0.0.1:11434`, una base local, el STT en el puerto
publicado `127.0.0.1:8000`. Es lo que permite trabajar sin internet con un modelo local.

**Qué se pierde.**

| Se pierde | Consecuencia concreta |
|---|---|
| Aislamiento del contenedor | Dos proyectos en la misma máquina se pelean el puerto 8080 |
| Portabilidad | En Docker Desktop (macOS/Windows) `network_mode: host` no se comporta igual; el `Dockerfile` y el compose están escritos para Linux |
| El nombre del servicio | `settings.py:61` trae `ws://stt:8000/ws/transcribe` por default y **no resuelve** en la red del host. El `.env` local lo sobreescribe a `127.0.0.1:8000`. Si el `.env` falta o se regenera desde el ejemplo, el backend no alcanza el STT |

**Qué dicen los documentos.** RNF-POR-02 pide que el backend se despliegue como una unidad
en cualquier máquina con el motor de contenedores. El SRS §6.2 y la imagen 6.2 dibujan dos
contenedores Docker en una máquina, **sin decir qué red usan**, así que la imagen no
choca con el código: es compatible con las dos opciones.

**Qué hay que hacer.** Documentar la restricción. Volver a la red de compose obligaría a
resolver el STT de otra forma **y** rompería el acceso al Ollama local, que es lo que
permite trabajar sin internet.

### 2.4 El punto 37 — `rt_first_sign_ms`, los dos casos a detalle

**El problema.** RNF-DES-01 y el SRS (`main.tex:843-844`) miden *"tiempo desde que el
texto se envía a traducir … hasta que el avatar ejecuta la primera seña"*. El nombre de la
métrica del backend dice `rt_first_sign_ms`, pero **no mide hasta la seña**: mide hasta que
el backend **envía** la primera oración (`app/controller/controller.py:205-224`). El resto
del tramo —de que la oración sale del cable hasta que el muñeco se mueve— lo mide la app
en `SignAiMetrics.onFirstSign`.

O sea: **el número existe y está en los dos lados, pero cada uno mide un tramo y el nombre
promete los dos.**

| | **A — Renombrar la métrica** | **B — Dejar el nombre y documentarlo** |
|---|---|---|
| Qué se gana | El nombre dice lo que mide. Nadie puede leer mal `/metrics` | Cero cambios. El invariante 4 del contrato (los dos lados tienen que instrumentar lo mismo) **ya se cumple**: las dos piezas existen |
| Qué se pierde | Se pierde la comparación con la línea base publicada (913 ms p50 / 1336 ms p95). Ese nombre se conservó **a propósito** para que la comparación fuera visible, y aparece en `docs/performance.md`, en `tools/TIEMPO-REAL.md` del repo de la app, en el skill del contrato y en sesiones ya escritas | El nombre sigue engañando a quien lea solo `/metrics`. Hay que decirlo en el SRS y en `performance.md` |
| Qué toca en los diagramas | Nada | Nada |

**Lo que yo recomiendo, y por qué.** **B**, pero con el SRS escrito de una forma que lo
haga cierto: en §Aspectos de medición decir que el número tiene **dos tramos** —el backend
mide *"frase recibida → primera oración enviada"* (`rt_first_sign_ms`) y la app mide
*"envío → primera seña"* (`onFirstSign`)— y que **la suma de los dos es el tiempo hasta la
primera seña** que pide el SRS. Así el documento queda verdadero, el nombre queda siendo la
etiqueta de una de las dos piezas, y no se rompe nada.

Una tercera vía que **no** recomiendo: renombrar ahora y publicar las dos series. Obliga a
rehacer la línea base vieja con un nombre que ya no existe, y esa línea base además no es
comparable (es del camino por palabras).

---

## 3. La tabla de contrastes

Cada fila tiene dos salidas: **A) se adapta el backend** (cambiar el código) y **B) se
adapta el documento** (cambiar el SRS, el SDD o los documentos del repo). La columna
**Toca un diagrama** dice si la fila obliga a editar un `.drawio`. Casi ninguna lo hace.

### 3.1 Diseño — el SDD y los diagramas

| # | El contraste | A) Se adapta el backend | B) Se adapta el documento | Recomiendo | Toca un diagrama | Decisión |
|---|---|---|---|---|---|---|
| **1** | **Overleaf y `docs/diagrams/` del backend tienen las 12 PNG del juego viejo. Las de `sign-ai-docs` son el juego nuevo.** Verificado byte a byte en §1.2 | No aplica | Reemplazar las 12 PNG de Overleaf por las de `sign-ai-docs/diagramas/png/`, y poner esas mismas en `docs/diagrams/` | **B.** Es subir archivos, no redibujar | **No.** Ninguna de las 12 fuentes hay que tocar | **B** |
| **2** | `Controller.sendResult(segments)` no existe. Hay cinco métodos de salida. Explicado en §2.1 | Crear un `sendResult` que nadie usaría | Reescribir §7.1 (`main.tex:308`) | **B.** La imagen de `sign-ai-docs` ya está correcta | No | **B** |
| **3** | El SDD dice que `Orchestrator` tiene un **único** método público, `translate(text)`. Hay dos: `translate` y `translate_stream`. Explicado en §2.2 | Borrar `translate()` y dejar solo `translate_stream`: se rompe `scripts/verify_orchestrator.py` | Decir que `translate_stream` es el camino del protocolo y `translate` el método cómodo | **B**, y no borrar `translate()`. La imagen de `sign-ai-docs` ya está correcta | No | **B** |
| **4** | `NLPService.transform(text)` es el único método; no hay segmentación. El código tiene `split(text)` y `transform_sentence(sentence)`, y `transform` se arma con los dos | Borrar `transform` | Describir los tres y decir que `transform` es la composición | **B.** Verificado: la Figura 5 de `sign-ai-docs` **ya tiene** `transform`, `split` y `transformSentence`, y 7.2 ya tiene los pasos `split` → `segment` → `transformSentence`. **El diagrama no cambia** | No | **Pendiente.** El owner pidió ver las implicaciones antes de decidir; la respuesta es que B no toca diagrama y que el diagrama ya está bien |
| **5** | El SDD dice que en el diagrama de clases de NLP no existen `SentenceSegmenter` ni `EmbeddingModel`, y que `NLPServiceImpl` tiene tres colaboradores | No aplica | Agregar las dos clases y su dependencia a la Figura 5 | **B**, y **no rompe nada**: verificado que la Figura 5 de `sign-ai-docs` **ya tiene las tres clases** y el cuarto colaborador `segmenter`. Lo único viejo es el texto del SDD | No | **B** |
| **6** | El SDD dice que `lookup` devuelve `List<Segment>` y que `store` guarda los `Segment`. El código usa `List<String>` | No aplica: la columna de la base es `glosses TEXT[]` y un `Segment` completo duplicaría el `type` | Corregir la firma en §7.1 (`:323`) y §7.2 (`:361`) | **B**. La Figura 5 de `sign-ai-docs` **ya dice** `List<String>?` y `glosses: List<String>` | No | **B** |
| **7** | El `store` aparece como paso **síncrono**. En el código corre en segundo plano | Volverlo síncrono: medido, costaba ~220 ms por frase nueva | Marcarlo como asíncrono en la Figura 7 | **B**. El 7.2 de `sign-ai-docs` **ya dice** *"store(sentence, fingerprint, glosses) (asíncrono, no se espera respuesta)"* | No | **B** |
| **8** | El SDD **nunca dice quién dispara la traducción**: §6.3 arranca en "el usuario activa el micrófono" y §7.2 empieza en "Controller recibe el texto final", como si el `final` del STT disparara | No aplica | Reescribir el arranque de §6.3 (`:266`) y §7.2 (`:359`) | **B.** El 6.3 de `sign-ai-docs` ya tiene `Silencio de 1.5s detectado?` → `Divide el texto final en oraciones`, que es compatible. Lo que falta es la frase que lo diga | No | **B** |
| **9** | Existe un **"Static GLB Server"** y un canal HTTPS aparte para los GLB (§6.1, §6.2, C4-2, C4-3). El SRS dice que los GLB van dentro del APK | Implementarlo: `app/static_glb/` está vacío y con el corpus en el APK sería un 404 garantizado | Sacarlo del SDD (`main.tex:215, :238, :240, :471, :507`) | **B**. Las cuatro imágenes de `sign-ai-docs` **ya no lo tienen**: verificado, el texto "Static GLB Server" no aparece en ninguno de los 12 `.drawio` | No | **B** |
| **10** | El SDD dice que `modified_at` "permite detectar cambios en el catálogo **sin reiniciar el backend**". No lo lee nadie | Recarga en caliente: rompe RNF-BD-03, porque para saber que cambió hay que consultar la base | Corregir la frase (§7.3, `main.tex:387`) | **B**. La imagen 7.3 de `sign-ai-docs` es una tabla de columnas y **no dice nada del reinicio**, así que no se toca | No | **B** (misma decisión que §6.2) |
| **11** | `catalog.semantic_category` está documentada pero **ningún código la lee**: el `SELECT` es `gloss, glb_animation_path` | Leerla: tres palabras en `catalog_repository.py:37-39` y un campo más en `Gloss` | Sacarla del SDD y quitar "categoría" de RF-CAT-01 | **A.** Y **no rompe el diagrama**: la imagen 7.3 de `sign-ai-docs` **ya lista `semantic_category`**, así que leerla pone el código de acuerdo con el diagrama, no al revés | No | **A** |
| **12** | `glb_animation_path` guarda rutas de un servidor que no existe (`/static/glb/…`) | Cambiar los valores en Neon | Escribir en el SDD que el valor es una clave que la app resuelve con sus propios recursos | **B.** La imagen 7.3 solo dice `glb_animation_path : VARCHAR`, así que no se toca | No | **B** |
| **13** | El diagrama 7.4 tiene **seis** estados —le falta *Texto listo*—. El texto del mismo SDD dice siete y el SRS tiene siete (`main.tex:717-766`) | No aplica | Agregar *Texto listo* al `.drawio` y regenerar la PNG | **B.** Y es el **único diagrama que hay que editar de verdad**: un nodo nuevo y las transiciones `Grabando → Texto listo`, `Texto listo → Procesando` (confirma envío) y `Texto listo → Inactivo` (cancela) | **Sí.** Un nodo y tres flechas en `sdd-7.4-diagrama-estados-ui.drawio` | **B** |
| **14** | El 7.4 rotula la salida de *Error* como "automático, **≤2s**". El SRS dice "vuelve a Inactivo automáticamente" **sin plazo** | No aplica: es de la app | Sacar el número del SDD (`:417`) y dejarlo solo en el SRS | **B.** Se hace **en el mismo archivo y el mismo minuto** que el punto 13, así que no agrega trabajo | **Sí.** Una etiqueta de flecha, en el mismo archivo del 13 | **B** |
| **15** | El C4-2 dice que el cliente "renderiza el avatar 3D con **Filament**". El SRS ya dice Three.js 0.169.0 en WebView | No aplica | Corregir el `.drawio` | **B.** **Una palabra.** Ya está en el contraste de la app (A8); se repite porque toca el mismo archivo | **Sí.** Una cadena de texto en `sdd-c4-2-contenedores.drawio` | **B** |
| **16** | El SRS no describe el protocolo que existe, y lista entre los avisos "**solicitud en espera**", que el backend nunca manda | Implementar un estado de espera | Describir los frames reales y sacar "solicitud en espera" | **B.** El SRS **no tiene ningún diagrama del protocolo** (sus dos imágenes están sin usar: `main.tex` no tiene un solo `\includegraphics`). Es solo prosa | No | **B** |
| **17** | spaCy no aparece en la tabla de software del SRS ni en el SDD §6.2. `es_core_news_md` pesa ≈ +440 MB | No aplica | Agregar la fila al SRS (`:1023-1074`) y al SDD §6.2 (`:240`) | **B.** La imagen 6.2 lista los contenedores y sus componentes, **no las librerías**, así que no se toca | No | **B** |
| **18** | El SRS dice "el NLP no consume memoria del servidor". Contradice el ítem de embeddings del mismo SRS dos párrafos antes | No aplica | Corregir la frase (`:1183-1190`) | **B** | No | **B** |
| **19** | El SRS dice "expone **dos** puntos de entrada". Expone cuatro | No aplica | Escribir los cuatro, o decir "dos más instrumentación de diagnóstico" | **B**, y sale de §6.6 | No | **B** |
| **20** | El SRS dice FastAPI 0.115 y LangChain 1.4.6. Medido el 2026-10-18 dentro de la imagen: **0.143.0** y **1.4.5** | Fijar en `requirements.txt` las del SRS: improbable que 0.115 funcione | Poner los números reales en el SRS | **B**, y además fijarlos en `requirements.txt` (punto 32) | No | **B** |
| **21** | El SRS dice "el servidor conserva 8 segundos de audio por frase". Ese tope está en el STT; el backend no guarda audio | No aplica | Aclarar que el tope está en el servicio de transcripción | **B** | No | **B** |
| **22** | RF-INT-SW-01 dice que el STT es "componente interno, no una llamada a un servicio externo por red". El SRS §2.1 lo pone en "un contenedor aparte" | Empaquetarlo en el proceso del backend: es otro repo y necesita su propia GPU | Aclarar RF-INT-SW-01 | **B.** La imagen 6.2 y la C4-2 **ya lo muestran como un contenedor aparte**, así que el diagrama está del lado del SRS | No | **B** |
| **23** | RNF-SEC-01 pide un límite de solicitudes por cliente. No existe nada | Implementarlo, pero la identificación del cliente sigue abierta en DEC-20 | Bajar o quitar el requisito y anotarlo como trabajo futuro | **B**, pero ver §7 | No si es B. **Sí** si fuera A: una cola o un rechazo es un nodo nuevo en el 6.3 | **Abierto.** El owner no sabe cómo tratarlo |
| **24** | RNF-SEC-02 pide validar que lo que llega por el canal sea audio. No existe | Implementarlo: el tamaño del chunk y la energía media (`_pcm16_rms` ya las calcula y hoy no rechaza nada) | Quitar el requisito | **A.** Es barato. Y **no toca el 6.3**, que empieza en "Activa micrófono": es una línea nueva en el §7.1 del SDD, no un paso del flujo | No | **A** |
| **25** | RNF-SEC-03: la caché guarda el texto sin vencimiento, **y el backend lo escribe en los logs** a nivel INFO, dos veces por frase | Sacar el texto de los logs (`controller.py:147` y `:161`) y poner vencimiento a la caché | Aclarar que el SRS ya autoriza el texto de la caché, pero no dice que sea para siempre | **A y B.** Los logs no tienen defensa: el SRS no los menciona. Para la caché, el SRS ya autoriza el texto guardado, lo que falta es un plazo y no hay número en ningún documento | No | **A y B** |
| **26** | RNF-REL-01 y RNF-DES-04 piden cola de sesiones y un mínimo de simultáneas. No hay cola ni tope | Implementar la cola | Aplicar el punto 13 de `modificaciones/requerimientos.md`: bajar a 2-3 sesiones y quitar la cola sin pérdida | **B**, pero ver §7 | No si es B. **Sí** si fuera A: una cola es un nodo nuevo en el 6.3 | **Abierto.** El owner no sabe cómo tratarlo |
| **27** | RNF-REL-03 pide reintentos hacia la base. No hay ni uno, y `CatalogRepository.load_all()` no está en un `try`: si Neon no contesta al arrancar, el proceso no levanta | Timeout de 5 s + un reintento, más el `try/except` del arranque | Ajustar el requisito a "error controlado sin reintentos" | **A**, que es §6.4 opción A. Y **no toca ningún diagrama**: la 7.2 no incluye a PostgreSQL entre los participantes, así que un reintento no se dibuja | No | **A** |
| **28** | RNF-MNT-05 dice que se puede borrar una entrada de la caché sin reiniciar. Con el preload no: la fila vive en memoria | Invalidación o relectura sin reiniciar | Cambiar el criterio a "reflejado tras reiniciar" | **B.** Es una línea en dos documentos que hoy describen el backend de antes del preload | No | **B** |
| **29** | RNF-BD-03 ("cero consultas a la base durante la traducción") es falso por el `store`, por el camino de reserva y por el keep-alive | Quitar el camino de reserva | Aclarar: "cero lecturas del catálogo durante la inferencia" | **B.** Lo que el requisito protege de verdad —el catálogo en memoria— sí se cumple | No | **B** |
| **30** | RNF-AV-03 pide avisar "en un par de segundos". Hoy son 3 intentos de 10 s, porque `max_retries` no está escrito | `max_retries=1` y `llm_timeout_ms=5000` | Cambiar el requisito al plazo que el cliente ya tiene | **A**, que es §6.3 opción B | No | **A** |
| **31** | RNF-MNT-03 pide analizadores estáticos. No hay ninguno. Y `CLAUDE.md` exige inglés sin excepción y quedan comentarios en español en cinco archivos | Configurar `ruff`, que de paso hace cumplir la regla de inglés | Relajar el requisito a revisión de código | **A.** Aviso: `app/metrics.py` tiene ~20 líneas de prosa en español y es el archivo que más se lee del repo. La traducción es mecánica y no toca el diagrama | No | **A** |
| **32** | RNF-MNT-04 pide dependencias fijadas. `requirements.txt` no fija nueve de ellas | Fijar versiones | Relajar el requisito | **A** | No | **A** |
| **33** | RNF-POR-02 pide un contenedor portable. `docker-compose.yml:20` usa **`network_mode: host`**. Explicado en §2.3 | Volver a la red de compose: rompe el acceso al Ollama local | Declarar la restricción en el documento | **B.** La imagen 6.2 dibuja dos contenedores sin especificar la red, así que **no hay que tocar el diagrama** | No | **B** |
| **34** | RF-INT-COM-03 y el SRS piden TLS y **WSS**. El backend no termina TLS. La app en release **solo** acepta `wss://` | Poner un proxy inverso con TLS delante del backend | Documentar que el cifrado lo termina el despliegue | **Ver §7.2.** Pero lo que hay que saber es que **ninguno de los 12 diagramas tiene un nodo de proxy**: el `«WSS»` está en la *flecha* de la 6.2 y en la arista `[Android, WSS]` de la C4-1. Poner proxy = nodo nuevo en **6.2, C4-2 y C4-1**. Documentar = **cero diagramas** | **Sí, si es A** (tres diagramas). No si es B | **Pendiente**, con el análisis en §7.2 |
| **35** | RF-NLP-02 dice que al modelo se le entrega "la frase completa". Lo que llega es **una oración** | No aplica | Aclarar el requisito | **B** | No | **B** |
| **36** | RF-CAT-03 dice que el sistema responde "Seña no disponible". El backend marca `available: false` y lo dice la app. Y 18 de las 50 glosas vienen con `available: true` y ruta inexistente | Que el catálogo diga si la animación existe y el backend lo mande | Aclarar el SRS para que cubra el segundo caso y decir que el aviso lo pone la app | **B**, y con este encuadre **el diagrama no se toca**: el 6.3 tiene `Glosa existe en el catalogo?` con dos salidas (disponible / "seña no disponible"), y las dos siguen siendo ciertas. El segundo caso —la glosa existe pero el archivo no— lo detecta la app, que ya lo resolvió | No | **B**, con esa condición |
| **37** | `rt_first_sign_ms` promete el tiempo hasta la seña y mide hasta el envío. Los dos casos, a detalle, en §2.4 | Renombrar la métrica | Dejar el nombre y documentar los dos tramos en el SRS | **B**, con el SRS escrito de forma que el número quede verdadero | No | **B**, y el owner pidió el análisis de los dos casos: está en §2.4 |
| **38** | La caché guarda duplicados (INSERT sin `UPSERT`) y respuestas vacías | `UPSERT` sobre `(original_text, phrase_type)` y no guardar vacías | Actualizar el plan de pruebas, que hoy describe el defecto como comportamiento | **A y B** | No | **A y B** |
| **39** | Cuando una frase falla a mitad, sale `error` y **no** sale `done`, y el contrato no lo dice | Mandar el `done` de todas formas | Dejarlo escrito en `docs/android-integration.md` §4 | **A**, en el mismo cambio que §6.5. Y **no obliga a tocar la 7.2**: el `done` ya está dibujado al final del bucle; lo que faltaría para el error es una arista opcional | No, salvo que se quiera dibujar la arista del `error` | **A** |
| **40** | Ni el SRS ni el SDD mencionan la instrumentación: ni `/metrics`, ni `PipelineTrace`, ni los `rt_*` | No aplica | Agregarlo al SDD como instrumentación no funcional | **B**, y **no toca los flujos**: es material no funcional, no un paso del 6.3 ni un mensaje de la 7.2. La 7.2 se queda con los 23 pasos funcionales que tiene | No | **B** |
| **41** | El SRS tiene la §3 vacía con los subtítulos de una plantilla de juegos | No aplica | Llenarla en un futuro | Lo dice el owner: si no está llena no incumbe ahora | No | **Diferido** |
| **42** | El SRS dice "SignAI" 25 veces y "SignALL" ninguna | No aplica | Corregir. El compañero ya lo sabe | — | No | **El compañero** |
| **43** | La portada del SDD tiene `[PENDIENTE DE COMPLETAR]`, sobran párrafos de plantilla azul y el Historial de Cambios tiene una sola entrada, del 19/08/2026 | No aplica | Limpiar antes de la entrega | El compañero ya lo sabe | No | **El compañero** |

---

## 4. Análisis: cuánto de esto toca los diagramas

Esta es la pregunta que el owner hizo, y la respuesta es buena.

### 4.1 Verificación de las doce fuentes

Se leyó el XML de los doce `.drawio` de `../sign-ai-docs/diagramas/` y se comparó cada
caja con el código.

| Diagrama | ¿Está al día? | Qué dice | Qué hay que tocar |
|---|---|---|---|
| 6.1 Vista lógica | **Sí** | `TranslateStream`, `Split`/`TransformSentence`, `Validate(segments)`, sin Static GLB | Solo subir la PNG |
| 6.2 Vista física | **Sí** | `OpenAI (gpt-4o-mini)`, `«WebSocket» /ws/transcribe`, `«PostgreSQL protocol (TLS)»`, `«HTTPS»`, sin Static GLB, sin nodo de red | Solo subir la PNG |
| 6.3 Procesos | **Sí** | `Silencio de 1.5s detectado?` → `Divide el texto final en oraciones` → `Para cada oración, en paralelo` → `Envía la oración al Android Client (en orden)` → `Envía aviso de fin` | Solo subir la PNG |
| 7.1-1 Orquestación | **Sí** | `sendTranscript`, `sendSegment(index, total, segment)`, `sendError`, `translate` **y** `translateStream`, `split`, `transformSentence`, `SttServiceClientImpl` | Solo subir la PNG |
| 7.1-2 NLP | **Sí** | Las **cuatro** clases: `GlossAnalyzer`, **`EmbeddingModel`**, **`SentenceSegmenter`**, `SemanticCache`, `LLMClient`, `buildSegment`, y `lookup`/`store` con `List<String>` | Solo subir la PNG |
| 7.1-3 Validación | **Sí** | `CatalogRepository` con `cache: Map<String, CatalogEntry>`, `Gloss(text, available, glbPath)` | Solo subir la PNG |
| 7.2 Secuencia | **Sí** | 23 pasos: `split` → `segment` → `transformSentence` → `analyze` → `lookup` → `store` *(asíncrono, no se espera respuesta)* → `validate` → `(index, total, ValidatedSegment)` → `segment` → `done`, con los fragmentos `par [para cada oración]` y `loop [en el orden de las oraciones]` | Solo subir la PNG |
| 7.3 Persistencia | **Sí** | `catalog` con las 5 columnas, incluida `semantic_category`; `semantic_cache` con las 8, incluido `embedding : VECTOR(384)` | Solo subir la PNG |
| **7.4 Estados UI** | **NO** | Seis estados. Falta *Texto listo*. Y la salida de *Error* rotulada "automático, **≤2s**" | **Editar el `.drawio`**: un nodo y tres flechas, y quitar el "≤2s" (mismo archivo, mismo trabajo) |
| C4-1 Contexto | **Sí** | Solo la API LLM como sistema externo, arista `[Android, WSS]` | Solo subir la PNG |
| **C4-2 Contenedores** | **Casi** | Correcto, salvo que el Android Client dice "renderiza el avatar 3D con **Filament**" | **Editar el `.drawio`**: cambiar una palabra |
| C4-3 Componentes | **Sí** | `translateStream(text)`, `split(text) / transformSentence(sentence)`, `validate(segments)`, `search(gloss)` | Solo subir la PNG |

### 4.2 El número

| | Cuántos |
|---|---|
| Diagramas que hay que **subir** sin tocar | **10 de 12** |
| Diagramas que hay que **editar** | **2 de 12** (el 7.4 y el C4-2) |
| Del 7.4 | Un nodo nuevo y tres flechas, que es el cambio más grande de todo el documento |
| Del C4-2 | Una palabra: "Filament" → Three.js |
| Diagramas que agregarían **por una decisión de fondo** | 3 si se pone el proxy inverso (§7.2) · 1 si se implementa la cola (§7) |

**De los 43 puntos de la tabla, 39 no tocan ningún diagrama.** Los cuatro que lo hacen son
el 13, el 14 y el 15 (que son el mismo archivo y una palabra) y, opcionalmente, el 39 si
se quiere dibujar la arista del `error`.

### 4.3 El orden que no rompe nada

| Paso | Qué | Por qué en ese orden |
|---|---|---|
| 1 | Copiar las 12 PNG de `sign-ai-docs/diagramas/png/` a Overleaf `images/` | Es lo que arregla de golpe los puntos 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 22 y parte del 1. **Sin tocar un solo `.drawio`** |
| 2 | Editar el C4-2: "Filament" → Three.js. Regenerar su PNG y volver a subirla | Una palabra |
| 3 | Editar el 7.4: agregar *Texto listo* y quitar el "≤2s". Regenerar y subir | El único desenho nuevo |
| 4 | Recién entonces corregir el texto del SDD | Para que el texto describa las imágenes que ya están bien |

Ese orden importa: si se empieza por el texto, se van a cambiar veinte frases del SDD y
luego aparecerán las imágenes y habrá que revisarlo todo otra vez. Al revés, primero las
imágenes y después el texto dice exactamente qué cambiar.

---

## 5. Los dos puntos que quedaron abiertos

### 5.1 El punto 23 — límite de solicitudes por cliente (RNF-SEC-01)

**Qué pide.** v0.15 RNF-SEC-01: que el backend limite el número de solicitudes de
traducción y de conexiones WebSocket de un mismo cliente "en un intervalo corto de
tiempo, rechazando o retrasando el excedente". Razón que da el requisito: *evitar que un
uso indebido o automatizado agote el saldo del proveedor del LLM, que se cobra por uso*.

**Qué pasa hoy.** No hay límite de nada. `app/controller/router.py:169` acepta toda
conexión. No hay tope de llamadas al modelo ni de gasto.

**Por qué no es trivial.** El propio requisito dice que *"el mecanismo de identificación
del cliente y el valor exacto del límite quedan pendientes de la definición de sesión
(DEC-20)"*. Y DEC-20 no está cerrada. Sin eso, "un mismo cliente" no está definido:
¿la IP? ¿el token de la sesión? ¿algo que mande la app?

**Lo que sí está a mano, sin DEC-20:**

| Salida | Qué es | Costo |
|---|---|---|
| **B1 — Quitar o bajar el requisito** y anotarlo como trabajo futuro | Una línea en `modificaciones/requerimientos.md` | Cero código. Y es coherente con lo que el SRS ya dice: la app es el único cliente, no hay registro de usuarios y el prototipo no se expone a internet |
| **B2 — Dejarlo como está y que la ronda de pruebas lo reporte** | Una fila en la lista de faltantes | Cero código. El requisito queda incumplido y anotado |

**Lo que NO recomiendo** es implementarlo ahora: sin DEC-20 se inventaría una noción de
"cliente" que después va a ser difícil de defender en la tesis, y el SRS ya dice que no hay
administración de usuarios.

### 5.2 El punto 26 — concurrencia y cola de sesiones (RNF-REL-01, RNF-DES-04)

**Qué piden.** RNF-REL-01: que el backend *"encole el excedente de sesiones cuando se
supere un número máximo de conexiones simultáneas"*, y su criterio dice *"las solicitudes
adicionales se encolan **sin pérdida de datos de audio** ni caída del servicio"*.
RNF-DES-04: que sostenga *"un número mínimo estimado de sesiones activas al mismo tiempo,
sin afectar la latencia de cada una"*.

**Qué pasa hoy.** No hay cola ni tope. El único cerrojo, `_PhraseTranslator`
(`router.py:56-94`), es **por sesión**: serializa las frases de *un* cliente para que el
`index` de las oraciones no se revierta. No dice nada de varios clientes.

**Por qué choca con lo demás.** El plan de pruebas ya resolvió esto en su parte:
`plan-pruebas/00-bases/alcance.md` §2.1 dice que **la escalabilidad a muchos usuarios está
fuera de alcance** y que *"solo se mide el comportamiento con dos o tres sesiones
simultáneas"*. Y `modificaciones/requerimientos.md` punto 13 ya propone: *"Bajar el
alcance a dos o tres sesiones simultáneas. Quitar la exigencia de cola sin pérdida de
audio, o bajarla de prioridad."*

| Salida | Qué es | Costo |
|---|---|---|
| **B — Aplicar el punto 13** | Dos cambios de texto en los requisitos: bajar el alcance a 2-3 sesiones y quitar la exigencia de cola sin pérdida | Cero código. Deja el requisito diciendo lo que el plan de pruebas ya asume |
| **A — Implementar la cola** | Una cola de sesiones en el backend, con su número máximo | Código nuevo **y un nodo nuevo en el 6.3**, que es el único punto de la tabla que rompería un diagrama de flujo |

**Recomiendo B**, por una razón que no es de esfuerzo: la exigencia de "sin pérdida de
audio" **no se puede cumplir con el diseño actual y no por falta de código**. El audio
llega al backend, se reenvía al STT y el STT decide; si una sesión espera en una cola del
backend, el audio ya se perdió. Poner la cola en el STT sería otro requisito entero. Es
decir: el requisito, tal como está escrito, describe una arquitectura que no es la del
proyecto.

---

## 6. Las cuatro decisiones de fondo

Cuatro temas que no se responden leyendo el código. Los tres primeros **dependen de una
decisión del owner**; el cuarto ya está cerrado.

### 6.1 El modelo de lenguaje — CERRADO

> **Decisión del owner (2026-10-18): el modelo oficial es `gpt-4o-mini` de OpenAI.**
> `qwen3:4b-instruct` queda para pruebas rápidas y uso local.
>
> **Y también cerrado:** antes de la ronda con el modelo oficial **se vacía
> `semantic_cache`**, porque las glosas guardadas con Qwen tienen un estilo distinto del que
> habría dado `gpt-4o-mini` y la remedición no debe mezclar las dos. Es caché derivada: se
> reconstruye sola con la primera frase de cada entrada.
>
> **Y también cerrado:** las métricas **no** llevan autenticación. Es un prototipo y son
> del equipo. Lo único que se hace es enmascarar `llm_base_url` y `stt_ws_url` en
> `/metrics.json`, porque son las dos direcciones internas del servidor.

| Dónde | Qué |
|---|---|
| `.env` | `LLM_MODEL` vuelve a `gpt-4o-mini` y `LLM_BASE_URL` a vacío (vacío = OpenAI). Lo local se mueve a un `.env.local` que no está en git |
| SRS `main.tex:1077-1080` | Ya dice `gpt-4o-mini` y OpenAI. **No hay que tocarlo**. La imagen 6.2 también lo dice |
| v0.15 RF-INT-SW-02 | Pide un proveedor externo. **Se cumple** |
| `docs/CAMBIOSBACKEND.md` §"Pendiente" 1 | "Falta remedir `rt_first_sign_ms` con el LLM de producción". La decisión lo destraba, pero la remedición sigue pendiente |
| Línea base | Los **273 ms p50 / 422 ms p95** son de Qwen local. **Dejan de ser la línea base de la tesis** |

### 6.2 El catálogo: ¿reiniciar el backend o recargar en caliente?

**Qué dice cada uno.** RNF-MNT-01 (v0.15 §6.4) pide que cambiar una seña se reconozca
"sin reiniciar el servicio". RNF-BD-03 (§7) pide que el catálogo se cargue en memoria al
arrancar para que la inferencia no consulte la base. El propio v0.15 lo reconoce al final:
*"RNF-MNT-01 exige que una seña nueva se reconozca sin reiniciar el servicio, lo cual está
en tensión con este RNF-BD-03… No se modifica RNF-MNT-01 hasta que el equipo lo
confirme"*. `modificaciones/requerimientos.md` punto 11 ya propone aceptar el reinicio.

**Qué hace el código.** `CatalogRepository.load_all()` corre **una vez**, en
`app/main.py:48`, y llena un diccionario (`catalog_repository.py:33-50`). `search()` solo
mira ese diccionario. `modified_at` no lo lee nadie.

| Opción | Qué se gana | Qué se pierde |
|---|---|---|
| **A — Aceptar el reinicio** (punto 10, opción B) | Cero código. RNF-BD-03 se cumple con holgura y su criterio es medible, que es el que sostiene RNF-DES-01. El reinicio con Docker es de segundos | Hay que reescribir RNF-MNT-01 y la frase del SDD §7.3. "Actualizar el catálogo" pasa a ser "actualizar y reiniciar" |
| **B — Recarga en caliente** (punto 10, opción A) | RNF-MNT-01 se cumple literal y se puede corregir una glosa sin cortar la demo | Código nuevo, y **rompe RNF-BD-03**: para saber que cambió hay que consultar la base. Y aparece una pregunta nueva: qué pasa si el catálogo cambia mientras una frase se traduce |

**Recomiendo A.** El SRS ya describe la realidad (`main.tex:1201-1204`: *"Las tareas
administrativas, como agregar o corregir señas del catálogo, las realiza el equipo de
desarrollo directamente sobre la base de datos"*). Y con un corpus cerrado de 50 señas
(RD-01) la recarga en caliente no le aporta nada: lo que cambia son las animaciones, que
van en el APK, no el catálogo.

**DECIDIDO — opción A (owner, 2026-10-18): se acepta el reinicio del backend.**

Se reescribe **RNF-MNT-01** para que diga que un cambio en el catálogo se reconoce **la
siguiente vez que se reinicia el backend, sin tocar código**. Y con eso se cierra también el
**punto 10** (la frase del SDD §7.3 que dice que `modified_at` "permite detectar cambios sin
reiniciar").

**La tensión que se cierra.** RNF-MNT-01 ("sin reiniciar el servicio") y RNF-BD-03 ("el
catálogo en memoria, cero consultas durante la inferencia") se contradecían, y el propio v0.15
lo reconocía: *"RNF-MNT-01 exige que una seña nueva se reconozca sin reiniciar el servicio, lo
cual está en tensión con este RNF-BD-03… No se modifica RNF-MNT-01 hasta que el equipo lo
confirme"*. Con esta decisión se elige RNF-BD-03 y se reescribe RNF-MNT-01. Se puede escribir
que es la misma tensión que el equipo ya había detectado como INC-08 en el Architecture
Backlog, y que queda registrada.

**Lo que se elige y por qué:**

| | |
|---|---|
| **RNF-BD-03 se queda como está** | Su criterio de aceptación es medible ("cero consultas durante la traducción") y es el que sostiene RNF-DES-01, que es el número de la tesis |
| **RNF-MNT-01 se reescribe** | Era una comodidad operativa, y con un corpus cerrado de 50 señas no aporta nada |
| **La recarga en caliente queda anotada** | Como trabajo futuro, con la razón de por qué no se hizo: would've roto RNF-BD-03, y habría abierto la pregunta de qué pasa si el catálogo cambia mientras una frase se traduce |

**Cero código. Cero diagramas.**

### 6.3 La espera máxima del modelo de lenguaje

**Qué es esto, en sencillo.** Cuando una frase no está en la caché, el backend le
pregunta al modelo por internet. Esa pregunta tiene dos defendas: un **tiempo máximo por
intento** (`llm_timeout_ms`, hoy 10 000 ms) y un **número de reintentos** cuando la
llamada falla.

Hoy el tiempo está escrito (`app/config/settings.py:32`). **El número de reintentos no
está escrito en ningún lado**: `app/nlp/llm_client.py:154-160` construye `ChatOpenAI` con
cinco argumentos y ninguno es ese. LangChain le pone su valor por defecto, que son 2
reintentos. O sea **tres intentos de 10 s**, unos **30 s** antes de que salga el frame
`error`. Eso es lo que `modificaciones/requerimientos.md` punto 23 ya registra.

**Por qué importa de verdad:** la app tiene un reloj de 15 s de silencio que el owner puso
el 2026-10-17 (SRS `main.tex:744`). Si el modelo tarda más de 15 s, **gana el reloj de la
app, no el backend**: la app pasa a *Error* y cierra el turno, y cuando el modelo conteste
el backend manda un `segment` y un `done` de una frase que ya se cerró. Ese `done`
huérfano es el problema de **6.5**.

| Opción | Qué se gana | Qué se pierde |
|---|---|---|
| **A — `max_retries=0`, `llm_timeout_ms=5000`** | El backend avisa en ≤5 s, muy por debajo del reloj de la app: **el `error` del backend llega siempre primero** y el turno se cierra limpio | Un corte de internet de un segundo se vuelve un error visible. En una demo, eso es un botón de reintentar |
| **B — `max_retries=1`, `llm_timeout_ms=5000`** | Un reintento cubre el corte momentáneo. El peor caso son ~10 s, **todavía por debajo de los 15 s** del reloj de la app | El usuario espera hasta 10 s en ver un error cuando el modelo está caído de verdad |
| **C — Dejarlo** (3 intentos, ≤30 s) | Máxima tolerancia a fallos transitorios | El error lo ve el usuario tarde y por el reloj de la app, no por el backend. El turno se cierra con un `done` huérfano. Contradice RNF-AV-03 por un orden de magnitud |

**Recomiendo B.** El criterio no es "el número más bajo posible", es **que el backend avise
antes que la app**. Con 5 s y un reintento el peor caso queda en ~10 s, con 5 s de margen.
Y con `gpt-4o-mini` la respuesta normal está en 1-3 s, así que un tope de 5 s no recorta
nada real.

**DECIDIDO — `llm_timeout_ms = 5000` y `max_retries = 1` (owner, 2026-10-18).**
Opción B. Son unas tres líneas: el número en `settings.py`, y `max_retries` en el constructor
de `ChatOpenAI` (`app/nlp/llm_client.py:154-160`) y en `Settings`.

**El número se mueve si se mueve el reloj de la app.** Si algún día el SRS cambia los 15 s
(`main.tex:744`), este tope tiene que quedar por debajo de ese número, siempre. Lo mismo
aplica a §6.4.

### 6.4 La base de datos: espera máxima y reintentos

**Qué hay hoy, en código.** `app/persistence/database.py:16-22` crea el pool con
`asyncpg.create_pool(...)` y **sin `command_timeout`**: no hay ningún tope en cuánto puede
tardar una consulta. Y sin `timeout` en `pool.acquire()`: si el pool se agota, la espera
tampoco tiene techo. Las tres llamadas que tocan la base son `_lookup_neon`
(`app/nlp/semantic_cache.py:248-274`), `store` (`:219-237`) y la carga del arranque.

**Qué hay hoy, en documentación.** v0.15 RNF-REL-03 pide reintentos con número acotado.
`modificaciones/requerimientos.md` punto 20: *"Hoy no hay reintentos. Decidir: implementar
uno o dos reintentos, o ajustar el requisito a 'error controlado sin reintentos'"*. Y hay
un detalle del arranque: `CatalogRepository.load_all()` (`app/main.py:48`) **no está
dentro de un `try`**, mientras que `SemanticCache.load_all()` sí lo está
(`app/nlp/semantic_cache.py:135-137`). Es decir: **si Neon no contesta al arrancar, el
backend no levanta.** La app ve *Desconectado* y reintenta cada ≤5 s, así que se recupera
sola cuando Neon vuelve, pero el proceso muere.

Y un dato del plan de pruebas: `plan-pruebas/01-diseno/cache-semantico/general.md` dice
*"la base de datos caída se prueba en resiliencia"*, y **no existe un bloque de
resiliencia**. Sin tope de espera esa prueba no se puede ni escribir.

| Opción | Qué se gana | Qué se pierde |
|---|---|---|
| **A — Timeout de 5 s + un reintento** (punto 27, opción A) | Cumple RNF-REL-03 literal. Peor caso ~10 s, por debajo de los 15 s del reloj de la app. Convierte la caída de la base en el caso de prueba que el plan ya promete | Algo más de código: un `try/except` con `asyncio.sleep` en las tres llamadas, y el `try/except` que falta en el arranque |
| **B — Timeout sin reintentos** (punto 27, opción B) | Poco código. Una consulta colgada **levanta** y se vuelve el frame `error` que la app ya sabe mostrar. El arranque deja de depender de que Neon esté vivo | RNF-REL-03 sigue sin cumplirse y hay que ajustarlo, que es lo que ofrece el punto 20 de `modificaciones` |
| **C — No tocar nada** | — | Un `lookup` colgado cuelga la frase **para siempre** y la app no tiene salida: su reloj la saca a *Error* a los 15 s pero el backend sigue esperando. Y si Neon está caído al arrancar, el proceso no levanta |

**Recomiendo A.** Por dos razones concretas. Una: con B hay que tocar el documento **y** el
código, y con A solo el código. Dos: el plan de pruebas promete probar la base caída y esa
prueba necesita un techo para poderse medir. El valor de 5 s sale de que es el mismo orden
del LLM y deja el peor caso por debajo del reloj de la app.

**Un detalle que ayuda:** el `store` corre en segundo plano y no bloquea la respuesta
(`app/nlp/nlp_service_impl.py:70-85`), así que un reintento ahí no cuesta latencia. El
tiempo crítico es solo el `lookup` y la carga del arranque.

**DECIDIDO — opción A (owner, 2026-10-18): `command_timeout = 5` segundos, un reintento con
espera breve, y el `try/except` alrededor de `catalog_repository.load_all()`.**

Se eligió A y no B por dos razones concretas:

1. **Con B hay que tocar el documento y el código; con A solo el código.** Y tocar el
   documento significa cambiar un requisito que el equipo ya escribió y aprobó
   (RNF-REL-03).
2. **El plan de pruebas ya promete una prueba que sin tope no se puede escribir**
   (`plan-pruebas/01-diseno/cache-semantico/general.md`: *"la base de datos caída se prueba en
   resiliencia"*, y no existe un bloque de resiliencia).

**El `try/except` del arranque se hace en cualquier caso**, porque no depende de esta decisión:
sin él, un mal momento de Neon mata el proceso del backend, y eso es cierto con o sin
reintentos. Es el arreglo con mejor relación entre esfuerzo y beneficio de todo §6.

### 6.5 El `done` no dice a qué frase pertenece

**Explicación, desde el principio.** Hoy el backend manda las oraciones de una frase
(`segment`) y al final un `done`. Cuando el usuario **cancela** una frase —apaga el
micrófono o el TR mientras espera la traducción— esa cancelación es **local, en el
teléfono**: el backend no tiene forma de enterarse. Sigue traduciendo, y cuando termina
manda el resto de las oraciones y su `done`.

La app ya lo sabe y lo maneja: descarta esas oraciones (`StaleTurn`, en
`../sign-ai-android/openspec/specs/ui/spec.md` `STA-25`). Lo que **no** puede hacer es
saber **a qué frase pertenece ese `done`**. El frame es `{"type": "done"}` y nada más.

El problema aparece cuando las dos cosas se cruzan. El usuario cancela la frase A, manda
la frase B, y el `done` de A llega cuando B ya está corriendo. La app lo traga, que es lo
correcto. Pero si el `done` de A se pierde, o llega antes de que B termine, el turno de B
se queda esperando un `done` que ya se fue, y **a los 15 s declara un fallo que no
ocurrió**. El usuario ve un error en una frase que sí se iba a representar.

La app nunca pone dos frases en vuelo (`MainScreenState.requestTranslation` y
`sendLivePhrase` rechazan). El cruce es exactamente el de cancelada + nueva.

| Opción | Qué se gana | Qué se pierde |
|---|---|---|
| **A — Un id de turno en `segment` y `done`** (punto 39) | La app descarta por id y no traga nada a ciegas. Es **aditivo**: un campo más, sin cambiar ninguna lógica del backend. Los dos lados se cambian en el mismo commit, y como el parser de la app es tolerante, un backend viejo no la rompe. **De paso resuelve el punto 39**: con id, el `error` también se sabe de qué turno es | Toca los dos repos en el mismo cambio. Hay que decidir quién pone el número: **tiene que ser el cliente**, porque la app necesita conocerlo para poder cancelar *antes* de que llegue el primer `segment`. O sea que el `text` que ya manda lleva un campo más |
| **B — Un frame `cancel` del cliente al backend** | Resuelve la raíz: el backend sabe que la frase ya no interesa y **deja de mandarla** | Toca el orquestador y suma un tipo de frame. Y tiene su propia carrera: si el `cancel` llega después de que el backend mandó el `done`, no sirve de nada |
| **C — Dejarlo** | Cero trabajo | La app mantiene el descarte a ciegas que ya tiene, y el fallo falso a los 15 s sigue ahí. El punto **39** también queda sin resolver por contrato |

**Recomiendo A.** Es la más barata y la que no depende de una carrera. Y el id lo pone el
cliente: `{"type":"text","text":"…","turn":7}`, y el backend lo copia al `segment` y al
`done`. Es la misma decisión que el punto **39**, porque el `done` que falta cuando hay
error tiene el mismo problema: sin id, la app no sabe si el turno que cerró con error era
el suyo.

**DECIDIDO — opción A (owner, 2026-10-18).** El identificador lo pone **el cliente** y el
backend lo copia **sin interpretarlo**. Se hace **junto con el punto 39** (mandar el `done`
también cuando hay `error`).

**Lo que toca, en el backend** (unas ocho líneas, y nada del orquestador: el identificador es
asunto del protocolo, no del pipeline):

| Dónde | Qué |
|---|---|
| `router.py:22-53` (`_parse_client_frame`) | Leer el campo y devolverlo |
| `controller.py:124` (`handle_text`) | Guardarlo |
| `controller.py:205` (`send_segment`) | Añadirlo al `segment` |
| `controller.py:164` (el `done`) | Añadirlo |
| `controller.py:235` (`send_error`) | Añadirlo |

**Por qué el backend no puede ponerlo:** la app necesita conocer el identificador para poder
cancelar *antes* de que llegue la primera oración. Si lo pusiera el backend, la app lo sabría
demasiado tarde.

**Por qué es seguro:** el parser de la app es tolerante a propósito. Un backend viejo que no
mande el campo no la rompe, y un backend viejo tampoco se rompe si la app manda un campo de
más. Se puede hacer de un lado y del otro sin ventana de rompimiento, siempre que se terminen
los dos en el mismo trabajo lógico.

**Riesgo para los diagramas: ninguno.** La 7.2 ya tiene los pasos 22 (`segment`) y 23
(`done`). Agregar un campo a un mensaje no cambia el mensaje.

**La forma del identificador, y por qué "escalable" aquí quiere decir algo concreto.** La
escalabilidad de esto **no está en el formato**, está en **quién lo genera**. Como lo genera
el cliente y viaja dentro del frame, el backend funciona igual detrás de un balanceador o con
varias réplicas: no lleva cuenta de nada. Si lo generara el backend, con dos réplicas el
contador se reiniciaría en cada una y los identificadores chocarían.

Y hay una propiedad que conviene dejar escrita: **el backend trata el identificador como un
texto opaco**. No lo parsea, no lo compara, no lo genera. Manda lo que le llegue.

**DECIDIDO — la forma: opción 1, un entero que sube desde 1 por conexión** (owner,
2026-10-18), declarado en el contrato como texto opaco.

**Por qué la 1 y no la 2 (un texto único).** La 2 se justificaba por un supuesto: que un turno
pudiera sobrevivir a una reconexión y el contador, al reiniciarse, produjera dos turnos vivos
con el mismo número. **Ese supuesto no se sostiene, porque la arquitectura lo impide:**

| Qué tendría que pasar | Por qué no pasa |
|---|---|
| Un turno sobrevive a la caída de la conexión | El backend cierra la sesión y **cancela las traducciones en vuelo** (`router.py:220-229`, en el `finally`). El turno muere con la conexión |
| La app reconecta y quiere continuar ese turno | No hay turno que continuar: ya no existe en el servidor |

Una conexión es una sesión, y una sesión nunca cruza una reconexión. Con eso, la diferencia
entre las dos es de **34 caracteres de tamaño y ruido en los logs** (`turn: 3` se lee de un
visto; `turn: a3f9c2e1-4b7d-…` hay que buscarlo), y el cambio futuro de una a otra sería de
**una línea en la app y nada en el backend**, justamente porque es opaco.

**Consecuencia de que sea opaco, y hay que escribirla en el contrato:** como el backend no lo
mira, **no puede validar que venga bien**. Si la app manda un `text` sin identificador, el
backend lo acepta y devuelve los mensajes sin él, y la app cae al comportamiento de hoy
(tragarse el `done`). Para la transición eso es lo correcto, pero tiene que estar escrito.

---

## 7. El punto 34 — ¿hace falta un proxy inverso?

El owner dijo que la app y los diagramas hacen creer que sí. Se revisaron las tres cosas.

### 7.1 Qué dice la app

`../sign-ai-android/docs/CONTRASTE-APPvsDOCUMENTOS.md` §8 (punto A3) y el skill del
contrato: desde el 2026-10-17 la app tiene el cifrado como cosa del **build type**:

| Build | URL | Texto en claro |
|---|---|---|
| `debug` | `-Psignai.backendWsUrl=…`, o `ws://10.0.2.2:8080/ws/translate` | Permitido |
| `release` | **Solo `wss://`**. Una property que no sea `wss://` se ignora con aviso | **Prohibido** |

Y el default de release quedó en `wss://backend.invalid/ws/translate`, porque **no hay
dominio** y esa fue una decisión del owner (2026-10-17): es un prototipo y no se va a
tener. O sea: **la app está lista para WSS, y el servidor todavía no está.**

### 7.2 Qué dicen los diagramas

**Ninguno de los doce tiene un nodo de proxy.** El `«WSS»` aparece **en las flechas**, no
en una caja:

| Diagrama | Dónde aparece el WSS |
|---|---|
| 6.2 Vista física | La flecha entre *Android Device* y *Demo / Dev Host* dice `«WSS» translation session (audio + results)` |
| C4-1 Contexto | La arista del oyente dice `Activa el microfono y habla  [Android, WSS]` |
| C4-2 Contenedores | La arista dice `Envia audio, recibe resultado [WSS]` |
| 6.1, C4-3 | `«interface» Translation Session (WebSocket)` y `[WSS]` |

Los otros tres enlaces ya son cifrados de verdad y no están en discusión: `«HTTPS»` hacia
OpenAI, `«PostgreSQL protocol (TLS)»` hacia Neon, y `«WebSocket» /ws/transcribe` entre los
dos contenedores de la misma máquina, que no sale del equipo.

**Conclusión: los diagramas no piden un proxy.** Piden que el canal se llame WSS, y eso es
una etiqueta, no una pieza. Lo que falta es quién termina el TLS.

### 7.3 Las dos salidas y lo que toca cada una

| | **B — Documentar** (lo termina el despliegue) | **A — Proxy inverso** (pieza en el diseño) |
|---|---|---|
| Qué dice el documento | "El backend sirve HTTP en claro; en un despliegue real, un proxy inverso delante termina TLS. El cliente ve `wss://`." | "Hay un proxy inverso delante del backend que termina TLS" |
| **Diagramas que hay que editar** | **Ninguno.** Las etiquetas `«WSS»` siguen siendo ciertas | **Tres: 6.2, C4-2 y C4-1.** Hay que agregar una caja y mover la flecha |
| Código | Ninguno | Una pieza más en el despliegue, más su configuración |
| Qué pasa si nadie lo despliega nunca | El SRS queda diciendo WSS y la realidad es `ws://`. **Es laínea que hoy está torcida** | El diagrama queda fiel y la pieza no existe |
| Qué lo hace defendible en la tesis | Depende de que el texto sea honesto: decir quién termina el TLS y que el prototipo corre sin él | Un nodo más en tres diagramas y una pieza que en la práctica nadie va a instalar |

**Lo que recomiendo: B**, y por una razón que no es de esfuerzo sino de coherencia. El
punto de este proyecto es que el despliegue es un equipo personal del equipo de
desarrollo (`main.tex:938-939`, RNF-DES-01 depende de eso). Un TLS terminado por el
despliegue es exactamente lo que pasa en ese escenario: el que despliega pone el proxy.
Documentarlo dice la verdad sin agregar una pieza que nadie va a instalar.

**Si el owner prefiere que el proxy esté en el diseño** (y es defendible: deja el SRS
cierto sin depender de un despliegue que no existe), el costo real es **editar tres
diagramas y agregar una caja**, y se puede hacer en el mismo lote que el 7.4 y el C4-2. Lo
que hay que tener presente es que **es el único punto de toda la lista que rompe el orden
"primero subo las imágenes, después toco el texto"**, porque obliga a redibujar antes de
empezar.

---

## 8. Lo que este documento absorbió

La versión anterior (2026-10-17) tenía 2 hallazgos y 8 semillas de auditoría. Ninguna se
pierde:

| Antes | Ahora |
|---|---|
| **Hallazgo 1** — la base no tiene tiempo máximo y el LLM sí | **6.4** (el arranque sin red de seguridad, el camino de reserva sin techo y el valor) y **6.3** para el LLM |
| **Hallazgo 2** — el `done` no identifica la frase | **6.5**, y el punto **39** |
| Semilla 1 · ¿el `error` siempre llega? | **39** y **6.3**: los dos caminos existen y los dos están mal cerrando el turno |
| Semilla 2 · ¿el `done` va después del último `segment`? | **39**: va después, salvo cuando algo falla |
| Semilla 3 · nombres de métrica contra `SignAiMetrics` | **37**, con los dos casos en §2.4. Los nombres coinciden en los dos lados; lo que no coincide es lo que el nombre **promete** |
| Semilla 4 · RNF-DES-01 (latencia con caché / con LLM) | **37**. `llm_ms{model}` y `cache_lookup_ms` ya están instrumentados, así que la base está; falta poder separar los dos escenarios en `rt_first_sign_ms` |
| Semilla 5 · columnas del catálogo contra `SignsCatalog.kt` | **11**, **12**, **36**. La migración `003` ya dejó las nueve columnas alineadas |
| Semilla 6 · RF-INT-COM-01, "detectará una desconexión" | Fuera de este repo: el latido es del cliente. En el backend queda **34**, con el análisis en §7 |
| Semilla 7 · protocolo del STT y `silence_timeout_ms` | Resuelto: el STT lo expone en su `/health` y el backend lo refleja en el suyo cada 30 s (`app/main.py:139-161`). Queda **21** |
| Semilla 8 · ¿puede `done` llegar sin ningún `segment`? | Con el segmentador, una frase no vacía siempre da al menos una oración. Queda el caso de un `segment` con `glosses: []`, que es **38** |

---

## 9. Resumen de las decisiones

### 9.1 Los once puntos revisados uno por uno — todos salieron B

El owner los revisó uno a uno el 2026-10-18: **2, 3, 5, 7, 23, 26, 33, 34, 36, 37 y 40**.
**Los once salieron "se adapta el documento".** Ninguno requirió cambiar el backend.

Eso es un resultado en sí mismo: **el código está más al día que los documentos.** Once de
once.

| Punto | Decisión | Diagrama que toca |
|---|---|---|
| **2** `sendResult(segments)` | B | Ninguno. El 6.1 de `sign-ai-docs` ya está bien |
| **3** `translate` contra `translateStream` | B | Ninguno. Los tres diagramas que lo nombran ya están bien |
| **5** `SentenceSegmenter` y `EmbeddingModel` | B | Ninguno. La Figura 5 ya tiene las dos clases |
| **4** `transform` contra `split` y `transform_sentence` | B | Ninguno. La Figura 5 ya muestra los tres métodos |
| **7** el `store` en segundo plano | B | Ninguno. El paso 14 de la 7.2 ya lo dice |
| **23** límite de solicitudes por cliente | B, con medición | Ninguno |
| **26** concurrencia y cola de sesiones | B, con la justificación escrita | Ninguno |
| **33** `network_mode: host` y RNF-POR-02 | B | Ninguno |
| **34** TLS, WSS y el proxy inverso | B, con 🔶 TODO | Ninguno |
| **36** "Seña no disponible" | B, con 🔶 TODO | Ninguno. Las dos ramas del 6.3 siguen siendo ciertas |
| **37** el nombre `rt_first_sign_ms` | B, con los dos tramos en el SRS | Ninguno |
| **40** la instrumentación | B, en el SDD | Ninguno |

### 9.2 Los que el owner decidió en la primera pasada

| Puntos | Decisión |
|---|---|
| **1, 6, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 28, 29, 35** | **B** — se adapta el documento |
| **11, 24, 27, 30, 31, 32, 39** | **A** — se adapta el backend |
| **25, 38** | **A y B** |
| **41** | **Diferido.** Llenar la §3 del SRS en un futuro |
| **42, 43** | **El compañero** ya lo sabe |

### 9.3 Lo que queda sin decidir

| # | Qué | Dónde |
|---|---|---|
| **Punto 4** | `NLPService.transform` contra `split` y `transform_sentence`. Se le explicó que **B no toca ningún diagrama** y que la Figura 5 y la 7.2 de `sign-ai-docs` ya están correctas, pero el owner no llegó a responder | §3.1, fila 4 |
| **§6.2** | Catálogo: ¿reinicio o recarga en caliente? Recomendando **A** (aceptar el reinicio) | §6.2 |
| **§6.3** | Espera máxima del modelo. Recomendando **B** (`max_retries=1`, `llm_timeout_ms=5000`) | §6.3 |
| **§6.4** | Espera máxima y reintentos de la base. Recomendando **A** (timeout de 5 s + un reintento) | §6.4 |
| **§6.5** | Id de turno en `segment` y `done`. Recomendando **A** (lo pone el cliente) | §6.5 |

Los cuatro de §6 **sí cambian el backend**, al revés de los once de §9.1 y el punto 4.

### 9.3 bis Estado a cierre de la revisión — 2026-10-18

**No queda ninguna decisión pendiente del owner.** Las cinco se resolvieron:

| # | Qué es | Decisión |
|---|---|---|
| **§6.2** | Catálogo: ¿reinicio o recarga en caliente? | **A** — aceptar el reinicio. Se reescribe RNF-MNT-01 |
| **§6.3** | Espera máxima del modelo | **B** — `llm_timeout_ms = 5000`, `max_retries = 1` |
| **§6.4** | Espera máxima y reintentos de la base | **A** — `command_timeout = 5 s`, un reintento, más el `try/except` del arranque |
| **§6.5** | Identificador de turno | **A** — lo pone el cliente, entero que sube desde 1 por conexión, tratado como texto opaco. Se hace junto con el punto 39 |
| **Punto 4** | `transform` contra `split` y `transform_sentence` | **B** |

**Los cuatro de §6 cambian el backend.** Los doce puntos de §9.1 no cambian nada: todos fueron
correcciones de documento.

**Los cuatro números de §6 están atados al reloj de 15 segundos de la app** (SRS
`main.tex:744`). Si ese número cambia en el SRS, los tres tiempos máximos tienen que bajar con
él:

| Decisión | Valor | Peor caso | Margen con los 15 s |
|---|---|---|---|
| §6.3 modelo | 5 s por intento, 1 reintento | ~10 s | 5 s |
| §6.4 base | 5 s por consulta, 1 reintento | ~10 s | 5 s |

**Una verificación que no es una decisión:** comprobar si la versión de Docker Desktop instalada
en el equipo tiene activada la opción de redes de host (ver el punto 33). No se midió.

**Punto 4, ya decidido el 2026-10-18: B.** Es el punto más barato de la lista: una frase en el
SDD, porque los dos diagramas que lo nombran ya están correctos. Lo que no se puede es A:
borrar `transform()` rompe `scripts/verify_nlp_service.py:34` y `:43`, y **no hay razón de
fondo**, porque la Figura 5 del propio `sign-ai-docs` ya muestra los tres métodos. Mientras se
escribe, conviene decir **por qué se segmenta antes de calcular la huella y no después**: es
la diferencia entre que "Me llamo Ana. ¿Cómo estás?" salga con un tipo de frase o con dos.

### 9.4 Cerrados

| Tema | Decisión | Fecha |
|---|---|---|
| Modelo de lenguaje oficial | `gpt-4o-mini` de OpenAI. Qwen queda para pruebas rápidas y uso local | 2026-10-18 |
| Caché antes de remedir | Vaciar `semantic_cache` | 2026-10-18 |
| Autenticación de las métricas | No. Se enmascaran `llm_base_url` y `stt_ws_url` | 2026-10-18 |
| Cómo se anotan los pendientes | Los 🔶 se escriben **en los documentos de Overleaf**, en el texto. El owner lo dijo así: es un documento en construcción y las anotaciones son para revisitarlas con el equipo | 2026-10-18 |

---

## 10. Dónde sigue cada cosa

| Si el trabajo toca… | Cargá |
|---|---|
| Un frame del WebSocket o un nombre de métrica | `../sign-ai-android/.opencode/skills/contrato-websocket/SKILL.md` — el contrato se lee en los dos lados antes de cambiarlo |
| Un nombre de clase o método que el SDD define | `.claude/skills/signai-sdd-conformance/SKILL.md` |
| El contrato completo con la app | `docs/android-integration.md` §3.1 y §4 |
| Qué se decidió ya entre el código y los documentos del backend | `docs/sdd-changes.md` |
| Qué cambió en el flujo por oraciones | `docs/CAMBIOSBACKEND.md` |
| Latencias y efecto de cada optimización | `docs/performance.md` |
| Los requisitos del proyecto y sus cambios pendientes | `../sign-ai-docs/documentos/requerimientos/` y `../sign-ai-docs/modificaciones/requerimientos.md` |
| El diseño del proyecto | `docs/sdd.md` (**desactualizado**, ver §1) y el SDD de Overleaf (**más desactualizado todavía**) |
| Los diagramas | `../sign-ai-docs/diagramas/draw.io` es la fuente, y es la buena. Los `.png` de `docs/diagrams/` de este repo y los de Overleaf son el juego viejo (§1.2) |