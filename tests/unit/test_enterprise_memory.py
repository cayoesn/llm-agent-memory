import time
import pytest
from app.domain.ebbinghaus_forgetting import EbbinghausForgettingEngine, MemoryItem, ebbinghaus_engine


def test_ebbinghaus_retention_decay():
    now = time.time()
    item = MemoryItem(
        id="mem_1",
        content="Usuário prefere café sem açúcar.",
        strength=1.0,
        last_accessed_timestamp=now - 7200,  # 2 horas atrás
        access_count=1,
    )

    retention = ebbinghaus_engine.calculate_retention(item, current_time=now)
    assert 0.0 < retention < 1.0


def test_memory_access_reinforcement():
    item = MemoryItem(id="mem_2", content="Usuário mora em São Paulo.", strength=1.0)
    updated_item = ebbinghaus_engine.access_memory(item)

    assert updated_item.access_count == 2
    assert updated_item.strength == 1.25
