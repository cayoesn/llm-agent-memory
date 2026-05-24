import os

import redis.asyncio as redis


class RedisCache:
    """Async Redis adapter for Working Memory and hot cache."""

    def __init__(self, url: str | None = None) -> None:
        self.url = url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client: redis.Redis[str] = redis.from_url(self.url, decode_responses=True)

    async def set(self, key: str, value: str, expire: int = 3600) -> None:
        await self.client.set(key, value, ex=expire)

    async def get(self, key: str) -> str | None:
        return await self.client.get(key)

    async def delete(self, key: str) -> None:
        await self.client.delete(key)

    async def push_to_list(self, key: str, value: str, max_size: int = 10) -> None:
        """Pushes to a list and trims to max_size (Working Memory sliding window)."""
        async with self.client.pipeline(transaction=True) as pipe:
            await pipe.lpush(key, value)
            await pipe.ltrim(key, 0, max_size - 1)
            await pipe.execute()

    async def get_list(self, key: str) -> list[str]:
        return await self.client.lrange(key, 0, -1)
