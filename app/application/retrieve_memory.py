from opentelemetry import trace

from app.infrastructure.ollama.client import OllamaClient
from app.infrastructure.storage.qdrant.adapter import QdrantAdapter
from app.telemetry.logger import logger

tracer = trace.get_tracer(__name__)


class RetrieveMemoryUseCase:
    """Use case for semantic retrieval of memories."""

    def __init__(self, vector_store: QdrantAdapter, ollama: OllamaClient):
        self.vector_store = vector_store
        self.ollama = ollama

    async def execute(self, query: str, session_id: str, limit: int = 5):
        with tracer.start_as_current_span("retrieve_memory_use_case"):
            logger.info("executing_retrieval", query=query, session_id=session_id)

            # 1. Generate query embedding
            query_vector = await self.ollama.embeddings("nomic-embed-text", query)

            # 2. Search in Qdrant
            results = await self.vector_store.search(
                vector=query_vector, limit=limit, session_id=session_id
            )

            # 3. Format results (simplified for now)
            memories = []
            for hit in results:
                memories.append(
                    {"content": hit.payload["content"], "score": hit.score, "id": hit.id}
                )

            return memories
