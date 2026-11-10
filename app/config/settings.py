from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.sentence_segmenter import SentenceSegmenterSettings


class Settings(BaseSettings):
    # `.env.local` is optional and overrides `.env` when it exists. It is the
    # file for a development-only provider (for example, a local Ollama), so a
    # run against the official model never picks it up unless it is present.
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        extra="ignore",
        env_nested_delimiter="__",
    )

    app_host: str = "127.0.0.1"
    app_port: int = 8080
    log_level: str = "INFO"

    # Send per-step pipeline timings to the client as a "trace" message.
    # Debug-only: keep it off for the production Android client.
    debug_trace_enabled: bool = False

    # RNF-SEC-02: a client audio chunk has to be non-empty, an even number of
    # bytes (PCM16 samples) and no larger than this. A normal 30 ms chunk at
    # 16 kHz is 960 bytes; 32 KiB is about one second, so anything bigger is
    # not a capture chunk and is rejected instead of being forwarded to the STT.
    audio_max_chunk_bytes: int = 32768

    database_url: str
    db_pool_min_size: int = 5
    db_pool_max_size: int = 10
    # 0 = never close idle pooled connections; the keep-alive below decides
    # when the database may go idle instead.
    db_pool_max_inactive_connection_lifetime_seconds: float = 0
    # Ceiling of a single query. A query that hangs takes the phrase with it,
    # and the Android client gives up on its own after 15 s: the backend is the
    # one that has to report the failure first.
    db_command_timeout_seconds: float = 5.0
    # Ceiling of opening one connection to the database. Without it, a database
    # that accepts TCP but never completes the PostgreSQL handshake leaves the
    # start-up waiting for the operating system's timeout.
    db_connect_timeout_seconds: float = 5.0
    # Ceiling of waiting for a free connection from the pool. The pool has
    # min_size 5 and max_size 10, so this is a guard against a leaked connection,
    # not the normal path.
    db_acquire_timeout_seconds: float = 5.0
    # How many times a failed query is tried again. One retry covers a database
    # that is resuming from scale-to-zero; with the ceiling above, the worst
    # case is about 10 s, still under the client's 15 s.
    db_max_retries: int = 1
    # Wait between two attempts of the same query.
    db_retry_delay_seconds: float = 0.5
    # How often the backend tries again to reach the database, or to load the
    # catalog and the semantic cache, when it started without them (PR-RES-04).
    # The check stops for good once everything is loaded. 0 disables it.
    db_recovery_interval_seconds: float = 15

    # Neon suspends compute after 5 min idle (fixed on the Free plan). While
    # there was activity (session opened / final transcript) within the idle
    # window, ping every interval to keep it awake. Interval 0 disables it.
    db_keepalive_interval_seconds: float = 240
    db_keepalive_idle_window_seconds: float = 1200
    llm_api_key: str
    llm_model: str
    llm_temperature: float = 0.0
    llm_timeout_ms: int = 5000
    # How many times a failed call to the model is tried again. One retry
    # absorbs a momentary network cut, and with the ceiling above the worst
    # case is about 10 s: under the 15 s the Android client waits before it
    # declares the phrase failed on its own.
    llm_max_retries: int = 1
    # Base URL of any OpenAI-compatible chat endpoint. Empty means OpenAI itself.
    # Set it to run the same prompt against a local model server, e.g.
    # http://host.docker.internal:11434/v1 for Ollama. From inside Docker on
    # Linux the service also needs
    # extra_hosts: ["host.docker.internal:host-gateway"].
    llm_base_url: str = ""

    # Mandar una frase de relleno al LLM al arrancar. Con un servidor local la
    # primera inferencia carga el modelo: medido 6.2 s contra 270-440 ms de las
    # siguientes. Sin esto la primera frase de la sesión paga ese costo y solo
    # esa, que es la peor forma de fallar. 0 lo desactiva.
    llm_warmup_enabled: bool = True

    # Modelo de embeddings del caché semántico. Estaba fijo en el código
    # (`DEFAULT_MODEL_NAME`), así que probar otra alternativa —`bge-m3`,
    # `multilingual-e5-large`— exigía editar `embedding_model.py` y reconstruir
    # la imagen. PR-CAC-01 pide comparar alternativas, y una comparación que
    # necesita tocar el código no es una comparación: es un cambio de código
    # por modelo. Cambiarlo obliga a vaciar `semantic_cache`, porque los
    # vectores guardados son de otro espacio y la distancia entre ellos no
    # significa nada.
    embedding_model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"

    # Max cosine distance (pgvector <=>) between embeddings to count as a
    # semantic cache HIT. Lower = stricter match required.
    #
    # 0.03 instead of 0.05 (owner's decision D5, 2026-11-05): with 0.05 the
    # cached variants of PR-CAC-03 resolved 21/30 but two of them returned the
    # glosses of a *different* phrase (measured 2026-11-04); with 0.03 no
    # variant matched a foreign row. The cost is fewer hits, i.e. more LLM
    # calls, which is the trade the round is paying for.
    semantic_cache_similarity_threshold: float = 0.03

    # Cargar el semantic_cache completo en memoria al arrancar. Con la base
    # Neon a ~100 ms por viaje, un HIT por red costaba más que el LLM que
    # estaba evitando. Es un caché derivado: se reconstruye solo.
    semantic_cache_preload: bool = True

    # Tope de filas en el caché en memoria. El caché crece con lo que la gente
    # dice; si sepas que va a crecer mucho, esto lo frena en vez de dejar que
    # el proceso se coma la RAM.
    semantic_cache_max_rows: int = 20000

    # Token for the administration endpoints (`POST /admin/cache/reload`, fase 5
    # of the implementation plan). Empty means the endpoints are not exposed at
    # all: a deployment that does not set it answers 404, instead of leaving a
    # route that reloads the cache open to anyone who can reach the port.
    #
    # It is a header (`X-Admin-Token`) and not a query parameter on purpose:
    # a token in the URL ends up in logs and in shell history.
    admin_token: str = ""

    # Default matches the "stt" service name in docker-compose.yml.
    stt_ws_url: str = "ws://stt:8000/ws/transcribe"

    # How often to re-read the STT's /health to mirror its runtime configuration
    # (today `silence_timeout_ms`) into our own /health. The Android app needs
    # that value for its debug overlay and cannot ask the STT directly, so it has
    # to travel through this service. 0 disables the poll.
    stt_config_poll_seconds: float = 30.0

    # Nested: override as SENTENCE_SEGMENTER__<FIELD>, e.g. SENTENCE_SEGMENTER__ENABLED=false.
    sentence_segmenter: SentenceSegmenterSettings = SentenceSegmenterSettings()


settings = Settings()
