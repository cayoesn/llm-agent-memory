import os
from fastapi import Depends, FastAPI
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.retrieve_memory import RetrieveMemoryUseCase
from app.application.store_memory import StoreMemoryUseCase
from app.application.user_profile_service import UserProfileService
from app.application.hierarchical_retrieval import HierarchicalRetrievalUseCase
from app.infrastructure.ollama.client import OllamaClient
from app.infrastructure.storage.postgres.repository import PostgresMemoryRepository
from app.infrastructure.storage.postgres.session import get_db, engine
from app.infrastructure.storage.postgres.models import Base
from app.infrastructure.storage.qdrant.adapter import QdrantAdapter
from app.infrastructure.storage.redis.cache import RedisCache
from app.schemas.memory import MemoryCreate, MemoryResponse, SearchRequest, HierarchicalSearchRequest
from app.workers.scheduler import (
    configure_scheduler,
    start_scheduler,
    run_reflection_generation,
    run_memory_decay,
    run_hierarchy_level2_promotion,
    run_hierarchy_level3_promotion,
)

app = FastAPI(title="Agent Memory Engine API")

# Singletons
ollama_client = OllamaClient(base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
qdrant_adapter = QdrantAdapter(host=os.getenv("QDRANT_HOST", "localhost"))
redis_cache = RedisCache()


@app.on_event("startup")
async def startup():
    # Ensure Postgres tables exist (useful for local/dev runs)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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


@app.get("/health")
async def health():
    return {
        "live": {"status": "alive"},
        "ready": {"status": "ready"},
    }


@app.get("/metrics")
async def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


# Worker control endpoints (manual triggers for E2E / debugging)
@app.post("/workers/reflect")
async def workers_reflect(run_async: bool = True):
    """Trigger reflection generation job.

    If run_async is true (default), schedule the job in background and return 202.
    If false, run synchronously and return the result status.
    """
    if run_async:
        import asyncio

        asyncio.create_task(run_reflection_generation())
        return {"status": "scheduled"}
    else:
        await run_reflection_generation()
        return {"status": "completed"}


@app.post("/workers/decay")
async def workers_decay(run_async: bool = True):
    if run_async:
        import asyncio

        asyncio.create_task(run_memory_decay())
        return {"status": "scheduled"}
    else:
        await run_memory_decay()
        return {"status": "completed"}


@app.post("/workers/hierarchy/level2")
async def workers_hierarchy_level2(run_async: bool = True):
    if run_async:
        import asyncio

        asyncio.create_task(run_hierarchy_level2_promotion())
        return {"status": "scheduled"}
    else:
        await run_hierarchy_level2_promotion()
        return {"status": "completed"}


@app.post("/workers/hierarchy/level3")
async def workers_hierarchy_level3(run_async: bool = True):
    if run_async:
        import asyncio

        asyncio.create_task(run_hierarchy_level3_promotion())
        return {"status": "scheduled"}
    else:
        await run_hierarchy_level3_promotion()
        return {"status": "completed"}
