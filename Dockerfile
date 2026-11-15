FROM python:3.12-slim

WORKDIR /app

# PyTorch comes from the CPU index, always. `sentence-transformers` needs torch
# for the local embeddings model, and that model runs on the CPU
# (`EmbeddingModel` never asks for CUDA): the PyPI wheel for Linux would drag
# 7,5 GB of `nvidia-*` packages this service cannot use. Installing torch first,
# from the explicit index, means the resolver in `requirements.txt` finds it
# already present and does not download the CUDA build.
#
# There is no CUDA variant of this image on purpose: the backend has no GPU code
# and the GPU profile belongs to the STT service, in the sibling repo.
COPY requirements.txt .
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu "torch==2.15.0" \
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
