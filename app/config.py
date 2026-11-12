from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Balance Vault"
    app_env: str = "development"
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        if value.startswith("postgres://"):
            value = f"postgresql://{value.removeprefix('postgres://')}"
        if value.startswith("postgresql://"):
            value = f"postgresql+psycopg://{value.removeprefix('postgresql://')}"
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.app_env.lower() in {"production", "prod"}:
            secret = self.jwt_secret_key.strip()
            if (
                len(secret) < 32
                or secret.lower().startswith(("replace-", "change-me"))
                or (secret.startswith("<") and secret.endswith(">"))
            ):
                raise ValueError("JWT_SECRET_KEY must be configured outside development")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        origins = (origin.strip().rstrip("/") for origin in self.cors_origins.split(","))
        return [
            origin if origin.startswith(("http://", "https://")) else f"https://{origin}"
            for origin in origins
            if origin
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
