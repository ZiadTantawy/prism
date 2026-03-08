from __future__ import annotations

try:
    from qdrant_client import AsyncQdrantClient as _AsyncQdrantClient
except ImportError:
    _AsyncQdrantClient = None  # type: ignore

from shared.logger import get_logger

logger = get_logger(__name__)


class AsyncQdrantClient:
    """Async Qdrant client wrapper. Use with FastAPI/async for non-blocking I/O."""
    
    def __init__(self, host: str, port: int, url: str | None = None):
        """Manages the low-level async connection to Qdrant.
        
        Args:
            host: Qdrant server hostname (required if url is not provided)
            port: Qdrant server port (required if url is not provided)
            url: Optional Qdrant server URL (if provided, host and port are ignored)
        """
        if _AsyncQdrantClient is None:
            raise ImportError(
                "AsyncQdrantClient is not available. Install qdrant-client>=1.6.1",
            )

        if url:
            logger.info("Initializing AsyncQdrantClient with url=%s", url)
            self._client = _AsyncQdrantClient(url=url)
        else:
            logger.info("Initializing AsyncQdrantClient with host=%s port=%s", host, port)
            self._client = _AsyncQdrantClient(host=host, port=port)
    
    @property
    def client(self):
        """Get the async Qdrant client."""
        return self._client
    
    async def close(self) -> None:
        """Close the Qdrant connection."""
        logger.info("Closing AsyncQdrantClient connection")
        await self._client.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()