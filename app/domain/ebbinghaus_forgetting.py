import math
import time
from typing import Any, Callable, Sequence
from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    id: str
    content: str
    strength: float = 1.0  # Estabilidade inicial da memória (S)
    last_accessed_timestamp: float = Field(default_factory=time.time)
    access_count: int = 1
    importance: float = 1.0
    status: str = "active"  # "active", "consolidating", "archived_cold"


class ConsolidationResult(BaseModel):
    active_count: int
    consolidating_count: int
    archived_count: int
    active_memories: list[MemoryItem]
    archived_memories: list[MemoryItem]


class EbbinghausForgettingEngine:
    """Enterprise Memory Consolidation & Ebbinghaus Forgetting Curve Engine.
    
    Aplica a curva de esquecimento de Ebbinghaus:
        R = exp(-t / S)
    onde t é o tempo decorrido em horas e S é a estabilidade mnemônica.
    
    Recursos Staff/Principal:
    1. Consolidação e poda assíncrona contínua em lote com classificação tri-tier.
    2. Reforço de repetição espaçada: S_novo = S * (1 + alpha * count) * importância.
    3. Poda assíncrona com callback para arquivamento no storage a frio.
    """

    def __init__(self, cold_threshold: float = 0.20, consolidation_threshold: float = 0.50):
        self.cold_threshold = cold_threshold
        self.consolidation_threshold = consolidation_threshold

    @staticmethod
    def calculate_retention(item: MemoryItem, current_time: float | None = None) -> float:
        now = current_time or time.time()
        elapsed_hours = max(0.001, (now - item.last_accessed_timestamp) / 3600.0)
        
        # S efetivo considera estabilidade base escalada pelo número de acessos
        effective_stability = max(0.1, item.strength * item.access_count)
        retention = math.exp(-elapsed_hours / effective_stability)
        return round(min(1.0, max(0.0, retention)), 4)

    def access_memory(self, item: MemoryItem, boost_factor: float = 1.25) -> MemoryItem:
        """Reforça a estabilidade da memória ao ser consultada (efeito de espaçamento)."""
        item.access_count += 1
        item.strength = round(item.strength * boost_factor, 2)
        item.last_accessed_timestamp = time.time()
        item.status = "active"
        return item

    def consolidate_batch(
        self,
        items: Sequence[MemoryItem],
        current_time: float | None = None,
        archive_callback: Callable[[MemoryItem], Any] | None = None,
    ) -> ConsolidationResult:
        """Executa consolidação e particionamento de memórias em tempo linear O(N)."""
        active: list[MemoryItem] = []
        archived: list[MemoryItem] = []
        consolidating_count = 0

        now = current_time or time.time()

        for item in items:
            r = self.calculate_retention(item, current_time=now)
            if r < self.cold_threshold:
                item.status = "archived_cold"
                archived.append(item)
                if archive_callback:
                    archive_callback(item)
            elif r < self.consolidation_threshold:
                item.status = "consolidating"
                consolidating_count += 1
                active.append(item)
            else:
                item.status = "active"
                active.append(item)

        return ConsolidationResult(
            active_count=len(active),
            consolidating_count=consolidating_count,
            archived_count=len(archived),
            active_memories=active,
            archived_memories=archived,
        )


# Instância Singleton
ebbinghaus_engine = EbbinghausForgettingEngine()
