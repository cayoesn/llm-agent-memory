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
