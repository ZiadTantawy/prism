from __future__ import annotations

try:
    import aio_pika
    from aio_pika.abc import AbstractRobustConnection as _AbstractRobustConnection
except ImportError:  # pragma: no cover - handled at runtime
    aio_pika = None  # type: ignore[assignment]
    _AbstractRobustConnection = None  # type: ignore[assignment]

from shared.logger import get_logger

logger = get_logger(__name__)


class AsyncRabbitMQClient:
    """Async RabbitMQ client wrapper using aio-pika robust connections."""

    def __init__(self, url: str, **connect_options: object) -> None:
        if aio_pika is None:
            raise ImportError(
                "AsyncRabbitMQClient is not available. Install aio-pika>=9.4.0",
            )
        self._url = url
        self._connect_options = dict(connect_options)
        self._connection: _AbstractRobustConnection | None = None

    async def connect(self) -> _AbstractRobustConnection:
        """Establish (or reuse) a robust connection to RabbitMQ."""
        if self._connection is None or self._connection.is_closed:
            logger.info("Opening RabbitMQ connection to %s", self._url)
            self._connection = await aio_pika.connect_robust(
                self._url,
                **self._connect_options,
            )
        return self._connection

    @property
    def connection(self) -> _AbstractRobustConnection:
        """Return the underlying robust connection.

        Raises:
            RuntimeError: If the connection has not been established yet.
        """
        if self._connection is None or self._connection.is_closed:
            raise RuntimeError(
                "RabbitMQ connection not established; call `await connect()` first.",
            )
        return self._connection

    async def close(self) -> None:
        """Close the underlying connection if it exists."""
        if self._connection is None or self._connection.is_closed:
            self._connection = None
            return
        logger.info("Closing RabbitMQ connection to %s", self._url)
        await self._connection.close()
        self._connection = None

    async def __aenter__(self) -> "AsyncRabbitMQClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

