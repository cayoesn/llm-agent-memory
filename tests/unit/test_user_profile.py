import pytest
from unittest.mock import MagicMock, AsyncMock
from app.application.user_profile_service import UserProfileService
from app.domain.entities import BaseMemory, MemoryType, MemoryMetadata

@pytest.mark.asyncio
async def test_user_profile_service_cache_hit():
    repo = MagicMock()
    ollama = MagicMock()
    cache = MagicMock()
    
    cache.get = AsyncMock(return_value="Cached profile summary.")
    
    service = UserProfileService(repo, ollama, cache)
    profile = await service.get_or_build_profile("session-1")
    
    assert profile == "Cached profile summary."
    cache.get.assert_called_once_with("user_profile:session-1")
    ollama.generate.assert_not_called()

@pytest.mark.asyncio
async def test_user_profile_service_cache_miss_and_build():
    repo = MagicMock()
    ollama = MagicMock()
    cache = MagicMock()
    
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    ollama.generate = MagicMock(side_effect=AsyncMock(return_value="Built user profile summary."))
    
    m1 = BaseMemory(
        content="User loves deep learning",
        memory_type=MemoryType.SEMANTIC,
        metadata=MemoryMetadata(session_id="session-1")
    )
    
    async def mock_get_by_session(session_id, memory_type):
        if memory_type == MemoryType.SEMANTIC:
            return [m1]
        return []
        
    repo.get_by_session = MagicMock(side_effect=mock_get_by_session)
    
    service = UserProfileService(repo, ollama, cache)
    profile = await service.get_or_build_profile("session-1")
    
    assert profile == "Built user profile summary."
    cache.get.assert_called_once_with("user_profile:session-1")
    cache.set.assert_called_once_with("user_profile:session-1", "Built user profile summary.", expire=3600)
