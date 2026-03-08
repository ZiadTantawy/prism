"""Async Postgres engine and session factory (SQLAlchemy + asyncpg)."""

import threading
from collections.abc import AsyncGenerator
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from shared.config import settings
from shared.logger import get_logger

logger = get_logger(__name__)

# Lazy-initialized module-level engine and session factory (set via init() or from settings)
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None
_init_lock = threading.Lock()
_url: Optional[str] = None
_pool_options: dict[str, Any] = {}


def init(
    url: str,
    *,
    pool_size: int = 5,
    max_overflow: int = 10,
    echo: bool = False,
) -> None:
    """Configure the client with the given URL and pool options. Call once at app startup (e.g. lifespan).
    If never called, engine is created on first use from settings.postgres_async_url and DATABASE_* settings.
    """
    global _url, _pool_options
    with _init_lock:
        _url = url
        _pool_options = {"pool_size": pool_size, "max_overflow": max_overflow, "echo": echo}


def _ensure_engine() -> AsyncEngine:
    """Create engine and session factory once, thread-safe."""
    global _engine, _session_factory
    if _engine is not None:
        return _engine
    with _init_lock:
        if _engine is not None:
            return _engine
        try:
            if _url is not None:
                url = _url
                pool_size = _pool_options.get("pool_size", 5)
                max_overflow = _pool_options.get("max_overflow", 10)
                echo = _pool_options.get("echo", False)
            else:
                url = settings.postgres_async_url
                pool_size = settings.DATABASE_POOL_SIZE
                max_overflow = settings.DATABASE_POOL_MAX_OVERFLOW
                echo = settings.DATABASE_ECHO
            _engine = create_async_engine(
                url,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=True,
                echo=echo,
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
    """Return the async engine; creates on first access if needed (from init() or settings)."""
    return _ensure_engine()


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    _ensure_engine()
    assert _session_factory is not None
    return _session_factory


class AsyncSessionContext:
    """Async context manager with explicit __aenter__ / __aexit__: commit on success, rollback and close on exit."""

    def __init__(self) -> None:
        self._session: Optional[AsyncSession] = None

    async def __aenter__(self) -> AsyncSession:
        factory = get_session_factory()
        self._session = factory()
        return self._session

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        if self._session is None:
            return False
        try:
            if exc_type is None:
                await self._session.commit()
            else:
                await self._session.rollback()
                logger.error(
                    "Session error; rolled back transaction: %s",
                    exc_val,
                    exc_info=(exc_type, exc_val, exc_tb),
                )
        finally:
            await self._session.close()
            self._session = None
        return False  # do not suppress the exception


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session; commits on success, rolls back on exception, closes on exit (for FastAPI Depends)."""
    async with AsyncSessionContext() as session:
        yield session


async def ping() -> bool:
    """Run a simple query to verify the database is reachable. Use for health checks."""
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.debug("Postgres ping failed: %s", e, exc_info=True)
        return False


async def close() -> None:
    """Dispose the engine and clear module state; call on shutdown (e.g. lifespan)."""
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
