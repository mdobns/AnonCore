"""Backend configuration – loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL
    database_url: str = "postgresql+asyncpg://anoncore:anoncore@localhost:5432/anoncore"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # JWT
    secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # API keys (comma-separated list of valid keys)
    valid_api_keys: str = "dev-api-key"

    # Moderation
    moderation_enabled: bool = True
    max_strikes: int = 3

    # CORS
    allowed_origins: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def api_keys(self) -> list[str]:
        return [k.strip() for k in self.valid_api_keys.split(",") if k.strip()]

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def admin_emails(self) -> list[str]:
        import os
        raw = os.getenv("ADMIN_EMAILS", "")
        return [e.strip() for e in raw.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
