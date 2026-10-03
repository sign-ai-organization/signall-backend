from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.sentence_segmenter import SentenceSegmenterSettings


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_nested_delimiter="__")

    app_host: str = "127.0.0.1"
    app_port: int = 8080
    log_level: str = "INFO"

    # Send per-step pipeline timings to the client as a "trace" message.
    # Debug-only: keep it off for the production Android client.
    debug_trace_enabled: bool = False

    database_url: str
    db_pool_min_size: int = 5
    db_pool_max_size: int = 10
    # 0 = never close idle pooled connections; the keep-alive below decides
    # when the database may go idle instead.
    db_pool_max_inactive_connection_lifetime_seconds: float = 0

    # Neon suspends compute after 5 min idle (fixed on the Free plan). While
    # there was activity (session opened / final transcript) within the idle
    # window, ping every interval to keep it awake. Interval 0 disables it.
    db_keepalive_interval_seconds: float = 240
    db_keepalive_idle_window_seconds: float = 1200
    llm_api_key: str
    llm_model: str
    llm_temperature: float = 0.0
    llm_timeout_ms: int = 10000

    # Max cosine distance (pgvector <=>) between embeddings to count as a
    # semantic cache HIT. Lower = stricter match required.
    semantic_cache_similarity_threshold: float = 0.05

    # Default matches the "stt" service name in docker-compose.yml.
    stt_ws_url: str = "ws://stt:8000/ws/transcribe"

    # Nested: override as SENTENCE_SEGMENTER__<FIELD>, e.g. SENTENCE_SEGMENTER__ENABLED=false.
    sentence_segmenter: SentenceSegmenterSettings = SentenceSegmenterSettings()


settings = Settings()
