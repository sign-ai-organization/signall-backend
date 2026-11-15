FROM python:3.12-slim

WORKDIR /app

# Where the PyTorch wheel comes from. CPU is the base case: the GPU override
# (`docker-compose.gpu.yml`) is the only place that changes this, pointing it at
# PyPI or at a CUDA index. Nothing detects the hardware.
#
# The CPU index matters because the PyPI wheel for Linux drags several GB of
# `nvidia-*` packages that a machine without a GPU cannot use. Installing torch
# first, from an explicit index, means the resolver in `requirements.txt` finds
# it already present and does not download the CUDA build.
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
ARG TORCH_VERSION=2.15.0

COPY requirements.txt .
RUN pip install --no-cache-dir --index-url "${TORCH_INDEX_URL}" "torch==${TORCH_VERSION}" \
    && pip install --no-cache-dir -r requirements.txt

# The configuration of the static analyzers (ruff, mypy) and the pinned
# versions of the tools themselves. They are not needed to run the service,
# but scripts/verify_static_analysis.py checks that they are there, and the
# analyzers can be run inside this image.
COPY pyproject.toml requirements-dev.txt ./

COPY app ./app
# Los `verify_*.py` corren dentro del contenedor (ver `tools/verificar-tiempo-real.sh`
# del repo de Android) porque necesitan las dependencias del servicio: en el host
# faltarían `spacy` y `httpx2`, y un check que solo pasa en un lado no verifica nada.
COPY scripts ./scripts

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
