from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TYPE_CHECKING

from shared.clients.qdrant import AsyncQdrantClient
from shared.logger import get_logger

if TYPE_CHECKING:  # pragma: no cover - import only for type checkers
    from qdrant_client import AsyncQdrantClient as _RawAsyncQdrantClient
    from qdrant_client import models as qmodels

logger = get_logger(__name__)


class QdrantRepository:
    """Async repository encapsulating low-level Qdrant operations.

    This layer centralizes common CRUD/search interactions with Qdrant while
    staying free of any domain/business logic. Application code should depend
    on this abstraction instead of talking to the raw client directly.
    """

    def __init__(self, client: AsyncQdrantClient) -> None:
        self._client = client

    @property
    def raw(self) -> "_RawAsyncQdrantClient":
        """Expose underlying qdrant_client.AsyncQdrantClient for advanced use."""
        return self._client.client  # type: ignore[no-any-return]

    async def create_collection(
        self,
        collection: str,
        vectors_config: "qmodels.VectorParams",
        **kwargs: Any,
    ) -> Any:
        """Create a collection with the given vector configuration."""
        logger.info("Creating Qdrant collection %s", collection)
        return await self.raw.create_collection(
            collection_name=collection,
            vectors_config=vectors_config,
            **kwargs,
        )

    async def delete_collection(self, collection: str) -> Any:
        """Delete a collection if it exists."""
        logger.info("Deleting Qdrant collection %s", collection)
        return await self.raw.delete_collection(collection_name=collection)

    async def get_collection(self, collection: str) -> Any:
        """Fetch collection information."""
        return await self.raw.get_collection(collection_name=collection)

    async def list_collections(self) -> Any:
        """List all collections in the Qdrant instance."""
        return await self.raw.get_collections()

    async def upsert_points(
        self,
        collection: str,
        points: "Sequence[qmodels.PointStruct]",
        **kwargs: Any,
    ) -> Any:
        """Upsert one or more points into a collection."""
        logger.debug(
            "Upserting %d points into Qdrant collection %s",
            len(points),
            collection,
        )
        return await self.raw.upsert(
            collection_name=collection,
            points=points,
            **kwargs,
        )

    async def search(
        self,
        collection: str,
        vector: "Sequence[float]",
        limit: int = 10,
        **kwargs: Any,
    ) -> Any:
        """Vector similarity search in a collection."""
        return await self.raw.search(
            collection_name=collection,
            query_vector=vector,
            limit=limit,
            **kwargs,
        )

    async def delete_points(
        self,
        collection: str,
        points_selector: "qmodels.PointIds | qmodels.Filter | qmodels.PointSelector",
        **kwargs: Any,
    ) -> Any:
        """Delete points from a collection using a selector."""
        return await self.raw.delete(
            collection_name=collection,
            points_selector=points_selector,
            **kwargs,
        )

