import pytest
from unittest.mock import AsyncMock, MagicMock
from app.application.store_memory import StoreMemoryUseCase
from app.schemas.memory import MemoryCreate
from app.domain.entities import MemoryType

@pytest.mark.asyncio
async def test_store_memory_use_case_semantic():
    # Mocks
    repo = MagicMock()
    repo.save = AsyncMock()
    
    vector_store = MagicMock()
    vector_store.upsert = AsyncMock()
    
    ollama = MagicMock()
    ollama.embeddings = AsyncMock(return_value=[0.1, 0.2, 0.3])
    
    cache = MagicMock()
    cache.push_to_list = AsyncMock()
    
    use_case = StoreMemoryUseCase(repo, vector_store, ollama, cache)
    
    cmd = MemoryCreate(
        content="Test semantic content",
        memory_type=MemoryType.SEMANTIC,
        session_id="test-session"
    )
    
    memory = await use_case.execute(cmd)
    
    assert memory.content == "Test semantic content"
    ollama.embeddings.assert_called_once()
    vector_store.upsert.assert_called_once()
    repo.save.assert_called_once()

@pytest.mark.asyncio
async def test_store_memory_use_case_working():
    repo = MagicMock()
    repo.save = AsyncMock()
    vector_store = MagicMock()
    ollama = MagicMock()
    cache = MagicMock()
    cache.push_to_list = AsyncMock()
    
    use_case = StoreMemoryUseCase(repo, vector_store, ollama, cache)
    
    cmd = MemoryCreate(
        content="Test working content",
        memory_type=MemoryType.WORKING,
        session_id="test-session"
    )
    
    memory = await use_case.execute(cmd)
    
    assert memory.content == "Test working content"
    cache.push_to_list.assert_called_once()
    ollama.embeddings.assert_not_called()
    repo.save.assert_called_once()
