import uuid
from opentelemetry import trace
from typing import Any

from app.infrastructure.ollama.client import OllamaClient
from app.infrastructure.storage.qdrant.adapter import QdrantAdapter
from app.infrastructure.storage.postgres.repository import PostgresMemoryRepository
from app.application.user_profile_service import UserProfileService
from app.domain.services import MemoryRanker
from app.telemetry.logger import logger

tracer = trace.get_tracer(__name__)


class RetrieveMemoryUseCase:
    """Use case for semantic and hybrid retrieval of memories with ranking, personalization, and MMR."""

    def __init__(
        self,
        vector_store: QdrantAdapter,
        ollama: OllamaClient,
        repository: PostgresMemoryRepository,
        user_profile_service: UserProfileService,
    ):
        self.vector_store = vector_store
        self.ollama = ollama
        self.repository = repository
        self.user_profile_service = user_profile_service
        self.ranker = MemoryRanker()

    async def execute(
        self,
        query: str,
        session_id: str,
        limit: int = 5,
        use_hybrid: bool = False,
        use_mmr: bool = False,
        personalize: bool = False,
        hierarchy_level: int | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> list[dict[str, Any]]:
        with tracer.start_as_current_span("retrieve_memory_use_case"):
            logger.info(
                "executing_retrieval",
                query=query,
                session_id=session_id,
                use_hybrid=use_hybrid,
                use_mmr=use_mmr,
                personalize=personalize,
                hierarchy_level=hierarchy_level,
                since=since,
                until=until,
            )

            # 1. Generate query embedding
            query_vector = await self.ollama.embeddings("nomic-embed-text", query)

            # 2. Apply personalization if requested
            if personalize:
                profile_vec = await self.user_profile_service.get_profile_embedding(session_id)
                # Blend query vector (70%) and user profile (30%)
                blended_vector = []
                for q_val, p_val in zip(query_vector, profile_vec):
                    blended_vector.append(0.7 * q_val + 0.3 * p_val)
                query_vector = blended_vector

            # 3. Retrieve from Vector Store
            with_vectors = use_mmr
            # If MMR is used, fetch double candidate pool to ensure diversity can be selected
            fetch_limit = limit * 2 if use_mmr else limit

            if use_hybrid:
                from app.infrastructure.search.sparse_encoder import SparseEncoder
                sparse_encoder = SparseEncoder()
                sparse_vector = sparse_encoder.encode(query)
                results = await self.vector_store.hybrid_search(
                    dense_vector=query_vector,
                    sparse_vector=sparse_vector,
                    limit=fetch_limit,
                    session_id=session_id,
                    hierarchy_level=hierarchy_level,
                    with_vectors=with_vectors,
                    since=since,
                    until=until,
                )
            else:
                results = await self.vector_store.search(
                    vector=query_vector,
                    limit=fetch_limit,
                    session_id=session_id,
                    hierarchy_level=hierarchy_level,
                    with_vectors=with_vectors,
                    since=since,
                    until=until,
                )

            # 4. Map vector hits to search results and build vectors map for MMR
            semantic_results = []
            vectors_map = {}
            for hit in results:
                hit_id = str(hit.id)
                semantic_results.append({
                    "id": hit_id,
                    "content": hit.payload.get("content", ""),
                    "score": hit.score,
                    "created_at": hit.payload.get("created_at"),
                    "importance_score": hit.payload.get("importance_score"),
                })
                
                if with_vectors and hit.vector is not None:
                    if isinstance(hit.vector, dict):
                        vectors_map[hit_id] = hit.vector.get("", [])
                    elif isinstance(hit.vector, list):
                        vectors_map[hit_id] = hit.vector

            # 5. Fetch Postgres metadata for accurate decay-aware scoring
            memory_ids = [uuid.UUID(h["id"]) for h in semantic_results]
            metadata_memories = []
            if memory_ids:
                metadata_memories = await self.repository.get_by_ids(memory_ids)

            # 6. Apply composite MemoryRanker (semantic + recency + importance)
            ranked_results = self.ranker.rank(semantic_results, metadata_memories)

            # 7. Apply MMR Reranking if requested
            if use_mmr:
                from app.domain.services import MMRReranker
                mmr_reranker = MMRReranker()
                ranked_results = mmr_reranker.rerank(
                    candidates=ranked_results,
                    vectors=vectors_map,
                    limit=limit,
                )
            else:
                ranked_results = ranked_results[:limit]

            return ranked_results
