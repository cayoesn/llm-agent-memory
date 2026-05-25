import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from qdrant_client.http import models
from app.infrastructure.search.sparse_encoder import SparseEncoder
from app.application.retrieve_memory import RetrieveMemoryUseCase

def test_sparse_encoder_mocked():
    mock_emb = MagicMock()
    mock_emb.indices = [10, 20]
    mock_emb.values = [0.5, 0.8]
    
    with patch("app.infrastructure.search.sparse_encoder.SparseTextEmbedding") as mock_class:
        mock_instance = MagicMock()
        mock_instance.embed.return_value = [mock_emb]
        mock_class.return_value = mock_instance
        
        encoder = SparseEncoder()
        encoder._model = mock_instance
        
        sparse_vec = encoder.encode("hello world")
        
        assert isinstance(sparse_vec, models.SparseVector)
        assert sparse_vec.indices == [10, 20]
        assert sparse_vec.values == [0.5, 0.8]

@pytest.mark.asyncio
async def test_retrieve_memory_use_case_hybrid():
    vector_store = MagicMock()
    ollama = MagicMock()
    repository = MagicMock()
    user_profile = MagicMock()
    
    ollama.embeddings = AsyncMock(return_value=[0.1] * 768)
    
    hit = MagicMock()
    hit.id = "00000000-0000-0000-0000-000000000001"
    hit.score = 0.95
    hit.payload = {"content": "Hybrid result content", "created_at": "2026-05-25T11:45:00", "importance_score": 0.8}
    hit.vector = None
    vector_store.hybrid_search = AsyncMock(return_value=[hit])
    vector_store.search = AsyncMock()
    
    meta = MagicMock()
    meta.id = hit.id
    meta.importance_score = 0.8
    meta.metadata.created_at = datetime.now(UTC)
    repository.get_by_ids = AsyncMock(return_value=[meta])
    
    use_case = RetrieveMemoryUseCase(vector_store, ollama, repository, user_profile)
    
    with patch("app.infrastructure.search.sparse_encoder.SparseEncoder") as mock_encoder_class:
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = MagicMock(indices=[1], values=[1.0])
        mock_encoder_class.return_value = mock_encoder
        
        results = await use_case.execute("hybrid query", "session-123", use_hybrid=True)
        
        assert len(results) == 1
        assert results[0]["content"] == "Hybrid result content"
        vector_store.hybrid_search.assert_called_once()
        vector_store.search.assert_not_called()
