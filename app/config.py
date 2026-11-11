from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LedgerLine"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://ledgerline:ledgerline_dev@localhost:5432/ledgerline"
    jwt_secret_key: str = "replace-this-development-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.app_env.lower() in {"production", "prod"}:
            if self.jwt_secret_key == "replace-this-development-secret-key":
                raise ValueError("JWT_SECRET_KEY must be configured outside development")
            if len(self.jwt_secret_key) < 32:
                raise ValueError("JWT_SECRET_KEY must contain at least 32 characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
