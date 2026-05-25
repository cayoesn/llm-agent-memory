import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, ForeignKey
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.entities import MemoryType


class Base(DeclarativeBase):
    pass


class MemoryModel(Base):
    """SQLAlchemy model for Memory metadata.

    Columns:
    - id, content, memory_type, session_id, agent_id: core identity fields.
    - importance_score: relevance weight, modified by DecayManager over time.
    - created_at, updated_at: temporal audit trail.
    - metadata_extra: free-form JSON for extra payload per memory type.
    - vector_id: optional cross-reference to the Qdrant point ID.
    - sequence_index: for EpisodicMemory — ordinal position within a session.
    - source_memory_ids: for ReflectionMemory — JSON list of UUIDs of source memories.
    - hierarchy_level: level in memory hierarchy (1=folha, 2=nó, 3=raiz).
    - parent_id: reference to a parent memory in the tree.
    """

    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content: Mapped[str] = mapped_column(String, nullable=False)
    memory_type: Mapped[MemoryType] = mapped_column(SQLEnum(MemoryType), nullable=False)
    session_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    agent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    importance_score: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    # Specific fields for different types stored in JSON for flexibility
    metadata_extra: Mapped[dict] = mapped_column(JSON, default=dict)

    # Optional vector ID cross-reference (Qdrant point ID)
    vector_id: Mapped[str | None] = mapped_column(String, nullable=True)

    # EpisodicMemory: ordinal position of this event within the session
    sequence_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ReflectionMemory: JSON array of source memory UUIDs (provenance)
    source_memory_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Hierarchical Memory levels
    hierarchy_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memories.id"), nullable=True
    )

