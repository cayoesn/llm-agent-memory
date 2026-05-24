import math
from datetime import datetime, UTC
from typing import List
from app.domain.entities import BaseMemory

class DecayManager:
    """Implements Time Decay for memory relevance scoring."""
    
    def __init__(self, decay_rate: float = 0.1):
        self.decay_rate = decay_rate

    def apply_decay(self, memories: List[BaseMemory]) -> List[BaseMemory]:
        """
        Applies exponential decay: score = initial_score * exp(-decay_rate * time_delta_hours)
        """
        now = datetime.now(UTC)
        for memory in memories:
            delta = now - memory.metadata.created_at
            hours = delta.total_seconds() / 3600
            
            # Simple exponential decay formula
            decay_factor = math.exp(-self.decay_rate * hours)
            memory.importance_score *= decay_factor
            
        return memories

class MemoryRanker:
    """Ranks memories based on Semantic Similarity, Recency, and Importance."""
    
    def __init__(self, semantic_weight: float = 0.5, recency_weight: float = 0.3, importance_weight: float = 0.2):
        self.semantic_weight = semantic_weight
        self.recency_weight = recency_weight
        self.importance_weight = importance_weight

    def rank(self, semantic_results: List[dict], metadata_memories: List[BaseMemory]) -> List[dict]:
        """
        Combines scores from multiple sources into a final rank.
        score = (sim * w1) + (recency * w2) + (importance * w3)
        """
        # This is a simplified placeholder for the ranking logic
        # In a real system, we'd cross-reference Qdrant IDs with Postgres metadata
        ranked = []
        for hit in semantic_results:
            # For now, just use the semantic score
            ranked.append({
                "content": hit["content"],
                "final_score": hit["score"] * self.semantic_weight
            })
            
        return sorted(ranked, key=lambda x: x["final_score"], reverse=True)
