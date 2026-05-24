from typing import List, Dict
from app.application.retrieve_memory import RetrieveMemoryUseCase
from app.infrastructure.storage.redis.cache import RedisCache
from app.domain.services import MemoryRanker
from app.telemetry.logger import logger

class ContextBuilder:
    """The most important component: orchestrates multiple memory types into a final prompt context."""
    
    def __init__(
        self, 
        retriever: RetrieveMemoryUseCase, 
        cache: RedisCache,
        ranker: MemoryRanker
    ):
        self.retriever = retriever
        self.cache = cache
        self.ranker = ranker

    async def build(self, query: str, session_id: str) -> str:
        logger.info("building_context", session_id=session_id)
        
        # 1. Get Working Memory (Hot Context from Redis)
        working_mem = await self.cache.get_list(f"working_mem:{session_id}")
        
        # 2. Retrieve Semantic Memories (Long-term Knowledge)
        semantic_memories = await self.retriever.execute(query, session_id, limit=5)
        
        # 3. Rank Results
        # For simplicity, we just concatenate here, but a real ranker would re-sort
        
        context_parts = []
        
        if working_mem:
            context_parts.append("### RECENT CONVERSATION:\n" + "\n".join(working_mem))
            
        if semantic_memories:
            context_parts.append("### RELEVANT KNOWLEDGE:\n" + "\n".join([m["content"] for m in semantic_memories]))
            
        return "\n\n".join(context_parts)
