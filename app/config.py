from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "InfoBeans Agent Hub"
    app_env: str = "production"
    app_debug: bool = False
    app_base_url: str = "https://agenthub.creatingwow.in"

    secret_key: str
    database_url: str

    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    google_allowed_domain: str = ""

    session_cookie_secure: bool = True
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "lax"
    session_max_age_seconds: int = 28800  # 8 hours

    max_upload_size_mb: int = 50

    ppt_validator_internal_url: str = "http://127.0.0.1:8080"

    @property
    def is_development(self) -> bool:
        return self.app_env in ("development", "dev", "local")


settings = Settings()
