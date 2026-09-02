# Documento de Requerimientos Consolidados — SignAI

**Versión:** 0.15 | **Estado:** Borrador (primera versión completa, pendiente de validación) | **Fecha:** 11 de agosto de 2026



# Historial de cambios

| **Versión** | **Fecha** | **Cambios** |
| --- | --- | --- |
| 0.1 | 10/08/2026 | Creación del documento. Esqueleto vacío, estructura calcada del SRS original (sección de funcionales por módulo separada de las de no funcionales). |
| 0.2 | 10/08/2026 | Se agrega la nota de convenciones sobre valores numéricos. Se redactan RF-STT-01, RF-STT-02 y RF-STT-03 (revisado: el envío al NLP ya no es automático, requiere confirmación del usuario). Queda pendiente en UI el requerimiento del botón de confirmar envío y edición de texto. |
| 0.3 | 10/08/2026 | Se redactan RF-NLP-01 a RF-NLP-04 (traducción a glosas, generación mediante LLM, identificación local del tipo de frase, caché semántica). El NLP no valida contra el catálogo, esa función queda pendiente para la sección 3.4. Deletreo intencionalmente no incluido por ahora. |
| 0.4 | 10/08/2026 | Se redactan RF-AVT-01 a RF-AVT-05 (carga del avatar, ejecución de animaciones, marcadores no manuales, interpolación, estado de reposo). Quedan pendientes para la sección 4 los valores de FPS y de duración máxima de transición entre señas, y para la sección 5 la limitación de uso del espacio (LIM-01). |
| 0.5 | 10/08/2026 | Se redactan RF-CAT-01 a RF-CAT-03 (almacenamiento del catálogo, validación de glosas, manejo de glosas no encontradas). Se resuelve la nota pendiente que había quedado desde NLP. El comportamiento de “Seña no disponible”, que originalmente estaba en RF-NLP-02, se traslada aquí. |
| 0.6 | 10/08/2026 | Se redactan RF-UI-01 a RF-UI-05 (control de captura con tres estados, barra de transcripción, distribución de pantalla, permisos, señalización de estados del sistema). Se resuelve el pendiente de confirmación de envío que había quedado desde STT. Se completa la sección 3. Queda anotado que la sección 2.1 usará el prefijo RF-INT-USR para no chocar con RF-UI de esta sección. |
| 0.7 | 11/08/2026 | Trabajo paralelo del equipo: se redactan RNF-REL-01 a 04, RNF-AV-01 a 03, RNF-SEC-01 a 03, RNF-MNT-01 a 05 y RNF-POR-01 a 04 (secciones 6.1 a 6.5). Los valores numéricos se expresan como rangos u órdenes de magnitud, no como compromisos cerrados. Varios quedan marcados como provisionales en tanto los ADR de los que dependen (ADR-005, ADR-006, ADR-007, ADR-011, ADR-012, ADR-013, ADR-014) no se cierren. |
| 0.8 | 11/08/2026 | Corrección de arquitectura confirmada por el equipo: el proyecto pasa de microservicios a monolito (cada función del pipeline como servicio interno dentro de un único despliegue), por recomendación del profesor de arquitectura consultado. Se actualizan RNF-MNT-02, RNF-POR-02 y RNF-AV-01 en consecuencia. Se fusiona el trabajo paralelo del equipo en las secciones 6.1 a 6.5, y se agregan títulos descriptivos a todos los requerimientos ya redactados (secciones 3 y 6). Queda pendiente que el equipo actualice ADR-011 en el ADR Log, que hoy sigue registrado como “Decidida” a favor de microservicios. |
| 0.9 | 11/08/2026 | Se redactan RF-INT-USR-01 y RF-INT-USR-02 (sección 2.1). El resto del contenido original de esta subsección del SRS (área de visualización del avatar, componente de transcripción, control de captura) queda cubierto por la sección 3 y no se repite aquí. |
| 0.10 | 11/08/2026 | Se redactan RF-INT-HW-01 a RF-INT-HW-04 (sección 2.2): micrófono, aceleración gráfica, conectividad y almacenamiento local de animaciones. Este último no estaba en el SRS original. |
| 0.11 | 11/08/2026 | Se redactan RF-INT-SW-01 a RF-INT-SW-04 (sección 2.3): reconocimiento de voz local, dependencia del LLM externo, persistencia relacional, framework del backend. Se dejan fuera el motor de renderizado del cliente y las versiones de librerías, por ser decisiones de implementación, no interfaces externas. |
| 0.12 | 11/08/2026 | Se redactan RF-INT-COM-01 a RF-INT-COM-03 (sección 2.4): canal persistente WebSocket, canal transaccional HTTP, cifrado de comunicaciones externas. Se cierra la sección 2 completa (interfaces externas). |
| 0.13 | 11/08/2026 | Se redactan RNF-DES-01 a RNF-DES-06 (sección 4). El punto de inicio de la latencia extremo a extremo cambia de “fin de voz” a “confirmación de envío del usuario”, por RF-STT-03. La latencia del NLP y la E2E se expresan en dos rangos (acierto de caché / llamada al LLM). La disponibilidad no se repite aquí, ya vive en RNF-AV-01 (6.2). Se resuelven los pendientes de FPS y duración de transición que venían desde Avatar. |
| 0.14 | 11/08/2026 | Se redactan RD-01 a RD-05 (sección 5): corpus cerrado, traducción unidireccional, avatar sin uso del espacio (LIM-01), infraestructura real distinta a la declarada (LIM-08), variabilidad de respuesta del LLM (LIM-06). Se adopta el prefijo RD, sin precedente en el SRS original. Se deja anotado que LIM-07 (microservicios como sobrecarga aceptada) ya no aplica desde el cambio a monolito de la v0.8. |
| 0.15 | 11/08/2026 | Se redactan RNF-BD-01 a RNF-BD-03 (sección 7): consultas parametrizadas, llave primaria autoincremental, carga del catálogo en memoria. Se deja fuera la indexación por glosa, de valor marginal con 50 registros. Queda pendiente de confirmar con el equipo un ajuste a RNF-MNT-01 (6.4) para resolver su tensión con la carga en memoria (INC-08); no se modifica todavía. Con esta sección, el documento completa su primera versión de todas las secciones. |

# 0. Propósito y alcance de este documento

Este documento consolida, en un solo lugar y con redacción propia del equipo, los requerimientos funcionales y no funcionales de SignAI. No reemplaza el SRS original (fuente F02 del Documento Maestro), sino que lo reconstruye de forma coherente con las decisiones ya tomadas o en curso en el Architecture Backlog y el ADR Log, manteniendo la estructura y el formato del SRS original.

Todo el contenido de este documento tiene carácter de borrador hasta nueva indicación. Los requerimientos que dependan de una decisión aún no cerrada (estado "En análisis" o "En evaluación" en el ADR Log) se marcan explícitamente como provisionales y no se redactan con precisión que todavía no existe.

*Nota de arquitectura (v0.8): el equipo confirmó el paso de microservicios a monolito, por recomendación del profesor de arquitectura consultado. Esto contradice el estado actual de ADR-011 en el ADR Log, que sigue registrado como “Decidida” a favor de microservicios. Este documento ya refleja el monolito; el ADR Log todavía no. Queda como acción pendiente del equipo actualizar formalmente ADR-011.*

# 1. Convenciones y plantilla por requerimiento

Cada requerimiento individual se documenta con los siguientes campos:

| **Campo** | **Uso** |
| --- | --- |
| ID | Identificador del requerimiento, con un título corto (ej. RF-STT-01, Captura continua de audio) |
| Descripción | Qué debe hacer o cumplir el sistema |
| Razón | Por qué existe el requerimiento |
| Casos de uso asociados | CU-XX relacionados |
| Criterio de aceptación | Cómo se verifica que el requerimiento se cumple |
| Prioridad | Alta / Media / Baja |
| Relacionado con (opcional) | ADR-XX / DEC-XX / TSK-XX, solo si el requerimiento depende de o está bloqueado por una decisión o tarea del Architecture Backlog / ADR Log |

## 1.1 Valores numéricos (tiempos, latencias, umbrales)

Ningún requerimiento funcional (RF) incluye valores numéricos de tiempo. Los números de latencia, throughput o umbrales similares se ubican únicamente en los requerimientos no funcionales (secciones 4 y 6), y se expresan como estimaciones, rangos u órdenes de magnitud, no como compromisos cerrados. Estos valores quedan sujetos a confirmación mediante las tareas de medición correspondientes (TSK-03, TSK-04, TSK-05) y pueden ajustarse una vez existan datos reales sobre el hardware disponible.

# 2. Requerimientos de interfaces externas

## 2.1 Interfaz con el usuario

*Los requerimientos de esta subsección usan el prefijo RF-INT-USR (no RF-UI), para no chocar con los RF-UI de la sección 3.5, que describen otro contenido.*

*Esta subsección queda deliberadamente corta. El área de visualización del avatar (interpolación, marcadores no manuales) ya está cubierta por RF-AVT-03 y RF-AVT-04 (3.3); el componente de transcripción, por RF-STT-02 y RF-UI-02 (3.1 y 3.5); y el control de captura, por RF-UI-01 (3.5). Aquí solo se documentan aspectos de la interfaz que no quedaron cubiertos en esos módulos.*

**REQUERIMIENTO: RF-INT-USR-01, Proporción del contenedor del avatar**

| Descripción | El contenedor donde se renderiza el avatar mantendrá su relación de aspecto sin deformarse, sin importar el tamaño o la orientación de la pantalla del dispositivo. |
| --- | --- |
| Razón | Evitar que el avatar se vea distorsionado en dispositivos con proporciones de pantalla distintas, lo cual afectaría la legibilidad de las señas. |
| Casos de uso asociados | CU-03 |
| Criterio de aceptación | Al cambiar el tamaño o la orientación de la pantalla, el avatar se redimensiona sin deformarse. |
| Prioridad | Media |
| Relacionado con | RF-UI-03 (distribución de pantalla, no la forma del avatar) |

**REQUERIMIENTO: RF-INT-USR-02, Legibilidad de la transcripción en distintas resoluciones**

| Descripción | El texto de la barra de transcripción se mostrará de forma legible en las distintas resoluciones de pantalla soportadas por la aplicación. |
| --- | --- |
| Razón | Garantizar que el usuario oyente pueda verificar el texto transcrito sin importar el dispositivo que use. |
| Casos de uso asociados | CU-04 |
| Criterio de aceptación | El texto de la barra de transcripción permanece legible, sin recortarse ni superponerse, en las resoluciones de pantalla soportadas. |
| Prioridad | Baja |
| Relacionado con | RF-UI-02 (existencia y edición del componente, no su legibilidad en distintas resoluciones) |

## 2.2 Interfaz con el hardware

**REQUERIMIENTO: RF-INT-HW-01, Acceso al micrófono**

| Descripción | La aplicación accederá al micrófono del dispositivo a través de las APIs nativas del sistema operativo, sin requerir hardware ni controladores adicionales. |
| --- | --- |
| Razón | El micrófono es el único canal de entrada de audio del sistema, depender de las APIs nativas evita fricciones de compatibilidad. |
| Casos de uso asociados | CU-02, CU-05 |
| Criterio de aceptación | La app captura audio usando exclusivamente las APIs de audio provistas por el sistema operativo del dispositivo. |
| Prioridad | Alta |
| Relacionado con | RF-STT-01 (comportamiento de captura), RF-UI-04 (permisos) |

**REQUERIMIENTO: RF-INT-HW-02, Aceleración gráfica para el avatar**

| Descripción | El dispositivo deberá contar con soporte de aceleración gráfica por hardware para el renderizado del avatar en tres dimensiones. |
| --- | --- |
| Razón | Sin aceleración gráfica, el avatar no podría renderizarse con la fluidez necesaria para que las señas sean comprensibles. |
| Casos de uso asociados | CU-03 |
| Criterio de aceptación | La app verifica o asume la disponibilidad de aceleración gráfica compatible antes de iniciar el renderizado del avatar. |
| Prioridad | Alta |
| Relacionado con | RF-AVT-01, RF-AVT-02 |

**REQUERIMIENTO: RF-INT-HW-03, Dependencia de conectividad**

| Descripción | La aplicación requerirá conexión a internet activa para operar, ya que el procesamiento de voz y traducción ocurre en el backend, no en el dispositivo. |
| --- | --- |
| Razón | La app no tiene forma de traducir sin comunicarse con el backend, no hay modo sin conexión. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | Sin conexión a internet, la app no puede iniciar el flujo de traducción y lo indica al usuario. |
| Prioridad | Alta |
| Relacionado con | RF-UI-05 (señalización de estados, incluyendo desconexión) |

**REQUERIMIENTO: RF-INT-HW-04, Almacenamiento local de las animaciones del corpus**

| Descripción | El dispositivo deberá tener espacio de almacenamiento disponible para las animaciones del corpus, que se cargarán localmente al iniciar una sesión, en lugar de descargarse durante la traducción. |
| --- | --- |
| Razón | Con un corpus cerrado de tamaño reducido, cargar las animaciones de forma local evita depender de descargas mientras el usuario está traduciendo. Esta estrategia es adecuada para el alcance actual de 50 señas, y quedaría sujeta a revisión si el corpus creciera en una versión futura del sistema. |
| Casos de uso asociados | CU-03 |
| Criterio de aceptación | La app cuenta con espacio suficiente para almacenar las animaciones del corpus antes de iniciar una sesión de traducción. |
| Prioridad | Media |
| Relacionado con | ADR-012 (Propuesta, bloqueada por TSK-04, define si cada archivo incluye solo movimiento o también malla, lo cual determina el tamaño real) |

## 2.3 Interfaz con el software

*Esta subsección cubre fronteras reales de integración del sistema, no las herramientas internas con las que se construye. El framework del backend y el motor de renderizado del cliente son decisiones de implementación y quedan fuera de esta lista, salvo el caso puntual de FastAPI señalado abajo.*

**REQUERIMIENTO: RF-INT-SW-01, Reconocimiento de voz como componente interno**

| Descripción | El modelo de reconocimiento de voz se ejecutará como un componente interno del backend, no como una llamada a un servicio externo por red. |
| --- | --- |
| Razón | Correr el modelo de forma local reduce la latencia y evita depender de la disponibilidad de un proveedor externo adicional para esta función. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | El flujo de transcripción no depende de una conexión de red hacia un proveedor externo de reconocimiento de voz. |
| Prioridad | Alta |
| Relacionado con | RF-STT-02, ADR-006 (en evaluación, bloqueada por TSK-03) |

**REQUERIMIENTO: RF-INT-SW-02, Dependencia de un modelo de lenguaje externo**

| Descripción | La generación de la traducción dependerá de un servicio externo de modelo de lenguaje, accedido por red mediante una API. |
| --- | --- |
| Razón | A diferencia del reconocimiento de voz, esta función sí depende de un proveedor externo, con implicaciones de disponibilidad, costo y seguridad ya cubiertas en otras secciones. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | El sistema se comunica con el proveedor del LLM mediante llamadas de red, sin que el modelo esté embebido dentro del backend. |
| Prioridad | Alta |
| Relacionado con | RF-NLP-02, ADR-007 (en evaluación, bloqueada por TSK-05), RNF-AV-03, RNF-SEC-03 |

**REQUERIMIENTO: RF-INT-SW-03, Persistencia mediante base de datos relacional**

| Descripción | El catálogo de señas se almacenará en una base de datos relacional (PostgreSQL), accedida por el backend como una dependencia externa. |
| --- | --- |
| Razón | La persistencia del catálogo requiere un motor de base de datos, y esta elección ya está tomada, sin las mismas incertidumbres que otros componentes del sistema. |
| Casos de uso asociados | CU-01 |
| Criterio de aceptación | El catálogo de señas se almacena y se consulta a través de una base de datos relacional. |
| Prioridad | Alta |
| Relacionado con | RF-CAT-01 |

**REQUERIMIENTO: RF-INT-SW-04, Framework del backend**

| Descripción | El backend se implementará sobre FastAPI, aprovechando su soporte para manejo asíncrono de peticiones y conexiones persistentes. |
| --- | --- |
| Razón | El sistema necesita sostener múltiples conexiones y el flujo continuo de audio sin que una tarea bloquee a las demás. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | El backend está construido sobre FastAPI y soporta peticiones concurrentes sin bloquear el hilo principal. |
| Prioridad | Media |
| Relacionado con | RNF-REL-01 |

## 2.4 Interfaz de comunicaciones

**REQUERIMIENTO: RF-INT-COM-01, Canal persistente (WebSocket)**

| Descripción | El sistema usará un canal WebSocket persistente y bidireccional entre la app y el backend, por el cual viaja el audio capturado en un sentido y las glosas junto con los datos de animación en el otro. El sistema detectará una desconexión del canal y se reconectará automáticamente. |
| --- | --- |
| Razón | El pipeline necesita mantener una conexión abierta mientras dura la sesión en vez de repetir peticiones independientes una por una, y detectar la desconexión es lo que permite que el avatar vuelva a reposo en vez de quedar congelado. |
| Casos de uso asociados | CU-02, CU-03 |
| Criterio de aceptación | El canal permanece abierto mientras dura la sesión, transporta audio y datos de animación sobre la misma conexión, y el sistema detecta una desconexión y reintenta reconectar. |
| Prioridad | Alta |
| Relacionado con | RF-STT-01, RNF-REL-02 |

**REQUERIMIENTO: RF-INT-COM-02, Canal transaccional (HTTP)**

| Descripción | El sistema usará peticiones HTTP independientes para operaciones que no necesitan mantener una conexión abierta. |
| --- | --- |
| Razón | Separar estas operaciones del canal WebSocket evita sobrecargarlo con tráfico que no depende de una conexión persistente. |
| Casos de uso asociados | CU-01 |
| Criterio de aceptación | Las operaciones puntuales se resuelven con peticiones HTTP, sin depender del canal WebSocket. |
| Prioridad | Baja |
| Relacionado con | Alcance exacto pendiente de DEC-20 (definición de sesión) |

**REQUERIMIENTO: RF-INT-COM-03, Cifrado de las comunicaciones externas**

| Descripción | Toda comunicación entre la app, el backend y los servicios externos viajará cifrada. |
| --- | --- |
| Razón | Generaliza como requisito de interfaz lo que ya se exige para datos personales, aplicándolo a todo el tráfico externo del sistema. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | Las conexiones del sistema usan cifrado, verificable mediante inspección del tráfico de red. |
| Prioridad | Alta |
| Relacionado con | RNF-SEC-03 |

# 3. Características del producto de software

*Requerimientos funcionales (RF), organizados por módulo. Los requerimientos no funcionales de cada módulo no van aquí, están en las secciones 4 (desempeño) y 6 (atributos del sistema), igual que en el SRS original.*

## 3.1 Captura y transcripción de voz (STT)

**REQUERIMIENTO: RF-STT-01, Captura continua de audio**

| Descripción | El sistema capturará el audio del usuario por el micrófono del dispositivo y lo enviará al backend por WebSocket en tiempo real, mientras el micrófono esté activo. El envío es continuo, no por bloques de varios segundos. |
| --- | --- |
| Razón | Que el usuario pueda hablar sin necesidad de escribir, y que el backend pueda empezar a transcribir mientras la persona todavía está hablando, no solo cuando termine. |
| Casos de uso asociados | CU-02, CU-05 |
| Criterio de aceptación | Al activar el micrófono, el audio llega al backend de manera continua, sin que el sistema tenga que esperar a juntar un bloque de tamaño fijo antes de enviarlo. |
| Prioridad | Alta |
| Relacionado con | INC-02, ADR-005 (bloqueada por TSK-03) |

**REQUERIMIENTO: RF-STT-02, Transcripción progresiva**

| Descripción | El sistema transcribirá el audio a texto en español usando el modelo Whisper y lo mostrará en la barra de transcripción de la app, actualizando el texto mientras el usuario habla y no solo cuando termine. |
| --- | --- |
| Razón | Que el usuario oyente pueda ver que el sistema está entendiendo bien lo que dice, sin esperar a que termine de hablar. |
| Casos de uso asociados | CU-02, CU-04 |
| Criterio de aceptación | El texto en la barra de transcripción se actualiza antes de que el usuario termine de hablar. El tiempo exacto de latencia se define en RNF-DES-02 (valor estimado, pendiente de TSK-03). |
| Prioridad | Alta |
| Relacionado con | ADR-005, ADR-006 (bloqueadas por TSK-03), INC-21 |

**REQUERIMIENTO: RF-STT-03, Confirmación antes de enviar al NLP**

| Descripción | El sistema detectará cuando el usuario deja de hablar, ya sea por un periodo de silencio o porque el usuario detiene el micrófono manualmente, y dejará el texto transcrito visible en la barra de transcripción. El sistema no enviará este texto al módulo de NLP de forma automática, el envío requiere una acción de confirmación del usuario. |
| --- | --- |
| Razón | Darle al usuario oportunidad de revisar o corregir lo que el sistema transcribió antes de que se traduzca, en vez de traducir de inmediato algo que pudo transcribirse mal. |
| Casos de uso asociados | CU-02, CU-04, CU-05 |
| Criterio de aceptación | Al detectar silencio o al detener el micrófono manualmente, la captura de audio se detiene y el texto queda disponible y editable en la barra, sin enviarse al NLP hasta que el usuario confirme el envío. |
| Prioridad | Media |
| Relacionado con | ADR-005 (bloqueada por TSK-03). Requiere RF-UI-01 (sección 3.5) para el botón o acción de confirmar envío y la edición del texto. |

## 3.2 Procesamiento semántico y traducción a glosas (NLP)

**REQUERIMIENTO: RF-NLP-01, Traducción a glosas LSC**

| Descripción | El sistema transformará el texto transcrito en una secuencia de glosas de LSC, siguiendo la gramática propia de la LSC y no el orden literal del español. |
| --- | --- |
| Razón | La LSC tiene su propia gramática, traducir palabra por palabra sería incomprensible para el usuario sordo. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | Para una frase del dominio, por ejemplo “¿Cuál es su nombre?”, el sistema entrega una secuencia de glosas que no sigue el orden literal de las palabras en español. El patrón exacto queda pendiente de validación con el intérprete. |
| Prioridad | Alta |
| Relacionado con | ADR-002 (en análisis) |

**REQUERIMIENTO: RF-NLP-02, Generación mediante LLM**

| Descripción | El sistema generará la secuencia de glosas mediante un modelo de lenguaje externo, entregándole la frase completa para su transformación gramatical a LSC. |
| --- | --- |
| Razón | Delegar la resolución de variaciones del lenguaje natural a un modelo capaz de interpretar distintas formas de decir lo mismo. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | Ante una frase que requiere traducción nueva, el sistema envía el texto al LLM externo y recibe una secuencia de glosas propuesta. Esta salida todavía no ha sido validada contra el catálogo de señas, esa verificación ocurre en un módulo distinto. |
| Prioridad | Alta |
| Relacionado con | ADR-007 (en evaluación, bloqueada por TSK-05) |

**REQUERIMIENTO: RF-NLP-03, Identificación del tipo de frase**

| Descripción | El sistema identificará el tipo de frase de forma local, sin depender del LLM, y lo incluirá junto con la secuencia de glosas en su salida. |
| --- | --- |
| Razón | El tipo de frase es información que las etapas posteriores del pipeline necesitan junto con las glosas. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | El sistema clasifica la frase en una categoría gramatical determinada localmente y la entrega junto con las glosas. |
| Prioridad | Alta |
| Relacionado con | ADR-008 (Propuesta) |

**REQUERIMIENTO: RF-NLP-04, Reutilización de traducciones (caché semántica)**

| Descripción | Antes de llamar al LLM, el sistema verificará si ya existe una traducción guardada para una frase igual o parecida, y la reutilizará si la encuentra. |
| --- | --- |
| Razón | Reducir la dependencia del LLM externo, bajar la latencia, y evitar que la misma frase se traduzca distinto cada vez que se repite. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | Para una frase ya procesada o suficientemente parecida, el sistema entrega la traducción guardada sin llamar al LLM. El criterio de similitud queda pendiente de diseño. |
| Prioridad | Media |
| Relacionado con | RSK-16, ADR-014 (en análisis) |

## 3.3 Visualización con avatar tridimensional

**REQUERIMIENTO: RF-AVT-01, Carga del avatar**

| Descripción | El sistema cargará el avatar en el área de visualización de la app a partir de archivos en formato GLB. |
| --- | --- |
| Razón | El avatar es el canal de salida visual para el usuario sordo, necesita estar disponible en pantalla antes de poder reproducir cualquier seña. |
| Casos de uso asociados | CU-03 |
| Criterio de aceptación | El avatar se carga correctamente en el área de visualización antes de reproducir una secuencia de señas. |
| Prioridad | Alta |
| Relacionado con | ADR-003, ADR-012 (ambas bloqueadas por TSK-04) |

**REQUERIMIENTO: RF-AVT-02, Ejecución de animaciones por glosa**

| Descripción | El sistema ejecutará la animación correspondiente a cada glosa recibida, con los movimientos de manos, brazos y cuerpo definidos para esa seña. |
| --- | --- |
| Razón | Cada seña tiene un movimiento específico que debe representarse fielmente para que el mensaje sea comprensible. |
| Casos de uso asociados | CU-03 |
| Criterio de aceptación | Para cada glosa de la secuencia recibida, el avatar reproduce la animación correspondiente registrada en el catálogo. |
| Prioridad | Alta |
| Relacionado con | ADR-003, ADR-004 (bloqueadas por TSK-04) |

**REQUERIMIENTO: RF-AVT-03, Marcadores no manuales**

| Descripción | El sistema aplicará expresiones faciales durante la reproducción de la secuencia, según el tipo de frase indicado por el NLP. |
| --- | --- |
| Razón | Los marcadores no manuales son parte de la gramática de la LSC, sin ellos el mensaje puede resultar ambiguo. |
| Casos de uso asociados | CU-03 |
| Criterio de aceptación | El avatar aplica la expresión facial correspondiente mientras reproduce la secuencia asociada a ese tipo de frase. |
| Prioridad | Media |
| Relacionado con | ADR-008 (Propuesta), ADR-009 (Propuesta, pendiente de confirmar capacidad del rig vía TSK-04) |

**REQUERIMIENTO: RF-AVT-04, Interpolación entre señas**

| Descripción | El sistema interpolará el movimiento entre el final de una seña y el inicio de la siguiente, para que la transición sea fluida. |
| --- | --- |
| Razón | Las transiciones bruscas entre señas dificultan la comprensión del mensaje. |
| Casos de uso asociados | CU-03 |
| Criterio de aceptación | Entre dos señas consecutivas de una misma secuencia, no se perciben cortes ni saltos visibles. |
| Prioridad | Alta |

**REQUERIMIENTO: RF-AVT-05, Estado de reposo del avatar**

| Descripción | Mientras no haya una secuencia de señas para reproducir, el avatar permanecerá en una posición base de reposo. |
| --- | --- |
| Razón | El avatar necesita un estado por defecto claro cuando no está traduciendo nada, en vez de quedar en una postura intermedia. |
| Casos de uso asociados | CU-03 |
| Criterio de aceptación | Al abrir la app, o al terminar una secuencia sin que llegue una nueva, el avatar se mantiene en la posición de reposo. |
| Prioridad | Media |
| Relacionado con | Distinto de RNF-REL-02 (retorno a reposo tras una desconexión, no el estado inicial por defecto) |

## 3.4 Gestión del catálogo de señas

**REQUERIMIENTO: RF-CAT-01, Almacenamiento del catálogo**

| Descripción | El sistema almacenará en una base de datos el catálogo de las 50 señas del corpus, con su glosa, categoría y la referencia a su animación. |
| --- | --- |
| Razón | El catálogo es la base de conocimiento del sistema, debe estar estructurado para que los demás módulos lo puedan consultar. |
| Casos de uso asociados | CU-01 |
| Criterio de aceptación | La base de datos contiene el registro de cada una de las 50 señas del corpus, con su glosa, categoría y referencia de animación. |
| Prioridad | Alta |
| Relacionado con | ADR-012 (Propuesta, bloqueada por TSK-04, en lo referente a la forma de la referencia de animación) |

**REQUERIMIENTO: RF-CAT-02, Validación de glosas**

| Descripción | El sistema recibirá la secuencia de glosas generada por el NLP y verificará, por cada una, si existe en el catálogo. |
| --- | --- |
| Razón | Garantizar que solo se envíen al avatar instrucciones de señas que sí existen en el corpus. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | Para cada glosa recibida, el sistema determina si existe o no en el catálogo antes de continuar el flujo. |
| Prioridad | Alta |

**REQUERIMIENTO: RF-CAT-03, Manejo de glosas no encontradas**

| Descripción | Cuando una glosa no exista en el catálogo, el sistema responderá con el mensaje “Seña no disponible” en lugar de enviar una instrucción de animación al avatar. |
| --- | --- |
| Razón | Evitar que el avatar reciba una instrucción inválida, y comunicarle al usuario que esa palabra no está soportada en el corpus actual. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | Ante una glosa no encontrada, el sistema retorna el mensaje “Seña no disponible” y no envía ninguna instrucción de animación. |
| Prioridad | Alta |
| Relacionado con | Comportamiento que antes estaba descrito en el RF-NLP-02 original, movido aquí porque es el catálogo quien tiene la información para decidirlo. |

## 3.5 Interfaz móvil y experiencia de usuario

**REQUERIMIENTO: RF-UI-01, Control de captura con tres estados**

| Descripción | La interfaz incluirá un botón de control de voz con tres estados visuales: uno para iniciar la grabación, uno para detenerla mientras el sistema está capturando audio, y uno para confirmar el envío del texto transcrito al NLP una vez la grabación se detiene. |
| --- | --- |
| Razón | Darle al usuario un control claro de en qué punto del flujo está, y resolver de forma concreta la confirmación de envío que exige RF-STT-03. |
| Casos de uso asociados | CU-02, CU-04, CU-05 |
| Criterio de aceptación | El ícono del botón cambia según el estado del sistema (inactivo, grabando, o texto listo para enviar), y al presionarlo en el último estado el texto se envía al NLP. |
| Prioridad | Alta |
| Relacionado con | RF-STT-03 (resuelve el pendiente de confirmación de envío) |

**REQUERIMIENTO: RF-UI-02, Barra de transcripción**

| Descripción | La interfaz incluirá una barra de texto donde se muestra la transcripción del audio capturado, permitiendo editar el texto antes de confirmar el envío. |
| --- | --- |
| Razón | Darle al usuario un lugar visible donde verificar y corregir lo que el sistema transcribió. |
| Casos de uso asociados | CU-04 |
| Criterio de aceptación | La barra de transcripción está visible en la interfaz y permite editar el texto mostrado. |
| Prioridad | Alta |
| Relacionado con | RF-STT-02, RF-STT-03 (la actualización en tiempo real y la lógica de edición viven en STT, aquí solo se describe el componente visual) |

**REQUERIMIENTO: RF-UI-03, Distribución de pantalla**

| Descripción | La pantalla principal distribuirá el espacio entre el área de visualización del avatar, que ocupará la mayor parte de la pantalla, y los controles de captura y transcripción, ubicados en la parte inferior. |
| --- | --- |
| Razón | El avatar es el canal de salida principal para el usuario sordo, necesita la mayor visibilidad posible. |
| Casos de uso asociados | CU-03, CU-05 |
| Criterio de aceptación | El área del avatar ocupa visiblemente más espacio en pantalla que el área de controles. La proporción exacta queda pendiente de una definición de diseño visual. |
| Prioridad | Media |

**REQUERIMIENTO: RF-UI-04, Permisos**

| Descripción | El sistema solicitará al usuario los permisos de micrófono y acceso a internet al iniciar la aplicación por primera vez, e indicará si la app no puede funcionar sin ellos. |
| --- | --- |
| Razón | La app depende del micrófono para capturar audio y de internet para comunicarse con el backend. |
| Casos de uso asociados | CU-01 |
| Criterio de aceptación | Al abrir la app por primera vez, se muestran las solicitudes de permisos del sistema operativo. Si el usuario los deniega, la app muestra un mensaje indicándolo. |
| Prioridad | Alta |

**REQUERIMIENTO: RF-UI-05, Señalización de estados del sistema**

| Descripción | La interfaz mostrará una señal visual cuando el sistema esté en un estado distinto al normal de funcionamiento, por ejemplo ante un error, una pérdida de conexión, o una solicitud que quedó en espera. |
| --- | --- |
| Razón | Sin una señal clara, el usuario no puede distinguir si el sistema está fallando, desconectado, o simplemente ocupado procesando, lo cual genera confusión, sobre todo para el usuario sordo, que no tiene forma de preguntar verbalmente qué pasa. |
| Casos de uso asociados | CU-02, CU-03, CU-05 |
| Criterio de aceptación | Ante un error, una desconexión, o una solicitud en cola, la interfaz muestra una señal visual distinta a la de operación normal. El diseño exacto de cada señal queda pendiente. |
| Prioridad | Media |
| Relacionado con | RNF-REL-02 (retorno del avatar a reposo tras desconexión), RNF-AV-03 (resiliencia ante fallas de API), RNF-DES-05 (encolado de sesiones) |

# 4. Requerimientos de desempeño

*Lista plana de RNF-DES, sin dividir por módulo (igual que 6.3 del SRS original). Todos los valores numéricos de esta sección son estimados, sujetos a TSK-03/TSK-04/TSK-05.*

*La disponibilidad del servicio no se redacta aquí, ya está cubierta por RNF-AV-01 (sección 6.2), para no duplicar contenido.*

**REQUERIMIENTO: RNF-DES-01, Latencia extremo a extremo**

| Descripción | El tiempo desde que el usuario confirma el envío del texto hasta que el avatar ejecuta la primera seña se mantendrá dentro de un rango estimado, con un rango para cuando la traducción se resuelve por caché y otro para cuando requiere llamada al LLM. |
| --- | --- |
| Razón | Es la métrica que refleja la espera real del usuario, sumando todos los módulos del pipeline. |
| Casos de uso asociados | CU-02, CU-03 |
| Criterio de aceptación | El tiempo medido se mantiene dentro del rango correspondiente a cada escenario. Valores exactos pendientes de TSK-03, TSK-04, TSK-05. |
| Prioridad | Alta |
| Relacionado con | RF-STT-03, RF-NLP-04 |

**REQUERIMIENTO: RNF-DES-02, Latencia de transcripción (STT)**

| Descripción | El tiempo entre que el usuario empieza a hablar y el sistema entrega el texto transcrito se mantendrá dentro de un rango estimado. |
| --- | --- |
| Razón | El STT es el primer eslabón del pipeline, su latencia afecta directamente el tiempo total. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | El tiempo de transcripción se mantiene dentro del rango estimado, sujeto a los datos reales de TSK-03. |
| Prioridad | Alta |
| Relacionado con | ADR-005, ADR-006 (bloqueadas por TSK-03) |

**REQUERIMIENTO: RNF-DES-03, Latencia del NLP**

| Descripción | El tiempo del NLP para producir la secuencia de glosas se expresará en dos rangos, uno para acierto de caché semántica y otro para llamada al LLM externo. |
| --- | --- |
| Razón | Los dos casos tienen tiempos muy distintos, un solo número no representaría bien a ninguno. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | El tiempo se mantiene dentro del rango correspondiente según si hubo acierto de caché o llamada al LLM. |
| Prioridad | Alta |
| Relacionado con | RF-NLP-04, ADR-007 (en evaluación, bloqueada por TSK-05) |

**REQUERIMIENTO: RNF-DES-04, Capacidad de sesiones concurrentes**

| Descripción | El sistema sostendrá un número mínimo estimado de sesiones activas al mismo tiempo, sin afectar la latencia de cada una. |
| --- | --- |
| Razón | El sistema está pensado para varios puntos de atención usándolo a la vez. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | Con el número estimado de sesiones simultáneas, la latencia de cada una se mantiene dentro de lo definido en RNF-DES-01. |
| Prioridad | Alta |
| Relacionado con | RNF-REL-01 |

**REQUERIMIENTO: RNF-DES-05, Renderizado del avatar**

| Descripción | El avatar se renderizará a una tasa de fotogramas por segundo dentro de un rango mínimo estimado. |
| --- | --- |
| Razón | Una tasa de fotogramas baja hace que las señas sean difíciles de seguir visualmente. |
| Casos de uso asociados | CU-03 |
| Criterio de aceptación | La tasa de fotogramas se mantiene dentro del rango mínimo estimado durante la reproducción de una secuencia de señas. |
| Prioridad | Alta |
| Relacionado con | RF-AVT-01, RF-AVT-02 |

**REQUERIMIENTO: RNF-DES-06, Transición entre señas**

| Descripción | La transición entre el final de una seña y el inicio de la siguiente durará, como máximo, un valor estimado de tiempo. |
| --- | --- |
| Razón | Una transición muy larga rompe la fluidez de la secuencia de señas. |
| Casos de uso asociados | CU-03 |
| Criterio de aceptación | La duración de la transición entre dos señas consecutivas no supera el valor máximo estimado. |
| Prioridad | Alta |
| Relacionado con | RF-AVT-04 |

# 5. Restricciones de diseño

*A diferencia del resto del documento, el SRS original no le daba ID ni tabla a estas restricciones, era texto corrido. Aquí se mantiene el mismo formato de tabla que el resto del documento, con el prefijo RD (Restricción de Diseño), para conservar la trazabilidad. Se excluyen del listado los riesgos de ejecución del proyecto (por ejemplo, la disponibilidad de intérpretes), que ya tienen su propio tratamiento en el Architecture Backlog (prefijo RSK) y no son restricciones del sistema en sí.*

**REQUERIMIENTO: RD-01, Corpus cerrado de 50 señas**

| Descripción | El sistema opera sobre un corpus cerrado de 50 señas del dominio Registro de Datos Básicos, no se soporta vocabulario abierto en esta versión del prototipo. |
| --- | --- |
| Razón | El alcance del proyecto se delimitó deliberadamente a un dominio controlado para hacer viable la validación lingüística y el desarrollo dentro del tiempo disponible. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | El sistema no traduce ni genera señas fuera de las 50 registradas en el catálogo. |
| Prioridad | Alta |
| Relacionado con | RF-CAT-01, RF-CAT-03, ADR-002 (en análisis) |

**REQUERIMIENTO: RD-02, Traducción unidireccional**

| Descripción | El sistema traduce únicamente de español hablado a LSC, no se implementa reconocimiento de señas ni traducción en sentido inverso. |
| --- | --- |
| Razón | El alcance del prototipo se limita a esta dirección, el reconocimiento de señas es un problema distinto y mucho más complejo, fuera del alcance de esta versión. |
| Casos de uso asociados | CU-02, CU-03 |
| Criterio de aceptación | No existe en el sistema ningún flujo que capture señas del usuario sordo y las traduzca a español. |
| Prioridad | Alta |

**REQUERIMIENTO: RD-03, Avatar sin uso del espacio ni concordancia**

| Descripción | El avatar concatena animaciones grabadas por seña, no ejecuta movimientos generados dinámicamente en el espacio ni realiza concordancia gramatical, es decir, desplazar un verbo entre dos puntos para indicar quién hace la acción sobre quién. |
| --- | --- |
| Razón | Producir animaciones con concordancia espacial excede el alcance técnico y de tiempo del prototipo, se prioriza que las 50 señas existan y sean legibles. |
| Casos de uso asociados | CU-03 |
| Criterio de aceptación | La selección de señas del corpus evita depender de concordancia espacial para ser comprensible. |
| Prioridad | Media |
| Relacionado con | LIM-01 del Architecture Backlog, ADR-002 |

**REQUERIMIENTO: RD-04, Infraestructura real distinta a la declarada**

| Descripción | El backend no se ejecuta sobre un servidor dedicado, corre sobre equipos de cómputo personales del equipo de desarrollo. |
| --- | --- |
| Razón | Es la infraestructura real disponible para el prototipo, condiciona directamente los rangos de disponibilidad y desempeño definidos en las secciones 4 y 6. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | Los rangos de disponibilidad y desempeño del sistema se definen en función de esta infraestructura real, no de un entorno de servidor dedicado. |
| Prioridad | Alta |
| Relacionado con | RNF-AV-01, RNF-DES-01 a 06, LIM-08 y RSK-18 del Architecture Backlog |

**REQUERIMIENTO: RD-05, Variabilidad de respuesta del LLM**

| Descripción | El modelo de lenguaje externo usado por el NLP no garantiza devolver siempre la misma salida ante la misma entrada. |
| --- | --- |
| Razón | Es una característica del proveedor externo, fuera del control del equipo, la caché semántica reduce su impacto pero no lo elimina. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | Las traducciones que ya pasaron por la caché no dependen de esta variabilidad, solo las que requieren llamada nueva al LLM están sujetas a ella. |
| Prioridad | Media |
| Relacionado con | RF-NLP-02, RF-NLP-04, LIM-06 del Architecture Backlog |

# 6. Atributos del sistema de software (No funcionales)

## 6.1 Confiabilidad

*Esta sección cubre la capacidad del sistema de seguir operando de forma consistente ante concurrencia, desconexiones y fallas transitorias de sus dependencias, en particular ahora que la captura de audio es un flujo continuo (RF-STT-01) y no por bloques.*

**REQUERIMIENTO: RNF-REL-01, Gestión de concurrencia en la captura de audio**

| Descripción | El backend debe recibir y procesar el flujo continuo de audio (RF-STT-01) mediante un mecanismo asíncrono que no bloquee el hilo principal, encolando el excedente de sesiones cuando se supere un número máximo de conexiones simultáneas soportadas por el servidor. |
| --- | --- |
| Razón | Con el envío continuo de audio (ya no por bloques de tamaño fijo), el servidor debe sostener varios flujos de streaming a la vez sin degradar el servicio ni agotar la memoria disponible para la inferencia del modelo STT. |
| Casos de uso asociados | CU-02, CU-05 |
| Criterio de aceptación | Ante una carga simulada que exceda la capacidad configurada, las solicitudes adicionales se encolan sin pérdida de datos de audio ni caída del servicio. El número máximo de conexiones simultáneas se define como un rango estimado, sujeto a confirmación con datos reales de hardware. |
| Prioridad | Alta |
| Relacionado con | RF-STT-01; ADR-005 (bloqueada por TSK-03); ADR-006 (en evaluación, bloqueada por TSK-03) |

**REQUERIMIENTO: RNF-REL-02, Recuperación del avatar ante pérdida de conexión**

| Descripción | Ante una interrupción del canal WebSocket durante la reproducción de una secuencia de señas, la aplicación móvil debe detectar la desconexión y llevar el avatar a la posición de reposo en un lapso breve, evitando que quede congelado en una postura intermedia. |
| --- | --- |
| Razón | Una animación interrumpida a medias genera una imagen confusa o potencialmente incorrecta para el usuario sordo, que no tiene forma de saber si esa postura es parte del mensaje o una falla. |
| Casos de uso asociados | CU-03, CU-05 |
| Criterio de aceptación | Al simular la pérdida de conexión durante una animación, el avatar retorna a la posición de reposo (RF-AVT-05) sin que la aplicación se cierre, en un tiempo corto (del orden de fracciones de segundo, no un valor exacto), y sin bloquear la interfaz. |
| Prioridad | Alta |
| Relacionado con | RF-AVT-05 (estado de reposo por defecto, distinto de este caso); RF-UI-05 (señal visual del estado) |

**REQUERIMIENTO: RNF-REL-03, Reintentos ante fallas transitorias de la base de datos**

| Descripción | Las consultas al catálogo de señas deben implementar una política de reintentos automáticos ante una falla transitoria de conexión con la base de datos, con un número máximo acotado de intentos y una espera breve entre ellos. |
| --- | --- |
| Razón | Asegurar la disponibilidad del catálogo frente a interrupciones momentáneas del servicio de base de datos en la nube, sin dejar la solicitud del usuario sin respuesta. |
| Casos de uso asociados | CU-01, CU-02 |
| Criterio de aceptación | Ante una desconexión simulada de la base de datos, el sistema reintenta un número reducido de veces antes de devolver un error controlado a la interfaz. |
| Prioridad | Media |
| Relacionado con | RF-CAT-01, RF-CAT-02 |

**REQUERIMIENTO: RNF-REL-04, Preservación del texto transcrito a la espera de confirmación**

| Descripción | El texto transcrito que queda a la espera de confirmación del usuario (RF-STT-03) no debe perderse por eventos menores como una fluctuación breve de red, solo se descarta si el usuario lo borra o cancela explícitamente. |
| --- | --- |
| Razón | Como el envío al NLP ahora depende de una acción explícita del usuario (ya no es automático), perder ese texto por una causa ajena a su decisión obligaría a repetir la grabación completa, lo cual resulta especialmente costoso en frases largas. |
| Casos de uso asociados | CU-02, CU-04 |
| Criterio de aceptación | Ante una interrupción breve de red mientras el texto está en la barra de transcripción a la espera de confirmación, el texto permanece visible y editable una vez se restablece la conexión. |
| Prioridad | Media |
| Relacionado con | RF-STT-03, RF-UI-02 |

## 6.2 Disponibilidad

*Esta sección define el tiempo operativo esperado del servicio y el comportamiento del sistema cuando sus dependencias externas (LLM, STT, base de datos) no responden con normalidad.*

**REQUERIMIENTO: RNF-AV-01, Tiempo operativo del servicio de traducción**

| Descripción | El backend debe mantener un tiempo operativo alto durante el horario de atención institucional definido para el prototipo, con una disponibilidad objetivo expresada como rango (por ejemplo, entre 90% y 98%). |
| --- | --- |
| Razón | Garantizar que la plataforma esté accesible durante las horas de mayor demanda, reconociendo que el prototipo depende de servicios externos (LLM, base de datos en la nube) cuyo tiempo de actividad no está bajo control directo del equipo. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | Al revisar los registros del servidor al cierre de cada semana de pruebas, el tiempo de indisponibilidad no controlada se mantiene dentro del rango objetivo definido para la ventana de cobertura acordada. |
| Prioridad | Alta |

**REQUERIMIENTO: RNF-AV-02, Ventanas de mantenimiento técnico**

| Descripción | Las tareas de actualización del catálogo, despliegues o mantenimiento de la base de datos deben programarse fuera del horario operativo institucional, dentro de una ventana acotada que no debe superar un máximo aproximado (del orden de 30 a 60 minutos continuos). |
| --- | --- |
| Razón | Evitar que el mantenimiento interrumpa el servicio mientras los usuarios finales están usando la aplicación. |
| Casos de uso asociados | CU-01 |
| Criterio de aceptación | Cualquier interrupción programada ocurre fuera del horario operativo y no excede el máximo acordado para la ventana de mantenimiento. |
| Prioridad | Media |

**REQUERIMIENTO: RNF-AV-03, Resiliencia ante fallas o lentitud de servicios externos (LLM, STT)**

| Descripción | Si el proveedor externo del LLM (o el modelo STT) no responde o responde con una lentitud fuera de lo normal, el backend debe seguir operativo: primero intenta resolver la frase con la caché semántica (RF-NLP-04), si no puede resolverla, informa a la aplicación móvil dentro de un plazo corto (del orden de máximo un par de segundos) para que esta active la señal visual correspondiente (RF-UI-05), en lugar de dejar al usuario esperando sin explicación. |
| --- | --- |
| Razón | Evitar que una falla de un proveedor externo bloquee indefinidamente la experiencia del usuario, aprovechando que ahora existe una caché de traducciones (RF-NLP-04) que reduce la dependencia del LLM y, con ella, el impacto de sus fallas. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | Al simular la caída o lentitud del proveedor del LLM, el sistema responde con un estado de error controlado dentro del plazo máximo definido, y la aplicación muestra la señal visual correspondiente. |
| Prioridad | Alta |
| Relacionado con | RF-NLP-02 (ADR-007, en evaluación, bloqueada por TSK-05); RF-NLP-04; RF-UI-05 |

## 6.3 Seguridad

*Esta sección cubre la protección del backend frente al uso indebido de recursos costeados por uso (el LLM externo) y el tratamiento de los datos personales que el sistema captura por voz, en línea con la Ley 1581 de 2012 citada en las restricciones legales del SRS original.*

**REQUERIMIENTO: RNF-SEC-01, Límite de solicitudes por cliente**

| Descripción | El backend debe limitar el número de solicitudes de traducción (incluyendo apertura de conexiones WebSocket) que un mismo cliente puede generar en un intervalo corto de tiempo, rechazando o retrasando el excedente. El mecanismo de identificación del cliente y el valor exacto del límite quedan pendientes de la definición de sesión (DEC-20), mientras tanto el umbral se establece como un orden de magnitud (decenas de solicitudes por minuto, no cientos) y no como un número cerrado. |
| --- | --- |
| Razón | Evitar que un uso indebido o automatizado agote el saldo del proveedor del LLM, que se cobra por uso, o sature el servidor. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | Ante un volumen de solicitudes muy por encima del uso normal de una sesión, el servidor comienza a rechazar o retrasar las solicitudes excedentes y responde con un mensaje de error controlado. |
| Prioridad | Alta |
| Relacionado con | ADR-014 (en análisis, depende de DEC-20); RSK-16 |

**REQUERIMIENTO: RNF-SEC-02, Validación del formato de audio recibido**

| Descripción | El backend debe verificar que los datos recibidos por el canal de streaming de audio (RF-STT-01) correspondan efectivamente a un formato de audio soportado antes de intentar procesarlos, descartando el flujo si no cumple, dentro de un tiempo breve (del orden de unos pocos cientos de milisegundos como máximo). |
| --- | --- |
| Razón | Evitar que datos malformados o de otro tipo bloqueen los hilos de procesamiento del pipeline de IA. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | Al enviar un flujo que no corresponde a audio, el backend lo identifica y cierra la conexión sin que el resto del pipeline se vea afectado. |
| Prioridad | Media |

**REQUERIMIENTO: RNF-SEC-03, Tratamiento de datos personales capturados por voz**

| Descripción | El audio y el texto transcrito pueden contener datos personales del usuario aun cuando el catálogo del prototipo se limita a un conjunto de 50 señas seleccionadas, por eso deben conservarse solo durante el tiempo mínimo necesario para completar la traducción de la sesión activa, salvo que se defina explícitamente una política de retención distinta. Toda comunicación que transporte esta información, incluida la que se envía al proveedor externo del LLM, debe viajar cifrada. |
| --- | --- |
| Razón | El sistema envía parte de esta información a un servicio externo, posiblemente fuera de Colombia, por lo que se requiere una postura mínima de protección de datos mientras se cierra la política definitiva de retención y base legal. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | Al revisar el almacenamiento del backend tras una sesión de prueba, no se conservan audio ni texto más allá del tiempo mínimo definido para el flujo de traducción activo, y las trazas de red confirman que las comunicaciones relevantes están cifradas. |
| Prioridad | Alta |
| Relacionado con | ADR-013 (en análisis, la política de retención y la base legal del envío al LLM externo aún no están cerradas, este requerimiento fija un piso mínimo mientras esa decisión se resuelve); Ley 1581 de 2012 |

## 6.4 Mantenibilidad

*Esta sección recoge cómo el sistema debe mantenerse fácil de modificar, extender y depurar, apoyándose en la arquitectura de monolito (cada función del pipeline como un servicio interno, dentro de un único despliegue) y en la nueva caché semántica del NLP (RF-NLP-04).*

*Nota de cambio de arquitectura: el equipo confirmó que SignAI se implementará como un monolito, no como microservicios distribuidos, por recomendación del profesor de arquitectura consultado. Cada función (STT, NLP, catálogo, visualización) se organiza como un servicio interno, pero todas corren dentro de un mismo proceso o despliegue. Esto reemplaza el enfoque de ADR-011 (que había decidido microservicios); queda pendiente actualizar ese ADR en el ADR Log para dejar registrado el motivo del cambio.*

**REQUERIMIENTO: RNF-MNT-01, Independencia del catálogo de señas**

| Descripción | El catálogo de señas debe poder actualizarse (agregar, modificar o retirar una seña, incluyendo su glosa y la referencia a su animación) directamente en la base de datos, sin requerir cambios en el código fuente del backend ni una nueva compilación del servicio. |
| --- | --- |
| Razón | Permitir ajustar o ampliar el corpus a medida que avanza su validación con el intérprete (ADR-002), sin acoplar esa evolución al ciclo de despliegue del backend. |
| Casos de uso asociados | CU-01, CU-02 |
| Criterio de aceptación | Al insertar o modificar un registro del catálogo, el pipeline lo reconoce en la siguiente solicitud sin reiniciar el servicio ni modificar código. |
| Prioridad | Alta |
| Relacionado con | RF-CAT-01; ADR-012 (Propuesta, bloqueada por TSK-04) |

**REQUERIMIENTO: RNF-MNT-02, Separación de componentes por servicio interno (monolito)**

| Descripción | Los componentes principales del pipeline (captura y transcripción, procesamiento semántico, catálogo y visualización) deben mantenerse desacoplados dentro de una única aplicación desplegable (monolito), comunicándose entre sí únicamente a través de interfaces internas bien definidas. Cada componente se organiza y se comporta como un servicio independiente, aunque todos corran dentro del mismo proceso y se desplieguen como una sola unidad. |
| --- | --- |
| Razón | Permitir reemplazar o modificar la implementación de un componente (por ejemplo, cambiar el proveedor del LLM o el modelo de STT) sin afectar el resto del sistema, sin asumir el costo operativo de una arquitectura distribuida. |
| Casos de uso asociados | CU-02, CU-03 |
| Criterio de aceptación | Es posible reemplazar la implementación de un componente por otra que respete el mismo contrato de interfaz interna, sin modificar el código de los demás módulos ni el proceso de despliegue. |
| Prioridad | Alta |
| Relacionado con | Reemplaza el enfoque de microservicios de ADR-011; queda pendiente actualizar ese ADR para registrar la decisión de monolito |

**REQUERIMIENTO: RNF-MNT-03, Estándar de documentación de código**

| Descripción | El código fuente del backend y de la aplicación móvil debe seguir guías de estilo estándar del lenguaje correspondiente, con comentarios en las funciones de mayor complejidad y tipado explícito donde el lenguaje lo permita. |
| --- | --- |
| Razón | Facilitar que una persona ajena al equipo original pueda entender y dar mantenimiento al sistema. |
| Casos de uso asociados | Todos los casos de uso |
| Criterio de aceptación | El código pasa una revisión con analizadores estáticos sin advertencias críticas de legibilidad. |
| Prioridad | Media |

**REQUERIMIENTO: RNF-MNT-04, Control de versiones y dependencias**

| Descripción | Las dependencias externas de software deben quedar centralizadas en archivos de configuración estándar del ecosistema correspondiente, de forma que el entorno de desarrollo o despliegue pueda reconstruirse de forma repetible. |
| --- | --- |
| Razón | Evitar que la reconstrucción del entorno dependa de configuraciones manuales no documentadas. |
| Casos de uso asociados | Todos los casos de uso |
| Criterio de aceptación | Un entorno nuevo puede levantar el backend o compilar la aplicación móvil siguiendo un número reducido de pasos automatizados, sin conflictos de versiones. |
| Prioridad | Media |

**REQUERIMIENTO: RNF-MNT-05, Actualización independiente de la caché semántica del NLP**

| Descripción | La caché de traducciones reutilizadas por el NLP (RF-NLP-04) debe poder invalidarse o corregirse de forma independiente al resto del pipeline, sin requerir un nuevo despliegue del servicio de NLP. |
| --- | --- |
| Razón | Si una traducción guardada resulta incorrecta tras la validación con el intérprete, el equipo necesita poder corregirla sin esperar un ciclo de despliegue completo. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | Es posible eliminar o reemplazar una entrada específica de la caché sin reiniciar el servicio de NLP y sin afectar las demás entradas. |
| Prioridad | Media |
| Relacionado con | RF-NLP-04; ADR-014 (en análisis) |

## 6.5 Portabilidad

*Esta sección define en qué dispositivos y entornos debe poder ejecutarse SignAI, considerando tanto el cliente móvil como el backend en contenedores, y la dependencia de hardware específico que introduce el modelo de STT.*

**REQUERIMIENTO: RNF-POR-01, Compatibilidad del sistema operativo móvil**

| Descripción | La aplicación cliente debe funcionar en un rango amplio de versiones de Android, desde una versión mínima que cubra la mayoría de los dispositivos vigentes en el mercado hasta las versiones más recientes. |
| --- | --- |
| Razón | Asegurar que la mayoría de los usuarios con teléfonos Android puedan instalar y usar la aplicación sin problemas de compatibilidad. |
| Casos de uso asociados | CU-03 |
| Criterio de aceptación | La aplicación compila fijando una versión mínima de Android y se ejecuta correctamente en dispositivos con esa versión o superior. |
| Prioridad | Alta |

**REQUERIMIENTO: RNF-POR-02, Independencia del entorno de despliegue del backend**

| Descripción | El backend, incluidos sus módulos de inteligencia artificial, debe poder ejecutarse mediante contenedores como una única unidad desplegable (monolito), de forma que el servicio no dependa de un proveedor de nube o sistema operativo de host específico. |
| --- | --- |
| Razón | Facilitar que el backend se pueda migrar entre proveedores de infraestructura sin reinstalar el entorno desde cero. Al ser un monolito, empaquetarlo en un único contenedor es además más simple que coordinar el despliegue de varios servicios independientes. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | El backend, empaquetado como imagen de contenedor, se despliega y levanta el servicio en cualquier máquina con el motor de contenedores instalado, dentro de un tiempo de arranque razonable (del orden de unos pocos minutos como máximo, no un valor exacto). |
| Prioridad | Alta |

**REQUERIMIENTO: RNF-POR-03, Entorno de desarrollo estándar**

| Descripción | El proyecto debe poder compilarse y ejecutarse usando exclusivamente herramientas estándar y públicamente documentadas de cada lenguaje (gestor de paquetes del backend y entorno oficial de compilación de la aplicación móvil), sin depender de configuraciones o parches locales no versionados. |
| --- | --- |
| Razón | Garantizar que cualquier integrante del equipo, o un tercero, pueda descargar el proyecto y compilarlo sin instalar herramientas no estándar. |
| Casos de uso asociados | Todos los casos de uso |
| Criterio de aceptación | El proyecto se compila exitosamente usando únicamente las herramientas estándar declaradas en la configuración del repositorio. |
| Prioridad | Media |

**REQUERIMIENTO: RNF-POR-04, Dependencia de aceleración por hardware para el STT**

| Descripción | El entorno donde se ejecuta el modelo de transcripción debe documentar explícitamente si requiere una GPU con una capacidad mínima aproximada para operar dentro de los rangos de desempeño esperados, dado que el tamaño de modelo aún no está confirmado (ADR-006) y podría no rendir adecuadamente en un entorno de solo CPU. |
| --- | --- |
| Razón | Sin esta aclaración, portar el backend a un proveedor de infraestructura sin GPU podría degradar la latencia de transcripción más allá de lo aceptable, sin quedar documentado como una limitación conocida. |
| Casos de uso asociados | CU-02 |
| Criterio de aceptación | La documentación de despliegue especifica si el entorno objetivo requiere GPU y de qué capacidad aproximada, una vez ese dato quede confirmado por TSK-03. |
| Prioridad | Media |
| Relacionado con | ADR-006 (en evaluación, bloqueada por TSK-03) |

# 7. Requerimientos de la base de datos

**REQUERIMIENTO: RNF-BD-01, Consultas parametrizadas**

| Descripción | Todas las consultas a la base de datos se ejecutarán mediante prepared statements o un ORM, sin construir sentencias SQL por concatenación de texto. |
| --- | --- |
| Razón | Prevenir inyección SQL en cualquier punto de acceso al catálogo, incluso si hoy no hay entrada libre del usuario hacia esas consultas. |
| Casos de uso asociados | CU-01, CU-02 |
| Criterio de aceptación | Ninguna función de acceso a datos construye consultas por concatenación de cadenas, todas pasan por el ORM o por sentencias parametrizadas. |
| Prioridad | Alta |
| Relacionado con | RNF-SEC-01, RNF-SEC-02, DEC-15 (en análisis) |

**REQUERIMIENTO: RNF-BD-02, Llave primaria autoincremental**

| Descripción | Cada registro del catálogo tendrá una llave primaria entera autoincremental, independiente de su contenido. |
| --- | --- |
| Razón | Evita duplicados, simplifica actualizar o eliminar un registro, y desacopla la identidad del registro de su glosa o ruta de animación, que sí pueden cambiar. |
| Casos de uso asociados | CU-01 |
| Criterio de aceptación | Intentar insertar dos registros con el mismo identificador genera un error de integridad. |
| Prioridad | Media |

**REQUERIMIENTO: RNF-BD-03, Carga del catálogo en memoria**

| Descripción | El catálogo completo se cargará en memoria al iniciar el backend, de forma que el flujo de traducción no dependa de consultas a la base de datos durante la inferencia. |
| --- | --- |
| Razón | Cada consulta durante la inferencia introduce latencia hacia la base de datos, cargar el catálogo en memoria elimina esa dependencia del flujo crítico. |
| Casos de uso asociados | CU-01, CU-02 |
| Criterio de aceptación | Durante una sesión de traducción, no se registran consultas a la base de datos originadas por el flujo de traducción en sí. |
| Prioridad | Alta |
| Relacionado con | RF-CAT-01, RNF-DES-01 a 06 |

*Pendiente (sin resolver todavía, no confirmado con el equipo): RNF-MNT-01 (6.4) exige que una seña nueva se reconozca sin reiniciar el servicio, lo cual está en tensión con este RNF-BD-03, que asume cero consultas a la base de datos durante la inferencia. Es la misma tensión documentada como INC-08 en el Architecture Backlog. No se modifica RNF-MNT-01 hasta que el equipo lo confirme.*