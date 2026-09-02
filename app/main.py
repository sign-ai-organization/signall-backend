from fastapi import FastAPI

from app.config.logging import configure_logging
from app.config.settings import settings

configure_logging(settings.log_level)

app = FastAPI()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
