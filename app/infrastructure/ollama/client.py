import httpx
from opentelemetry import trace
from tenacity import retry, stop_after_attempt, wait_exponential

from app.telemetry.logger import logger

tracer = trace.get_tracer(__name__)


class OllamaClient:
    """Manual Async Ollama Client with Tracing and Retries."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate(self, model: str, prompt: str):
        """Generates a response from Ollama /api/generate."""
        with tracer.start_as_current_span("ollama_generate") as span:
            span.set_attribute("llm.model", model)

            try:
                response = await self.client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                )
                response.raise_for_status()
                data = response.json()

                logger.info("ollama_request_success", model=model)
                return data["response"]

            except Exception as e:
                logger.error("ollama_request_failed", error=str(e))
                span.record_exception(e)
                raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def embeddings(self, model: str, prompt: str):
        """Generates embeddings from Ollama /api/embeddings."""
        with tracer.start_as_current_span("ollama_embeddings") as span:
            span.set_attribute("llm.model", model)

            try:
                response = await self.client.post(
                    f"{self.base_url}/api/embeddings", json={"model": model, "prompt": prompt}
                )
                response.raise_for_status()
                data = response.json()

                return data["embedding"]

            except Exception as e:
                logger.error("ollama_embedding_failed", error=str(e))
                span.record_exception(e)
                raise
