import pytest
from unittest.mock import AsyncMock, MagicMock
from app.application.retrieve_memory import RetrieveMemoryUseCase

@pytest.mark.asyncio
async def test_retrieve_memory_use_case():
    vector_store = MagicMock()
    # Mock return value of search
    mock_hit = MagicMock()
    mock_hit.payload = {"content": "Found content"}
    mock_hit.score = 0.9
    mock_hit.id = "test-id"
    vector_store.search = AsyncMock(return_value=[mock_hit])
    
    ollama = MagicMock()
    ollama.embeddings = AsyncMock(return_value=[0.1] * 768)
    
    use_case = RetrieveMemoryUseCase(vector_store, ollama)
    
    results = await use_case.execute(query="test query", session_id="session-1")
    
    assert len(results) == 1
    assert results[0]["content"] == "Found content"
    assert results[0]["score"] == 0.9
    ollama.embeddings.assert_called_once()
    vector_store.search.assert_called_once()
