import pytest
from app.infrastructure.storage.redis.cache import RedisCache
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

@pytest.fixture
async def redis_cache():
    cache = RedisCache(url=REDIS_URL)
    yield cache
    # Cleanup
    await cache.client.flushdb()
    await cache.client.aclose()

@pytest.mark.asyncio
async def test_redis_cache_integration(redis_cache: RedisCache):
    key = "test_key"
    value = "test_value"
    
    await redis_cache.set(key, value)
    cached = await redis_cache.get(key)
    assert cached == value
    
    # Test sliding window list
    list_key = "test_list"
    await redis_cache.push_to_list(list_key, "item1", max_size=2)
    await redis_cache.push_to_list(list_key, "item2", max_size=2)
    await redis_cache.push_to_list(list_key, "item3", max_size=2)
    
    items = await redis_cache.get_list(list_key)
    assert len(items) == 2
    assert items[0] == "item3" # Latest item (LPHUSH)
