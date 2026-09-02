# Descripción del Diseño del Software (SDD) — SignAI

**Pontificia Universidad Javeriana**
**Fecha del documento:** 30 de agosto de 2026


---

## 1. Historial de Cambios

| Fecha | Descripción del cambio | Persona(s) |
|---|---|---|
| 19/08/2026 | Migración de plantilla institucional a formato LaTeX para su edición en Overleaf. | Julián Ramos |

---

## 2. Tabla de Contenidos

1. Historial de Cambios
2. Tabla de Contenidos
3. Lista de Figuras
4. Lista de Tablas
5. Introducción
6. Arquitectura
   6.1. Vista Lógica del Sistema
   6.2. Vista Física del Sistema
   6.3. Vista de Procesos del Sistema
7. Diseño Detallado
   7.1. Estructura del Sistema
   7.2. Comportamiento del Sistema
   7.3. Persistencia
   7.4. Interfaz de Usuario
8. Modelo C4
   8.1. Contexto
   8.2. Contenedores
   8.3. Componentes
9. Referencias

---

## 3. Lista de Figuras

1. Diagrama de componentes de la Vista Lógica del Sistema — `diagrams/sdd-6.1-vista-logica-componentes.drawio.png`
2. Diagrama de despliegue de la Vista Física del Sistema — `diagrams/sdd-6.2-vista-fisica-despliegue.drawio.png`
3. Diagrama de actividades de la Vista de Procesos del Sistema — `diagrams/sdd-6.3-vista-procesos-actividades.drawio.png`
4. Diagrama de clases de Orquestación — `diagrams/sdd-7.1-clases-1-orquestacion.drawio.png`
5. Diagrama de clases de NLP — `diagrams/sdd-7.1-clases-2-nlp.drawio.png`
6. Diagrama de clases de Validación y Catálogo — `diagrams/sdd-7.1-clases-3-validacion-catalogo.drawio.png`
7. Diagrama de secuencia del flujo de traducción — `diagrams/sdd-7.2-secuencia-flujo-traduccion.drawio.png`
8. Modelo relacional de persistencia — `diagrams/sdd-7.3-persistencia-relacional.drawio.png`
9. Diagrama de estados de la interfaz de usuario — `diagrams/sdd-7.4-diagrama-estados-ui.drawio.png`
10. Diagrama de contexto del sistema (C4 Nivel 1) — `diagrams/sdd-c4-1-contexto.drawio.png`
11. Diagrama de contenedores del sistema (C4 Nivel 2) — `diagrams/sdd-c4-2-contenedores.drawio.png`
12. Diagrama de componentes del Backend (C4 Nivel 3) — `diagrams/sdd-c4-3-componentes-backend.drawio.png`

## 4. Lista de Tablas

*(El documento original no incluye tablas de contenido de datos adicionales fuera de la de Historial de Cambios.)*

---

## 5. Introducción

Este documento describe el diseño de software de SignAI, un sistema que traduce audio en español a Lengua de Señas Colombiana mediante inteligencia artificial y lo reproduce a través de un avatar 3D. Presenta la arquitectura del sistema en tres vistas complementarias (lógica, física y de procesos), la profundiza bajo el modelo C4 en sus tres niveles de abstracción (contexto, contenedores y componentes), y desarrolla el diseño detallado del backend: la estructura de sus clases, el comportamiento del flujo de traducción, el modelo de persistencia de datos y los estados de la interfaz de usuario.

Este documento está dirigido a quienes implementan y mantienen SignAI, así como a quienes evalúan el proyecto en su desarrollo académico. Su propósito es servir como referencia técnica de las decisiones de diseño detrás de cada componente del sistema, de modo que cualquier persona que se incorpore al proyecto pueda entender cómo está construido.

---

## 6. Arquitectura

La arquitectura de SignAI se describe en tres vistas complementarias. La Vista Lógica muestra los componentes de software del backend y las interfaces por las que se comunican entre sí. La Vista Física muestra en qué máquinas y contenedores corre cada uno de esos componentes. La Vista de Procesos muestra el flujo completo de una traducción, desde que el usuario activa el micrófono hasta que ve la seña ejecutada por el avatar.

### 6.1. Vista Lógica del Sistema

Para la Vista Lógica del Sistema se usa un diagrama de componentes, ya que permite mostrar los módulos principales del backend y las interfaces que los conectan entre sí, sin entrar todavía en detalles de implementación ni de despliegue físico.

**Figura 1: Diagrama de componentes de la Vista Lógica del Sistema**

![Figura 1: Diagrama de componentes de la Vista Lógica del Sistema](diagrams/sdd-6.1-vista-logica-componentes.drawio.png)

En el diagrama, el backend está organizado como un monolito, con el Servicio STT como único componente que corre en un proceso aparte, debido a su consumo de GPU y VRAM.

El Controller recibe la conexión WebSocket del cliente Android y se comunica con el Servicio STT para transcribir el audio. Una vez tiene el texto, se lo entrega al Orchestrator, que es quien conoce la secuencia completa del proceso de traducción: primero llama a NLPService y después a ValidatorService.

NLPService depende de la extensión pgvector de PostgreSQL para buscar coincidencias semánticas en el caché, y de la API del LLM externo cuando no encuentra ninguna. Sus colaboradores internos (el analizador de huella gramatical, el caché semántico y el cliente del LLM) no se muestran aquí, porque corresponden al diagrama de clases de la sección 7.1.

ValidatorService solo se comunica con CatalogRepository, que es el único componente con acceso a las tablas del catálogo en PostgreSQL.

Por último, el cliente Android descarga los archivos de animación directamente del Servidor estático de GLB, sin pasar por el Controller.

### 6.2. Vista Física del Sistema

Para la Vista Física del Sistema se usa un diagrama de despliegue, ya que permite mostrar en qué máquinas y contenedores corre cada componente, y qué protocolo de comunicación usa cada conexión entre ellos.

**Figura 2: Diagrama de despliegue de la Vista Física del Sistema**

![Figura 2: Diagrama de despliegue de la Vista Física del Sistema](diagrams/sdd-6.2-vista-fisica-despliegue.drawio.png)

Elementos del diagrama:
- **Android Device** («device», Android 8.0+ / API 26+) contiene el **Android Client**.
  - Canal `«WSS» translation session (audio + results)` hacia el Backend.
  - Canal `«HTTPS» GLB asset download` hacia el Static GLB Server.
- **Demo / Dev Host** («device», máquina personal con GPU RTX 3050), que contiene dos contenedores Docker:
  - **Backend Container** («execution environment» Docker): Controller, Orchestrator, NLPService, ValidatorService, CatalogRepository, Static GLB Server.
  - **STT Container** («execution environment» Docker): STT Service (Whisper). Protocolo entre Backend y STT: TBD.
- Servicios en la nube:
  - **External LLM API** («cloud service», pay-per-use), conectado desde el Backend por HTTPS.
  - **Neon PostgreSQL** («cloud service», managed DB), conectado desde el Backend mediante protocolo PostgreSQL sobre TLS.

El cliente Android corre en el dispositivo del usuario (Android 8.0 o superior) y se comunica con el backend por dos canales distintos: un canal WebSocket que transporta tanto el audio como los resultados de la traducción, y un canal HTTPS aparte para descargar los archivos de animación GLB.

El backend corre en un mismo equipo físico, una máquina personal, dividido en dos contenedores Docker: el contenedor del backend, que agrupa Controller, Orchestrator, NLPService, ValidatorService, CatalogRepository y el Servidor estático de GLB, y el contenedor del Servicio STT, que corre aparte por su consumo de GPU y VRAM.

El backend se comunica además con dos servicios en la nube: la API del LLM externo, por HTTPS, y Neon PostgreSQL, mediante el protocolo nativo de PostgreSQL sobre TLS.

### 6.3. Vista de Procesos del Sistema

Para la Vista de Procesos del Sistema se usa un diagrama de actividades, ya que la aplicación tiene un único flujo de interacción de punta a punta, sin variantes de proceso que ameriten varios diagramas.

**Figura 3: Diagrama de actividades de la Vista de Procesos del Sistema**

![Figura 3: Diagrama de actividades de la Vista de Procesos del Sistema](diagrams/sdd-6.3-vista-procesos-actividades.drawio.png)

El flujo se divide en tres carriles: Usuario, App Android y Backend.

1. El usuario activa el micrófono y habla.
2. La app captura el audio y lo transmite continuamente por WebSocket.
3. El backend transcribe los fragmentos de audio (STT) y la app muestra el texto parcial en pantalla.
4. Al detectar 1.5 segundos de silencio:
   - `GlossAnalyzer` calcula la huella gramatical (*fingerprint*) del texto.
   - `SemanticCache` busca una coincidencia por texto y huella.
     - Si hay acierto (**cache hit**): se reutiliza el resultado guardado.
     - Si no (**cache miss**): `LLMClient` obtiene las glosas desde el LLM externo (HTTPS) y `SemanticCache` guarda la huella junto con las glosas para futuras búsquedas.
   - En ambos casos, el tipo de frase del segmento siempre proviene de la huella calculada localmente, **nunca del LLM**.
5. Se arma el segmento con el tipo de la huella y las glosas.
6. `ValidatorService` valida cada glosa contra el catálogo:
   - Si la glosa existe: resuelve la ruta de animación GLB.
   - Si no existe: marca la glosa como "seña no disponible".
7. Se arma el resultado (segmentos + tipo + rutas GLB) y se envía al Android Client.
8. El Android Client descarga los archivos GLB faltantes y reproduce las animaciones aplicando los marcadores no manuales (MNM) según el tipo de cada segmento.

---

## 7. Diseño Detallado

El diseño detallado de SignAI se describe en cuatro subsecciones. La **Estructura del Sistema** presenta las clases del backend y sus relaciones. El **Comportamiento del Sistema** muestra, mediante un diagrama de secuencia, cómo colaboran esas clases a lo largo de una traducción completa. La **Persistencia** describe las tablas que el sistema usa para guardar el catálogo de señas y el caché semántico. Por su parte, la **Interfaz de Usuario** describe los estados por los que pasa la pantalla única de la aplicación.

### 7.1. Estructura del Sistema

La estructura interna del backend se presenta en tres diagramas de clases: orquestación, NLP, y validación con catálogo. Las clases que ya aparecen detalladas en otro diagrama se muestran aquí como referencia, con una nota que indica dónde se desarrollan por completo.

#### Diagrama de Clases — Orquestación (Controller y Orchestrator)

**Figura 4: Diagrama de clases de Orquestación**

![Figura 4: Diagrama de clases de Orquestación](diagrams/sdd-7.1-clases-1-orquestacion.drawio.png)

Clases y elementos principales:
- **Controller**
  - Atributos: `orchestrator: Orchestrator`, `sttClient: SttServiceClient`
  - Métodos:
    - `+ handleAudioChunk(chunk: ByteArray): void`
    - `+ handleTranscript(text: String, isFinal: Boolean): void`
    - `+ sendResult(segments: List<ValidatedSegment>): void`
- **«interface» SttServiceClient** (detalle completo fuera de este diagrama)
- **Orchestrator**
  - Atributos: `nlpService: NLPService`, `validatorService: ValidatorService`
  - Métodos: `+ translate(text: String): List<ValidatedSegment>`
- **«interface» NLPService** — `+ transform(text: String): List<Segment>` (detalle completo en el Diagrama de NLP)
- **«interface» ValidatorService** — `+ validate(segments: List<Segment>): List<ValidatedSegment>` (detalle completo en el diagrama de Validación y Catálogo)
- **ValidatedSegment** (detalle completo en diagrama de NLP)

Controller mantiene una referencia a `Orchestrator` y a `SttServiceClient`, y expone tres métodos: `handleAudioChunk(chunk)` recibe cada fragmento de audio que llega del cliente Android y lo reenvía a `SttServiceClient`; `handleTranscript(text, isFinal)` recibe la transcripción, ya sea parcial o final, de vuelta desde el servicio de STT; y `sendResult(segments)` envía el resultado final de la traducción al cliente. Cuando el texto llega marcado como final, Controller lo entrega a Orchestrator a través de su único método público, `translate(text)`.

Orchestrator mantiene referencias a `NLPService` y `ValidatorService`, ambas como interfaces en vez de implementaciones concretas. Dentro de `translate(text)`, primero llama a `NLPService.transform(text)` para obtener la lista de segmentos con sus glosas, y luego pasa esa lista a `ValidatorService.validate(segments)`, cuyo resultado, una lista de `ValidatedSegment`, es lo que Orchestrator devuelve a Controller. La estructura de `ValidatedSegment` se desarrolla más adelante en esta misma sección.

Dentro de NLPService, la transformación de texto a glosas involucra varias entidades, las cuales se detallan en el siguiente diagrama.

#### Diagrama de Clases — NLP

**Figura 5: Diagrama de clases de NLP**

![Figura 5: Diagrama de clases de NLP](diagrams/sdd-7.1-clases-2-nlp.drawio.png)

Clases y elementos principales:
- **NLPServiceImpl** implementa `NLPService`
  - Atributos: `analyzer: GlossAnalyzer`, `cache: SemanticCache`, `llmClient: LLMClient`
  - Método: `+ transform(text: String): List<Segment>`
- **GlossAnalyzer**
  - `+ analyze(text: String): Fingerprint`
- **SemanticCache**
  - `+ lookup(text: String, fingerprint: Fingerprint): List<Segment>?`
  - `+ store(text: String, fingerprint: Fingerprint, segments: List<Segment>): void`
- **LLMClient**
  - Atributos: `model: String`, `temperature: Double`, `timeoutMs: Int`
  - `+ transform(text: String): List<String>`
  - Se apoya en **External LLM API** y en **PostgreSQL (pgvector)** (para `SemanticCache`)
- **Fingerprint**
  - Atributos: `category: PhraseType`, `secondarySignals: List<PhraseType>`, `hasCollision: Boolean`
- **PhraseType** (enum): `AFFIRMATIVE`, `YES_NO_QUESTION`, `CONTENT_QUESTION`, `NEGATIVE`, `IMPERATIVE`
- **Segment**
  - Atributos: `type: PhraseType`, `glosses: List<String>`

`NLPServiceImpl` implementa la interfaz `NLPService` apoyándose en tres colaboradores, referenciados como atributos: `analyzer` (`GlossAnalyzer`), `cache` (`SemanticCache`) y `llmClient` (`LLMClient`). `GlossAnalyzer` expone un único método, `analyze(text)`, que calcula la huella gramatical del texto y la devuelve como un objeto `Fingerprint`, con tres atributos: `category` (el tipo de frase que determinan las reglas gramaticales), `secondarySignals` (otras señales de tipo detectadas en el mismo texto) y `hasCollision` (si hubo más de una señal en conflicto).

Con esa huella calculada, `NLPServiceImpl` llama a `SemanticCache.lookup(text, fingerprint)`, que busca una traducción ya resuelta comparando tanto el embedding del texto como el tipo de frase de la huella. Si no hay coincidencia, se invoca `LLMClient.transform(text)`, cuyos atributos (`model`, `temperature`, `timeoutMs`) configuran la llamada al modelo de lenguaje externo; su responsabilidad se limita a devolver la lista de glosas, sin opinar sobre el tipo de frase. El resultado se guarda con `SemanticCache.store(text, fingerprint, segments)` para futuras búsquedas. En cualquiera de los dos caminos, `NLPServiceImpl` arma cada `Segment` con `buildSegment(fingerprint, glosses)`, de modo que el tipo de frase siempre proviene de la huella calculada por `GlossAnalyzer`, **nunca del LLM**. `Segment` queda entonces compuesto por `type` (`PhraseType`) y `glosses` (la lista de texto plano de las glosas), y `PhraseType` enumera las cinco categorías posibles: afirmativa, interrogativa de sí o no, interrogativa de contenido, negativa e imperativa.

La validación de esas glosas contra el catálogo, y la resolución de sus rutas de animación, se muestran en el tercer diagrama.

#### Diagrama de Clases — Validación y Catálogo

**Figura 6: Diagrama de clases de Validación y Catálogo**

![Figura 6: Diagrama de clases de Validación y Catálogo](diagrams/sdd-7.1-clases-3-validacion-catalogo.drawio.png)

Clases y elementos principales:
- **ValidatorServiceImpl** implementa `ValidatorService`
  - `+ validate(segments: List<Segment>): List<ValidatedSegment>`
  - Atributo: `catalogRepository: CatalogRepository`
- **CatalogRepository**
  - Atributo: `cache: Map<String, CatalogEntry>`
  - `+ loadAll(): void`
  - `+ search(gloss: String): CatalogEntry?`
- **CatalogEntry**
  - Atributos: `gloss: String`, `glbPath: String`
- **Gloss**
  - Atributos: `text: String`, `available: Boolean`, `glbPath: String`
- **PhraseType** (referenciado desde el diagrama de NLP)
- **ValidatedSegment**
  - Atributos: `type: PhraseType`, `glosses: List<Gloss>`

`ValidatorServiceImpl` implementa la interfaz `ValidatorService` y depende de `CatalogRepository`, al que mantiene como atributo. Su único método, `validate(segments)`, recorre las glosas de cada segmento y, por cada una, llama a `CatalogRepository.search(gloss)`. `CatalogRepository` mantiene en memoria un mapa (`cache`, de tipo `Map<String, CatalogEntry>`) que se carga una sola vez con `loadAll()` al arrancar el backend; a partir de ahí, `search(gloss)` resuelve las búsquedas contra ese mapa en memoria en lugar de consultar PostgreSQL en cada solicitud. Cada `CatalogEntry` tiene dos atributos, `gloss` y `glbPath`.

Con esa información, `ValidatorServiceImpl` construye un objeto `Gloss` por cada glosa, con tres atributos: `text`, `available` (si la glosa existe en el catálogo) y `glbPath` (la ruta de su animación, vacía si no está disponible). El resultado se agrupa en `ValidatedSegment`, que conserva el `type` del segmento original junto con la lista de `glosses`, ahora ya resueltas, y es esa lista de `ValidatedSegment` la que finalmente recibe Orchestrator.

### 7.2. Comportamiento del Sistema

El comportamiento del sistema se documenta en un único diagrama de secuencia, que cubre el flujo completo de una traducción, desde que Controller recibe el texto final hasta que arma el resultado que se envía al cliente.

**Figura 7: Diagrama de secuencia del flujo de traducción**

![Figura 7: Diagrama de secuencia del flujo de traducción](diagrams/sdd-7.2-secuencia-flujo-traduccion.drawio.png)

Participantes: `Controller`, `Orchestrator`, `NLPServiceImpl`, `GlossAnalyzer`, `SemanticCache`, `LLMClient`, `ValidatorServiceImpl`, `CatalogRepository`.

Secuencia (resumen de los pasos numerados en el diagrama):

1. `Controller` → `Orchestrator`: `translate(text)`
2. `Orchestrator` → `NLPServiceImpl`: `transform(text)`
3. `NLPServiceImpl` → `GlossAnalyzer`: `analyze(text)` → devuelve `Fingerprint`
4. `NLPServiceImpl` → `SemanticCache`: `lookup(text, fingerprint)`
   - **Fase NLP — cache hit:** `SemanticCache` devuelve glosas; `NLPServiceImpl` las reutiliza directamente, sin llamar al LLM.
   - **Fase NLP — cache miss:**
     5. `NLPServiceImpl` → `LLMClient`: `transform(text)` (HTTPS a la API del LLM externo)
     6. `LLMClient` devuelve `glosses`
     7. `NLPServiceImpl` → `SemanticCache`: `store(text, fingerprint, glosses)`
5. `NLPServiceImpl` devuelve la `List<Segment>` a `Orchestrator`.
6. `Orchestrator` → `ValidatorServiceImpl`: `validate(segments)` — **Fase Validación**
   - Para cada glosa del segmento:
     - `ValidatorServiceImpl` → `CatalogRepository`: `search(gloss)` → devuelve `CatalogEntry` o `null`
     - Si existe: arma `Gloss(available=true, glbPath=...)`
     - Si no existe: arma `Gloss(available=false)`
7. `ValidatorServiceImpl` devuelve `List<ValidatedSegment>` a `Orchestrator`, que la reenvía a `Controller` como resultado final.

Controller entrega el texto a Orchestrator mediante `translate(text)`, y este llama a `NLPService.transform(text)` para iniciar la fase de NLP. Dentro de esa llamada, `NLPServiceImpl` invoca primero `GlossAnalyzer.analyze(text)`, el cual devuelve la huella gramatical del texto. Con esa huella, llama a `SemanticCache.lookup(text, fingerprint)`, que compara tanto el embedding del texto como el tipo de frase de la huella contra lo ya guardado.

Si hay acierto en el caché, `NLPServiceImpl` reutiliza directamente las glosas devueltas. Si no lo hay, invoca `LLMClient.transform(text)`, que hace la llamada HTTPS al LLM externo y devuelve la lista de glosas, y guarda ese resultado con `SemanticCache.store(text, fingerprint, glosses)` para futuras búsquedas. En cualquiera de los dos caminos, `NLPServiceImpl` arma el segmento con `buildSegment(fingerprint, glosses)`, tomando el tipo de frase según la huella, y devuelve la lista de `Segment` a Orchestrator.

Con esa lista, Orchestrator llama a `ValidatorService.validate(segments)`. `ValidatorServiceImpl` recorre cada glosa del segmento y, por cada una, llama a `CatalogRepository.search(gloss)`. Cuando la glosa existe en el catálogo, arma un `Gloss` con `available=true` y la ruta de su animación; cuando no existe, lo arma con `available=false`. Terminado el recorrido, `ValidatorServiceImpl` devuelve la lista de `ValidatedSegment` a Orchestrator. Este la reenvía a Controller como resultado final de la traducción.

Antes de que arranque esta secuencia, `CatalogRepository` ya ejecutó `loadAll()` al iniciar el backend, por lo que las búsquedas de `search(gloss)` se resuelven contra el catálogo en memoria, sin consultar PostgreSQL en cada solicitud.

### 7.3. Persistencia

La persistencia del sistema se documenta con un diagrama relacional, ya que las dos tablas que maneja el backend no tienen relaciones entre sí y su estructura se describe mejor con columnas y tipos de dato concretos que con un modelo entidad-relación.

**Figura 8: Modelo relacional de persistencia**

![Figura 8: Modelo relacional de persistencia](diagrams/sdd-7.3-persistencia-relacional.drawio.png)

**Tabla `catalog`**

| Columna | Tipo | Notas |
|---|---|---|
| `id_sign` | INTEGER (PK) | Llave primaria |
| `gloss` | VARCHAR (indexed) | Indexado; es el valor por el que `CatalogRepository` busca en cada validación |
| `semantic_category` | VARCHAR | Clasifica la seña dentro del corpus |
| `glb_animation_path` | VARCHAR | Ruta usada por `ValidatorServiceImpl` para construir cada `Gloss` |
| `modified_at` | TIMESTAMP | Permite detectar cambios en el catálogo sin reiniciar el backend |

**Tabla `semantic_cache`**

| Columna | Tipo | Notas |
|---|---|---|
| `id` | INTEGER (PK) | Llave primaria |
| `original_text` | TEXT | La oración tal como llegó |
| `embedding` | VECTOR(384) | Representación vectorial calculada por un modelo de embeddings local; pgvector como motor de comparación por similitud |
| `phrase_type` | VARCHAR | Mismo valor que `Fingerprint.category`; junto con `embedding` es lo que `SemanticCache` compara en cada búsqueda |
| `glosses` | TEXT[] | Lista de glosas de la traducción |
| `secondary_signals` | TEXT[] | Qué otras señales de tipo detectó `GlossAnalyzer` en el mismo texto |
| `had_collision` | BOOLEAN | Si hubo alguna colisión entre señales — pensado para medir con datos reales qué tan seguido ocurre ese caso |
| `created_at` | TIMESTAMP | Cuándo se guardó cada entrada |

La tabla `catalog` guarda las 50 glosas del corpus, con `id_sign` como llave primaria. El campo `gloss` está indexado, ya que es el valor por el que `CatalogRepository` busca en cada solicitud de validación. `semantic_category` clasifica la seña dentro del corpus, y `glb_animation_path` es la ruta que `ValidatorServiceImpl` usa para construir cada `Gloss`. `modified_at` permite detectar cambios en el catálogo sin reiniciar el backend.

La tabla `semantic_cache` guarda las traducciones que `SemanticCache` ya resolvió, con `id` como llave primaria. `original_text` conserva la oración tal como llegó, y `embedding` guarda su representación vectorial, calculada por un modelo de embeddings local, con la extensión pgvector de PostgreSQL como motor de comparación por similitud. `phrase_type` es el mismo valor que `Fingerprint.category`, y junto con `embedding` es lo que `SemanticCache` compara en cada búsqueda. `glosses` guarda la lista de glosas de la traducción, mientras que `secondary_signals` y `had_collision` registran, respectivamente, qué otras señales de tipo detectó `GlossAnalyzer` en el mismo texto y si hubo alguna colisión entre ellas, información pensada para medir con datos reales qué tan seguido ocurre ese caso. `created_at` registra cuándo se guardó cada entrada.

### 7.4. Interfaz de Usuario

La aplicación tiene una única pantalla, sin navegación entre vistas, por lo que la interfaz de usuario se documenta con un diagrama de estados en vez de uno de navegación. Cada estado representa lo que la pantalla muestra en un momento dado.

**Figura 9: Diagrama de estados de la interfaz de usuario**

![Figura 9: Diagrama de estados de la interfaz de usuario](diagrams/sdd-7.4-diagrama-estados-ui.drawio.png)

Estados: `Inactivo`, `Grabando`, `Texto listo`, `Procesando`, `Reproduciendo`, `Error`, `Desconectado`.

Transiciones principales:
- `Inactivo` → (activa micrófono) → `Grabando`
- `Grabando` → (detiene grabación / silencio detectado) → `Texto listo`
- `Texto listo` → (cancela / borra) → `Inactivo`
- `Texto listo` → (confirma envío) → `Procesando`
- `Procesando` → (resultado recibido) → `Reproduciendo`
- `Procesando` → (error en STT/NLP/LLM) → `Error`
- `Error` → (automático, ≤2 s) → `Inactivo`
- `Reproduciendo` → (animación termina) → `Inactivo`
- `Reproduciendo` → (pierde conexión WebSocket) → `Desconectado`
- `Desconectado` → (reconecta automático) → `Inactivo`

La pantalla inicia en `Inactivo`, con el micrófono apagado. Al activarlo, pasa a `Grabando`, y se mantiene ahí capturando audio hasta que el usuario detiene la grabación o el sistema detecta silencio, momento en el que pasa a `Texto listo`, con la transcripción final a la vista. Desde ese estado, el usuario puede confirmar el envío, pasando a `Procesando`, o cancelar y volver directamente a `Inactivo`.

Durante `Procesando`, si el resultado llega correctamente, la pantalla pasa a `Reproduciendo`, donde el avatar ejecuta la traducción; si alguno de los servicios de backend falla, pasa a `Error`, del cual se vuelve a `Inactivo` de forma automática en dos segundos o menos.

Desde `Reproduciendo`, la pantalla vuelve a `Inactivo` cuando la animación termina. Si en cambio se pierde la conexión por WebSocket durante la reproducción, pasa a `Desconectado`, y regresa a `Inactivo` una vez el cliente logra reconectarse.

---

## 8. Modelo C4

Además de las vistas de arquitectura presentadas en la sección 6, el sistema se documenta bajo el modelo C4, el cual permite observarlo en tres niveles de abstracción progresivos: contexto, contenedores y componentes. Cada nivel abre la caja del anterior: el contexto muestra el sistema completo frente a sus usuarios y dependencias externas, sin ningún detalle interno; los contenedores exponen los bloques tecnológicos que lo conforman; y los componentes desglosan el contenedor del Backend para mostrar sus piezas internas y cómo se comunican entre sí.

### 8.1. Contexto

El diagrama de contexto muestra a SignAI como una sola caja, junto con las personas que interactúan con el sistema y los sistemas externos de los que depende, sin entrar en su arquitectura interna.

**Figura 10: Diagrama de contexto del sistema (C4 Nivel 1)**

![Figura 10: Diagrama de contexto del sistema (C4 Nivel 1)](diagrams/sdd-c4-1-contexto.drawio.png)

El sistema tiene dos tipos de usuario. El **usuario oyente** activa el micrófono y habla en español, mientras que el **usuario sordo o usuario LSC** observa la traducción que el sistema ejecuta a través de su avatar 3D. Ambos interactúan desde la misma aplicación Android, en momentos distintos del flujo de traducción.

El único sistema externo del que depende SignAI es la **API del LLM externo**, a la que se envía el texto transcrito para transformarlo en glosas de Lengua de Señas Colombiana. PostgreSQL y el servicio de transcripción de voz no aparecen en este diagrama ya que, en este nivel de abstracción, se consideran parte del propio sistema y no un tercero del que dependa.

### 8.2. Contenedores

El diagrama de contenedores muestra los bloques tecnológicos que componen el sistema, junto con el protocolo de comunicación que usa cada conexión entre ellos.

**Figura 11: Diagrama de contenedores del sistema (C4 Nivel 2)**

![Figura 11: Diagrama de contenedores del sistema (C4 Nivel 2)](diagrams/sdd-c4-2-contenedores.drawio.png)

El Android Client se comunica con el Backend por dos canales: uno WebSocket, que transporta el audio y devuelve el resultado de la traducción, y uno HTTPS, para descargar los archivos de animación GLB.

El Backend, a su vez, se comunica con el STT Container para transcribir el audio y con PostgreSQL para leer y escribir el catálogo de señas y el caché semántico. Hacia afuera, envía el texto transcrito a la API del LLM externo para transformarlo en glosas.

El Backend y el STT Container corren en contenedores Docker separados, mientras que PostgreSQL es una instancia gestionada en Neon.

### 8.3. Componentes

El diagrama de componentes desglosa el Backend y muestra sus piezas internas, junto con las interfaces por las que cada una se comunica.

**Figura 12: Diagrama de componentes del Backend (C4 Nivel 3)**

![Figura 12: Diagrama de componentes del Backend (C4 Nivel 3)](diagrams/sdd-c4-3-componentes-backend.drawio.png)

El Controller recibe la conexión WebSocket del Android Client y se comunica con el STT Container para transcribir el audio. Una vez tiene el texto, lo entrega al Orchestrator mediante `translate(text)`, el cual llama primero a NLPService con `transform(text)` y después a ValidatorService con `validate(segments)`.

NLPService depende de PostgreSQL para las búsquedas por pgvector en el caché semántico, y de la API del LLM externo cuando no encuentra una coincidencia. ValidatorService solo se comunica con CatalogRepository, que a su vez consulta el catálogo en PostgreSQL.

Por fuera de este flujo, el Android Client descarga los archivos de animación directamente del Static GLB Server, sin pasar por el Controller.

---

## 9. Referencias

1. ISO/IEC/IEEE 42010.
2. IEEE Std 1016-2009.
3. RUP. *Software Architecture Document*. http://www.ts.mah.se/RUP/RationalUnifiedProcess/webtmpl/templates/a_and_d/rup_sad.htm
4. Philippe Kruchten, *Architectural Blueprints — The "4+1" View Model of Software Architecture*. http://www.cs.ubc.ca/~gregor/teaching/papers/4+1view-architecture.pdf
5. Scott Ambler, *UML Data Modeling Profile*. http://www.agiledata.org/essays/umlDataModelingProfile.html
6. Scott Ambler, *User Interface Flow Diagrams*. http://www.agilemodeling.com/artifacts/uiFlowDiagram.htm
