import redis.asyncio as redis
import os
from typing import Optional, List

class RedisCache:
    """Async Redis adapter for Working Memory and hot cache."""
    
    def __init__(self, url: Optional[str] = None):
        self.url = url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client = redis.from_url(self.url, decode_responses=True)

    async def set(self, key: str, value: str, expire: int = 3600):
        await self.client.set(key, value, ex=expire)

    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)

    async def delete(self, key: str):
        await self.client.delete(key)

    async def push_to_list(self, key: str, value: str, max_size: int = 10):
        """Pushes to a list and trims to max_size (Working Memory sliding window)."""
        async with self.client.pipeline(transaction=True) as pipe:
            await pipe.lpush(key, value)
            await pipe.ltrim(key, 0, max_size - 1)
            await pipe.execute()

    async def get_list(self, key: str) -> List[str]:
        return await self.client.lrange(key, 0, -1)
