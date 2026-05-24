from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.domain.entities import MemoryType

class MemoryCreate(BaseModel):
    content: str
    memory_type: MemoryType
    session_id: str
    agent_id: Optional[str] = None
    importance_score: float = 0.0
    extra: dict = {}

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
