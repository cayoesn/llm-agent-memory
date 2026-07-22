import math
import time
from typing import Any
from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    id: str
    content: str
    strength: float = 1.0  # Estabilidade inicial da memória
    last_accessed_timestamp: float = Field(default_factory=time.time)
    access_count: int = 1


class EbbinghausForgettingEngine:
    """Enterprise Memory Consolidation & Ebbinghaus Forgetting Curve Engine.
    
    Aplica a curva de esquecimento de Ebbinghaus (R = e^(-t / S)) para calcular
    a retenção de memórias ao longo do tempo. Memórias com baixa retenção são
    arquivadas/consolidadas e memórias acessadas frequentemente têm sua estabilidade reforçada.
    """

    @staticmethod
    def calculate_retention(item: MemoryItem, current_time: float | None = None) -> float:
        now = current_time or time.time()
        elapsed_hours = max(0.001, (now - item.last_accessed_timestamp) / 3600.0)
        
        # Curva de esquecimento: R = e^(-t / S)
        retention = math.exp(-elapsed_hours / max(0.1, item.strength * item.access_count))
        return round(min(1.0, max(0.0, retention)), 4)

    def access_memory(self, item: MemoryItem) -> MemoryItem:
        """Reforça a estabilidade da memória ao ser consultada."""
        item.access_count += 1
        item.strength = round(item.strength * 1.25, 2)
        item.last_accessed_timestamp = time.time()
        return item


# Instância Singleton
ebbinghaus_engine = EbbinghausForgettingEngine()
