from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from app.domain.entities import BaseMemory, MemoryType

class IMemoryRepository(ABC):
    """Abstract Repository for Memory Metadata (PostgreSQL)."""
    
    @abstractmethod
    async def save(self, memory: BaseMemory) -> BaseMemory:
        pass

    @abstractmethod
    async def get_by_id(self, memory_id: UUID) -> Optional[BaseMemory]:
        pass

    @abstractmethod
    async def get_by_session(self, session_id: str, memory_type: Optional[MemoryType] = None) -> List[BaseMemory]:
        pass

class IVectorStore(ABC):
    """Abstract Interface for Vector Search (Qdrant)."""
    
    @abstractmethod
    async def upsert(self, memory_id: str, vector: List[float], metadata: dict) -> None:
        pass

    @abstractmethod
    async def search(self, vector: List[float], limit: int = 5, filters: Optional[dict] = None) -> List[dict]:
        pass
