import pytest
from unittest.mock import AsyncMock, MagicMock
from app.application.context_builder import ContextBuilder

@pytest.mark.asyncio
async def test_context_builder_full():
    retriever = MagicMock()
    retriever.execute = AsyncMock(return_value=[{"content": "Semantic context"}])
    
    cache = MagicMock()
    cache.get_list = AsyncMock(return_value=["Recent message"])
    
    ranker = MagicMock()
    
    builder = ContextBuilder(retriever, cache, ranker)
    
    context = await builder.build(query="test", session_id="session-123")
    
    assert "RECENT CONVERSATION" in context
    assert "Recent message" in context
    assert "RELEVANT KNOWLEDGE" in context
    assert "Semantic context" in context
    
    retriever.execute.assert_called_once()
    cache.get_list.assert_called_once()
