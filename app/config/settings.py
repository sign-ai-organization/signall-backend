from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_host: str = "127.0.0.1"
    app_port: int = 8080

    database_url: str
    llm_api_key: str
    llm_model: str
    llm_temperature: float = 0.0


settings = Settings()
