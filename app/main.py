from fastapi import FastAPI

from app.config.logging import configure_logging
from app.config.settings import settings
from app.controller.router import router as controller_router

configure_logging(settings.log_level)

app = FastAPI()
app.include_router(controller_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
