import time
import asyncio
import httpx
from app.telemetry.logger import logger

async def run_benchmark():
    """Simple benchmark script to measure API latency."""
    url = "http://localhost:8000/memory/store"
    payload = {
        "content": "The user likes coffee without sugar.",
        "memory_type": "semantic",
        "session_id": "bench-1"
    }
    
    start_time = time.time()
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            latency = time.time() - start_time
            print(f"Store Memory Latency: {latency:.4f}s")
            print(f"Status: {response.status_code}")
        except Exception as e:
            print(f"Benchmark failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
