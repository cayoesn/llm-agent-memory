from datetime import datetime, UTC
import pytest
from httpx import AsyncClient, ASGITransport
from app.interfaces.http.main import app
from app.domain.entities import MemoryType
from app.infrastructure.storage.postgres.models import Base
from sqlalchemy.ext.asyncio import create_async_engine
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/memory_engine")

@pytest.fixture(scope="module", autouse=True)
async def db_setup():
    # Postgres setup
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Qdrant setup
    from app.interfaces.http.main import qdrant_adapter
    # Force recreate to ensure sparse support
    try:
        await qdrant_adapter.client.delete_collection(qdrant_adapter.collection_name)
    except Exception:
        pass
    await qdrant_adapter.ensure_collection()

    yield
    
    # Postgres cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(autouse=True)
def mock_repo():
    with patch("app.interfaces.http.main.PostgresMemoryRepository") as mock_class:
        mock_instance = MagicMock()
        mock_instance.save = AsyncMock()
        
        mock_entity = MagicMock()
        mock_entity.content = "API integration test content"
        mock_entity.importance_score = 0.8
        mock_entity.metadata.created_at = datetime.now(UTC)
        mock_instance.get_by_ids = AsyncMock(return_value=[mock_entity])
        
        mock_instance.get_by_session = AsyncMock(return_value=[mock_entity])
        mock_class.return_value = mock_instance
        yield mock_instance

@pytest.fixture(autouse=True)
def mock_qdrant():
    with patch("app.interfaces.http.main.qdrant_adapter") as mock:
        mock.upsert = AsyncMock()
        mock_hit = MagicMock()
        mock_hit.payload = {"content": "API integration test content", "created_at": "2026-05-25T11:45:00", "importance_score": 0.8}
        mock_hit.score = 0.95
        mock_hit.id = str(uuid.uuid4())
        mock.search = AsyncMock(return_value=[mock_hit])
        mock.hybrid_search = AsyncMock(return_value=[mock_hit])
        yield mock

@pytest.fixture(autouse=True)
def mock_ollama():
    with patch("app.interfaces.http.main.ollama_client") as mock:
        mock.embeddings = AsyncMock(return_value=[0.1] * 768)
        mock.generate = AsyncMock(return_value="Mocked response")
        yield mock

@pytest.mark.asyncio
async def test_health_live():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}

@pytest.mark.asyncio
async def test_health_ready():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}

@pytest.mark.asyncio
async def test_store_and_search_memory_integration():
    session_id = f"test-session-{uuid.uuid4()}"
    
    # 1. Store Memory
    memory_data = {
        "content": "API integration test content",
        "memory_type": "semantic",
        "session_id": session_id,
        "importance_score": 0.9,
        "extra": {"key": "val"}
    }
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        store_res = await ac.post("/memory/store", json=memory_data)
        assert store_res.status_code == 200
        stored_id = store_res.json()["id"]
        
        # 2. Search Memory
        search_data = {
            "query": "integration test",
            "session_id": session_id,
            "limit": 5
        }
        search_res = await ac.post("/memory/search", json=search_data)
        assert search_res.status_code == 200
        results = search_res.json()
        assert len(results) > 0
        assert results[0]["content"] == "API integration test content"

@pytest.mark.asyncio
async def test_working_memory_api():
    session_id = f"test-session-{uuid.uuid4()}"
    
    # Store working memory
    memory_data = {
        "content": "This is working memory",
        "memory_type": "working",
        "session_id": session_id
    }
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/memory/store", json=memory_data)
        
        # Get working memory
        get_res = await ac.get(f"/memory/working/{session_id}")
        assert get_res.status_code == 200
        results = get_res.json()
        assert "This is working memory" in results
