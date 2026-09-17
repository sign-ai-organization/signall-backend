from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_host: str = "127.0.0.1"
    app_port: int = 8080
    log_level: str = "INFO"

    database_url: str
    llm_api_key: str
    llm_model: str
    llm_temperature: float = 0.0
    llm_timeout_ms: int = 10000

    # Max cosine distance (pgvector <=>) between embeddings to count as a
    # semantic cache HIT. Lower = stricter match required.
    semantic_cache_similarity_threshold: float = 0.15

    # Default matches the "stt" service name in docker-compose.yml.
    stt_ws_url: str = "ws://stt:8000/ws/transcribe"


settings = Settings()
