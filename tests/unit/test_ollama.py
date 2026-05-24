import pytest
from unittest.mock import AsyncMock, MagicMock
from app.infrastructure.ollama.client import OllamaClient

@pytest.mark.asyncio
async def test_ollama_client_generate(monkeypatch):
    # Mock httpx.AsyncClient
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "Hello!"}
    mock_response.raise_for_status = MagicMock()
    
    # We need to mock the client instance inside OllamaClient
    client = OllamaClient()
    client.client.post = AsyncMock(return_value=mock_response)
    
    result = await client.generate("llama3", "hi")
    
    assert result == "Hello!"
    client.client.post.assert_called_once()

@pytest.mark.asyncio
async def test_ollama_client_embeddings():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embedding": [0.1, 0.2]}
    mock_response.raise_for_status = MagicMock()
    
    client = OllamaClient()
    client.client.post = AsyncMock(return_value=mock_response)
    
    result = await client.embeddings("nomic-embed-text", "test")
    
    assert result == [0.1, 0.2]
