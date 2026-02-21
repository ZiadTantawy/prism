"""Tests for database.postgres.client (engine, session, ping, close)."""
import importlib.util
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import text

import database.postgres.client as client_module

_HAS_AIOSQLITE = importlib.util.find_spec("aiosqlite") is not None
_HAS_GREENLET = importlib.util.find_spec("greenlet") is not None
_SKIP_SQLITE_INTEGRATION = not (_HAS_AIOSQLITE and _HAS_GREENLET)


@pytest.fixture(autouse=True)
def reset_client_state():
    """Clear client module engine/factory after each test."""
    yield
    # Clear so next test gets fresh engine when using real settings
    client_module._engine = None
    client_module._session_factory = None


# ---- Unit tests (mocked) ----

@pytest.mark.asyncio
async def test_get_engine_calls_create_async_engine_with_settings():
    """Engine is created with URL and pool/echo from settings."""
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    with (
        patch.object(client_module, "settings") as mock_settings,
        patch.object(client_module, "create_async_engine", return_value=mock_engine) as create_engine,
    ):
        mock_settings.postgres_async_url = "postgresql+asyncpg://u:p@localhost/db"
        mock_settings.DATABASE_POOL_SIZE = 3
        mock_settings.DATABASE_POOL_MAX_OVERFLOW = 7
        mock_settings.DATABASE_ECHO = True

        engine = client_module.get_engine()

        assert engine is mock_engine
        create_engine.assert_called_once()
        call_kw = create_engine.call_args[1]
        assert call_kw["pool_size"] == 3
        assert call_kw["max_overflow"] == 7
        assert call_kw["echo"] is True
        assert call_kw["pool_pre_ping"] is True
        assert create_engine.call_args[0][0] == "postgresql+asyncpg://u:p@localhost/db"


@pytest.mark.asyncio
async def test_get_engine_returns_same_engine_on_repeated_calls():
    """Repeated get_engine() returns the same engine (lazy singleton)."""
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    with (
        patch.object(client_module, "settings") as mock_settings,
        patch.object(client_module, "create_async_engine", return_value=mock_engine),
    ):
        mock_settings.postgres_async_url = "postgresql+asyncpg://localhost/db"
        mock_settings.DATABASE_POOL_SIZE = 5
        mock_settings.DATABASE_POOL_MAX_OVERFLOW = 10
        mock_settings.DATABASE_ECHO = False

        e1 = client_module.get_engine()
        e2 = client_module.get_engine()
        assert e1 is e2


@pytest.mark.asyncio
async def test_get_session_commits_on_success():
    """get_session() commits when the block completes without exception."""
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_factory = MagicMock(return_value=mock_session)

    with patch.object(client_module, "get_session_factory", return_value=mock_factory):
        async with client_module.get_session() as session:
            assert session is mock_session

    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()
    mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_session_rolls_back_on_exception():
    """get_session() rolls back and re-raises when the block raises."""
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_factory = MagicMock(return_value=mock_session)

    with patch.object(client_module, "get_session_factory", return_value=mock_factory):
        with pytest.raises(ValueError, match="boom"):
            async with client_module.get_session() as session:
                raise ValueError("boom")

    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_called_once()
    mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_session_closes_even_on_exception():
    """Session is always closed in finally, even when rollback raises."""
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock(side_effect=RuntimeError("rollback failed"))
    mock_session.close = AsyncMock()
    mock_factory = MagicMock(return_value=mock_session)

    with patch.object(client_module, "get_session_factory", return_value=mock_factory):
        with pytest.raises(RuntimeError, match="rollback failed"):
            async with client_module.get_session() as session:
                raise ValueError("boom")

    mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_ping_returns_true_when_execute_succeeds():
    """ping() returns True when SELECT 1 succeeds."""
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.close = AsyncMock()
    mock_factory = MagicMock(return_value=mock_session)

    with patch.object(client_module, "get_session_factory", return_value=mock_factory):
        result = await client_module.ping()

    assert result is True
    mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_ping_returns_false_on_exception():
    """ping() returns False when the session or execute fails."""
    mock_factory = MagicMock(side_effect=ConnectionError("db down"))

    with patch.object(client_module, "get_session_factory", side_effect=mock_factory):
        result = await client_module.ping()

    assert result is False


@pytest.mark.asyncio
async def test_close_disposes_engine_and_clears_state():
    """close() disposes the engine and sets _engine and _session_factory to None."""
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    with (
        patch.object(client_module, "settings") as mock_settings,
        patch.object(client_module, "create_async_engine", return_value=mock_engine),
    ):
        mock_settings.postgres_async_url = "postgresql+asyncpg://localhost/db"
        mock_settings.DATABASE_POOL_SIZE = 5
        mock_settings.DATABASE_POOL_MAX_OVERFLOW = 10
        mock_settings.DATABASE_ECHO = False
        client_module.get_engine()
        assert client_module._engine is mock_engine
        assert client_module._session_factory is not None

    await client_module.close()

    mock_engine.dispose.assert_called_once()
    assert client_module._engine is None
    assert client_module._session_factory is None


# ---- Integration-style test (real SQLite in-memory) ----

@pytest.mark.asyncio
@pytest.mark.skipif(
    _SKIP_SQLITE_INTEGRATION,
    reason="aiosqlite and greenlet required for in-memory SQLite integration test",
)
async def test_real_engine_session_ping_and_close_with_sqlite():
    """With in-memory SQLite, get_engine, get_session, ping, and close work end-to-end."""
    # Reset so we create a new engine with patched settings
    client_module._engine = None
    client_module._session_factory = None

    fake_settings = MagicMock()
    fake_settings.postgres_async_url = "sqlite+aiosqlite:///:memory:"
    fake_settings.DATABASE_POOL_SIZE = 2
    fake_settings.DATABASE_POOL_MAX_OVERFLOW = 1
    fake_settings.DATABASE_ECHO = False

    # SQLite uses StaticPool and doesn't accept pool_size/max_overflow; strip them in the test
    real_create = client_module.create_async_engine

    def create_sqlite_friendly(url, **kwargs):
        if "sqlite" in str(url):
            kwargs.pop("pool_size", None)
            kwargs.pop("max_overflow", None)
        return real_create(url, **kwargs)

    with (
        patch.object(client_module, "settings", fake_settings),
        patch.object(client_module, "create_async_engine", side_effect=create_sqlite_friendly),
    ):
        engine = client_module.get_engine()
        assert engine is not None

        factory = client_module.get_session_factory()
        assert factory is not None

        async with client_module.get_session() as session:
            await session.execute(text("SELECT 1"))
        # commit and close happen in get_session

        ok = await client_module.ping()
        assert ok is True

        await client_module.close()
        assert client_module._engine is None
        assert client_module._session_factory is None
