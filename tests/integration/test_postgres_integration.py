import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.infrastructure.storage.postgres.models import Base, MemoryModel
from app.infrastructure.storage.postgres.repository import PostgresMemoryRepository
from app.domain.entities import BaseMemory, MemoryType, MemoryMetadata
import os

# We use the DATABASE_URL from environment for integration tests
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/memory_engine")

@pytest.fixture
async def db_session():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.mark.asyncio
async def test_postgres_repository_integration(db_session: AsyncSession):
    repo = PostgresMemoryRepository(db_session)
    
    metadata = MemoryMetadata(session_id="session-int-1")
    memory = BaseMemory(
        content="Integration test content",
        memory_type=MemoryType.SEMANTIC,
        metadata=metadata
    )
    
    # Save
    await repo.save(memory)
    
    # Get by session
    results = await repo.get_by_session("session-int-1")
    assert len(results) == 1
    assert results[0].content == "Integration test content"
    
    # Get by ID
    found = await repo.get_by_id(memory.id)
    assert found is not None
    assert found.id == memory.id

    # Get by IDs
    found_list = await repo.get_by_ids([memory.id])
    assert len(found_list) == 1
    assert found_list[0].id == memory.id

    # Get All
    all_mems = await repo.get_all()
    assert len(all_mems) >= 1

    # Update Score
    await repo.update_score(memory.id, 0.123)
    updated = await repo.get_by_id(memory.id)
    assert abs(updated.importance_score - 0.123) < 0.001

    # Get Recent by Type
    recent = await repo.get_recent_by_type(MemoryType.SEMANTIC, since_hours=1.0)
    assert len(recent) >= 1

    # Hierarchical checks
    child_metadata = MemoryMetadata(session_id="session-int-1")
    child_memory = BaseMemory(
        content="Child content",
        memory_type=MemoryType.SEMANTIC,
        metadata=child_metadata,
        parent_id=memory.id,
        hierarchy_level=1
    )
    await repo.save(child_memory)
    
    children = await repo.get_children(memory.id)
    assert len(children) == 1
    assert children[0].id == child_memory.id

    by_level = await repo.get_by_hierarchy_level(1)
    assert len(by_level) >= 1
