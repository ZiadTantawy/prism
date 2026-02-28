import logging
import uuid
from typing import Any, Dict, List, Optional

from qdrant_client.models import PointStruct, Vector, Filter, FieldCondition

from database.qdrant.client import AsyncQdrantClient
from database.qdrant.types import QdrantSearchResult


logger = logging.getLogger(__name__)


class QdrantRepositoryError(Exception):
    """Base for Qdrant repository errors."""
    pass


def generate_point_id(chunk_id: str) -> str:
    """Generate deterministic UUID for a chunk point. Uses UUIDv5 (namespace + name-based) so re-ingests update the same point."""
    namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # Standard UUID namespace
    return str(uuid.uuid5(namespace, chunk_id))

class QdrantRepository:
    """Repository for Qdrant vector database."""

    def __init__(self, client: AsyncQdrantClient): 
        self._client = client

    @property
    def client(self) -> AsyncQdrantClient: 
        return self._client.client

    async def upsert_vector_points(self, collection_name: str, points: List[PointStruct], batch_size: int = 100) -> None:
        """Upsert vector points into the Qdrant collection with simple batching."""
        try:
            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                await self.client.upsert(collection_name=collection_name, points=batch)
        except Exception as e:
            logger.exception("Qdrant upsert failed for collection %s: %s", collection_name, e)
            raise QdrantRepositoryError(f"Failed to upsert points into {collection_name}: {e}") from e

    async def search_vector_points(self, collection_name: str, query_vector: Vector, k: int = 10, query_filter: Optional[Filter] = None) -> List[QdrantSearchResult]:
        """Search vector points in the Qdrant collection."""
        try:
            result = await self.client.search(collection_name=collection_name, query_vector=query_vector, limit=k, filter=query_filter)
        except Exception as e:
            logger.exception("Qdrant search failed for collection %s: %s", collection_name, e)
            raise QdrantRepositoryError(f"Failed to search collection {collection_name}: {e}") from e

        return [QdrantSearchResult(id=point.id, score=point.score, payload=point.payload) for point in result]

    async def delete_points(self, collection_name: str, point_ids: Optional[List[str]] = None, filter_conditions: Optional[List[FieldCondition]] = None) -> None:
        """Delete points from a collection."""
        if point_ids and filter_conditions:
            raise ValueError("Cannot specify both point_ids and filter_conditions")

        if not point_ids and not filter_conditions:
            raise ValueError("Must specify either point_ids or filter_conditions")

        try:
            if point_ids:
                await self.client.delete(collection_name=collection_name, points_selector=point_ids)
            else:
                await self.client.delete(collection_name=collection_name, points_selector=Filter(must=filter_conditions))
        except Exception as e:
            logger.exception("Qdrant delete failed for collection %s: %s", collection_name, e)
            raise QdrantRepositoryError(f"Failed to delete points in {collection_name}: {e}") from e

    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get collection information/stats."""
        try:
            info = await self.client.get_collection(collection_name=collection_name)
            return {
                "name": collection_name,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "segments_count": getattr(info, "segments_count", None),
                "status": str(info.status) if hasattr(info.status, "__str__") else info.status,
            }
        except Exception as e:
            logger.exception("Qdrant get_collection_info failed for collection %s: %s", collection_name, e)
            raise QdrantRepositoryError(f"Failed to get collection info for {collection_name}: {e}") from e

    async def delete_collection(self, collection_name: str) -> None:
        """Delete an entire collection."""
        try:
            await self.client.delete_collection(collection_name=collection_name)
            logger.info("Deleted collection: %s", collection_name)
        except Exception as e:
            logger.exception("Qdrant delete_collection failed for collection %s: %s", collection_name, e)
            raise QdrantRepositoryError(f"Failed to delete collection {collection_name}: {e}") from e