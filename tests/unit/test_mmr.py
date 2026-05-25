import pytest
from app.domain.services import MMRReranker

def test_mmr_reranker_diversity():
    reranker = MMRReranker(lambda_param=0.5)
    
    # 3 candidates. Candidates A and B are very similar. Candidate C is different.
    candidates = [
        {"id": "A", "content": "I love reading sci-fi books", "semantic_score": 0.9},
        {"id": "B", "content": "Reading science fiction novels is my passion", "semantic_score": 0.85},
        {"id": "C", "content": "Cooking delicious pasta is great", "semantic_score": 0.7},
    ]
    
    # Vectors representing candidates
    # A and B have close/identical vectors, C is orthogonal
    vectors = {
        "A": [1.0, 0.0],
        "B": [0.99, 0.05], # highly similar to A
        "C": [0.0, 1.0],   # orthogonal to A and B
    }
    
    # Rerank and request 2 items
    reranked = reranker.rerank(candidates, vectors, limit=2)
    
    assert len(reranked) == 2
    # First item must be A (highest semantic score)
    assert reranked[0]["id"] == "A"
    # Second item should be C instead of B, because B is too redundant with A!
    assert reranked[1]["id"] == "C"
