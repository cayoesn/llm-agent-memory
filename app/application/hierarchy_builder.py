from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.storage.postgres.models import MemoryModel
from app.infrastructure.storage.postgres.repository import PostgresMemoryRepository
from app.application.summarize_memories import SummarizationService
from app.domain.entities import BaseMemory, MemoryMetadata, MemoryType
from app.infrastructure.storage.qdrant.adapter import QdrantAdapter
from app.infrastructure.ollama.client import OllamaClient
from app.telemetry.logger import logger

class HierarchyBuilder:
    """Service to build and maintain the hierarchical memory tree (Level 1 -> 2 -> 3)."""

    def __init__(
        self,
        session: AsyncSession,
        summarizer: SummarizationService,
        vector_store: QdrantAdapter,
        ollama: OllamaClient,
    ):
        self.session = session
        self.repo = PostgresMemoryRepository(session)
        self.summarizer = summarizer
        self.vector_store = vector_store
        self.ollama = ollama

    async def promote_to_level2(self, session_id: str) -> BaseMemory | None:
        """Fetches level 1 memories without parents in a session, summarizes them,
        creates a level 2 node, and links them.
        """
        # 1. Fetch level 1 memories for this session without a parent
        stmt = (
            select(MemoryModel)
            .where(MemoryModel.session_id == session_id)
            .where(MemoryModel.hierarchy_level == 1)
            .where(MemoryModel.parent_id.is_(None))
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        if len(models) < 2:
            # Not enough memories to summarize/promote
            return None

        # 2. Summarize content
        contents = [m.content for m in models]
        summary_text = await self.summarizer.summarize_batch(contents)

        # 3. Create level 2 node
        level2_memory = BaseMemory(
            content=summary_text,
            memory_type=MemoryType.SEMANTIC,
            importance_score=0.8,
            hierarchy_level=2,
            parent_id=None,
            metadata=MemoryMetadata(
                session_id=session_id,
                agent_id=models[0].agent_id,
            )
        )

        # 4. Save level 2 memory in Postgres
        await self.repo.save(level2_memory)
        
        # Vectorize and index in Qdrant
        vector = await self.ollama.embeddings("nomic-embed-text", summary_text)
        from app.infrastructure.search.sparse_encoder import SparseEncoder
        sparse_encoder = SparseEncoder()
        sparse_vector = sparse_encoder.encode(summary_text)

        await self.vector_store.upsert(
            memory_id=str(level2_memory.id),
            vector=vector,
            sparse_vector=sparse_vector,
            payload={
                "session_id": session_id,
                "content": summary_text,
                "created_at": level2_memory.metadata.created_at.isoformat(),
                "importance_score": 0.8,
                "hierarchy_level": 2,
            }
        )

        # 5. Link level 1 memories to this level 2 node
        for model in models:
            model.parent_id = level2_memory.id
        
        logger.info("promoted_memories_to_level2", session_id=session_id, count=len(models), parent_id=str(level2_memory.id))
        return level2_memory

    async def promote_to_level3(self, agent_id: str) -> BaseMemory | None:
        """Fetches level 2 memories without parents for an agent across sessions,
        summarizes them into a level 3 root node, and links them.
        """
        # 1. Fetch level 2 memories for this agent without a parent
        stmt = (
            select(MemoryModel)
            .where(MemoryModel.agent_id == agent_id)
            .where(MemoryModel.hierarchy_level == 2)
            .where(MemoryModel.parent_id.is_(None))
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        if len(models) < 2:
            return None

        # 2. Summarize
        contents = [m.content for m in models]
        summary_text = await self.summarizer.summarize_batch(contents)

        # 3. Create level 3 root memory
        level3_memory = BaseMemory(
            content=summary_text,
            memory_type=MemoryType.SEMANTIC,
            importance_score=0.9,
            hierarchy_level=3,
            parent_id=None,
            metadata=MemoryMetadata(
                session_id="global_agent_profile",
                agent_id=agent_id,
            )
        )

        # 4. Save and index
        await self.repo.save(level3_memory)

        vector = await self.ollama.embeddings("nomic-embed-text", summary_text)
        from app.infrastructure.search.sparse_encoder import SparseEncoder
        sparse_encoder = SparseEncoder()
        sparse_vector = sparse_encoder.encode(summary_text)

        await self.vector_store.upsert(
            memory_id=str(level3_memory.id),
            vector=vector,
            sparse_vector=sparse_vector,
            payload={
                "session_id": "global_agent_profile",
                "content": summary_text,
                "created_at": level3_memory.metadata.created_at.isoformat(),
                "importance_score": 0.9,
                "hierarchy_level": 3,
            }
        )

        # 5. Link level 2 memories to this level 3 node
        for model in models:
            model.parent_id = level3_memory.id
        
        logger.info("promoted_memories_to_level3", agent_id=agent_id, count=len(models), parent_id=str(level3_memory.id))
        return level3_memory
