import pytest
from unittest.mock import AsyncMock, MagicMock
from app.application.summarize_memories import SummarizationService

@pytest.mark.asyncio
async def test_summarization_service_success():
    ollama = MagicMock()
    ollama.generate = AsyncMock(return_value="Summary paragraph.")
    
    service = SummarizationService(ollama)
    summary = await service.summarize_batch(["Memory 1", "Memory 2"])
    
    assert summary == "Summary paragraph."
    ollama.generate.assert_called_once()
