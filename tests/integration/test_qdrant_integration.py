import pytest
from app.infrastructure.storage.qdrant.adapter import QdrantAdapter
import os
import uuid

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")

@pytest.fixture
async def qdrant_adapter():
    adapter = QdrantAdapter(host=QDRANT_HOST)
    # Use a test collection
    adapter.collection_name = "test_collection"
    await adapter.ensure_collection(vector_size=3)
    yield adapter
    # Cleanup
    await adapter.client.delete_collection(adapter.collection_name)
    await adapter.client.close()

@pytest.mark.asyncio
async def test_qdrant_adapter_integration(qdrant_adapter: QdrantAdapter):
    memory_id = str(uuid.uuid4())
    vector = [0.1, 0.2, 0.3]
    payload = {"session_id": "session-test", "content": "integration test"}
    
    await qdrant_adapter.upsert(memory_id, vector, payload)
    
    # Search
    results = await qdrant_adapter.search(vector, limit=1, session_id="session-test")
    assert len(results) == 1
    assert results[0].id == memory_id
    assert results[0].payload["content"] == "integration test"
