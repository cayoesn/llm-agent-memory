import pytest
from datetime import datetime, UTC
from unittest.mock import MagicMock, AsyncMock
from app.application.hierarchical_retrieval import HierarchicalRetrievalUseCase
from app.domain.entities import BaseMemory, MemoryType, MemoryMetadata

@pytest.mark.asyncio
async def test_hierarchical_retrieval_flow():
    vector_store = MagicMock()
    ollama = MagicMock()
    repository = MagicMock()
    
    ollama.embeddings = AsyncMock(return_value=[0.1] * 768)
    
    # 1. Level 3 hits
    l3_hit = MagicMock()
    l3_hit.id = "00000000-0000-0000-0000-000000000003"
    l3_hit.score = 0.8
    
    # 2. Get children level 2 nodes
    mock_session = MagicMock()
    repository.session = mock_session
    
    l2_node = MagicMock()
    l2_node.id = "00000000-0000-0000-0000-000000000002"
    
    mock_res_l2 = MagicMock()
    mock_res_l2.scalars.return_value.all.return_value = [l2_node]
    
    # Mock Level 1 children fetch result
    l1_leaf = MagicMock()
    l1_leaf.id = "00000000-0000-0000-0000-000000000001"
    mock_res_l1 = MagicMock()
    mock_res_l1.scalars.return_value.all.return_value = [l1_leaf]
    
    async def mock_execute(stmt):
        # Determine based on condition
        stmt_str = str(stmt)
        if "parent_id IN" in stmt_str or "parent_id" in stmt_str:
            # Check if l2_node is queried (l2_node id in matched_l3_ids)
            # or l1_leaf is queried (parent is l2_node)
            # In our mocked sequence, we yield l2 results then l1 results
            pass
        return mock_res_l2
        
    # Simply use side effect on execute to return different query results
    mock_session.execute = MagicMock(side_effect=AsyncMock(side_effect=[mock_res_l2, mock_res_l1]))
    
    # Mock Level 1 hit search in Qdrant
    l1_hit = MagicMock()
    l1_hit.id = "00000000-0000-0000-0000-000000000001"
    l1_hit.score = 0.9
    l1_hit.payload = {"content": "Leaf content", "created_at": "2026-05-25T11:45:00", "importance_score": 0.5}
    
    l2_hit = MagicMock()
    l2_hit.id = "00000000-0000-0000-0000-000000000002"
    l2_hit.score = 0.7
    
    vector_store.search = MagicMock(side_effect=AsyncMock(side_effect=[[l3_hit], [l2_hit], [l1_hit]]))
    
    # Mock repository get_by_ids and get_by_id
    leaf_entity = MagicMock()
    leaf_entity.id = l1_hit.id
    leaf_entity.parent_id = l2_node.id
    leaf_entity.metadata.created_at = datetime.now(UTC)
    
    repository.get_by_ids = AsyncMock(return_value=[leaf_entity])
    
    parent_node = MagicMock()
    parent_node.content = "Parent Level 2 context summary"
    repository.get_by_id = AsyncMock(return_value=parent_node)
    
    use_case = HierarchicalRetrievalUseCase(vector_store, ollama, repository)
    results = await use_case.execute("test query", "agent-1", "session-1")
    
    assert len(results) == 1
    assert results[0]["content"] == "Leaf content"
    assert results[0]["parent_summary_context"] == "Parent Level 2 context summary"
    
    # Verify vector store called 3 times (Level 3, Level 2, Level 1)
    assert vector_store.search.call_count == 3
