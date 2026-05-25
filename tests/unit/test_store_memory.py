import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.application.store_memory import StoreMemoryUseCase
from app.schemas.memory import MemoryCreate
from app.domain.entities import MemoryType

@pytest.mark.asyncio
async def test_store_memory_use_case_semantic():
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
    
    with patch("app.infrastructure.search.sparse_encoder.SparseEncoder") as mock_encoder_class:
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = MagicMock()
        mock_encoder_class.return_value = mock_encoder
        
        memory = await use_case.execute(cmd)
        
        assert memory.content == "Test semantic content"
        ollama.embeddings.assert_called_once()
        vector_store.upsert.assert_called_once()
        repo.save.assert_called_once()

@pytest.mark.asyncio
async def test_store_memory_use_case_episodic():
    repo = MagicMock()
    repo.save = AsyncMock()
    repo.get_next_sequence_index = AsyncMock(return_value=1)
    
    vector_store = MagicMock()
    vector_store.upsert = AsyncMock()
    
    ollama = MagicMock()
    ollama.embeddings = AsyncMock(return_value=[0.1, 0.2, 0.3])
    
    cache = MagicMock()
    
    use_case = StoreMemoryUseCase(repo, vector_store, ollama, cache)
    
    cmd = MemoryCreate(
        content="Test episodic content",
        memory_type=MemoryType.EPISODIC,
        session_id="test-session"
    )
    
    with patch("app.infrastructure.search.sparse_encoder.SparseEncoder") as mock_encoder_class:
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = MagicMock()
        mock_encoder_class.return_value = mock_encoder
        
        memory = await use_case.execute(cmd)
        
        assert memory.memory_type == MemoryType.EPISODIC
        assert memory.sequence_index == 1
        ollama.embeddings.assert_called_once()
        vector_store.upsert.assert_called_once()
        repo.save.assert_called_once()
        repo.get_next_sequence_index.assert_called_once_with("test-session")

@pytest.mark.asyncio
async def test_store_memory_use_case_reflection():
    repo = MagicMock()
    repo.save = AsyncMock()
    
    vector_store = MagicMock()
    vector_store.upsert = AsyncMock()
    
    ollama = MagicMock()
    ollama.embeddings = AsyncMock(return_value=[0.1, 0.2, 0.3])
    
    cache = MagicMock()
    
    use_case = StoreMemoryUseCase(repo, vector_store, ollama, cache)
    
    cmd = MemoryCreate(
        content="Test reflection content",
        memory_type=MemoryType.REFLECTION,
        session_id="test-session",
        extra={"insight_type": "behavioral_pattern"}
    )
    
    with patch("app.infrastructure.search.sparse_encoder.SparseEncoder") as mock_encoder_class:
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = MagicMock()
        mock_encoder_class.return_value = mock_encoder
        
        memory = await use_case.execute(cmd)
        
        assert memory.memory_type == MemoryType.REFLECTION
        assert memory.insight_type == "behavioral_pattern"
        ollama.embeddings.assert_called_once()
        vector_store.upsert.assert_called_once()
        repo.save.assert_called_once()
