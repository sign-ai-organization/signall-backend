#!/usr/bin/env bash
# Verificación local del backend: lo que antes corría en GitHub Actions.
#
#     tools/calidad/verificar.sh
#
# Corre ruff y mypy (el análisis estático que pide RNF-MNT-03) y después
# gitleaks sobre el árbol y la historia. El escaneo de credenciales vive en el
# repositorio hermano de la app, que es el que conoce los cinco repositorios:
#
#     ../signall-android/tools/calidad/leaks.sh
#
# Los `verify_*.py` no corren acá: necesitan las dependencias del servicio
# (spaCy, el modelo de embeddings) y, algunos, la base de datos levantada. Se
# corren dentro del contenedor:
#
#     docker compose -f docker-compose.yml -f docker-compose.host.yml exec backend \
#         python -m scripts.verify_client_frames

set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$RAIZ"

if ! command -v ruff >/dev/null 2>&1 || ! command -v mypy >/dev/null 2>&1; then
  echo "Falta ruff o mypy. Se instalan con:" >&2
  echo "    pip install -r requirements-dev.txt" >&2
  exit 2
fi

echo "== ruff =="
ruff check app scripts

echo
echo "== mypy =="
mypy

echo
echo "== gitleaks =="
LEAKS="../signall-android/tools/calidad/leaks.sh"
if [ -x "$LEAKS" ]; then
  "$LEAKS"
else
  echo "No está $LEAKS (el repo hermano de la app no está al lado)." >&2
  echo "El escaneo de credenciales queda sin hacer." >&2
  exit 2
fi
