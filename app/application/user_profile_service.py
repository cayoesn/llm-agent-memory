import json
from app.infrastructure.storage.postgres.repository import PostgresMemoryRepository
from app.infrastructure.ollama.client import OllamaClient
from app.infrastructure.storage.redis.cache import RedisCache
from app.domain.entities import MemoryType
from app.telemetry.logger import logger

class UserProfileService:
    """Service to build, cache, and retrieve user profiles for Personalized Retrieval."""

    def __init__(
        self,
        repository: PostgresMemoryRepository,
        ollama: OllamaClient,
        cache: RedisCache,
    ):
        self.repository = repository
        self.ollama = ollama
        self.cache = cache

    async def get_or_build_profile(self, session_id: str) -> str:
        """Retrieves user profile from cache, or builds and caches it if missing."""
        cache_key = f"user_profile:{session_id}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        # Build new profile
        logger.info("user_profile_cache_miss", session_id=session_id)
        profile = await self.build_profile(session_id)
        await self.cache.set(cache_key, profile, expire=3600)  # 1 hour TTL
        return profile

    async def build_profile(self, session_id: str) -> str:
        """Synthesizes a user profile based on semantic and reflection memories."""
        # 1. Fetch semantic and reflection memories
        semantic_memories = await self.repository.get_by_session(session_id, MemoryType.SEMANTIC)
        reflection_memories = await self.repository.get_by_session(session_id, MemoryType.REFLECTION)

        memories = semantic_memories + reflection_memories
        if not memories:
            return "No profile context available yet."

        # Extract contents
        memory_texts = [f"- {m.content}" for m in memories]
        memories_payload = "\n".join(memory_texts)

        prompt = (
            "Analyze the following list of user memories and reflections to construct a "
            "comprehensive but extremely concise (max 3 sentences) profile describing the user's "
            "preferences, habits, goals, and key context. Keep it objective.\n\n"
            f"User Memories:\n{memories_payload}\n\n"
            "Profile summary:"
        )

        try:
            profile = await self.ollama.generate("llama3", prompt)
            return profile.strip()
        except Exception as e:
            logger.error("error_building_user_profile", session_id=session_id, error=str(e))
            return "User with general interests."

    async def get_profile_embedding(self, session_id: str) -> list[float]:
        """Returns the dense embedding vector for the user's profile."""
        profile_text = await self.get_or_build_profile(session_id)
        try:
            return await self.ollama.embeddings("nomic-embed-text", profile_text)
        except Exception as e:
            logger.error("error_embedding_user_profile", session_id=session_id, error=str(e))
            return [0.0] * 768
