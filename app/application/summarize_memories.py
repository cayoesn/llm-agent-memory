from app.infrastructure.ollama.client import OllamaClient
from app.telemetry.logger import logger

class SummarizationService:
    """Service to compress memories using LLM summarization."""
    
    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama

    async def summarize_batch(self, memories: list[str]) -> str:
        """Compresses a list of memory contents into a single summary."""
        combined_text = "\n".join([f"- {m}" for m in memories])
        prompt = f"""
        Summarize the following agent memories into a concise, high-density paragraph.
        Maintain all key facts, names, and preferences.
        
        Memories:
        {combined_text}
        
        Summary:
        """
        
        try:
            summary = await self.ollama.generate("llama3", prompt)
            return summary.strip()
        except Exception as e:
            logger.error("summarization_failed", error=str(e))
            raise
