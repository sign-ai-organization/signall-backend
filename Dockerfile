FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# Las herramientas de verificación viajan con la imagen para poder correrlas
# contra el mismo entorno que el servicio:
#
#   docker compose exec backend python scripts/verify_incremental.py
#   docker compose exec backend python scripts/verify_client_frames.py
#
# En el host faltarían dependencias (httpx2 para el TestClient), y un check que
# solo corre en un lado no verifica nada.
COPY scripts ./scripts

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
