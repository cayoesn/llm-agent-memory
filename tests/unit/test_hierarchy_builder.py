import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from app.application.hierarchy_builder import HierarchyBuilder
from app.domain.entities import MemoryType, BaseMemory
from app.infrastructure.storage.postgres.models import MemoryModel

@pytest.mark.asyncio
async def test_promote_to_level2():
    mock_session = AsyncMock()
    mock_summarizer = MagicMock()
    mock_summarizer.summarize_batch = AsyncMock(return_value="Level 2 Summary")
    mock_vector_store = MagicMock()
    mock_vector_store.upsert = AsyncMock()
    mock_ollama = MagicMock()
    mock_ollama.embeddings = AsyncMock(return_value=[0.1] * 768)

    builder = HierarchyBuilder(mock_session, mock_summarizer, mock_vector_store, mock_ollama)

    # Mock level 1 models
    m1 = MemoryModel(id=uuid4(), content="c1", session_id="s1", hierarchy_level=1, agent_id="a1")
    m2 = MemoryModel(id=uuid4(), content="c2", session_id="s1", hierarchy_level=1, agent_id="a1")
    
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [m1, m2]
    mock_session.execute.return_value = mock_res

    with patch("app.infrastructure.search.sparse_encoder.SparseEncoder") as mock_encoder_class:
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = MagicMock()
        mock_encoder_class.return_value = mock_encoder
        
        level2_memory = await builder.promote_to_level2("s1")
        
        assert level2_memory is not None
        assert level2_memory.content == "Level 2 Summary"
        assert level2_memory.hierarchy_level == 2
        
        mock_summarizer.summarize_batch.assert_called_once()
        mock_vector_store.upsert.assert_called_once()
        mock_session.commit.assert_called_once()
        
        # Verify linking
        assert m1.parent_id == level2_memory.id
        assert m2.parent_id == level2_memory.id

@pytest.mark.asyncio
async def test_promote_to_level3():
    mock_session = AsyncMock()
    mock_summarizer = MagicMock()
    mock_summarizer.summarize_batch = AsyncMock(return_value="Level 3 Global Summary")
    mock_vector_store = MagicMock()
    mock_vector_store.upsert = AsyncMock()
    mock_ollama = MagicMock()
    mock_ollama.embeddings = AsyncMock(return_value=[0.1] * 768)

    builder = HierarchyBuilder(mock_session, mock_summarizer, mock_vector_store, mock_ollama)

    # Mock level 2 models
    m1 = MemoryModel(id=uuid4(), content="s1 summary", agent_id="a1", hierarchy_level=2)
    m2 = MemoryModel(id=uuid4(), content="s2 summary", agent_id="a1", hierarchy_level=2)
    
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [m1, m2]
    mock_session.execute.return_value = mock_res

    with patch("app.infrastructure.search.sparse_encoder.SparseEncoder") as mock_encoder_class:
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = MagicMock()
        mock_encoder_class.return_value = mock_encoder
        
        level3_memory = await builder.promote_to_level3("a1")
        
        assert level3_memory is not None
        assert level3_memory.content == "Level 3 Global Summary"
        assert level3_memory.hierarchy_level == 3
        
        mock_summarizer.summarize_batch.assert_called_once()
        mock_vector_store.upsert.assert_called_once()
        mock_session.commit.assert_called_once()
        
        assert m1.parent_id == level3_memory.id
        assert m2.parent_id == level3_memory.id
