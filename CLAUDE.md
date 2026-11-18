# SignAll — backend

Servicio central de SignAll: recibe español por texto o audio desde la app Android, lo convierte
en glosas de Lengua de Señas Colombiana (LSC) y devuelve las señas que el avatar representa, una
oración por vez. Trabajo de grado de Ingeniería de Sistemas, Pontificia Universidad Javeriana,
con un corpus fijo de 50 señas (LSC50) para "Registro Básico de Datos". Este archivo son las
reglas del repositorio; el resto del contexto se carga cuando la tarea lo pide.

Al owner se le escribe en español neutro, sin voseo y sin jerga sin explicar. El término de la
tesis es representar, no firmar ni signar, y una frase se envía. Los números van con su origen.

## El sistema

- signall-android: la app. Captura, envía y representa las señas.
- signall-backend: este repositorio. WebSocket, glosas, catálogo y caché. Puerto 8080.
- signall-stt: faster-whisper y VAD, audio a texto. Puerto 8000.
- signall-docs: los documentos de la tesis.
- signall-avatar (rama dev): producción de las animaciones.

Los repos hermanos son fuentes de información, no cajas negras. Antes de cambiar un frame, una
glosa o un nombre de métrica se lee el otro lado: el contrato son frames y ningún compilador avisa
cuando se rompe. Un cambio que cruza el contrato no está terminado hasta que el otro lado lo
refleja, y los comandos suponen los clones uno al lado del otro.

## El contrato con la app

Un solo WebSocket, de la app solo al backend: :8080/ws/translate. La app nunca habla con el STT ni
con Neon, y el backend mantiene su propio socket saliente al STT (STT_WS_URL). El contrato campo
por campo está en docs/android-integration.md y se actualiza en el mismo cambio.

- Solo se traduce lo que el cliente manda como text; la voz vuelve como transcript y no se traduce.
- segment es una oración, con index y total reales desde el primero. No existen stream, provisional
  ni source_text.
- El final siempre llega, incluso vacío: un final sin texto es "no se escuchó nada", no un error.
- Los mismos nombres de métrica en los dos lados (rt_* acá, SignAllMetrics en el dispositivo).

## Cómo se levanta

El default es el entorno del plan de pruebas: Whisper medium en GPU (cuda/float16), la tarjeta
reservada. No se cambia sin decisión del owner; nada detecta el hardware, el perfil se declara.

    docker compose -f docker-compose.yml -f docker-compose.host.yml up -d

Para una máquina sin GPU se agrega -f docker-compose.cpu.yml: fija small/cpu/int8, quita la
reserva y compila el STT sin las librerías CUDA; cambiar de perfil necesita --build la primera vez.

La imagen del backend instala siempre torch desde el índice de CPU, porque el contenedor nunca
recibe la GPU: la reserva vive solo en stt y los embeddings corren en CPU. Si algún día van en GPU
es un cambio de diseño, no un ajuste del Dockerfile.

## Arquitectura

Monolito modular en FastAPI con PostgreSQL 16 y pgvector (Neon). El flujo de una frase es
Controller (WebSocket) → Orchestrator → NLPService → ValidatorService → CatalogRepository.

- Persistencia: dos tablas sin relaciones, catalog y semantic_cache, con asyncpg sin ORM y
  migraciones .sql versionadas.
- El diseño vive en docs/sdd.md y los requisitos en signall-docs. Si el SDD y el código no
  coinciden, no se edita el SDD: se anota en docs/sdd-changes.md y decide el owner.

## Decisiones que guían el trabajo

- LLMClient solo devuelve glosas; el phrase_type siempre sale de GlossAnalyzer.
- CatalogRepository carga todo el catálogo en memoria al arrancar; el validador no consulta
  PostgreSQL durante la inferencia.
- El prompt de glosas no lleva la lista de glosas; el trabajo lo hacen la reparación de glosas, la
  unión de fragmentos y el validador, porque LSC50 tiene glosas frasales (COMO ESTAS, BUENOS DIAS).
- Las señales de colisión de GlossAnalyzer nunca se ocultan; son instrumentación para validación.
- Sin umbrales numéricos en la lógica funcional: van a configuración o a no-funcionales.

## Trampas operativas

- Cambiar el prompt no invalida semantic_cache: las glosas viejas salen por HIT y el prompt nuevo
  no se ejecuta. Después de tocarlo: DELETE FROM semantic_cache; se reconstruye sola.
- El catálogo se carga una sola vez al arrancar. Después de un seed hay que reiniciar el servicio.
- LLM_BASE_URL vacío significa OpenAI; con una URL apunta a cualquier endpoint compatible (Ollama,
  LM Studio, vLLM) sin API key, alcanzable por host.docker.internal desde la red de Compose.
- El proxy TLS es parte del sistema: docker compose up -d a secas lo deja abajo y el APK demo no
  conecta. Se levanta con los dos archivos y se verifica con scripts/verify_proxy.sh.

## Convenciones de código

- El código y los comentarios van en inglés, sin excepción.
- Nombres de clases y métodos como el SDD, en snake_case: PEP 8 le gana a la notación UML.
- Type hints, funciones pequeñas y una sola responsabilidad; sin código muerto ni comentado.
- La métrica se agrega antes que la feature.

## Verificación

    tools/calidad/verificar.sh      # ruff, mypy y gitleaks
    scripts/cobertura.sh            # corre los verify_* bajo coverage
    docker compose -f docker-compose.yml -f docker-compose.host.yml exec backend \
        python -m scripts.verify_client_frames
    curl -s http://localhost:8080/health
    curl -s http://localhost:8080/metrics

No hay suite de pytest: las pruebas son los scripts/verify_*.py, que se corren como módulo
(python -m scripts.nombre) y salen con código 1 cuando el comportamiento que vigilan cambió.

## Documentación, fuentes de verdad y git

Cada cambio no trivial se documenta en signall-docs/cambios: qué cambió y qué quedó pendiente. Si
toca un documento formal (srs, sdd, memoria, plan-pruebas, administracion, vfp) se edita el .tex y
se compila con make. Acá la sesión además deja un archivo en docs/sessions/.

Las dos fuentes de verdad son este repositorio, con el código, y signall-docs, con los documentos.
Antes de decidir se leen los documentos; al implementar se comprueba que el código esté alineado.
Si no lo están, no se sigue por cuenta propia: se determina cuál está mal y se pregunta al owner.

Git: commit y push directo a main, sin PR, y no se commitea sin que el owner lo pida. Los hermanos
tampoco. Todo va a main; develop no existe; los mensajes siguen Conventional Commits en inglés.

## Qué leer según la tarea

- Un frame o una métrica: docs/android-integration.md y el skill contrato-websocket.
- Diseño, diagramas o plan: docs/sdd.md, docs/diagrams/ y docs/plan-implementacion-backend.md.
- Decisiones cerradas o abiertas: docs/decisions.md; divergencias con el SDD: docs/sdd-changes.md.
- Latencia o el efecto de una optimización: docs/performance.md y docs/tablas-rendimiento.md.
- Proxy, certificado o demo cifrada: deploy/README.md.
- Mapa del sistema y protocolo del STT: signall-android/docs/SISTEMA.md y el README de signall-stt.
