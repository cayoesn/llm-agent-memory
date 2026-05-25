from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MemoryType(StrEnum):
    WORKING = "working"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    REFLECTION = "reflection"


class MemoryMetadata(BaseModel):
    """Metadata for memory entities."""

    session_id: str
    agent_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    extra: dict[str, Any] = Field(default_factory=dict)


class BaseMemory(BaseModel):
    """Base Domain Entity for all memory types."""

    id: UUID = Field(default_factory=uuid4)
    content: str
    memory_type: MemoryType
    metadata: MemoryMetadata
    importance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    hierarchy_level: int = Field(default=1, ge=1, le=3)
    parent_id: UUID | None = Field(default=None)


class SemanticMemory(BaseMemory):
    """Domain Entity for Long-term Semantic Memory."""

    memory_type: MemoryType = MemoryType.SEMANTIC
    embedding_id: str | None = None


class EpisodicMemory(BaseMemory):
    """Domain Entity for Sequential Event Memory.

    Tracks events in chronological order within a session using sequence_index.
    Each event is stamped with event_time for temporal ordering.
    """

    memory_type: MemoryType = MemoryType.EPISODIC
    event_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sequence_index: int | None = None  # Ordinal position within a session (1, 2, 3, ...)


class ReflectionMemory(BaseMemory):
    """Domain Entity for Derived Insights.

    Reflects on a batch of source memories to generate a higher-level insight
    (e.g., user_preference, behavioral_pattern). source_memory_ids provides
    provenance — a traceable link back to the raw memories used to produce this insight.
    """

    memory_type: MemoryType = MemoryType.REFLECTION
    insight_type: str  # e.g., "user_preference", "behavioral_pattern", "auto_reflection"
    source_memory_ids: list[UUID] = Field(default_factory=list)
