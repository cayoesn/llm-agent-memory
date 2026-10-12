import time
import pytest
from app.domain.ebbinghaus_forgetting import (
    EbbinghausForgettingEngine,
    MemoryItem,
    ebbinghaus_engine,
)
from app.domain.services import MMRReranker


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


def test_ebbinghaus_batch_consolidation():
    now = time.time()
    engine = EbbinghausForgettingEngine(cold_threshold=0.20, consolidation_threshold=0.50)

    # 1 item muito recente (ativo)
    item_active = MemoryItem(
        id="mem_fresh",
        content="Gosta de TypeScript",
        strength=2.0,
        last_accessed_timestamp=now - 60,
        access_count=5,
    )
    # 1 item em consolidação (meia-vida intermediária)
    item_consolidating = MemoryItem(
        id="mem_mid",
        content="Leu artigo sobre LLMOps",
        strength=1.0,
        last_accessed_timestamp=now - (3600 * 1.5),
        access_count=1,
    )
    # 1 item antigo esquecido (frio / arquivar)
    item_cold = MemoryItem(
        id="mem_cold",
        content="Senha temporária antiga",
        strength=0.5,
        last_accessed_timestamp=now - (3600 * 24),
        access_count=1,
    )

    archived_callbacks = []
    result = engine.consolidate_batch(
        [item_active, item_consolidating, item_cold],
        current_time=now,
        archive_callback=lambda m: archived_callbacks.append(m.id),
    )

    assert result.archived_count == 1
    assert result.archived_memories[0].id == "mem_cold"
    assert "mem_cold" in archived_callbacks
    assert result.active_count == 2
    assert result.consolidating_count == 1


def test_vectorized_mmr_multi_item_diversity():
    reranker = MMRReranker(lambda_param=0.6)

    candidates = [
        {"id": "doc_1", "content": "Machine learning em Python", "semantic_score": 0.95},
        {"id": "doc_2", "content": "Deep learning e redes neurais em Python", "semantic_score": 0.92},
        {"id": "doc_3", "content": "Culinária italiana e vinhos", "semantic_score": 0.70},
        {"id": "doc_4", "content": "Receitas de massas caseiras", "semantic_score": 0.68},
    ]

    # doc_1 e doc_2 possuem vetores quase colineares
    # doc_3 e doc_4 são ortogonais a doc_1/doc_2 mas colineares entre si
    vectors = {
        "doc_1": [1.0, 0.05],
        "doc_2": [0.98, 0.08],
        "doc_3": [0.05, 1.0],
        "doc_4": [0.08, 0.99],
    }

    selected = reranker.rerank(candidates, vectors, limit=2)
    assert len(selected) == 2
    assert selected[0]["id"] == "doc_1"
    # MMR deve diversificar e escolher doc_3 em vez do redundante doc_2
    assert selected[1]["id"] == "doc_3"
