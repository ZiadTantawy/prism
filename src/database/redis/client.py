import logging

from redis.asyncio import Redis as AsyncRedis

logger = logging.getLogger(__name__)


class AsyncRedisClient:
    """Async Redis client wrapper. Use with FastAPI/async for non-blocking I/O."""

    def __init__(self, host: str, port: int, decode_responses: bool = True, socket_connect_timeout: float = 5.0):
        """Manages the low-level async connection to Redis."""
        self._client: AsyncRedis = AsyncRedis(host=host, port=port, decode_responses=decode_responses, socket_connect_timeout=socket_connect_timeout)

    @property
    def client(self) -> AsyncRedis:
        """Get the async Redis client."""
        return self._client

    async def close(self) -> None:
        """Close the Redis connection."""
        try:
            await self._client.close()
        except Exception as e:
            logger.exception("Error closing Redis client: %s", e)
            raise
    
    async def ping(self) -> bool:
        """Return True if Redis is reachable."""
        try:
            await self._client.ping()
            return True
        except Exception as e:
            logger.exception("Error pinging Redis: %s", e)
            return False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
