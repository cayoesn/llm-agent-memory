from opentelemetry import trace

from app.domain.entities import BaseMemory, EpisodicMemory, MemoryMetadata, MemoryType, ReflectionMemory, SemanticMemory
from app.infrastructure.ollama.client import OllamaClient
from app.infrastructure.storage.postgres.repository import PostgresMemoryRepository
from app.infrastructure.storage.qdrant.adapter import QdrantAdapter
from app.infrastructure.storage.redis.cache import RedisCache
from app.schemas.memory import MemoryCreate
from app.telemetry.logger import logger

tracer = trace.get_tracer(__name__)


class StoreMemoryUseCase:
    """Use case for storing memory with metadata and vectorization."""

    def __init__(
        self,
        repository: PostgresMemoryRepository,
        vector_store: QdrantAdapter,
        ollama: OllamaClient,
        cache: RedisCache,
    ):
        self.repository = repository
        self.vector_store = vector_store
        self.ollama = ollama
        self.cache = cache

    async def execute(self, cmd: MemoryCreate):
        with tracer.start_as_current_span("store_memory_use_case"):
            logger.info("executing_store_memory", session_id=cmd.session_id, type=cmd.memory_type)

            # 1. Create Domain Entity based on type
            metadata = MemoryMetadata(
                session_id=cmd.session_id, agent_id=cmd.agent_id, extra=cmd.extra
            )
            
            if cmd.memory_type == MemoryType.EPISODIC:
                next_idx = await self.repository.get_next_sequence_index(cmd.session_id)
                memory = EpisodicMemory(
                    content=cmd.content,
                    importance_score=cmd.importance_score if cmd.importance_score is not None else 0.5,
                    sequence_index=next_idx,
                    metadata=metadata,
                )
            elif cmd.memory_type == MemoryType.SEMANTIC:
                memory = SemanticMemory(
                    content=cmd.content,
                    importance_score=cmd.importance_score if cmd.importance_score is not None else 0.7,
                    metadata=metadata,
                )
            elif cmd.memory_type == MemoryType.REFLECTION:
                memory = ReflectionMemory(
                    content=cmd.content,
                    importance_score=cmd.importance_score if cmd.importance_score is not None else 0.8,
                    insight_type=cmd.extra.get("insight_type", "general"),
                    metadata=metadata,
                )
            else:
                memory = BaseMemory(
                    content=cmd.content,
                    memory_type=cmd.memory_type,
                    importance_score=cmd.importance_score or 0.0,
                    metadata=metadata,
                )

            # 2. Vectorize if not working memory (Semantic, Episodic, and Reflection should be searchable)
            if cmd.memory_type != MemoryType.WORKING:
                vector = await self.ollama.embeddings("nomic-embed-text", cmd.content)
                from app.infrastructure.search.sparse_encoder import SparseEncoder
                sparse_encoder = SparseEncoder()
                sparse_vector = sparse_encoder.encode(cmd.content)
                await self.vector_store.upsert(
                    memory_id=str(memory.id),
                    vector=vector,
                    sparse_vector=sparse_vector,
                    payload={
                        "session_id": cmd.session_id,
                        "content": cmd.content,
                        "created_at": memory.metadata.created_at.isoformat(),
                        "importance_score": float(memory.importance_score),
                        "hierarchy_level": int(memory.hierarchy_level),
                        "memory_type": str(cmd.memory_type),
                    },
                )

            # 3. Store Metadata in Postgres
            await self.repository.save(memory)

            # 4. Update Working Memory list in Redis if applicable
            if cmd.memory_type == MemoryType.WORKING:
                await self.cache.push_to_list(f"working_mem:{cmd.session_id}", cmd.content)

            return memory
