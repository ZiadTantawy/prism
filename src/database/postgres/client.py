"""
Postgres: async engine + session factory from settings.postgres_async_url.
Uses SQLAlchemy (asyncpg driver). Exposes engine, session factory,
get_session helper, ping, and close for lifecycle.
"""

import threading
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from core.config import settings

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Lazy-initialized module-level engine and session factory
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None
_init_lock = threading.Lock()


def _ensure_engine() -> AsyncEngine:
    """Create engine and session factory once (thread-safe)."""
    global _engine, _session_factory
    if _engine is not None:
        return _engine
    with _init_lock:
        if _engine is None:
            url = settings.postgres_async_url
            _engine = create_async_engine(
                url,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_POOL_MAX_OVERFLOW,
                pool_pre_ping=True,
                echo=settings.DATABASE_ECHO,
            )
            _session_factory = async_sessionmaker(
                _engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
    return _engine


def get_engine() -> AsyncEngine:
    """Return the async SQLAlchemy engine (creates on first use)."""
    return _ensure_engine()


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the async session factory (creates engine on first use)."""
    _ensure_engine()
    assert _session_factory is not None
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Session scope: commit on success, rollback on error, always close."""
    factory = get_session_factory()
    session: AsyncSession = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def ping() -> bool:
    """Verify the database connection is alive (e.g. for health checks)."""
    try:
        factory = get_session_factory()
        session: AsyncSession = factory()
        try:
            await session.execute(text("SELECT 1"))
            return True
        finally:
            await session.close()
    except Exception:
        return False


async def close() -> None:
    """Dispose the engine and clear module state. Call on app shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
