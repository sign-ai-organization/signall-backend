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

    # Max cosine distance (pgvector <=>) between embeddings to count as a
    # semantic cache HIT. Lower = stricter match required.
    semantic_cache_similarity_threshold: float = 0.05

    # Default matches the "stt" service name in docker-compose.yml.
    stt_ws_url: str = "ws://stt:8000/ws/transcribe"

    # ---- Tiempo real -------------------------------------------------------
    # Con esto apagado el backend se comporta exactamente como antes: espera el
    # transcripción final y manda la frase completa en un solo lote. Encendido,
    # traduce y envia cada fragmento de la frase a medida que el STT lo
    # confirma como dicho (ver app/realtime/).
    realtime_enabled: bool = True

    # Margen en ms entre "la palabra terminó" y "la doy por firme". Whisper
    # marca el final de una palabra un poco antes de que de verdad se calle,
    # así que un margen pequeño hace que se firme tarde. Con 180 ms la palabra
    # anterior al silencio ya está estable pero todavía hay Cola para
    # transcribir la que se está formando.
    realtime_settle_margin_ms: int = 180

    # Cuántas palabras nuevas esperar antes de lanzar una traducción, cuando el
    # STT no manda timestamps por palabra. Evita una llamada al LLM por sílaba;
    # a cambio la última palabra de la frase espera un poco más.
    realtime_batch_words: int = 2

    # Máximo de fragmentos enviados por utterance. Si el STT se desarma y nunca
    # cierra el segmento, esto corta la racha en vez de acumular indefinida.
    realtime_max_segments: int = 32

    # Cargar el semantic_cache completo en memoria al arrancar. Con la base
    # Neon a ~100 ms por viaje, un HIT por red costaba más que el LLM que
    # estaba evitando. Es un caché derivado: se reconstruye solo.
    semantic_cache_preload: bool = True

    # Tope de filas en el caché en memoria. El caché crece con lo que la gente
    # dice; si sepas que va a crecer mucho, esto lo frena en vez de dejar que
    # el proceso se coma la RAM.
    semantic_cache_max_rows: int = 20000

    # Nested: override as SENTENCE_SEGMENTER__<FIELD>, e.g. SENTENCE_SEGMENTER__ENABLED=false.
    sentence_segmenter: SentenceSegmenterSettings = SentenceSegmenterSettings()


settings = Settings()
