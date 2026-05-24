import pytest
from datetime import datetime, UTC, timedelta
from app.domain.entities import BaseMemory, MemoryType, MemoryMetadata
from app.domain.services import DecayManager

def test_decay_manager_exponential():
    manager = DecayManager(decay_rate=0.5)
    
    # Create a memory created 2 hours ago
    created_at = datetime.now(UTC) - timedelta(hours=2)
    metadata = MemoryMetadata(session_id="test", created_at=created_at)
    memory = BaseMemory(
        content="old memory",
        memory_type=MemoryType.SEMANTIC,
        metadata=metadata,
        importance_score=1.0
    )
    
    manager.apply_decay([memory])
    
    # After 2 hours with decay_rate 0.5:
    # score = 1.0 * exp(-0.5 * 2) = 1.0 * exp(-1) approx 0.367
    assert 0.36 < memory.importance_score < 0.37
