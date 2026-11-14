#!/usr/bin/env bash
#
# Real coverage for SonarQube: runs the `scripts/verify_*.py` under `coverage`
# and leaves `coverage.xml` at the root of the repository.
#
# Why like this:
#
# - The `verify_*.py` are the project's de facto tests (`scripts/` has no
#   `tests/` yet). They are the only coverage that can be measured today: each
#   one exercises a path of the pipeline and exits 1 when that path changes.
# - They run inside the backend image because they need spaCy, the Spanish
#   model and the embedding model, which are not installed on the host. The
#   repository is mounted at `/app` so `coverage.xml` and the `.coverage.*` data
#   files land in the host tree instead of inside the container.
# - `coverage` is not in the service image (serving does not need it), so it is
#   installed into a temporary directory of the container on every run, pinned
#   to the version of `requirements-dev.txt`.
#
# Usage:
#
#     scripts/cobertura.sh                                 # the ones that need no service
#     SIGNALL_COBERTURA_SERVICIOS=1 scripts/cobertura.sh   # Neon and the LLM too
#
# `--source=app` measures the application package only and **counts as 0 % the
# modules that no script imported**: an honest 0 % is what makes the missing
# coverage visible, and no coverage is invented for a file nobody ran.

set -u

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT" || exit 1

COVERAGE_PIN=$(sed -n 's/^coverage==\(.*\)$/\1/p' requirements-dev.txt | head -1)
COVERAGE_PIN=${COVERAGE_PIN:-7.17.3}
# Coverage is installed on the host tree and mounted, because every
# `docker compose run` is a fresh container: a directory inside the container
# would be gone by the next script.
DEPS_HOST=${TMPDIR:-/tmp}/signall-cobertura-deps-$(id -u)
DEPS_CONTAINER=/coverage-deps
LIMIT_SECONDS=${SIGNALL_COBERTURA_LIMITE:-300}
mkdir -p "$DEPS_HOST"

# Scripts that need a real service. They are not run by default: some write to
# Neon and the others call the model (which costs money). Doubles are not used
# here on purpose: a script that fakes a service also fakes its failures, and
# that is exactly what coverage has to show.
needs_service() {
  case "$1" in
    verify_catalog_repository) echo "reads the catalog from Neon (real DATABASE_URL)" ;;
    verify_validator_service)  echo "reads the catalog from Neon (real DATABASE_URL)" ;;
    verify_semantic_cache)     echo "writes to and reads from Neon" ;;
    verify_nlp_service)        echo "Neon + embeddings + LLM" ;;
    verify_orchestrator)       echo "Neon + embeddings + LLM" ;;
    verify_llm_client)         echo "calls the LLM and also reads the keyboard" ;;
    *)                         echo "" ;;
  esac
}

# Runs a command line inside the backend image with the repository mounted at
# /app. `--user` keeps the files it writes owned by the host user.
in_image() {
  timeout "$LIMIT_SECONDS" docker compose run --rm --no-deps \
    --user "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    -e PYTHONPATH="$DEPS_CONTAINER" \
    -v "$ROOT":/app \
    -v "$DEPS_HOST":"$DEPS_CONTAINER" \
    -w /app \
    backend bash -lc "$1"
}

if ! command -v docker >/dev/null 2>&1; then
  echo "cobertura: falta docker; los verify scripts necesitan la imagen del backend" >&2
  exit 2
fi

echo "cobertura: limpiando los archivos de la corrida anterior"
rm -f coverage.xml .coverage .coverage.*

if ! in_image "python -m coverage --version" >/dev/null 2>&1; then
  echo "cobertura: instalando coverage==$COVERAGE_PIN en $DEPS_HOST"
  if ! in_image "pip install --quiet --disable-pip-version-check --target $DEPS_CONTAINER 'coverage==$COVERAGE_PIN'"; then
    echo "cobertura: no se pudo instalar coverage; se aborta" >&2
    exit 2
  fi
fi

run_count=0
failed=""
skipped=""
results=""

for path in scripts/verify_*.py; do
  module=$(basename "$path" .py)
  reason=$(needs_service "$module")
  if [ -n "$reason" ] && [ "${SIGNALL_COBERTURA_SERVICIOS:-0}" != "1" ]; then
    skipped="$skipped\n  SALTEADO  $module  ($reason)"
    continue
  fi

  run_count=$((run_count + 1))
  output=$(in_image "python -m coverage run --parallel-mode --source=app -m scripts.$module" 2>&1)
  status=$?
  case $status in
    0) results="$results\n  PASS      $module" ;;
    124) results="$results\n  FALLA     $module  (no terminó en ${LIMIT_SECONDS}s)"
         failed="$failed $module" ;;
    *) results="$results\n  FALLA     $module  (exit $status)"
       failed="$failed $module"
       printf '%s\n' "$output" | tail -5 | sed 's/^/            /' ;;
  esac
done

echo
echo "cobertura: combinando $(find . -maxdepth 1 -name '.coverage.*' | wc -l) archivo(s) de datos"
if ! in_image "python -m coverage combine && python -m coverage xml -o coverage.xml" >/dev/null 2>&1; then
  echo "cobertura: no se generó cobertura (¿ningún script produjo datos?)" >&2
  printf '%b\n' "$results"
  exit 3
fi

total=$(in_image "python -m coverage report" 2>/dev/null | tail -1)
echo
echo "cobertura por script ($run_count corridos):"
printf '%b\n' "$results"
if [ -n "$skipped" ]; then
  echo
  echo "cobertura: salteados por necesitar servicios (SIGNALL_COBERTURA_SERVICIOS=1 para incluirlos):"
  printf '%b\n' "$skipped"
fi
echo
echo "cobertura total de app/ (coverage report): $total"
echo "reporte XML: coverage.xml"

if [ -n "$failed" ]; then
  echo
  echo "cobertura: scripts que fallaron:$failed" >&2
  echo "cobertura: el reporte es válido (salió del código que sí corrió); el fallo es de" >&2
  echo "           esos scripts, no del runner. La salida de cada uno está arriba." >&2
  if [ "${SIGNALL_COBERTURA_ESTRICTO:-0}" = "1" ]; then
    exit 1
  fi
fi
exit 0
