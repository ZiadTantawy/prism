from db.async_session import (
    AsyncSessionContext,
    close as close_async_db,
    get_async_db,
    get_engine,
    get_session_factory,
    init as init_async_db,
    ping as ping_async_db,
)

__all__ = [
    "get_engine",
    "get_session_factory",
    "get_async_db",
    "AsyncSessionContext",
    "init_async_db",
    "ping_async_db",
    "close_async_db",
]


def _lazy_sync():
    """Import sync session objects on demand to avoid eager engine creation."""
    from db.session import SessionLocal, engine, get_db, ping  # noqa: F811
    return SessionLocal, engine, get_db, ping
