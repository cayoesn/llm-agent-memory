import os

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.retrieve_memory import RetrieveMemoryUseCase
from app.application.store_memory import StoreMemoryUseCase
from app.infrastructure.ollama.client import OllamaClient
from app.infrastructure.storage.postgres.repository import PostgresMemoryRepository
from app.infrastructure.storage.postgres.session import get_db
from app.infrastructure.storage.qdrant.adapter import QdrantAdapter
from app.infrastructure.storage.redis.cache import RedisCache
from app.schemas.memory import MemoryCreate, MemoryResponse, SearchRequest

app = FastAPI(title="Agent Memory Engine API")

# Singletons (could use a proper DI container, but keep it simple for now)
ollama_client = OllamaClient(base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
qdrant_adapter = QdrantAdapter(host=os.getenv("QDRANT_HOST", "localhost"))
redis_cache = RedisCache()


@app.on_event("startup")
async def startup():
    await qdrant_adapter.ensure_collection()


@app.post("/memory/store", response_model=MemoryResponse)
async def store_memory(cmd: MemoryCreate, db: AsyncSession = Depends(get_db)):
    repo = PostgresMemoryRepository(db)
    use_case = StoreMemoryUseCase(repo, qdrant_adapter, ollama_client, redis_cache)
    memory = await use_case.execute(cmd)
    return MemoryResponse(
        id=memory.id,
        content=memory.content,
        memory_type=memory.memory_type,
        session_id=memory.metadata.session_id,
        importance_score=memory.importance_score,
        created_at=memory.metadata.created_at,
    )


@app.post("/memory/search")
async def search_memory(req: SearchRequest):
    use_case = RetrieveMemoryUseCase(qdrant_adapter, ollama_client)
    return await use_case.execute(req.query, req.session_id, req.limit)


@app.get("/health/live")
async def liveness():
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness():
    # Basic check: could expand to check db/redis/qdrant
    return {"status": "ready"}
