# Contraste Backend ↔ Documentos

**Fecha del contraste:** 2026-10-18 · **Backend:** `sign-ai-backend`, rama `flujo-oraciones`,
commit `4b8b9b8` (sin mergear).

**Última actualización: 2026-10-26**, cuando el punto 33 se cerró: la red de compose pasó a
ser el default y `network_mode: host` quedó como override en `docker-compose.host.yml`.
Antes, **2026-10-21**: relectura de las cuatro fuentes enteras y corrección de los números
que no cuadraban. Este documento nació como el contraste; ahora es
también el registro de lo que se hizo. **Lo que se hizo y lo que falta está en
[§10](#10-estado-de-la-ejecución--del-2026-10-19-al-2026-10-21).**

> **Revisión de cierre, 2026-10-21.** Al terminar la sesión se volvió a leer este documento
> entero y se corrigieron **nueve citas por número de línea** que apuntaban a otra cosa (las
> del prompt, las del `requirements.txt`, las de la migración del catálogo y dos del v0.16),
> y se reverificaron con script los números de §10.1. El detalle está en §10.6.
> **Lo que falta de los documentos está en [§10.2](#102-lo-que-falta); lo que falta de
> código, en [§10.3](#103-los-cambios-de-código-que-faltan).**

> **Este es el documento único de contraste.** Reemplaza a los dos que lo precedieron:
> `../sign-ai-docs/auditoria-flujo-2026-10-15.md` (el primer contraste, del 15 de
> octubre) y `../sign-ai-docs/modificaciones/texto-overleaf-pendiente.md` (el archivo de
> textos para pegar en Overleaf, que ya no sirve: todo lo que tenía se pegó).
> Los dos se borraron el 2026-10-21.

**Fuentes leídas, enteras. La columna "Sello" dice con qué versión se leyó cada una:**

| Fuente | Qué se leyó | Sello | Cuándo |
|---|---|---|---|
| **El código** | `app/` completo, `scripts/verify_*.py`, `tools/`, migraciones, `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `.env` | `flujo-oraciones` @ `4b8b9b8` | 2026-10-21 |
| **Los documentos del proyecto** | `../sign-ai-docs`: Requerimientos (**750 líneas**, v0.16), `modificaciones/requerimientos.md` (**45 filas**), `plan-pruebas/00-bases/` (3) y `plan-pruebas/01-diseno/*/general.md` (6), y los **12 `.drawio` con sus PNG** | `docs-contraste-2026-10-19` @ `18457be`, con 9 archivos modificados sin commitear | 2026-10-21 |
| **Overleaf — SDD** | proyecto `6a85c9a632974414503d9b82`, `main.tex`, **550 líneas**, más las **12 PNG de `images/`** | **v212** | 2026-10-21 |
| **Overleaf — SRS** | proyecto `6a122a19bb9a5dd9d390ba3d`, `main.tex`, **1495 líneas** | **v524**, editado el **2026-10-21 04:05** | 2026-10-21 |
| **La app** | `.opencode/skills/contrato-websocket/SKILL.md`, **solo lectura** | `flujo-oraciones` @ `dee9241` | 2026-10-21 |

> El contraste de la app (`../sign-ai-android/docs/CONTRASTE-APPvsDOCUMENTOS.md`) es un
> documento **de otro repo** y no se lleva desde acá. Lo único que se lee de ese repo es
> el contrato del WebSocket, que es lo que este repo implementa.
>
> **Overleaf es de solo lectura.** Si un `.tex` está mal, lo corrige el owner.

---

## ⚠ Orden de trabajo de la sesión siguiente — **ejecutado**

Este documento es el registro de las decisiones. **La sesión siguiente es la de ejecutar.**
Y lo primero que se hace es la **documentación y los diagramas**, en los dos sitios donde
viven:

| # | Qué | Dónde | Cómo terminó |
|---|---|---|---|
| 1 | **Copiar las 12 imágenes** del juego viejo al juego nuevo. No es redibujar: es subir el archivo que ya existe | De `../sign-ai-docs/diagramas/png/` a `images/` del SDD en Overleaf, y a `docs/diagrams/` de este repo | **Hecho.** Los tres juegos son el mismo archivo: verificado byte a byte el 2026-10-21 (§10.1) |
| 2 | **Editar el C4-2**: cambiar "Filament" por Three.js. Regenerar su PNG y volver a subirla | `../sign-ai-docs/diagramas/draw.io/sdd-c4-2-contenedores.drawio` | **Hecho.** Editado y con su PNG nueva |
| 3 | **Editar el 7.4**: agregar el estado *Texto listo* con sus tres transiciones, y quitar el "≤2s" de la salida de *Error*. Regenerar su PNG y volver a subirla | `../sign-ai-docs/diagramas/draw.io/sdd-7.4-diagrama-estados-ui.drawio` | **Hecho.** Editado y con su PNG nueva |
| 4 | **Solo después**, corregir el texto del SDD §6.1, §6.2, §6.3, §7.1, §7.2 y §7.3 | SDD de Overleaf y `docs/sdd.md` de este repo | **Hecho.** Los 17 lugares del SDD de Overleaf y 11 secciones de `docs/sdd.md` (que son 32 bloques de párrafo) |

El orden importa: si se empieza por el texto se cambian veinte frases y después aparecen
las imágenes y hay que revisarlo todo otra vez. Al revés, primero las imágenes y después
el texto dice exactamente qué cambiar.

Los tres pasos de arriba dejan resueltos, de un solo movimiento, los puntos **1, 2, 3, 5,
6, 7, 8, 9, 10, 11, 12, 22** y parte del **33** de §3. Los puntos **23** y **26**van a
trabajo futuro, y el **34** depende de la decisión del proxy.

**Nunca se commitea nada sin que el owner lo pida**, y Overleaf no se escribe desde acá.

> Se editó además el **7.1-1** (el diagrama de clases de la orquestación), que no estaba en
> la lista de arriba pero quedó desalineado al cambiar el texto del SDD.

---

## 📌 Convención: cómo se marca un punto abierto

Decidido el 2026-10-19. **Todo lo que escribamos y quede abierto se marca en el
propio texto del documento con `(TODO: ...)`**, para poder buscarlo de un tirón y
no dejar nada colgado:

```
(TODO: definir e implementar la política de retención del texto de la caché.)
```

Aplica a los tres documentos: el **SRS** y el **SDD** de Overleaf, y el
**Requerimientos Consolidados v0.16** de `../sign-ai-docs`. La marca es la misma
en los tres, y el texto del documento **no se deforma para dejarla**: el
requerimiento sigue diciendo lo que dice, y la coletilla va al final, entre
paréntesis.

Tres reglas para que la marca sirva de algo:

1. **Una sola sintaxis.** `(TODO: ...)`. El `[PENDIENTE: ...]` que ya existía en el
   SRS (§2.1.6, el tamaño del APK) se convierte a la misma forma.
2. **Un TODO marca un punto abierto de este documento o de la implementación.** Una
   referencia a una tarea externa (TSK-03, DEC-20, ADR-011) **sigue siendo
   referencia** y no se convierte en TODO: no está abierto en este documento.
3. **Una pasada de cierre antes de entregar la tesis.** Cada TODO se cierra o se
   mueve a *trabajo futuro*. Mientras queden, el documento es un borrador, y el
   v0.16 ya se declara como tal ("Estado: Borrador (primera versión completa,
   pendiente de validación)").

**No se usa esta marca para dos cosas distintas.** Hay que separar:

| Qué es | Cómo se marca | Ejemplo |
|---|---|---|
| Una **decisión que no está tomada** | En el texto, como provisional, según la convención del §1.1 del v0.16 | "El criterio de similitud queda pendiente de diseño" |
| Una **brecha entre lo especificado y lo construido** | `(TODO: ...)`, y el trabajo futuro lo recoge la *Memoria* | "el texto se escribe en los registros del servidor (TODO: dejar de escribirlo)" |

Las dos se confunden fácil, y por eso quedan separadas. El registro
`modificaciones/requerimientos.md` sigue siendo el sitio donde está el *estado* de
cada cambio (Propuesto / Acordado / Hecho); la marca `(TODO: ...)` va en el texto
del documento, y el registro la refleja.

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

> **Este resumen es la foto del 18/10.** Los dos puntos abiertos y los cuatro temas de §6
> se resolvieron esa misma tarde (§9.3 bis), y las correcciones se ejecutaron los días 19,
> 20 y 21. **Para saber qué está hecho y qué falta, el sitio es §10**, no este resumen.

Una nota que atraviesa todo el documento: **la línea base publicada de `rt_first_sign_ms`
(913 ms p50 / 1336 ms p95) es del camino por palabras y con oraciones no es comparable.**
La del flujo por oraciones es **p50 273 ms / p95 422 ms**, medida el **2026-10-15** con
`qwen3:4b-instruct` en Ollama local y la caché semántica vacía. Ninguna de las dos es la
de la tesis.

---

## 1. Cuál está desactualizado, y cómo se sabe

El owner preguntó esto primero, así que va primero.

> **Este veredicto es el del 2026-10-18.** Las correcciones se aplicaron los días 19, 20 y
> 21 de octubre: lo que se hizo y lo que falta está en **§10**. El estado de §10 se
> reverificó entero el 2026-10-21, leyendo los archivos y no de memoria.

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
| **`../sign-ai-docs/documentos/requerimientos` v0.16** | **Es la fuente de los RF/RNF**; su lista de cambios pendientes ya recoge varios de estos ítems | 11 de agosto de 2026 |

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

> **Esta tabla es la foto del 2026-10-18 y ya no describe el estado.** El 7.4 de Overleaf
> tenía `932e5740` y hoy tiene `474f6e0b`, que es el nuevo: el estado *Texto listo* ya está
> en la imagen de Overleaf. Lo mismo pasó con las otras once. **Los tres juegos de PNG son
> hoy el mismo archivo**, verificado byte a byte el 2026-10-21 (§10.1). La columna de
> Overleaf y la de este repo dicen "= igual" porque las dos eran el juego viejo; ahora las
> tres son iguales al nuevo.

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

**Punto 33 — RNF-POR-02 y `network_mode: host`: A desde el 2026-10-26.**

> **Corrección doble, y la segunda es la que importa.** Una primera versión de este análisis
> decía que `network_mode: host` "no es confiable en Windows y macOS": **eso era incorrecto**,
> las versiones recientes de Docker Desktop lo soportan. Pero la conclusión a la que se llegó
> después —dejarlo como default y documentar la restricción— **tampoco era la correcta**: el
> owner hizo notar el 2026-10-26 que el propio RNF-POR-02 ya preveía quitar el modo host, y que
> la portabilidad es un criterio del requisito, no un detalle a documentar. El código se alineó
> con el documento y no al revés. Las dos correcciones quedan registradas porque el error de
> este punto es el mismo en los dos sentidos: suponer que la configuración de esta máquina es
> la configuración del proyecto.

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

**Lo que se hizo, el 2026-10-26.** La red de compose es el default y el modo host quedó como
override, en un archivo aparte, para quien use un modelo local:

| Archivo | Qué hace |
|---|---|
| `docker-compose.yml` | Backend en la red de compose, `ports: ["8080:8080"]` publicado, `extra_hosts: ["host.docker.internal:host-gateway"]` para llegar a un servidor de modelos del host, y el STT por nombre de servicio (`ws://stt:8000/ws/transcribe`), que ya era el default de `app/config/settings.py` y de `.env.example` |
| `docker-compose.host.yml` | Override: `network_mode: host`, con `ports` y `extra_hosts` anulados (`!reset`, porque son incompatibles con la red del host) y `STT_WS_URL` / `LLM_BASE_URL` apuntando a `127.0.0.1`, donde el nombre del servicio no resuelve |
| `.env.example` | El default del STT ahora resuelve; el bloque del LLM documenta las dos direcciones y el comando que levanta cada una |

**La medición que obligó al override, 2026-10-26.** En esta máquina (Linux, Docker 29.9.2,
`ufw` activo) un contenedor en el bridge por defecto **no alcanza el host**: `ufw` filtra el
tráfico del bridge hacia el host, así que `host.docker.internal:11434` y `172.17.0.1:11434`
dan timeout —y el 5672 publicado de otro contenedor también—, mientras que la salida a
internet del mismo contenedor funciona (`1.1.1.1:80` responde). Ollama escucha en `*:11434`,
o sea que el bind no era la causa, y por eso "que escuche en `0.0.0.0`" no alcanza: es lo que
el comentario viejo del compose ya decía. Consecuencia práctica: **en esta máquina el camino
diario es el override**; el default es el que se lleva a otra máquina.

**Lo que sigue sin resolverse solo en Windows y macOS** es el acceso al modelo local. Con la
red de compose, `host.docker.internal` es alcanzable en Docker Desktop sin tocar nada, así que
el default ya cubre ese caso; la solución que se había propuesto antes —Ollama como servicio
opcional con perfil `local`— **sigue sin aplicarse** y no es necesaria para cerrar el punto:
el requisito pide que el backend se despliegue como una unidad portable, y eso ahora se
cumple con el default. Queda como mejora opcional, para no duplicar el modelo de 2,5 GB en
una máquina que ya lo tiene en el host.

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

**Qué era.** Docker normalmente mete cada contenedor en su propia red privada, y se hablan
por nombre (`stt`, `backend`). Hasta el 2026-10-26 este repo **no hacía eso**:
`docker-compose.yml` ponía el backend directamente en la red de la máquina, con
`network_mode: host`.

**Qué se ganaba.** El backend alcanzaba cualquier cosa de la máquina del desarrollador sin
configurar nada: un Ollama en `127.0.0.1:11434`, una base local, el STT en el puerto
publicado `127.0.0.1:8000`. Es lo que permite trabajar sin internet con un modelo local.

**Qué se perdía.**

| Se perdía | Consecuencia concreta |
|---|---|
| Portabilidad | En Docker Desktop (macOS/Windows) el modo host necesita una opción que hay que prender y `127.0.0.1` deja de ser "esta máquina": apunta adentro de la máquina virtual |
| El nombre del servicio | `stt` no resuelve en la red del host, así que el default de `settings.py` y de `.env.example` era inútil y el `.env` tenía que pisarlo |
| Aislamiento | Dos proyectos en la misma máquina se pelean el puerto 8080 |

**Cómo está desde el 2026-10-26.** El default es la red de compose, con el 8080 publicado y
el STT por nombre de servicio; el modo host quedó en `docker-compose.host.yml` como override
para quien use un modelo local que el firewall no deje alcanzar. La medición y el detalle
están en el punto 33 de §2. Lo que se conserva del análisis: **la imagen 6.2 dibuja dos
contenedores sin decir qué red usan**, así que ninguna de las dos configuraciones choca con
el diagrama.

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
| **33** | RNF-POR-02 pide un contenedor portable. Hasta el 2026-10-26 `docker-compose.yml` usaba **`network_mode: host`**. Explicado en §2.3 | Hecho: red de compose por defecto, `8080` publicado, y el modo host en `docker-compose.host.yml` | Nada: el requisito ya pedía esto | **A.** La imagen 6.2 dibuja dos contenedores sin especificar la red, así que **no hay que tocar el diagrama** | No | **A**, cerrado el 2026-10-26 |
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

> **La columna "Qué hay que tocar" es el plan del 2026-10-18, y ya se ejecutó entero.** Los
> dos `.drawio` que había que editar (el 7.4 y el C4-2) están editados, más el 7.1-1 que
> se desalineó al cambiar el texto. Y las doce PNG ya están en los tres sitios. Lo que sigue
> es el análisis, no el estado: el estado está en §10.

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

**Qué pide.** v0.16 RNF-SEC-01: que el backend limite el número de solicitudes de
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
| v0.16 RF-INT-SW-02 | Pide un proveedor externo. **Se cumple** |
| `docs/CAMBIOSBACKEND.md` §"Pendiente" 1 | "Falta remedir `rt_first_sign_ms` con el LLM de producción". La decisión lo destraba, pero la remedición sigue pendiente |
| Línea base | Los **273 ms p50 / 422 ms p95** son de Qwen local. **Dejan de ser la línea base de la tesis** |

### 6.2 El catálogo: ¿reiniciar el backend o recargar en caliente?

**Qué dice cada uno.** RNF-MNT-01 (v0.16 §6.4) pide que cambiar una seña se reconozca
"sin reiniciar el servicio". RNF-BD-03 (§7) pide que el catálogo se cargue en memoria al
arrancar para que la inferencia no consulte la base. El propio v0.16 lo reconoce al final:
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
catálogo en memoria, cero consultas durante la inferencia") se contradecían, y el propio v0.16
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

**Qué hay hoy, en documentación.** v0.16 RNF-REL-03 pide reintentos con número acotado.
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
| **33** red de compose y RNF-POR-02 | A desde el 2026-10-26 | Ninguno |
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

> **Esta tabla es de las 18:00 del 18/10.** Las cinco quedaron resueltas esa misma tarde:
> está en §9.3 bis, abajo.

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

## 10. Estado de la ejecución — del 2026-10-19 al 2026-10-21

La sesión del 2026-10-18 dejó el contraste y las decisiones. Las sesiones siguientes se
dedicaron a **ejecutar** esas decisiones en los tres documentos de la tesis. Esta sección es
el estado: qué se hizo, qué falta y de quién es.

**Todo lo de §10 se reverificó el 2026-10-21**, leyendo los archivos y no de memoria: el
código de este repo con `git`, los documentos de `../sign-ai-docs` con `git diff`, y los dos
`.tex` y las doce PNG de Overleaf por el MCP. Donde dice "verificado", está verificado con
esa lectura; no con lo que se recuerda de la sesión anterior.

### 10.1 Lo que se hizo

| Documento | Qué se aplicó | Cómo terminó |
|---|---|---|
| **SRS de Overleaf** (`6a122a19bb9a5dd9d390ba3d`) | Los doce lugares: el protocolo del canal (§2.1.5), los cuatro puntos de entrada, la memoria del NLP, el búfer de audio del STT, la caché y su retención, el tiempo hasta la primera seña en dos tramos, el plazo del modelo de lenguaje, la GPU, la tabla de software, y los `[PENDIENTE:]` convertidos en `(TODO:)` | Aplicado. Verificado el 2026-10-20 y **reverificado el 2026-10-21** en `v524` (1495 líneas): `:643` los cuatro puntos de entrada, `:751` el plazo del modelo, `:850-857` los dos tramos, `:1041-1042` y `:1062-1063` la tabla de software, `:1117` el protocolo, `:1211` el búfer del STT, `:1272-1279` la caché y la retención, `:1291` la GPU, y los cuatro `(TODO:)` en `:945`, `:1190`, `:1272` y `:1279` |
| **SDD de Overleaf** (`6a85c9a632974414503d9b82`) | Los diecisiete lugares de texto: §6.1, §6.2, §6.3, §7.1, §7.4, §8.2 y §8.3, más la subsección nueva `\subsection{Instrumentación}` (línea 425) y la fila del historial del 20/10/2026 (línea 131) | Aplicado. Verificado el 2026-10-20 y **reverificado el 2026-10-21** en `v212` (550 líneas): `:131` la fila del historial, `:210-217` el §6.1, `:310` los tres métodos de entrada, `:323` los cuatro colaboradores, `:361` el `translateStream`, `:391` la tabla `catalog`, `:419-421` el §7.4 con el estado *Texto listo*, `:425-431` la subsección de instrumentación, `:513-517` el §8.3 |
| **`docs/sdd.md`** de este repo | Once secciones corregidas (§6.1, §6.2, §6.3, §7.1, §7.2, §7.3, §7.4, §8.2, §8.3, el índice y el §7.5 nuevo), que en párrafos son **32 bloques** | Hecho. Es el único de los tres que se corrige en este repo, sin pasar por Overleaf |
| **v0.16** de `../sign-ai-docs` (antes v0.15) | El encabezado pasó a 0.16 con su fila de historial; se agregaron seis requerimientos (RF-NLP-05, RF-STT-04, RF-STT-05, RF-UI-06, RF-UI-07 y RF-UI-08); se reescribieron **treinta y siete** requerimientos; se eliminó RNF-POR-03 (fusionado en RNF-MNT-04) y RNF-BD-02 pasó al SDD; **quince** de los **setenta y uno** requerimientos quedaron con un `(TODO: ...)` | Hecho. El archivo ahora se llama `SignAI_Requerimientos_Consolidados_v0.16.md` — el rename se hizo el 2026-10-21 |
| **Registro** `../sign-ai-docs/modificaciones/requerimientos.md` | **Cuarenta y cinco filas: 36 Hecho**, 4 Acordado, 4 Bloqueado hasta la ronda diagnóstica y 1 Propuesto | Al día. Contado con script, no a ojo |
| **Trazabilidad** `plan-pruebas/00-bases/trazabilidad.md` | Las dos referencias a RNF-BD-02, la fusión de RNF-POR-03 (tres lugares), y el **contraste reverificado el 2026-10-20**: las seis filas de los requerimientos nuevos, el estado real de la aplicación (el modo dictado, la entrada de texto y el historial ya existen) y el estado de los **trece** bloques | Hecho. El conteo de bloques no cambió: siguen siendo trece |
| **Diagramas** | Tres `.drawio` editados (7.1-1, 7.4 y C4-2) con sus PNG regeneradas, y las doce PNG de `docs/diagrams/` de este repo reemplazadas por las nuevas | Hecho. Las doce de este repo y las doce de `../sign-ai-docs/diagramas/png/` son **el mismo archivo**, verificado con md5 el 2026-10-21 |
| **Las doce PNG del SDD en Overleaf** | Subidas a `images/` del proyecto `6a85c9a632974414503d9b82`, con los nombres idénticos a los de `../sign-ai-docs/diagramas/png/` | Hecho el 2026-10-20. **Verificado el 2026-10-21 por hash:** las doce, leídas del servidor, coinciden byte a byte con las locales |
| **La tabla de software del SRS** | FastAPI 0.115 → **0.143.0** y LangChain 1.4.6 → **1.4.5** | Hecho el 2026-10-20, verificado por el MCP: los números viejos ya no están |
| **RF-UI-04 del v0.16** | El permiso de micrófono se pide al abrir la app y de nuevo al activar la captura si fue denegado. El requisito decía solo lo segundo, que no era lo que el código hacía | Hecho el 2026-10-20, decisión del owner: escribir los dos momentos en el requisito, sin tocar la app |
| **`docs/requirements.md`** | Borrado: duplicaba el documento de requerimientos y estaba desactualizado | Hecho el 2026-10-21. `CLAUDE.md` pasó a apuntar al documento consolidado |
| **El nombre del archivo de requerimientos** | `../sign-ai-docs/documentos/requerimientos/` | El `.md` pasó de `..._v0.15.md` a `..._v0.16.md`, para que el nombre coincida con la versión de adentro. Las **nueve citas por nombre** de los tres repos se cambiaron en el mismo momento, y las referencias sueltas a "v0.15" en el repo de documentos y en el de la app pasaron a "v0.16". Hecho el 2026-10-21 |
| **El historial de `docs/sdd.md`** | `docs/sdd.md:9-14` | Le faltaba la fila del 20/10/2026. El contenido del SDD del backend ya estaba alineado con el código desde el 20 de octubre, pero su tabla de historial solo tenía la del 19 de agosto: el documento contaba una historia distinta a la del SDD de Overleaf sobre el mismo día. Se copió la fila de Overleaf (`main.tex:131`, v212) tal cual, cambiando `\textit{Texto listo}` por `*Texto listo*`. Hecho el 2026-10-21 |
| **`docs/sdd-changes.md`** | `docs/sdd-changes.md` | Las siete entradas que seguían diciendo "pendiente de reflejar en el SDD" se verificaron una por una contra el código, los diagramas y el texto del SDD. Seis están **aplicadas** desde el 20/10/2026 y su línea de estado se reescribió diciendo qué se hizo, dónde y cuándo; una quedó a medias y se documentó como entrada nueva del 2026-10-21. Las dos entradas que son registro de trabajo (15/10 y 16/10) se dejaron intactas, con su pendiente de remedir `rt_first_sign_ms`. Hecho el 2026-10-21 |
| **La revisión de cierre de este mismo documento** | `docs/CONTRASTE-BACKENDvsDOCUMENTOS.md` | Se leyó entero y se corrigieron **nueve citas por número de línea** que apuntaban a otra cosa, más una afirmación sobre las dependencias fijadas y otra sobre las herramientas de análisis estático. Los números de §10.1 se reverificaron con script, no a ojo. Hecho el 2026-10-21 |
| **El trabajo de octubre, integrado en `main`** | Los cuatro repos | El 2026-10-21 el owner decidió que `flujo-oraciones` fuera el nuevo `main`. En este repo fue un **fast-forward** (`979e99d` → `6842ce9`), sin conflictos y sin reescribir historia. `develop` quedó con el árbol de `main` mediante un commit de merge con dos padres, que conserva los 8 commits del camino por fragmentos en su historia. El punto de retorno quedó en `respaldo/main-2026-10-21`, que apunta al `main` viejo. En los otros tres repos: `sign-ai-docs` (`18457be` → `f0d673c`, desde `docs-contraste-2026-10-19`), `sign-ai-android` (`587ed04` → `2d8c757`, con el merge de `origin/main` que ya traía) y `sign-ai-stt` (`7e724d8` → `41d9390`) |

### 10.2 Lo que falta

Todo lo de esta tabla, menos el punto 13, es **trabajo pendiente y se puede hacer**. Lo que no
compete está en §10.4, y el punto 13 es una remisión a esa tabla. Lo que es solo código está
desglosado en §10.3.

**Los puntos 1 y 2 ya no cuentan como trabajo pendiente** (decisión del owner, 2026-10-21):
el 1 queda **en pausa** hasta que el owner pregunte al equipo, y el 2 queda **para preguntar**.
Se dejan en la tabla como están, pero no se trabajan: no son trabajo, son decisiones tomadas.

| # | Qué falta | Dónde hay que hacerlo | Por qué |
|---|---|---|---|
| 1 | **Las referencias a ADR, TSK, DEC, INC, LIM y RSK** del v0.16 | `../sign-ai-docs/...v0.16.md`, 44 líneas | **En pausa.** El owner prefiere preguntar primero al equipo. Los treinta y tres reemplazos propuestos quedaron preparados en §4.1 del registro, sin aplicar |
| 2 | **El proxy inverso (punto 34)**: no hay TLS de verdad sin él | Decisión, no código | **Toca preguntar.** Falta decidir si se va a usar o no. Hoy la decisión es "se adapta el documento", con un `(TODO:)` en RNF-INT-COM-03. El detalle de qué costaría está en §10.2 bis |
| 3 | **Hecho (2026-10-21).** Las tres citas al documento de requerimientos por número de línea | `../sign-ai-android/docs/PLAN-MEDICION.md:19`, `:135` y `:186` | `:380` → **`:439`**, `:237` → **`:260`**, `:326` → **`:358`**. El fondo de las tres sigue siendo cierto, pero dos de las tres **citas textuales** también cambiaron de palabras: RF-NLP-02 pasó de "una frase / el texto" a "una oración / esa oración", y RF-CAT-03 pasó de "el sistema responderá" a "es la aplicación la que muestra", y ahora cubre dos casos. Las tres se corrigieron en el repo de la app |
| 4 | **Hecho (2026-10-21).** Las citas al `docs/requirements.md` borrado | `docs/decisions.md` y `docs/sdd-changes.md` | `docs/requirements.md` era una **copia** del documento de requerimientos de `../sign-ai-docs` (764 líneas), duplicada y desactualizada. Las dos citas apuntaron al documento real: **RF-INT-COM-01** (`decisions.md:103` → `...v0.16.md:168`) y **RF-INT-SW-04** y **RNF-REL-01** (`sdd-changes.md:373` → `...v0.16.md:160` y `:553`). Se encontró **una tercera** cita al archivo borrado, en el repo de la app (`openspec/sessions/2026-10-16-latencia-y-decisiones.md:99`), y se corrigió igual |
| 5 | **Hecho (2026-10-21).** Las referencias a `fixtures/audio/` y a `tools/verificar-tiempo-real.sh` | `docs/performance.md` y `docs/sdd-changes.md` | Los 28 clips de audio **no están en este repo**: están en `../sign-ai-stt/fixtures/audio` y se generan con `scripts/make_audio_fixtures.py --all` en el repo del STT. El script de medición está en `../sign-ai-android/tools/verificar-tiempo-real.sh`. Las dos referencias quedaron apuntando bien |
| 6 | **Hecho (2026-10-21).** El `.docx` se borró y el `.md` se renombró | `../sign-ai-docs/documentos/requerimientos/` | El archivo ahora se llama `SignAI_Requerimientos_Consolidados_v0.16.md` y su versión interna dice 0.16: coinciden. Las **nueve citas por nombre** de los tres repos se cambiaron en el mismo momento: `docs/decisions.md:104`, `docs/sdd-changes.md:373`, `CLAUDE.md:28`, `AGENTS.md:261`, `../sign-ai-android/docs/SISTEMA.md:83`, `../sign-ai-android/docs/PLAN-MEDICION.md:19`, `:135`, `:186` y `../sign-ai-android/openspec/sessions/2026-10-16-latencia-y-decisiones.md:101`. El `.docx`, ver §10.5 |
| 7 | **Hecho (2026-10-21).** La fila del historial del 20/10 en `docs/sdd.md` | `docs/sdd.md:9-14` | El SDD de Overleaf la tenía (`main.tex:131`) y esta copia no. Se copió tal cual, con `\textit{Texto listo}` en LaTeX pasado a `*Texto listo*` en Markdown. La fecha del documento (`docs/sdd.md:4`) quedó como estaba: en Overleaf es `\today`, que se pone solo al compilar |
| 8 | **Hecho (2026-10-21).** `docs/sdd-changes.md` al día | `docs/sdd-changes.md` | Las siete entradas que decía "pendiente de reflejar en el SDD" se verificaron una por una contra el código, el diagrama y el texto: seis quedaron **aplicadas** el 20/10 y se reescribió su línea de estado diciendo qué se hizo y cuándo; una quedó **a medias** y se documentó como la entrada nueva del 2026-10-21 (punto 14). Las dos entradas que son registro de trabajo (15/10 y 16/10) se dejaron como están, con su pendiente de remedir `rt_first_sign_ms` |
| 9 | **La fila del historial del v0.16 dice "ocho TODO"** | `../sign-ai-docs/...v0.16.md:32` | Hay **quince** `(TODO:)` en el archivo. La fila del historial quedó corta |
| 10 | **Dos filas del registro contradicen el documento** | `../sign-ai-docs/modificaciones/requerimientos.md:43` (#16) y `:47` (#20) | Las dos dicen "el texto del requisito se queda como está", pero RNF-MNT-04 y RNF-REL-03 **sí** cambiaron de texto. Una de las dos cosas está mal |
| 11 | **RF-UI-06 dice "un selector con dos opciones"** | `../sign-ai-docs/...v0.16.md:410` | La app tiene **dos interruptores** en la barra inferior, no un selector. La trazabilidad ya lo dice (`../sign-ai-docs/plan-pruebas/00-bases/trazabilidad.md:24-26`); el requisito no. También es lo que dejó el SRS con una descripción de los modos que no es la del código |
  | 12 | **`AGENTS.md` describe mal el estado del árbol** | `AGENTS.md`, sección "Estado del repo" | Dice "15 archivos modificados y 2 sin trackear". Al cierre de la sesión del 21 de octubre eran **22 modificados, 1 borrado y 0 sin trackear**, y después de commitear y pasar `flujo-oraciones` a `main` (2026-10-21) el árbol quedó **limpio**. El número se mueve con cada tanda, así que conviene ponerlo con la fecha y no como un hecho fijo |
| 13 | **La §3 del SRS, las dos portadas y los casos de uso CU-01 a CU-05** | Ver §10.4 | No nos compete. Quedan anotadas para que el owner sepa que están ahí |
| 14 | **La lista de clases de la §7.1 no coincide con su propio diagrama** | `docs/sdd.md:192-210` contra la Figura 5 | La lista dice `lookup(...): List<Segment>?`, `store(..., segments: List<Segment>)` y tres atributos en `NLPServiceImpl`, **sin `EmbeddingModel`**. El diagrama de al lado dice `List<String>`, `glosses: List<String>`, cuatro atributos y `EmbeddingModel` con `embed()`. El SDD se contradice dentro de la misma sección, y la narrativa de 17 líneas más abajo ya está con la versión nueva. **Documentado** en `docs/sdd-changes.md` (entrada del 2026-10-21); **no se aplicó**, porque la regla del repo es anotar el cambio del SDD y que lo aplique el owner |
| 15 | **Queda una referencia suelta a "la SRS v0.15"** | `docs/plan-implementacion-backend.md:25` | El SRS de Overleaf se versiona con los números de Overleaf (v159, v436, v524); **"v0.15" es la versión del documento de requerimientos**, no la del SRS. Está dentro de una frase que recuerda que el punto ya estaba identificado antes. Es la **última** referencia a "v0.15" que queda viva en los cuatro repos: las otras dos están en logs de sesión, que no se reescriben |

### 10.2 bis El punto 2 en detalle — qué costaría montar el proxy inverso hoy

El owner preguntó si se podría hacer ya, en el prototipo. **Sí se puede, y el backend no
cambia ni una línea.** El detalle está verificado el 2026-10-21.

| Pieza | Qué es | Dónde |
|---|---|---|
| **El proxy** | **Caddy** sirve de proxy inverso con un archivo de configuración: escucha en el 443 con TLS y le pasa todo al backend en el 8080. El backend publica el 8080, así que el proxy lo alcanza en `127.0.0.1:8080` si corre en el host, o como `backend:8080` si corre como un contenedor de la misma red de compose | Host de desarrollo |
| **El certificado** | El teléfono tiene que confiar en él. El `network_security_config.xml` de la app (el de `release`, `sign-ai-android/app/src/main/res/xml/network_security_config.xml`) prohíbe el texto en claro pero **no confía en los certificados instalados por el usuario**: falta el `<certificates src="user"/>`. Sin esa línea, el teléfono rechaza la conexión aunque el proxy esté perfecto. La herramienta estándar es `mkcert`, que genera la CA local y la instala en el teléfono | **Repo de la app**, que desde acá es de solo lectura |
| **La URL** | `-Psignai.backendWsUrl=wss://…`. En `release` solo se acepta si empieza por `wss://`; el default es `wss://backend.invalid/ws/translate`, que no resuelve | `sign-ai-android/app/build.gradle.kts` |

**Lo que quedaría es un TLS de laboratorio**: CA propia, sin dominio público, con el teléfono
apuntando a la máquina por `adb reverse` o por el `hosts`. Sirve para demostrar que el canal
va cifrado; no es un despliegue público.

**Diagramas (3).** El 6.2 Vista física (caja nueva entre *Android Device* y *Demo / Dev Host`,
que pasa de dos contenedores a tres, y la flecha de adentro del host en texto en claro), el
C4-2 Contenedores (el contenedor nuevo y la frontera del host) y el C4-1 Contexto (el nodo
nuevo). Los tres se editan en `../sign-ai-docs/diagramas/draw.io/`, se regenera su PNG, y esa
PNG va a tres sitios: `sign-ai-backend/docs/diagrams/`, `../sign-ai-docs/diagramas/png/` y
`images/` del SDD en Overleaf. Los otros nueve no se tocan: el 6.1 y el C4-3 son vistas
lógicas, donde el proxy no aparece.

**Documentos (4).** El RNF-INT-COM-03 de `../sign-ai-docs/...v0.16.md:186-189` (quitar el
`(TODO:)` de `:189` y reescribir `:186`, que hoy dice que el cifrado "lo termina el
despliegue"); el SRS de Overleaf (el mismo requisito y el §2.1.5 del protocolo del canal); el
SDD de Overleaf y `docs/sdd.md` (el §6.2, que hoy describe el host con dos contenedores, más
una nota de que el certificado es de laboratorio); y `docs/sdd-changes.md` con este punto.

El costo real no son los diagramas: son el certificado y el cambio en la app. Si se decide
hacerlo, el orden sería el del backend primero (Caddy más su servicio en el
`docker-compose`), y después los documentos, para que los diagramas no describan una pieza que
todavía no existe.

### 10.3 Los cambios de código que faltan

> **Actualizado el 2026-10-21 (tarde): los nueve puntos de esta tabla están
> implementados**, con un `scripts/verify_*.py` para cada comportamiento nuevo
> (`verify_llm_prompt`, `verify_llm_timeout`, `verify_database_resilience`,
> `verify_turn_id`, `verify_done_on_error`, `verify_catalog_semantic_category`,
> `verify_cache_upsert`, `verify_static_analysis` y
> `verify_dependencies_pinned`). La columna "Estado real verificado" de
> abajo queda como la foto de antes del cambio: dice lo que se encontró. Lo
> que se hizo, con las decisiones de fondo que lo Accompañan, está en
> `docs/sdd-changes.md` (2026-10-21) y en `docs/android-integration.md`
> §3.2 y §4, que son el contrato con la app.
>
> **Lo que sigue en pie:** la migración `004` (índice único de
> `semantic_cache`) hay que aplicarla en Neon **antes** de desplegar el
> código que escribe con `UPSERT`; sin ella, cada guardado del caché falla
> (y el pipeline sigue funcionando: el error queda en el log y la frase se
> responde igual). Y lo de §10.3.2 sigue sin implementarse: **validar el
> audio** que llega por el canal y **sacar el texto de los logs**.

Cada punto es un cambio del backend. **Ninguno está hecho**: se verificó uno por uno en
`app/`, `requirements.txt` y `tools/`, y se reverificó el 2026-10-21 con el código ya en
`main`.

**El owner decidió el 2026-10-21 que este punto NO se hace por ahora:**

| Fuera de alcance por ahora | Por qué |
|---|---|
| **Sacar el texto de los logs del servidor** (`app/controller/controller.py:147`, `:154`, `:155`, `:161`, `app/nlp/nlp_service_impl.py:59`, `:65`, `:85`, `app/nlp/segmenter/sentence_segmenter.py:31`) | El owner quiere **todos los logs, con el texto**, mientras se mide. El `(TODO:)` de RNF-SEC-03 sigue en pie y el texto se sigue escribiendo: `logger.info("Phrase received: %r -> translating", text)`. **Una sesión que implemente esta tabla no toca los logs** |

Los demás puntos van con la decisión que los respalda y **sí** se implementan:

| # | Qué | Dónde debería estar | Estado real verificado el 2026-10-21 | Decisión |
|---|---|---|---|---|
| 1 | **Quitar el vocabulario cerrado del prompt (D-7)** | `app/nlp/llm_client.py:149-150` y las tres reglas de `:81-84` y `:91-92` | **No está hecho.** El prompt sigue recibiendo el catálogo entero: `catalog_repository.vocabulary()` (`app/main.py:74`) se inyecta en `self._prompt`. El SDD no dice nada del contenido del prompt, así que no toca ningún diagrama. Ver `docs/performance.md` §9 y el §10.3 bis de este documento | **D-7**, owner, 2026-10-16 |
| 2 | `llm_timeout_ms = 5000` y `max_retries = 1` | `app/config/settings.py:32` | **Sigue en `10000`, y no hay `max_retries`** | owner, 2026-10-18 (punto 37 del contraste) |
| 3 | Tiempo máximo de la base (5 s) y un reintento | `app/persistence/` | **No existe**. Además, la excepción en el arranque del backend no está controlada: si la base no contesta, el proceso no levanta | owner, 2026-10-18 (punto 29) |
| 4 | Identificador de turno en `segment` y en `done` | `app/controller/controller.py` | **No existe**. El `done` solo se manda en el camino feliz (`:164`) | owner, 2026-10-18 (punto 39) |
| 5 | `done` cuando la traducción falla | `app/controller/controller.py` | **No existe**: en el camino del error no se cierra el turno | owner, 2026-10-18 (punto 39) |
| 6 | Leer `semantic_category` | `app/validation/catalog_repository.py:38` y el campo en `Gloss` | **Solo está en la migración** (`app/persistence/migrations/001_create_catalog.sql:5`); el `SELECT` es `gloss, glb_animation_path` y el código no lee la columna en ningún `.py` | **A**, owner: leerla. No rompe el diagrama, porque la imagen 7.3 de `../sign-ai-docs` ya la lista (punto 11 de §3) |
| 7 | `UPSERT` de la caché | `app/nlp/semantic_cache.py:225` | **No existe**: el `store()` hace un `INSERT` simple y la tabla no tiene restricción única sobre `(original_text, phrase_type)` | **A y B**, owner: `UPSERT` sobre `(original_text, phrase_type)` y no guardar respuestas vacías (punto 38 de §3) |
| 8 | Analizadores estáticos (mypy, ruff) | No hay `.github/` (o sea, no hay integración continua) | **No hay**. `tools/` existe, pero trae un solo script (`verificar-conexiones-stt.py`); no hay configuración de mypy ni de ruff en ninguna parte | RNF-MNT-03 lo pide |
| 9 | Dependencias fijadas | `requirements.txt` | **Nueve de las once** están sin versión: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `asyncpg`, `sentence-transformers`, `langchain`, `langchain-openai` y `websockets`. Solo `spacy` (con rango) y `es_core_news_md` (con rueda exacta) están fijados | RNF-MNT-04 lo pide |

#### 10.3.1 Cómo se implementa cada uno

**1. D-7, quitar el vocabulario cerrado del prompt.** Es el más serio y el que tiene el
análisis escrito (§10.3 bis, `docs/performance.md` §9 y `../sign-ai-android/docs/PLAN-MEDICION.md`
§3). Tres cosas:

- `app/nlp/llm_client.py:149-150`: `self._prompt` se arma con
  `", ".join(sorted(set(self.vocabulary.values())))`. **La lista sale.**
- `app/main.py:74`: se saca el argumento `catalog_repository.vocabulary()` al `LLMClient`.
  **El `LLMClient` sigue recibiendo el vocabulario**, porque lo necesita para `_repair_glosses`
  y `_merge_fragments`; lo que cambia es que ya no va al prompt.
- Las tres reglas del prompt que mencionan "the vocabulary" (`:81-84` y `:91-92`) se reescriben
  sin hablar de la lista. El ejemplo de "COMO ESTAS" como glosa de varias palabras **se
  conserva**, como ejemplo concreto y sin decir de dónde sale.

**Lo que se queda, y no hay que tocar:** `_repair_glosses` (`:206`), `_merge_fragments` (`:238`)
y `ValidatorServiceImpl._validate_gloss` (`app/validation/validator_service_impl.py:17-21`).
Los tres son O(1) y escalan sin problema.

**2. `llm_timeout_ms` y `max_retries`.** Los dos van en `app/config/settings.py:32`, que es
donde vive cualquier valor cuantitativo. Los dos números salen de la decisión, no de una
medición.

**3. Tiempo máximo de la base y reintento.** En `app/persistence/`: un timeout de 5 segundos
por consulta más un reintento. El peor caso son unos 10 segundos, por debajo de los 15 del
reloj de la aplicación. Además, la excepción en el arranque tiene que estar controlada: hoy,
si la base no contesta, el proceso no levanta.

**4 y 5. Identificador de turno y `done` en el error.** Los dos en
`app/controller/controller.py`. **El punto 4 cambia el contrato del WebSocket**: antes de
tocarlo hay que leer `../sign-ai-android/.opencode/skills/contrato-websocket/SKILL.md`, y
después hay que actualizar el otro lado (`../sign-ai-android`) o decir explícitamente qué
queda pendiente de ese lado. El identificador lo pone la aplicación y sube desde 1 en cada
conexión.

**6. Leer `semantic_category`.** `app/validation/catalog_repository.py:38` hoy pide
`gloss, glb_animation_path`; se agrega la columna y el campo en `Gloss`. La decisión fue
leerla, para que el código quede de acuerdo con el diagrama y no al revés.

**7. `UPSERT` de la caché.** En `app/nlp/semantic_cache.py:225`, el `store()` hoy hace un
`INSERT` simple. Tiene que pasar a ser un `UPSERT` sobre `(original_text, phrase_type)`, y
tiene que dejar de guardar respuestas vacías. **Eso pide una migración**: la tabla
(`app/persistence/migrations/002_create_semantic_cache.sql`) no tiene restricción única
sobre `(original_text, phrase_type)`, y el `UPSERT` necesita una contra la que entrar en
conflicto. Y el plan de pruebas de `../sign-ai-docs` hay que actualizarlo, porque hoy
describe el defecto como si fuera el comportamiento.

**8 y 9. Analizadores estáticos y dependencias fijadas.** `mypy` y `ruff` con su
configuración, y las nueve dependencias sin versión de `requirements.txt` fijadas a las
versiones con las que corre el proyecto. Las dos que ya están fijadas (`spacy` y
`es_core_news_md`) se quedan como están.

#### 10.3.2 Lo que NO se implementa, y por qué

- **Validar el audio que llega por el canal** (`app/controller/`): **no tiene decisión
  tomada.** No se implementa; queda como pregunta abierta.
- **Sacar el texto de los logs del servidor**: **aplazado por el owner el 2026-10-21.** Se
  quieren todos los logs, con el texto, mientras se mide.

#### 10.3.3 Verificación

```bash
docker compose up -d --build
docker compose exec backend python -m scripts.verify_client_frames
docker compose exec backend python -m scripts.verify_sentence_segmenter
```

Los scripts se corren **como módulo** (`python -m scripts.x`), no como
`python scripts/x.py`: en el segundo caso `sys.path[0]` es `/app/scripts` y `import app` no
resuelve.

Cada comportamiento nuevo necesita su propio `scripts/verify_*.py`, que es la prueba de
regresión de esa pieza.

**La trampa de D-7:** cambiar el prompt **no** invalida `semantic_cache`. Las glosas viejas
siguen en Neon y salen por `SemanticCache HIT`, así que el prompt nuevo no se ejecuta y
parece que el arreglo no sirvió. Hay que correr `DELETE FROM semantic_cache;` y reiniciar el
backend. Es caché derivada y se reconstruye sola.

### 10.3 bis El prompt no debe llevar la lista de glosas (D-7)

**Es la más seria de las que faltan, y la única que ya tiene decisión tomada.** El owner la
tomó el 2026-10-16 y **el código no la cumple**. Se encontró el 2026-10-21 al rescatar el
§9 del contraste que se borró (§10.5), y el rescate quedó anotado al revés: como si la
lista en el prompt fuera el diseño. No lo es.

**Qué dice la decisión.** El prompt **no** lleva la lista de glosas del catálogo. Está en
`../sign-ai-android/docs/PLAN-MEDICION.md` §3 (líneas 96-180), con el análisis. Las dos
razones:

1. **Va contra el plan de pruebas.** `../sign-ai-docs/plan-pruebas/01-diseno/llm/general.md:31-33`
   dice, del prompt: *"No incluye la lista de las 50 glosas del catálogo, así que el modelo
   puede inventar glosas. Las que no existen las marca como no disponibles el validador."*
2. **No escala**, y el mecanismo que hace falta ya está: **RF-CAT-02** (`:348-354`) pone la
   verificación en el validador, y **RF-NLP-02** (`:255-262`) dice que la salida del modelo
   *"todavía no ha sido validada contra el catálogo de señas, esa verificación ocurre en un
   módulo distinto."*

**Qué hace el código hoy, que es lo contrario.** `app/main.py:74` le pasa
`catalog_repository.vocabulary()` al `LLMClient`; ese método devuelve **todas** las glosas
(`app/validation/catalog_repository.py:55-62`), y `app/nlp/llm_client.py:149-150` las
inyecta en el prompt, que se manda como mensaje de sistema en cada llamada (`:180`).

**Qué sale y qué se queda.**

| | Qué | Por qué |
|---|---|---|
| **Sale** | La lista de glosas del prompt, y las tres reglas que la mencionan: `app/nlp/llm_client.py:81-84` y `:91-92` | D-7 |
| **Se queda** | `_repair_glosses` (`app/nlp/llm_client.py:206`) y `_merge_fragments` (`:238`), que consultan el vocabulario con `normalize_gloss` contra un diccionario: es O(1) | Es lo que evita que "cómo estás" vuelva como `TÚ, ESTAR, CÓMO` |
| **Se queda** | `ValidatorServiceImpl._validate_gloss` (`app/validation/validator_service_impl.py:17-21`) | Es el mecanismo de RF-CAT-02 y de RF-CAT-03 |
| **Se queda** | La regla de que una glosa puede ser de varias palabras, con el ejemplo de `COMO ESTAS` | Se conserva como ejemplo concreto, sin decir de dónde sale |

**No toca ningún diagrama, y el SDD ni el SRS se oponen.** Se comprobó en Overleaf el
2026-10-21: el SDD (`v212`, 550 líneas) y el SRS (`v524`, 1495 líneas) **no mencionan el
prompt ni el vocabulario cerrado** en ninguna línea. `docs/sdd.md` describe a
`LLMClient.transform(text)` como "devolver la lista de glosas" y nada más. En el SRS, lo
único que hay del vocabulario es del **sistema**, no del prompt: *"No soporta vocabulario
abierto"* (`:228` y `:1389`) y el catálogo en memoria para validar sin consultar la base
(`:1212` y `:1266`). Todo eso sigue siendo cierto con D-7.

**Lo que falta medir.** La Fase 2 del plan de la app: la reparación es lo que cubre el
riesgo, y hay que medirlo con las 28 frases antes de afirmarlo en la tesis. Ver
`docs/performance.md` §9.

**Las anotaciones que se corrigieron el 2026-10-21**, para que en ningún lado quede escrito
que el prompt puede llevar la lista:

| Dónde | Qué decía |
|---|---|
| `CLAUDE.md` | "El prompt de glosas usa el catálogo como vocabulario cerrado", como invariante |
| `app/nlp/llm_client.py:47-59` | el comentario de cabecera, los tres puntos de "the fix has three parts" |
| `app/main.py:70-72` y `:74` | el comentario que dice que el vocabulario va al prompt, y la llamada que lo pasa |
| `docs/performance.md` §9 | el §9 rescatado, que lo daba por bueno |
| `docs/sdd-changes.md` | la lista de lo que se trajo de `develop` |
| `docs/CAMBIOSBACKEND.md` | la nota del cherry-pick `db1fa69` |
| `docs/sessions/2026-10-15-vuelta-al-flujo-por-oraciones.md` | la tabla de lo que se trajo |
| `../sign-ai-android/openspec/sessions/2026-10-14-conectar-stt-y-backend-real.md` | la nota del prompt nuevo |
| `../sign-ai-android/Revisión de develop.md` | los dos puntos del prompt |
| `../sign-ai-docs/plan-pruebas/01-diseno/llm/general.md:31-33` | la limitación, que ya es el diseño |

### 10.4 Lo que no nos compete

Está pendiente, pero **no lo vamos a llenar desde acá**. Queda anotado para que el owner sepa
que existe y para que la *Memoria* lo recoja como trabajo futuro.

| Qué | Dónde | Por qué no es nuestro |
|---|---|---|
| La §3 del SRS ("Requerimientos Específicos") | Overleaf SRS `main.tex:1435-1477` | Son veinte subtítulos de la plantilla de un juego. Es el punto 41 del contraste |
| La portada del SDD | Overleaf SDD `main.tex:101-110` | Tiene el `[PENDIENTE DE COMPLETAR]`, "Falta hoja de portada acá" y los párrafos azules de instrucción. Es el punto 43 |
| La portada del SRS | Overleaf SRS `main.tex:99-119` | Tiene `[Nombre del proyecto]`, `[Nombre de la empresa]`, `[Fecha]`, `[Versión del documento]`, `[Logos]` y `[Autores]`, y el pie dice "IronWorks -- Ingeniería de Sistemas PUJ" |
| Los casos de uso CU-01 a CU-05 | No están en ningún documento | **68 líneas** del v0.16 los nombran y **ningún archivo del repo de documentos los define**. Los llenamos hasta donde alcancen los repos; definirlos es otra cosa |

### 10.5 Lo que se borró

| Qué | Dónde | Por qué |
|---|---|---|
| `auditoria-flujo-2026-10-15.md` | `../sign-ai-docs/` | Era **el primer contraste**, del 15 de octubre. Está commiteado y no se tocaba desde el 16. Todo lo que tenía está en este documento |
| `texto-overleaf-pendiente.md` | `../sign-ai-docs/modificaciones/` | Era la lista de textos para pegar en Overleaf. **Todo lo que tenía ya se pegó**, así que el archivo solo servía para confundir. Decisión del owner, 2026-10-21 |
| `SignAI_Requerimientos_Consolidados_v0.15.docx` | `../sign-ai-docs/documentos/requerimientos/` | La versión en Word del mismo documento. Lo había hecho **pandoc el 12 de agosto** (se sabe por los metadatos: el autor es "Un-named", el default de pandoc) y **nunca se actualizó**: seguía en la v0.15, sin RF-NLP-05, RF-UI-08 ni RF-STT-05, y todavía con RNF-POR-03 y RNF-BD-02, que en la v0.16 ya se fusionaron o se quitaron. Que en Word se lea la versión vieja, sin avisar, es el peor de los tres estados. **Decisión del owner, 2026-10-21: se borra** y el documento vive solo en Markdown. Queda la nota en el `.md` |

**Lo que se rescató antes de borrarlo** (el 2026-10-21, el mismo día):

| Qué estaba en el archivo borrado | Dónde quedó |
|---|---|
| El §9, "Escalabilidad del prompt": el prompt lleva el vocabulario completo, el costo es lineal con el corpus y se paga en cada llamada, con la tabla de 50 / 500 / 5 000 glosas, y el aviso de que `_repair_glosses` y `_merge_fragments` **no** hay que tocarlos porque son O(1) | **`docs/performance.md` §9**, nueva. El código se reverificó: `self._prompt` se arma una vez en `app/nlp/llm_client.py:149` y se manda como mensaje de sistema en `:180`. **Ojo:** la sección quedó anotada el mismo día con la decisión **D-7** (owner, 2026-10-16), que dice que esa lista **sale** del prompt. Ver §10.3 |
| El §7, la decisión de diseño del modo en vivo (opción A: el micrófono queda prendido, cada frase pasa por el divisor de oraciones, y se pierde empezar a representar antes de terminar la primera oración) | Ya estaba en `docs/CAMBIOS.md`, `docs/MODO-EN-VIVO.md` y `tools/TIEMPO-REAL.md` de la app. Lo que faltaba era el puntero, y se corrigió |
| El §6, el plan por repositorio | El plan se ejecutó entero. Su estado es el §10 de este documento, y el resumen por repo está en `docs/CAMBIOSBACKEND.md` (backend), `docs/CAMBIOS.md` y `docs/MODO-EN-VIVO.md` (app) |

**Las referencias que quedaron colgando** y se corrigieron el 2026-10-21: diez en el repo de la
app (una en el código, `MicMode.kt`, y nueve en `docs/CAMBIOS.md`, `docs/MODO-EN-VIVO.md`,
`docs/PLAN-MEDICION.md`, `tools/TIEMPO-REAL.md`, `tools/medir-primera-sena.py`,
`openspec/specs/ui/spec.md` y `openspec/sessions/README.md`) y una en
`docs/sdd-changes.md`. **Se dejaron sin tocar** las cuatro que están en logs de sesión
(`openspec/sessions/2026-10-15-flujo-oraciones-android.md`,
`openspec/sessions/2026-10-16-latencia-y-decisiones.md` ×2 y
`docs/sessions/2026-10-15-vuelta-al-flujo-por-oraciones.md`): un log de sesión es el registro
de lo que pasó ese día, y no se reescribe.

### 10.6 Lo que se encontró revisando

**El 2026-10-20**, al verificar los tres documentos leyendo los archivos, apareció una cosa
que no estaba anotada: **la tabla de software del SRS todavía decía FastAPI 0.115 y LangChain
1.4.6**, cuando las versiones medidas el 2026-10-18 dentro de la imagen eran **0.143.0** y
**1.4.5**. Es el punto 20 del contraste. El owner lo pegó el mismo día 20 de octubre.

**El 2026-10-21**, al releer las cuatro fuentes enteras para esta actualización, aparecieron
las diferencias que están en §10.2 como puntos 4 a 12. La más seria es la **#8**: el
registro de cambios pendientes del SDD describe cosas que ya se aplicaron. Las demás son
números desactualizados en los registros y una contradicción entre RF-UI-06 y la app.

**Lo que se corrigió en esta misma actualización**, porque estaba en este documento y era
mentira:

| Qué decía | Qué es verdad |
|---|---|
| "faltan las doce PNG nuevas" en Overleaf (§11) | **Las doce están subidas**, y son las nuevas: verificado por hash |
| "Cuarenta y cuatro filas: 35 Hecho" (§10.1) | **45 filas: 36 Hecho** |
| "se reescribieron veintiocho requerimientos" (§10.1) | **Treinta y siete** |
| "quince de los sesenta y seis" (§10.1) | **Quince de los setenta y uno** |
| "los once bloques" de la trazabilidad (§10.1) | **Trece** |
| "las 11 correcciones de `docs/sdd.md`" | **11 secciones**, que son 32 bloques de párrafo. Además tocaron §7.4, §8.2 y §8.3, que no estaban en la orden de trabajo original |

**Las citas por número de línea que se movieron** (2026-10-21). Al escribir la §9 de
`docs/performance.md` y al anotar el plan de pruebas, algunos archivos cambiaron de largo y
las citas por línea quedaron apuntando a otra cosa. Se corrigieron todas:

| Cita | Antes | Ahora |
|---|---|---|
| `docs/sdd-changes.md:371` → `docs/performance.md` | `:618-623` | **`:676-681`** |
| `docs/sdd-changes.md:433` → `docs/performance.md` | `:688-693` | **`:756`** |
| `../sign-ai-android/docs/PLAN-MEDICION.md:216` → `docs/CAMBIOSBACKEND.md` | `:183-185` | **`:186-188`** |
| `../sign-ai-android/docs/PLAN-MEDICION.md:425` → `llm/general.md` | `:38` | **`:44`** |
| `../sign-ai-android/openspec/sessions/2026-10-16-latencia-y-decisiones.md:93` | `docs/performance.md:621-623` | **`SignAiBottomBar.kt:114-115`**, que es donde está la cita textual |

La última estaba mal desde antes: el texto *"intercalados, el `index` de las oraciones deja de
corresponder al orden en que llegaron"* nunca estuvo en `performance.md`, estaba en el
comentario del código de la app.

**Las nueve citas corregidas en la revisión de cierre** (2026-10-21, al releer este documento
entero y abrir cada archivo citado). Todas apuntaban a una línea Nearby:

| Cita | Apuntaba a | Donde está |
|---|---|---|
| `app/nlp/llm_client.py:146-148` | la asignación de `self.vocabulary` | **`:149-150`**, que es donde se arma el prompt |
| `app/nlp/llm_client.py:78-81` y `:88-89` | dos reglas del prompt | **`:81-84` y `:91-92`**, que son las tres reglas que mencionan el vocabulario |
| `app/nlp/llm_client.py:177` | el mensaje de sistema | **`:180`** |
| `app/nlp/llm_client.py:203` y `:235` | `_repair_glosses` y `_merge_fragments` | **`:206` y `:238`** |
| `app/main.py:69` | `catalog_repository.vocabulary()` | **`:74`** |
| `app/main.py:65-68` | el comentario del vocabulario | **`:70-72`**, y el bloque de los tres puntos es `:47-59` |
| `app/persistence/001_create_catalog.sql:5` | un archivo que no está ahí | **`app/persistence/migrations/001_create_catalog.sql:5`** (faltaba `migrations/`) |
| `...v0.16.md:185` y `:182` | el `(TODO:)` y la descripción de RF-INT-COM-03 | **`:189` y `:186`** |
| `trazabilidad.md:22-25` | la frase de los dos interruptores | **`:24-26`** |

Además, dos afirmaciones que estaban mal enteras:

| Qué decía | Qué es verdad |
|---|---|
| "`fastapi`, `uvicorn`, `pydantic` y `asyncpg` **sin versión**" | **Nueve de las once** dependencias están sin versión. Solo `spacy` (con su rango) y `es_core_news_md` (con su rueda exacta) están fijadas |
| "Analizadores estáticos: no hay `.github/` ni `tools/`" | No hay `.github/` —o sea, no hay integración continua— pero **`tools/` sí existe**: trae `verificar-conexiones-stt.py`. Lo que no hay es configuración de mypy ni de ruff en ninguna parte |

**Los números de §10.1, reverificados con script** el 2026-10-21 (no a ojo): el registro de
`modificaciones/requerimientos.md` tiene **45 filas** (36 Hecho, 4 Acordado, 4 Bloqueado, 1
Propuesto); el v0.16 tiene **71 requerimientos** (66 RF/RNF y 5 RD), contra **66** del v0.15;
**6** son nuevos, **1** se eliminó (RNF-POR-03) y **37** reescribieron su texto; **15** tienen
`(TODO:)`; y la trazabilidad asigna los requisitos a **13 bloques**. Todo coincide con lo que
§10.1 afirma.

---

## 11. Dónde sigue cada cosa

| Si el trabajo toca… | Cargá |
|---|---|
| Un frame del WebSocket o un nombre de métrica | `../sign-ai-android/.opencode/skills/contrato-websocket/SKILL.md` — el contrato se lee en los dos lados antes de cambiarlo |
| Un nombre de clase o método que el SDD define | `.claude/skills/signai-sdd-conformance/SKILL.md` |
| El contrato completo con la app | `docs/android-integration.md` §3.1 y §4 |
| Qué se decidió ya entre el código y los documentos del backend | `docs/sdd-changes.md` — **con lo que quedó viejo, ver §10.2 punto 8** |
| Qué cambió en el flujo por oraciones | `docs/CAMBIOSBACKEND.md` |
| Latencias y efecto de cada optimización | `docs/performance.md` |
| Los requisitos del proyecto | `../sign-ai-docs/documentos/requerimientos/SignAI_Requerimientos_Consolidados_v0.16.md` — internamente v0.16 |
| El estado de cada cambio de los requerimientos | `../sign-ai-docs/modificaciones/requerimientos.md` — **45 filas**, con el estado de cada una |
| El estado de la ejecución de la alineación | Este documento, §10 |
| El diseño del proyecto | `docs/sdd.md` (alineado con el backend el 2026-10-20) y el SDD de Overleaf (`v212`, texto alineado y las doce PNG nuevas subidas) |
| Los diagramas | `../sign-ai-docs/diagramas/draw.io` es la fuente, y es la buena. Los tres juegos —el de ahí, el de `docs/diagrams/` de este repo y el de `images/` en Overleaf— son **el mismo archivo** |