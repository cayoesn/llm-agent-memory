import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC, timedelta
from app.workers.scheduler import run_memory_decay, run_reflection_generation, configure_scheduler
from app.domain.entities import MemoryType, BaseMemory, MemoryMetadata, EpisodicMemory

@pytest.mark.asyncio
async def test_run_memory_decay():
    # Mock repository and session
    mock_repo = MagicMock()
    mock_memory = BaseMemory(
        id="00000000-0000-0000-0000-000000000001",
        content="test",
        memory_type=MemoryType.SEMANTIC,
        importance_score=1.0,
        metadata=MemoryMetadata(session_id="s1", created_at=datetime.now(UTC) - timedelta(hours=1))
    )
    mock_repo.get_all = AsyncMock(return_value=[mock_memory])
    mock_repo.update_score = AsyncMock()

    with patch("app.workers.scheduler.async_session_factory") as mock_session_factory:
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        with patch("app.workers.scheduler.PostgresMemoryRepository", return_value=mock_repo):
            await run_memory_decay()
            
            mock_repo.get_all.assert_called_once()
            mock_repo.update_score.assert_called_once()
            # Score should be decayed (less than 1.0)
            args, _ = mock_repo.update_score.call_args
            assert args[1] < 1.0

@pytest.mark.asyncio
async def test_run_reflection_generation():
    mock_ollama = MagicMock()
    mock_ollama.generate = AsyncMock(return_value="Reflected insight")
    configure_scheduler(mock_ollama, MagicMock())

    mock_repo = MagicMock()
    mock_episodic = EpisodicMemory(
        id="00000000-0000-0000-0000-000000000001",
        content="I love coffee",
        memory_type=MemoryType.EPISODIC,
        metadata=MemoryMetadata(session_id="s1", agent_id="a1")
    )
    mock_repo.get_recent_by_type = AsyncMock(return_value=[mock_episodic])
    mock_repo.save = AsyncMock()

    with patch("app.workers.scheduler.async_session_factory") as mock_session_factory:
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        with patch("app.workers.scheduler.PostgresMemoryRepository", return_value=mock_repo):
            await run_reflection_generation()
            
            mock_repo.get_recent_by_type.assert_called_once()
            mock_ollama.generate.assert_called_once()
            mock_repo.save.assert_called_once()
            
            # Check if reflection memory was saved
            saved_memory = mock_repo.save.call_args[0][0]
            assert saved_memory.memory_type == MemoryType.REFLECTION
            assert saved_memory.content == "Reflected insight"
            assert saved_memory.source_memory_ids == [mock_episodic.id]
