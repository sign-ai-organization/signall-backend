FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# Los `verify_*.py` corren dentro del contenedor (ver `tools/verificar-tiempo-real.sh`
# del repo de Android) porque necesitan las dependencias del servicio: en el host
# faltarían `spacy` y `httpx2`, y un check que solo pasa en un lado no verifica nada.
COPY scripts ./scripts

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
