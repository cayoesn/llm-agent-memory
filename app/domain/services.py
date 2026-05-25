import math
from datetime import UTC, datetime
from typing import Any

from app.domain.entities import BaseMemory


class DecayManager:
    """Implements Time Decay for memory relevance scoring.

    Uses exponential decay so that old memories gradually lose relevance
    unless they have been explicitly reinforced (importance boosted):

        score(t) = initial_score * exp(-decay_rate * Δt_hours)

    A higher decay_rate means memories fade faster.
    """

    def __init__(self, decay_rate: float = 0.1):
        self.decay_rate = decay_rate

    def apply_decay(self, memories: list[BaseMemory]) -> list[BaseMemory]:
        """Applies exponential decay in-place to each memory's importance_score.

        Args:
            memories: list of BaseMemory entities (mutated in place).

        Returns:
            The same list with updated importance_scores.
        """
        now = datetime.now(UTC)
        for memory in memories:
            created_at = memory.metadata.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            delta = now - created_at
            hours = delta.total_seconds() / 3600
            decay_factor = math.exp(-self.decay_rate * hours)
            memory.importance_score = round(memory.importance_score * decay_factor, 6)

        return memories

    def compute_recency_score(
        self, created_at: datetime, decay_rate: float | None = None
    ) -> float:
        """Returns a normalized recency score in [0, 1] for a single memory.

        The score is 1.0 for a memory created right now and decays exponentially
        as the memory ages. This is used by MemoryRanker to weight results.

        Args:
            created_at: when the memory was originally created.
            decay_rate: override for the instance's default decay_rate.

        Returns:
            Float in [0.0, 1.0] — higher means more recent.
        """
        rate = decay_rate if decay_rate is not None else self.decay_rate
        now = datetime.now(UTC)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        delta = now - created_at
        hours = max(delta.total_seconds() / 3600, 0.0)
        return math.exp(-rate * hours)


class MemoryRanker:
    """Ranks memories by a weighted composite of three signals:

    1. Semantic similarity  — how closely the retrieved memory matches the query
                              (score from Qdrant cosine similarity, range [0, 1]).
    2. Recency              — how fresh the memory is, computed via exponential decay
                              (same formula as DecayManager, range [0, 1]).
    3. Importance           — the stored importance_score at retrieval time ([0, 1]).

    Final score:
        final_score = (semantic_sim * w_sem) + (recency * w_rec) + (importance * w_imp)

    Default weights: 0.5 / 0.3 / 0.2 — semantic similarity is the dominant signal,
    but recency and importance prevent old or low-quality memories from surfacing.
    """

    def __init__(
        self,
        semantic_weight: float = 0.5,
        recency_weight: float = 0.3,
        importance_weight: float = 0.2,
        decay_rate: float = 0.1,
    ):
        self.semantic_weight = semantic_weight
        self.recency_weight = recency_weight
        self.importance_weight = importance_weight
        self.decay_manager = DecayManager(decay_rate=decay_rate)

    def rank(
        self,
        semantic_results: list[dict[str, Any]],
        metadata_memories: list[BaseMemory],
    ) -> list[dict[str, Any]]:
        """Combines Qdrant semantic scores with Postgres metadata into a final rank.

        Two sources of metadata are used (in priority order):
        1. `metadata_memories` — BaseMemory objects fetched from Postgres, keyed by ID.
           Preferred because they reflect the latest importance_score after decay.
        2. Qdrant payload fields (`created_at`, `importance_score`) — used as fallback
           when the Postgres metadata is not available (e.g., in lightweight retrieval).

        Args:
            semantic_results: list of dicts with at least {"id", "content", "score"}.
                              May also include "created_at" and "importance_score"
                              from the Qdrant payload.
            metadata_memories: list of BaseMemory from Postgres (can be empty).

        Returns:
            Sorted list of dicts with keys:
            {"id", "content", "semantic_score", "recency_score", "importance_score", "final_score"}
        """
        # Build O(1) lookup from memory_id -> BaseMemory
        metadata_map: dict[str, BaseMemory] = {str(m.id): m for m in metadata_memories}

        ranked = []
        for hit in semantic_results:
            memory_id = str(hit.get("id", ""))
            semantic_score = float(hit.get("score", 0.0))

            meta = metadata_map.get(memory_id)
            if meta:
                # Primary source: Postgres metadata (most up-to-date after decay)
                recency_score = self.decay_manager.compute_recency_score(meta.metadata.created_at)
                importance = meta.importance_score
            else:
                # Fallback: use data stored in the Qdrant payload
                created_at_str = hit.get("created_at")
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str)
                        recency_score = self.decay_manager.compute_recency_score(created_at)
                    except (ValueError, TypeError):
                        recency_score = 1.0
                else:
                    recency_score = 1.0  # Assume fresh when unknown
                
                importance_val = hit.get("importance_score")
                importance = float(importance_val) if importance_val is not None else 0.5

            final_score = (
                (semantic_score * self.semantic_weight)
                + (recency_score * self.recency_weight)
                + (importance * self.importance_weight)
            )

            ranked.append(
                {
                    "id": memory_id,
                    "content": hit.get("content", ""),
                    "semantic_score": round(semantic_score, 6),
                    "recency_score": round(recency_score, 6),
                    "importance_score": round(importance, 6),
                    "final_score": round(final_score, 6),
                }
            )

        return sorted(ranked, key=lambda x: x["final_score"], reverse=True)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Computes the cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


class MMRReranker:
    """Implements Maximal Marginal Relevance (MMR) for reranking search results to ensure diversity."""

    def __init__(self, lambda_param: float = 0.5):
        self.lambda_param = lambda_param

    def rerank(
        self,
        candidates: list[dict[str, Any]],
        vectors: dict[str, list[float]],
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Reranks the candidates using Maximal Marginal Relevance.

        Args:
            candidates: list of dicts from MemoryRanker (sorted by final_score desc).
            vectors: dict mapping candidate memory IDs (as strings) to their dense embedding vectors.
            limit: maximum number of items to return in the final selection.

        Returns:
            Sublist of candidates reranked and filtered to limit.
        """
        if not candidates or limit <= 0:
            return []

        # Filter out candidates that do not have vectors, or keep them with low priority
        # Let's perform MMR on the candidates
        selected: list[dict[str, Any]] = []
        unselected = list(candidates)

        # Helper to compute similarity
        def sim(doc_id: str, other_vec: list[float]) -> float:
            vec = vectors.get(doc_id)
            if vec is None:
                return 0.0
            return cosine_similarity(vec, other_vec)

        # First item is always the top ranked candidate
        first = unselected.pop(0)
        selected.append(first)

        while len(selected) < limit and unselected:
            best_score = -float("inf")
            best_cand = None

            for cand in unselected:
                cand_id = cand["id"]
                sim_to_query = cand.get("semantic_score", 0.0)

                # max sim to already selected
                max_sim_to_selected = 0.0
                cand_vec = vectors.get(cand_id)
                if cand_vec and selected:
                    max_sim_to_selected = max(
                        sim(cand_id, vectors.get(sel["id"], []))
                        for sel in selected
                        if sel["id"] in vectors
                    )

                mmr_score = (
                    self.lambda_param * sim_to_query
                    - (1.0 - self.lambda_param) * max_sim_to_selected
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_cand = cand

            if best_cand:
                unselected.remove(best_cand)
                selected.append(best_cand)
            else:
                break

        return selected

