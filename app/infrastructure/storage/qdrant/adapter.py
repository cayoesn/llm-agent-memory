import asyncio
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from app.telemetry.logger import logger
from typing import List, Optional

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
                    size=vector_size,
                    distance=models.Distance.COSINE
                )
            )

    async def upsert(self, memory_id: str, vector: List[float], payload: dict):
        """Upserts a vector with payload metadata."""
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=memory_id,
                    vector=vector,
                    payload=payload
                )
            ]
        )

    async def search(self, vector: List[float], limit: int = 10, session_id: Optional[str] = None):
        """Performs semantic search with optional session filtering."""
        query_filter = None
        if session_id:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="session_id",
                        match=models.MatchValue(value=session_id)
                    )
                ]
            )

        response = await self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=query_filter,
            limit=limit
        )
        return response.points
