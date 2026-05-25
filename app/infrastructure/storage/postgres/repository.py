from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import (
    BaseMemory,
    EpisodicMemory,
    MemoryMetadata,
    MemoryType,
    ReflectionMemory,
    SemanticMemory,
)
from app.domain.repositories import IMemoryRepository
from app.infrastructure.storage.postgres.models import MemoryModel, Base
from app.infrastructure.storage.postgres.session import engine
from sqlalchemy.exc import ProgrammingError


class PostgresMemoryRepository(IMemoryRepository):
    """Implementation of Memory Repository using SQLAlchemy Async.

    Provides:
    - save / get_by_id / get_by_session (core CRUD)
    - get_recent_by_type  — used by the reflection scheduler
    - get_all             — used by the decay scheduler
    - update_score        — persists the post-decay importance_score
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, memory: BaseMemory) -> BaseMemory:
        # Extract type-specific fields
        sequence_index = getattr(memory, "sequence_index", None)
        source_memory_ids = None
        if hasattr(memory, "source_memory_ids") and memory.source_memory_ids:
            source_memory_ids = [str(uid) for uid in memory.source_memory_ids]

        model = MemoryModel(
            id=memory.id,
            content=memory.content,
            memory_type=memory.memory_type,
            session_id=memory.metadata.session_id,
            agent_id=memory.metadata.agent_id,
            importance_score=memory.importance_score,
            metadata_extra=memory.metadata.extra,
            created_at=memory.metadata.created_at.replace(tzinfo=None),
            updated_at=memory.metadata.updated_at.replace(tzinfo=None),
            sequence_index=sequence_index,
            source_memory_ids=source_memory_ids,
            hierarchy_level=memory.hierarchy_level,
            parent_id=memory.parent_id,
        )
        try:
            self.session.add(model)
            await self.session.commit()
            return memory
        except ProgrammingError as e:
            # Handle case where table doesn't exist yet (race on startup or missing migrations)
            msg = str(e).lower()
            if "relation \"memories\" does not exist" in msg or "undefinedtableerror" in msg:
                # Attempt to create tables and retry once
                await self.session.rollback()
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                # Retry insert
                self.session.add(model)
                await self.session.commit()
                return memory
            # Re-raise for other programming errors
            raise

    async def get_by_id(self, memory_id: UUID) -> BaseMemory | None:
        result = await self.session.execute(select(MemoryModel).where(MemoryModel.id == memory_id))
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._map_to_entity(model)

    async def get_by_ids(self, memory_ids: list[UUID]) -> list[BaseMemory]:
        if not memory_ids:
            return []
        stmt = select(MemoryModel).where(MemoryModel.id.in_(memory_ids))
        result = await self.session.execute(stmt)
        return [self._map_to_entity(m) for m in result.scalars().all()]

    async def get_by_session(
        self, session_id: str, memory_type: MemoryType | None = None
    ) -> list[BaseMemory]:
        stmt = select(MemoryModel).where(MemoryModel.session_id == session_id)
        if memory_type:
            stmt = stmt.where(MemoryModel.memory_type == memory_type)

        result = await self.session.execute(stmt)
        return [self._map_to_entity(m) for m in result.scalars().all()]

    async def get_recent_by_type(
        self,
        memory_type: MemoryType,
        since_hours: float = 4.0,
        session_id: str | None = None,
        limit: int = 100,
    ) -> list[BaseMemory]:
        """Fetches memories of a given type created within the last N hours.

        Used by the reflection scheduler to find episodic memories to summarize.

        Args:
            memory_type: filter by this MemoryType.
            since_hours: only include memories newer than this many hours ago.
            session_id: optional extra filter to scope to a specific session.
            limit: maximum number of results.
        """
        cutoff = (datetime.now(UTC) - timedelta(hours=since_hours)).replace(tzinfo=None)
        stmt = (
            select(MemoryModel)
            .where(MemoryModel.memory_type == memory_type)
            .where(MemoryModel.created_at >= cutoff)
            .order_by(MemoryModel.created_at.asc())
            .limit(limit)
        )
        if session_id:
            stmt = stmt.where(MemoryModel.session_id == session_id)

        result = await self.session.execute(stmt)
        return [self._map_to_entity(m) for m in result.scalars().all()]

    async def get_all(self, limit: int = 1000) -> list[BaseMemory]:
        """Fetches all memories ordered by most recent first.

        Used by the decay scheduler to batch-apply importance_score decay.

        Args:
            limit: cap on number of memories processed in one run.
        """
        stmt = select(MemoryModel).order_by(MemoryModel.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return [self._map_to_entity(m) for m in result.scalars().all()]

    async def update_score(self, memory_id: UUID, new_score: float) -> None:
        """Persists an updated importance_score for a specific memory.

        Called after DecayManager.apply_decay() to write the decayed value back
        to PostgreSQL.

        Args:
            memory_id: UUID of the memory to update.
            new_score: the new computed importance score.
        """
        stmt = (
            update(MemoryModel)
            .where(MemoryModel.id == memory_id)
            .values(importance_score=new_score, updated_at=datetime.now(UTC).replace(tzinfo=None))
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_next_sequence_index(self, session_id: str) -> int:
        """Calculates the next sequence index for a new episodic memory in a session."""
        from sqlalchemy import func
        stmt = select(func.max(MemoryModel.sequence_index)).where(MemoryModel.session_id == session_id)
        result = await self.session.execute(stmt)
        max_idx = result.scalar()
        return (max_idx or 0) + 1

    def _map_to_entity(self, model: MemoryModel) -> BaseMemory:
        """Maps a SQLAlchemy MemoryModel row to a BaseMemory domain entity subclass."""
        # Handle naive datetime from DB (Postgres stores without timezone)
        created_at = model.created_at
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        updated_at = model.updated_at
        if updated_at and updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)

        metadata = MemoryMetadata(
            session_id=model.session_id,
            agent_id=model.agent_id,
            created_at=created_at,
            updated_at=updated_at,
            extra=model.metadata_extra or {},
        )

        common_params = {
            "id": model.id,
            "content": model.content,
            "importance_score": model.importance_score,
            "hierarchy_level": model.hierarchy_level,
            "parent_id": model.parent_id,
            "metadata": metadata,
        }

        if model.memory_type == MemoryType.SEMANTIC:
            return SemanticMemory(**common_params, embedding_id=model.vector_id)
        elif model.memory_type == MemoryType.EPISODIC:
            return EpisodicMemory(
                **common_params,
                event_time=created_at,  # Using created_at as event_time
                sequence_index=model.sequence_index,
            )
        elif model.memory_type == MemoryType.REFLECTION:
            source_ids = []
            if model.source_memory_ids:
                source_ids = [UUID(uid) for uid in model.source_memory_ids]
            return ReflectionMemory(
                **common_params,
                insight_type=model.metadata_extra.get("insight_type", "general"),
                source_memory_ids=source_ids,
            )
        else:
            return BaseMemory(memory_type=model.memory_type, **common_params)

    async def get_by_hierarchy_level(
        self, level: int, agent_id: str | None = None
    ) -> list[BaseMemory]:
        """Fetches all memories at a specific hierarchy level."""
        stmt = select(MemoryModel).where(MemoryModel.hierarchy_level == level)
        if agent_id:
            stmt = stmt.where(MemoryModel.agent_id == agent_id)
        result = await self.session.execute(stmt)
        return [self._map_to_entity(m) for m in result.scalars().all()]

    async def get_children(self, parent_id: UUID) -> list[BaseMemory]:
        """Fetches all children memories for a given parent memory ID."""
        stmt = select(MemoryModel).where(MemoryModel.parent_id == parent_id)
        result = await self.session.execute(stmt)
        return [self._map_to_entity(m) for m in result.scalars().all()]

