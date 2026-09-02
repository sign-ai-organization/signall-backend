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
