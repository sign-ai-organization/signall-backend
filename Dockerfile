FROM python:3.12-slim

WORKDIR /app

# PyTorch comes from the CPU index, always. `sentence-transformers` needs torch
# for the local embeddings model, and this container is never given the GPU: the
# device reservation lives only on the `stt` service, because the GPU is for
# faster-whisper (SDD, deployment table: only "Servicio STT" is a "Contenedor
# Docker con GPU"). `EmbeddingModel` does not choose a device, so
# `SentenceTransformer` uses whatever it can see, and inside this container that
# is always the CPU: `torch.cuda.is_available()` is False because there are no
# NVIDIA devices, not because torch lacks CUDA.
#
# Which is why the PyPI wheel is pure waste: it would add 7,5 GB of `nvidia-*`
# packages that never get used in the documented deployment. Installing torch
# first, from the explicit CPU index, means the resolver in `requirements.txt`
# finds it already present and does not download the CUDA build.
#
# If the embeddings ever should run on the GPU, it is a design change, not a
# build tweak: the service would have to request the device and take a CUDA
# torch, and the documents would have to say so.
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
