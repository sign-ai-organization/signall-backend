# SignAll Backend

Backend del proyecto SignAll (traducción de audio en español a
Lengua de Señas Colombiana mediante un avatar 3D). Ver `CLAUDE.md` y
`docs/sdd.md` para la arquitectura completa.

## Setup local

1. Crear el entorno virtual (una sola vez, no se sube al repo):

   ```bash
   python -m venv .venv
   ```

2. Activar el entorno virtual (cada vez que se trabaje en el proyecto):

   - Windows (PowerShell): `.venv\Scripts\Activate.ps1`
   - Windows (Git Bash): `source .venv/Scripts/activate`
   - Linux/Mac: `source .venv/bin/activate`

3. Instalar las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

Para desactivar el entorno virtual en cualquier momento: `deactivate`.

### Nota sobre el modelo de embeddings

`requirements.txt` incluye `sentence-transformers` (usado por
`EmbeddingModel` para el caché semántico, ver `docs/decisions.md`), que
trae PyTorch como dependencia — el `pip install` tarda notablemente más
por esto, es esperado.

Además, la primera vez que el modelo se use (no al instalar, sino al
correr código que lo invoque por primera vez).

### Nota sobre el modelo de spaCy

`requirements.txt` también instala `spacy` y el modelo `es_core_news_md`
(como wheel con versión fija), que usa `SentenceSegmenter` para dividir el
texto final del STT en oraciones. El modelo se carga una sola vez al
arrancar el backend. Para comprobar que el segmentador sigue cortando igual
que el laboratorio donde se evaluó:

```bash
python -m scripts.verify_sentence_segmenter
```

## Carpeta `scripts/`

Contiene scripts sueltos para probar manualmente una pieza del backend
(un repositorio, un servicio) sin pasar por la API HTTP/WebSocket —
útil en fases tempranas del proyecto, antes de que el Controller (Fase 11)
exista, o simplemente para verificar un componente de forma aislada. No es
parte de la aplicación en sí, no se despliega con el backend.

Cada script se corre como módulo, desde la raíz del proyecto, con el
entorno virtual activado:

```bash
python -m scripts.<nombre_del_script>
```

Por ejemplo:

```bash
python -m scripts.verify_catalog_repository
```

### Dependencias solo de desarrollo (`requirements-dev.txt`)

Algunos scripts necesitan librerías que el backend en sí nunca usa (ej.
captura de micrófono para probar manualmente una sesión de traducción
completa). Esas van en `requirements-dev.txt`, no en `requirements.txt`,
para no inflar la imagen Docker del backend con algo que solo sirve para
pruebas locales:

```bash
pip install -r requirements-dev.txt
```
