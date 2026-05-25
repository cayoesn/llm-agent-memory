from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from app.domain.entities import BaseMemory, MemoryType


class IMemoryRepository(ABC):
    """Abstract Repository for Memory Metadata (PostgreSQL)."""

    @abstractmethod
    async def save(self, memory: BaseMemory) -> BaseMemory:
        pass

    @abstractmethod
    async def get_by_id(self, memory_id: UUID) -> BaseMemory | None:
        pass

    @abstractmethod
    async def get_by_ids(self, memory_ids: list[UUID]) -> list[BaseMemory]:
        pass

    @abstractmethod
    async def get_by_session(
        self, session_id: str, memory_type: MemoryType | None = None
    ) -> list[BaseMemory]:
        pass


class IVectorStore(ABC):
    """Abstract Interface for Vector Search (Qdrant)."""

    @abstractmethod
    async def upsert(self, memory_id: str, vector: list[float], metadata: dict[str, Any]) -> None:
        pass

    @abstractmethod
    async def search(
        self, vector: list[float], limit: int = 5, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        pass
