import pytest
from datetime import datetime, UTC, timedelta
from app.domain.entities import BaseMemory, MemoryType, MemoryMetadata
from app.domain.services import MemoryRanker

def test_ranker_composite_score_with_postgres_metadata():
    ranker = MemoryRanker(semantic_weight=0.5, recency_weight=0.3, importance_weight=0.2, decay_rate=0.1)
    
    # 1. Semantic hits from Qdrant
    semantic_results = [
        {"id": "00000000-0000-0000-0000-000000000001", "content": "Memory A", "score": 0.8},
        {"id": "00000000-0000-0000-0000-000000000002", "content": "Memory B", "score": 0.9},
    ]
    
    # 2. Latest Postgres metadata (A is older, B is fresh)
    created_at_a = datetime.now(UTC) - timedelta(hours=10)
    created_at_b = datetime.now(UTC)
    
    meta_a = BaseMemory(
        id="00000000-0000-0000-0000-000000000001",
        content="Memory A",
        memory_type=MemoryType.SEMANTIC,
        importance_score=0.9,
        metadata=MemoryMetadata(session_id="test", created_at=created_at_a)
    )
    
    meta_b = BaseMemory(
        id="00000000-0000-0000-0000-000000000002",
        content="Memory B",
        memory_type=MemoryType.SEMANTIC,
        importance_score=0.4,
        metadata=MemoryMetadata(session_id="test", created_at=created_at_b)
    )
    
    ranked = ranker.rank(semantic_results, [meta_a, meta_b])
    
    assert len(ranked) == 2
    # B should rank higher than A because of higher semantic similarity and recency
    assert ranked[0]["id"] == "00000000-0000-0000-0000-000000000002"
    assert ranked[0]["recency_score"] == 1.0
    assert ranked[0]["importance_score"] == 0.4
    
    # Verify score calculation for B: 0.9 * 0.5 + 1.0 * 0.3 + 0.4 * 0.2 = 0.45 + 0.30 + 0.08 = 0.83
    assert abs(ranked[0]["final_score"] - 0.83) < 0.001

def test_ranker_composite_score_fallback_to_qdrant_payload():
    ranker = MemoryRanker(semantic_weight=0.5, recency_weight=0.3, importance_weight=0.2, decay_rate=0.1)
    
    created_at_str = (datetime.now(UTC) - timedelta(hours=5)).isoformat()
    semantic_results = [
        {
            "id": "00000000-0000-0000-0000-000000000003",
            "content": "Fallback Memory",
            "score": 0.7,
            "created_at": created_at_str,
            "importance_score": 0.6
        }
    ]
    
    ranked = ranker.rank(semantic_results, [])
    assert len(ranked) == 1
    assert ranked[0]["id"] == "00000000-0000-0000-0000-000000000003"
    assert ranked[0]["importance_score"] == 0.6
    assert 0.0 < ranked[0]["recency_score"] < 1.0
