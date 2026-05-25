from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from app.telemetry.logger import logger


class QdrantAdapter:
    """Async Adapter for Qdrant Vector Store."""

    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = AsyncQdrantClient(host=host, port=port)
        self.collection_name = "agent_memories"

    async def ensure_collection(self, vector_size: int = 768):
        """Creates the collection if it doesn't exist."""
        collections = await self.client.get_collections()
        exists = any(c.name == self.collection_name for c in collections.collections)

        if not exists:
            logger.info("creating_qdrant_collection", collection=self.collection_name)
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size, distance=models.Distance.COSINE
                ),
                sparse_vectors_config={
                    "text_sparse": models.SparseVectorParams(
                        index=models.SparseIndexParams(
                            on_disk=False,
                        )
                    )
                }
            )

    async def upsert(
        self,
        memory_id: str,
        vector: list[float],
        payload: dict,
        sparse_vector: models.SparseVector | None = None,
    ):
        """Upserts a vector with payload metadata and optional sparse vector."""
        if sparse_vector is not None:
            qdrant_vector = {
                "": vector,
                "text_sparse": sparse_vector,
            }
        else:
            qdrant_vector = vector

        await self.client.upsert(
            collection_name=self.collection_name,
            points=[models.PointStruct(id=memory_id, vector=qdrant_vector, payload=payload)],
        )

    def _build_filter(
        self,
        session_id: str | None = None,
        hierarchy_level: int | None = None,
        point_ids: list[str] | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> models.Filter | None:
        must_conditions = []
        if session_id:
            must_conditions.append(
                models.FieldCondition(
                    key="session_id", match=models.MatchValue(value=session_id)
                )
            )
        if hierarchy_level is not None:
            must_conditions.append(
                models.FieldCondition(
                    key="hierarchy_level", match=models.MatchValue(value=hierarchy_level)
                )
            )
        if point_ids:
            must_conditions.append(
                models.HasIdCondition(has_id=point_ids)
            )
        
        if since or until:
            range_filter = {}
            if since:
                range_filter["gte"] = since
            if until:
                range_filter["lte"] = until
            must_conditions.append(
                models.FieldCondition(
                    key="created_at",
                    range=models.Range(**range_filter)
                )
            )

        if must_conditions:
            return models.Filter(must=must_conditions)
        return None

    async def search(
        self,
        vector: list[float],
        limit: int = 10,
        session_id: str | None = None,
        hierarchy_level: int | None = None,
        point_ids: list[str] | None = None,
        with_vectors: bool = False,
        since: str | None = None,
        until: str | None = None,
    ):
        """Performs semantic search with optional session, hierarchy level, ID, and temporal filtering."""
        query_filter = self._build_filter(session_id, hierarchy_level, point_ids, since, until)

        response = await self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            with_vectors=with_vectors,
        )
        return response.points

    async def hybrid_search(
        self,
        dense_vector: list[float],
        sparse_vector: models.SparseVector,
        limit: int = 10,
        session_id: str | None = None,
        hierarchy_level: int | None = None,
        point_ids: list[str] | None = None,
        with_vectors: bool = False,
        since: str | None = None,
        until: str | None = None,
    ):
        """Performs hybrid search using RRF with optional session, hierarchy level, ID, and temporal filtering."""
        query_filter = self._build_filter(session_id, hierarchy_level, point_ids, since, until)

        response = await self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(
                    query=dense_vector,
                    filter=query_filter,
                    limit=limit * 2,
                ),
                models.Prefetch(
                    query=sparse_vector,
                    using="text_sparse",
                    filter=query_filter,
                    limit=limit * 2,
                ),
            ],
            query=models.FusionQuery(
                fusion=models.Fusion.RRF
            ),
            filter=query_filter,
            limit=limit,
            with_vectors=with_vectors,
        )
        return response.points
