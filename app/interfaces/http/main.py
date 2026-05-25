import os
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.retrieve_memory import RetrieveMemoryUseCase
from app.application.store_memory import StoreMemoryUseCase
from app.application.user_profile_service import UserProfileService
from app.application.hierarchical_retrieval import HierarchicalRetrievalUseCase
from app.infrastructure.ollama.client import OllamaClient
from app.infrastructure.storage.postgres.repository import PostgresMemoryRepository
from app.infrastructure.storage.postgres.session import get_db
from app.infrastructure.storage.qdrant.adapter import QdrantAdapter
from app.infrastructure.storage.redis.cache import RedisCache
from app.schemas.memory import MemoryCreate, MemoryResponse, SearchRequest, HierarchicalSearchRequest
from app.workers.scheduler import configure_scheduler, start_scheduler

app = FastAPI(title="Agent Memory Engine API")

# Singletons
ollama_client = OllamaClient(base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
qdrant_adapter = QdrantAdapter(host=os.getenv("QDRANT_HOST", "localhost"))
redis_cache = RedisCache()


@app.on_event("startup")
async def startup():
    await qdrant_adapter.ensure_collection()
    # Configure and start background scheduler tasks
    configure_scheduler(ollama_client, redis_cache)
    start_scheduler()


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
async def search_memory(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    repo = PostgresMemoryRepository(db)
    user_profile_service = UserProfileService(repo, ollama_client, redis_cache)
    use_case = RetrieveMemoryUseCase(qdrant_adapter, ollama_client, repo, user_profile_service)
    return await use_case.execute(
        query=req.query,
        session_id=req.session_id,
        limit=req.limit,
        use_hybrid=req.use_hybrid,
        use_mmr=req.use_mmr,
        personalize=req.personalize,
        since=req.since,
        until=req.until,
    )


@app.post("/memory/search/hierarchical")
async def search_memory_hierarchical(req: HierarchicalSearchRequest, db: AsyncSession = Depends(get_db)):
    repo = PostgresMemoryRepository(db)
    use_case = HierarchicalRetrievalUseCase(qdrant_adapter, ollama_client, repo)
    return await use_case.execute(
        query=req.query,
        agent_id=req.agent_id,
        session_id=req.session_id,
        limit=req.limit,
        score_threshold=req.score_threshold,
    )


@app.get("/memory/working/{session_id}")
async def get_working_memory(session_id: str):
    results = await redis_cache.get_list(f"working_mem:{session_id}")
    return results


@app.get("/profile/{session_id}")
async def get_profile(session_id: str, db: AsyncSession = Depends(get_db)):
    repo = PostgresMemoryRepository(db)
    user_profile_service = UserProfileService(repo, ollama_client, redis_cache)
    profile = await user_profile_service.get_or_build_profile(session_id)
    return {"session_id": session_id, "profile": profile}


@app.get("/health/live")
async def liveness():
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness():
    return {"status": "ready"}
