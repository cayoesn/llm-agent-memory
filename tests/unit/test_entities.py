import pytest
from app.domain.entities import BaseMemory, MemoryType, MemoryMetadata

def test_memory_entity_creation():
    metadata = MemoryMetadata(session_id="test-session")
    memory = BaseMemory(
        content="Hello world",
        memory_type=MemoryType.WORKING,
        metadata=metadata
    )
    assert memory.content == "Hello world"
    assert memory.memory_type == MemoryType.WORKING
    assert memory.metadata.session_id == "test-session"
    assert memory.importance_score == 0.0

def test_memory_importance_validation():
    metadata = MemoryMetadata(session_id="test")
    # Pydantic validation for ge=0.0 and le=1.0
    with pytest.raises(Exception):
        BaseMemory(content="x", memory_type=MemoryType.WORKING, metadata=metadata, importance_score=1.5)
