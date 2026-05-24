import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.entities import MemoryType


class Base(DeclarativeBase):
    pass


class MemoryModel(Base):
    """SQLAlchemy model for Memory metadata."""

    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content: Mapped[str] = mapped_column(String, nullable=False)
    memory_type: Mapped[MemoryType] = mapped_column(SQLEnum(MemoryType), nullable=False)
    session_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    agent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    importance_score: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Specific fields for different types stored in JSON for flexibility
    metadata_extra: Mapped[dict] = mapped_column(JSON, default=dict)

    # Optional vector ID reference
    vector_id: Mapped[str | None] = mapped_column(String, nullable=True)
