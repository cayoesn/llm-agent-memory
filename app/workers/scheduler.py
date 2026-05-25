from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from app.infrastructure.storage.postgres.session import async_session_factory
from app.infrastructure.storage.postgres.repository import PostgresMemoryRepository
from app.infrastructure.storage.postgres.models import MemoryModel
from app.domain.services import DecayManager
from app.domain.entities import MemoryType, ReflectionMemory, BaseMemory, MemoryMetadata
from app.application.summarize_memories import SummarizationService
from app.application.hierarchy_builder import HierarchyBuilder
from app.infrastructure.storage.qdrant.adapter import QdrantAdapter
from app.infrastructure.ollama.client import OllamaClient
from app.infrastructure.storage.redis.cache import RedisCache
from app.telemetry.logger import logger
import os

scheduler = AsyncIOScheduler()

# Global clients
_ollama_client: OllamaClient = None
_redis_cache: RedisCache = None

def configure_scheduler(ollama_client: OllamaClient, redis_cache: RedisCache) -> None:
    global _ollama_client, _redis_cache
    _ollama_client = ollama_client
    _redis_cache = redis_cache

async def run_memory_decay() -> None:
    """Periodic task to apply decay to memory importance scores."""
    logger.info("scheduler_running_decay")
    
    async with async_session_factory() as session:
        repo = PostgresMemoryRepository(session)
        memories = await repo.get_all(limit=1000)
        if not memories:
            logger.info("scheduler_decay_no_memories")
            return

        decay_manager = DecayManager(decay_rate=0.1)
        decayed_memories = decay_manager.apply_decay(memories)

        for memory in decayed_memories:
            await repo.update_score(memory.id, memory.importance_score)

        logger.info("scheduler_decay_completed", count=len(decayed_memories))


async def run_reflection_generation() -> None:
    """Periodic task to analyze recent memories and generate insights."""
    logger.info("scheduler_running_reflection")
    if _ollama_client is None:
        logger.warning("scheduler_reflection_skipped_no_ollama")
        return

    async with async_session_factory() as session:
        repo = PostgresMemoryRepository(session)
        recent_episodic = await repo.get_recent_by_type(
            memory_type=MemoryType.EPISODIC,
            since_hours=4.0,
            limit=100,
        )
        if not recent_episodic:
            logger.info("scheduler_reflection_no_recent_episodic")
            return

        grouped: dict[str, list[BaseMemory]] = {}
        for mem in recent_episodic:
            grouped.setdefault(mem.metadata.session_id, []).append(mem)

        for session_id, mems in grouped.items():
            contents = "\n".join([f"- {m.content}" for m in mems])
            
            prompt = (
                "Review the following recent episodic logs of an agent's interaction in this session. "
                "Synthesize a high-level reflection memory containing key insights, lessons learned, or "
                "important user facts discovered. Keep the reflection extremely brief, objective, and dense.\n\n"
                f"Logs:\n{contents}\n\n"
                "Key reflection insight:"
            )

            try:
                reflection_content = await _ollama_client.generate("llama3", prompt)
                reflection_content = reflection_content.strip()

                source_memory_ids = [m.id for m in mems]
                reflection = ReflectionMemory(
                    content=reflection_content,
                    source_memory_ids=source_memory_ids,
                    importance_score=0.8,
                    insight_type="behavioral_pattern",
                    metadata=MemoryMetadata(
                        session_id=session_id,
                        agent_id=mems[0].metadata.agent_id,
                    )
                )

                await repo.save(reflection)
                logger.info("scheduler_reflection_generated", session_id=session_id, source_count=len(source_memory_ids))
            except Exception as e:
                logger.error("scheduler_reflection_failed", session_id=session_id, error=str(e))


async def run_hierarchy_level2_promotion() -> None:
    """Promotes session leaves to level 2 summary nodes hourly/daily."""
    logger.info("scheduler_running_level2_promotion")
    if _ollama_client is None:
        return

    async with async_session_factory() as session:
        # Get unique session IDs in Postgres
        stmt = select(MemoryModel.session_id).distinct()
        res = await session.execute(stmt)
        sessions = res.scalars().all()

        summarizer = SummarizationService(_ollama_client)
        vector_store = QdrantAdapter(host=os.getenv("QDRANT_HOST", "localhost"))
        builder = HierarchyBuilder(session, summarizer, vector_store, _ollama_client)

        for session_id in sessions:
            try:
                await builder.promote_to_level2(session_id)
            except Exception as e:
                logger.error("scheduler_level2_promotion_failed", session_id=session_id, error=str(e))


async def run_hierarchy_level3_promotion() -> None:
    """Promotes level 2 nodes to level 3 root nodes daily."""
    logger.info("scheduler_running_level3_promotion")
    if _ollama_client is None:
        return

    async with async_session_factory() as session:
        # Get unique agent IDs in Postgres
        stmt = select(MemoryModel.agent_id).distinct().where(MemoryModel.agent_id.is_not(None))
        res = await session.execute(stmt)
        agents = res.scalars().all()

        summarizer = SummarizationService(_ollama_client)
        vector_store = QdrantAdapter(host=os.getenv("QDRANT_HOST", "localhost"))
        builder = HierarchyBuilder(session, summarizer, vector_store, _ollama_client)

        for agent_id in agents:
            try:
                await builder.promote_to_level3(agent_id)
            except Exception as e:
                logger.error("scheduler_level3_promotion_failed", agent_id=agent_id, error=str(e))


def start_scheduler() -> None:
    scheduler.add_job(run_memory_decay, "interval", hours=1)
    scheduler.add_job(run_reflection_generation, "interval", hours=4)
    scheduler.add_job(run_hierarchy_level2_promotion, "interval", hours=12)
    scheduler.add_job(run_hierarchy_level3_promotion, "interval", hours=24)
    scheduler.start()
    logger.info("scheduler_started")
