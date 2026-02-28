"""Async Postgres engine and session factory (SQLAlchemy + asyncpg)."""

import logging
import threading
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)

# Lazy-initialized module-level engine and session factory (set via init())
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None
_init_lock = threading.Lock()
_url: Optional[str] = None
_pool_options: dict[str, Any] = {}


def init(url: str, *, pool_size: int = 5, max_overflow: int = 10, echo: bool = False) -> None:
    """Configure the client with the given URL and pool options. Call once at app startup (e.g. from deps or lifespan)."""
    global _url, _pool_options
    with _init_lock:
        _url = url
        _pool_options = { "pool_size": pool_size, "max_overflow": max_overflow, "echo": echo }


def _ensure_engine() -> AsyncEngine:
    """Create engine and session factory once, thread-safe. Requires init() to have been called."""
    global _engine, _session_factory
    if _engine is not None:
        return _engine
    with _init_lock:
        if _engine is None:
            if _url is None:
                msg = "Postgres client not initialized. Call init(url, ...) at app startup (e.g. from deps or lifespan)."
                logger.error(msg)
                raise RuntimeError(msg)
            try:
                _engine = create_async_engine(
                    _url,
                    pool_size=_pool_options.get("pool_size", 5),
                    max_overflow=_pool_options.get("max_overflow", 10),
                    pool_pre_ping=True,
                    echo=_pool_options.get("echo", False),
                )
                _session_factory = async_sessionmaker(
                    _engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                    autocommit=False,
                    autoflush=False,
                )
            except Exception as e:
                logger.exception("Failed to create async Postgres engine: %s", e)
                raise
    return _engine


def get_engine() -> AsyncEngine:
    """Return the async engine; creates on first use."""
    return _ensure_engine()


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the async session factory; creates engine on first use."""
    _ensure_engine()
    assert _session_factory is not None
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session; commit on success, rollback on error, always close."""
    factory = get_session_factory()
    session: AsyncSession = factory()
    try:
        yield session
        await session.commit()
    except Exception as e:
        logger.exception("Session error; rolling back transaction: %s", e)
        await session.rollback()
        raise
    finally:
        await session.close()


async def ping() -> bool:
    """Return True if the database is reachable."""
    try:
        factory = get_session_factory()
        session: AsyncSession = factory()
        try:
            await session.execute(text("SELECT 1"))
            return True
        finally:
            await session.close()
    except Exception as e:
        logger.debug("Postgres ping failed: %s", e, exc_info=True)
        return False


async def close() -> None:
    """Dispose the engine and clear module state; call on shutdown."""
    global _engine, _session_factory, _url, _pool_options
    if _engine is not None:
        try:
            await _engine.dispose()
        except Exception as e:
            logger.exception("Error while disposing Postgres engine: %s", e)
            raise
        finally:
            _engine = None
            _session_factory = None
            _url = None
            _pool_options = {}
