from app.infrastructure.ollama.client import OllamaClient
from app.infrastructure.storage.postgres.repository import PostgresMemoryRepository
from app.infrastructure.storage.qdrant.adapter import QdrantAdapter
from app.infrastructure.storage.redis.cache import RedisCache
from app.domain.entities import BaseMemory, MemoryMetadata, MemoryType
from app.schemas.memory import MemoryCreate
from app.telemetry.logger import logger
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class StoreMemoryUseCase:
    """Use case for storing memory with metadata and vectorization."""
    
    def __init__(
        self, 
        repository: PostgresMemoryRepository, 
        vector_store: QdrantAdapter, 
        ollama: OllamaClient,
        cache: RedisCache
    ):
        self.repository = repository
        self.vector_store = vector_store
        self.ollama = ollama
        self.cache = cache

    async def execute(self, cmd: MemoryCreate):
        with tracer.start_as_current_span("store_memory_use_case") as span:
            logger.info("executing_store_memory", session_id=cmd.session_id, type=cmd.memory_type)
            
            # 1. Create Domain Entity
            memory = BaseMemory(
                content=cmd.content,
                memory_type=cmd.memory_type,
                importance_score=cmd.importance_score,
                metadata=MemoryMetadata(
                    session_id=cmd.session_id,
                    agent_id=cmd.agent_id,
                    extra=cmd.extra
                )
            )

            # 2. Vectorize if semantic
            if cmd.memory_type == MemoryType.SEMANTIC:
                vector = await self.ollama.embeddings("nomic-embed-text", cmd.content)
                await self.vector_store.upsert(
                    memory_id=str(memory.id),
                    vector=vector,
                    payload={"session_id": cmd.session_id, "content": cmd.content}
                )

            # 3. Store Metadata in Postgres
            await self.repository.save(memory)

            # 4. Update Working Memory list in Redis if applicable
            if cmd.memory_type == MemoryType.WORKING:
                await self.cache.push_to_list(f"working_mem:{cmd.session_id}", cmd.content)

            return memory
