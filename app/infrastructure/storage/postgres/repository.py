from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.entities import BaseMemory, MemoryType
from app.domain.repositories import IMemoryRepository
from app.infrastructure.storage.postgres.models import MemoryModel

class PostgresMemoryRepository(IMemoryRepository):
    """Implementation of Memory Repository using SQLAlchemy Async."""
    
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, memory: BaseMemory) -> BaseMemory:
        model = MemoryModel(
            id=memory.id,
            content=memory.content,
            memory_type=memory.memory_type,
            session_id=memory.metadata.session_id,
            agent_id=memory.metadata.agent_id,
            importance_score=memory.importance_score,
            metadata_extra=memory.metadata.extra,
            created_at=memory.metadata.created_at.replace(tzinfo=None),
            updated_at=memory.metadata.updated_at.replace(tzinfo=None)
        )
        self.session.add(model)
        await self.session.commit()
        return memory

    async def get_by_id(self, memory_id: UUID) -> Optional[BaseMemory]:
        result = await self.session.execute(select(MemoryModel).where(MemoryModel.id == memory_id))
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._map_to_entity(model)

    async def get_by_session(self, session_id: str, memory_type: Optional[MemoryType] = None) -> List[BaseMemory]:
        stmt = select(MemoryModel).where(MemoryModel.session_id == session_id)
        if memory_type:
            stmt = stmt.where(MemoryModel.memory_type == memory_type)
        
        result = await self.session.execute(stmt)
        return [self._map_to_entity(m) for m in result.scalars().all()]

    def _map_to_entity(self, model: MemoryModel) -> BaseMemory:
        # Internal mapping logic from DB model to Domain entity
        from app.domain.entities import MemoryMetadata
        return BaseMemory(
            id=model.id,
            content=model.content,
            memory_type=model.memory_type,
            importance_score=model.importance_score,
            metadata=MemoryMetadata(
                session_id=model.session_id,
                agent_id=model.agent_id,
                created_at=model.created_at,
                updated_at=model.updated_at,
                extra=model.metadata_extra
            )
        )
