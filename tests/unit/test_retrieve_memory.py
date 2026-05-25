import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.application.retrieve_memory import RetrieveMemoryUseCase

@pytest.mark.asyncio
async def test_retrieve_memory_use_case_temporal():
    vector_store = MagicMock()
    mock_hit = MagicMock()
    mock_hit.payload = {
        "content": "Temporal content",
        "created_at": "2023-06-01T10:00:00",
        "importance_score": 0.5
    }
    mock_hit.score = 0.85
    mock_hit.id = "00000000-0000-0000-0000-000000000001"
    vector_store.search = AsyncMock(return_value=[mock_hit])
    
    ollama = MagicMock()
    ollama.embeddings = AsyncMock(return_value=[0.1] * 768)
    
    repository = MagicMock()
    repository.get_by_ids = AsyncMock(return_value=[])
    
    user_profile = MagicMock()
    
    use_case = RetrieveMemoryUseCase(vector_store, ollama, repository, user_profile)
    
    results = await use_case.execute(
        query="test query",
        session_id="session-1",
        since="2023-01-01T00:00:00",
        until="2023-12-31T23:59:59"
    )
    
    assert len(results) == 1
    vector_store.search.assert_called_once()
    args, kwargs = vector_store.search.call_args
    assert kwargs["since"] == "2023-01-01T00:00:00"
    assert kwargs["until"] == "2023-12-31T23:59:59"

@pytest.mark.asyncio
async def test_retrieve_memory_use_case_hybrid():
    vector_store = MagicMock()
    mock_hit = MagicMock()
    mock_hit.payload = {
        "content": "Hybrid content",
        "created_at": "2023-06-01T10:00:00",
        "importance_score": 0.5
    }
    mock_hit.score = 0.88
    mock_hit.id = "00000000-0000-0000-0000-000000000001"
    vector_store.hybrid_search = AsyncMock(return_value=[mock_hit])
    
    ollama = MagicMock()
    ollama.embeddings = AsyncMock(return_value=[0.1] * 768)
    
    repository = MagicMock()
    repository.get_by_ids = AsyncMock(return_value=[])
    
    user_profile = MagicMock()
    
    use_case = RetrieveMemoryUseCase(vector_store, ollama, repository, user_profile)
    
    with patch("app.infrastructure.search.sparse_encoder.SparseEncoder") as mock_encoder_class:
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = MagicMock()
        mock_encoder_class.return_value = mock_encoder
        
        results = await use_case.execute(
            query="test query",
            session_id="session-1",
            use_hybrid=True
        )
        
        assert len(results) == 1
        vector_store.hybrid_search.assert_called_once()
        mock_encoder.encode.assert_called_once_with("test query")
