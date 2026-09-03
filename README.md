# SignAI Backend

Backend del proyecto SignAI (traducción de audio en español a
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
