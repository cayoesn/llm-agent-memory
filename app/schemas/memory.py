from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.domain.entities import MemoryType


class MemoryCreate(BaseModel):
    content: str
    memory_type: MemoryType
    session_id: str
    agent_id: str | None = None
    importance_score: float = 0.0
    extra: dict[str, Any] = {}


class MemoryResponse(BaseModel):
    id: UUID
    content: str
    memory_type: MemoryType
    session_id: str
    importance_score: float
    created_at: datetime


class SearchRequest(BaseModel):
    query: str
    session_id: str
    limit: int = 5
