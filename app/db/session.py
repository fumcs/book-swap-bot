"""Async SQLModel session and engine helpers."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.config import get_settings

settings = get_settings()


def _normalize_database_url(raw_url: str) -> str:
    """Ensure the database URL is async-driver compatible.

    The settings may provide plain ``postgresql://`` URLs which we upgrade to
    ``postgresql+asyncpg://`` for SQLAlchemy's async engine.
    """

    if raw_url.startswith("postgresql://") and "+" not in raw_url.split(":", 1)[0]:
        return raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if raw_url.startswith("sqlite://") and "+" not in raw_url.split(":", 1)[0]:
        # default to sqlite+aiosqlite for async operation
        return raw_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return raw_url


DATABASE_URL = _normalize_database_url(settings.DATABASE_URL)

def _should_echo(log_level: str) -> bool:
    return log_level.upper() == "DEBUG"


def create_engine(echo: Optional[bool] = None) -> AsyncEngine:
    """Create the global async engine.

    Args:
        echo: Optional override of SQL echo flag. Defaults to True when
            ``LOG_LEVEL`` is ``DEBUG``.
    """

    return create_async_engine(
        DATABASE_URL,
        echo=_should_echo(settings.LOG_LEVEL) if echo is None else echo,
        future=True,
        pool_pre_ping=True,
    )


engine: AsyncEngine = create_engine()

# SQLModel-compatible async session factory
async_session_factory: sessionmaker[AsyncSession] = sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def init_db() -> None:
    """Create database tables based on SQLModel metadata.

    This is primarily useful for local development. Production environments
    should prefer running Alembic migrations.
    """

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def dispose_engine() -> None:
    """Dispose of the global engine (used on graceful shutdown)."""

    await engine.dispose()


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Provide a transactional scope for a series of operations."""

    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI/Starlette dependency-compatible session provider."""

    async with async_session_factory() as session:
        yield session
