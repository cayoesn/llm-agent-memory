import uuid
from opentelemetry import trace
from typing import Any
from sqlalchemy import select
from app.infrastructure.storage.postgres.models import MemoryModel
from app.infrastructure.storage.postgres.repository import PostgresMemoryRepository
from app.infrastructure.storage.qdrant.adapter import QdrantAdapter
from app.infrastructure.ollama.client import OllamaClient
from app.domain.services import MemoryRanker
from app.telemetry.logger import logger

tracer = trace.get_tracer(__name__)

class HierarchicalRetrievalUseCase:
    """Use case for Top-Down Hierarchical Memory Retrieval (Level 3 -> Level 2 -> Level 1)."""

    def __init__(
        self,
        vector_store: QdrantAdapter,
        ollama: OllamaClient,
        repository: PostgresMemoryRepository,
    ):
        self.vector_store = vector_store
        self.ollama = ollama
        self.repository = repository
        self.ranker = MemoryRanker()

    async def execute(
        self,
        query: str,
        agent_id: str,
        session_id: str,
        limit: int = 5,
        score_threshold: float = 0.25,
    ) -> list[dict[str, Any]]:
        with tracer.start_as_current_span("hierarchical_retrieval_use_case"):
            logger.info("executing_hierarchical_retrieval", query=query, session_id=session_id, agent_id=agent_id)

            # 1. Generate query embedding
            query_vector = await self.ollama.embeddings("nomic-embed-text", query)

            # --- STEP 1: Search at Level 3 (Global Agent/User Root Node) ---
            l3_hits = await self.vector_store.search(
                vector=query_vector,
                limit=3,
                hierarchy_level=3,
            )
            
            matched_l3_ids = [uuid.UUID(hit.id) for hit in l3_hits if hit.score >= score_threshold]
            logger.info("hierarchical_retrieval_level3_hits", count=len(l3_hits), matched=len(matched_l3_ids))

            l2_ids = []
            if matched_l3_ids:
                # Get Level 2 child nodes of these Level 3 roots from Postgres
                stmt = select(MemoryModel).where(MemoryModel.parent_id.in_(matched_l3_ids))
                res = await self.repository.session.execute(stmt)
                l2_nodes = res.scalars().all()
                l2_ids = [str(n.id) for n in l2_nodes]

            # --- STEP 2: Search at Level 2 (Session Node) ---
            if l2_ids:
                # Search within the selected subtree
                l2_hits = await self.vector_store.search(
                    vector=query_vector,
                    limit=5,
                    hierarchy_level=2,
                    point_ids=l2_ids,
                )
            else:
                # Fallback: search Level 2 directly in the session
                l2_hits = await self.vector_store.search(
                    vector=query_vector,
                    limit=5,
                    hierarchy_level=2,
                    session_id=session_id,
                )

            matched_l2_ids = [uuid.UUID(hit.id) for hit in l2_hits if hit.score >= score_threshold]
            logger.info("hierarchical_retrieval_level2_hits", count=len(l2_hits), matched=len(matched_l2_ids))

            l1_ids = []
            if matched_l2_ids:
                # Get Level 1 child leaf memories of these Level 2 nodes from Postgres
                stmt = select(MemoryModel).where(MemoryModel.parent_id.in_(matched_l2_ids))
                res = await self.repository.session.execute(stmt)
                l1_nodes = res.scalars().all()
                l1_ids = [str(n.id) for n in l1_nodes]

            # --- STEP 3: Search at Level 1 (Raw/Episodic Leaves) ---
            if l1_ids:
                l1_hits = await self.vector_store.search(
                    vector=query_vector,
                    limit=limit * 2,
                    hierarchy_level=1,
                    point_ids=l1_ids,
                )
            else:
                # Fallback: search Level 1 directly in the session
                l1_hits = await self.vector_store.search(
                    vector=query_vector,
                    limit=limit * 2,
                    hierarchy_level=1,
                    session_id=session_id,
                )

            # 4. Score and Rank Level 1 candidates using Postgres metadata
            semantic_results = []
            for hit in l1_hits:
                semantic_results.append({
                    "id": str(hit.id),
                    "content": hit.payload.get("content", ""),
                    "score": hit.score,
                    "created_at": hit.payload.get("created_at"),
                    "importance_score": hit.payload.get("importance_score"),
                })

            memory_ids = [uuid.UUID(h["id"]) for h in semantic_results]
            metadata_memories = []
            if memory_ids:
                metadata_memories = await self.repository.get_by_ids(memory_ids)

            ranked_leaves = self.ranker.rank(semantic_results, metadata_memories)

            # Enrich leaves with parent node info (Level 2/3 summary context) for the LLM
            enriched_results = []
            for leaf in ranked_leaves[:limit]:
                # Find leaf's parent ID from Postgres metadata
                leaf_entity = next((m for m in metadata_memories if str(m.id) == leaf["id"]), None)
                parent_content = None
                if leaf_entity and leaf_entity.parent_id:
                    parent_node = await self.repository.get_by_id(leaf_entity.parent_id)
                    if parent_node:
                        parent_content = parent_node.content

                leaf["parent_summary_context"] = parent_content
                enriched_results.append(leaf)

            return enriched_results
