"""Application configuration loaded via `pydantic-settings`.

This module exposes a cached :func:`get_settings` helper for use across the
project. The configuration automatically loads values from environment
variables and optionally an `.env` file (if present).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed application configuration."""

    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_file_encoding="utf-8",
        case_sensitive=False,
        frozen=True,
    )

    TELEGRAM_TOKEN: str = Field(..., description="Telegram bot token issued by @BotFather")
    DATABASE_URL: str = Field(
        ..., description="SQLAlchemy-compatible async connection string (e.g. postgresql+asyncpg://user:pass@host:5432/db)"
    )

    LOG_LEVEL: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = Field(
        "INFO", description="Log verbosity for both bot and web server"
    )
    PAGE_SIZE: PositiveInt = Field(10, description="Default pagination size for book listings")
    UVICORN_HOST: str = Field("0.0.0.0", description="Host interface for the Starlette app")
    UVICORN_PORT: PositiveInt = Field(8000, description="Port for the Starlette app")
    UVICORN_RELOAD: bool = Field(
        False,
        description="Enable uvicorn auto-reload (development only)",
    )
    POLLING: bool = Field(False, description='Run bot polling')
    WEB_CONCURRENCY: PositiveInt = Field(
        1,
        description="Number of uvicorn worker tasks spawned inside the async runner",
    )
    BOT_POLLING_INTERVAL: float = Field(
        1.0,
        ge=0.1,
        description="Polling interval (seconds) for long polling fallback",
    )
    ADMIN_CHAT_ID: Optional[int] = Field(
        None,
        description="Optional Telegram chat id for administrative alerts",
    )
    LOCALE: Optional[str] = Field(
        'en',
        description='Translate code'
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache :class:`Settings` instance.

    Raises:
        pydantic.ValidationError: if required environment variables are missing
            or invalid.
    """

    return Settings()
