"""Async Qdrant client wrapper: connection, ensure_collection, health, close."""

import logging
from typing import Optional

from qdrant_client.async_qdrant_client import AsyncQdrantClient as _AsyncQdrantClient
from qdrant_client.http.models import Distance, VectorParams

from core.config import settings


logger = logging.getLogger(__name__)


class AsyncQdrantClient:
    """Thin wrapper around qdrant_client.AsyncQdrantClient for Prism."""

    def __init__(self, url: str) -> None: 
        self._client = _AsyncQdrantClient(url=url)

    @property
    def client(self) -> _AsyncQdrantClient: return self._client

    async def close(self) -> None:
        try:
            await self._client.close()
        except Exception as e:
            logger.exception("Error closing Qdrant client: %s", e)
            raise

    async def ping(self) -> bool:
        """Return True if Qdrant is reachable (e.g. via a cheap API call)."""
        try:
            await self._client.get_collections()
            return True
        except Exception as e:
            logger.debug("Qdrant ping failed: %s", e, exc_info=True)
            return False

    async def ensure_collection(self, collection_name: str, vector_size: int, *, distance: Distance = Distance.COSINE) -> None:
        """Create the collection if it does not exist; idempotent."""
        try:
            exists = await self._client.collection_exists(collection_name)
            if not exists:
                await self._client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=distance),
                )
        except Exception as e:
            logger.exception("Qdrant ensure_collection failed for %s: %s", collection_name, e)
            raise

    async def __aenter__(self) -> "AsyncQdrantClient": return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        try:
            await self._client.close()
        except Exception as e:
            logger.exception("Error closing Qdrant client in context manager: %s", e)
            raise
