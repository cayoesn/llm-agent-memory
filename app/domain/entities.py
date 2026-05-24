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


class SemanticMemory(BaseMemory):
    """Domain Entity for Long-term Semantic Memory."""

    memory_type: MemoryType = MemoryType.SEMANTIC
    embedding_id: str | None = None


class EpisodicMemory(BaseMemory):
    """Domain Entity for Sequential Event Memory."""

    memory_type: MemoryType = MemoryType.EPISODIC
    event_time: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReflectionMemory(BaseMemory):
    """Domain Entity for Derived Insights."""

    memory_type: MemoryType = MemoryType.REFLECTION
    insight_type: str  # e.g., "user_preference", "behavioral_pattern"
