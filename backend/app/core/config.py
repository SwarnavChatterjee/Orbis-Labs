from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Orbis Labs"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://orbis:orbis@localhost:5432/orbis_labs"
    openai_api_key: str | None = None
    openai_model: str = "gpt-6-astra"
    demo_mode: bool = False
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"
    session_secret: str = "change-me-in-production"
    frontend_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
