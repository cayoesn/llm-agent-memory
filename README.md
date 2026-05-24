# Agent Memory Engine

Enterprise-grade, highly observable memory system for AI Agents.

## 🚀 Architecture
This project follows a **Simplified DDD** (Domain-Driven Design) architecture:
- `app/domain`: Core entities (Memories), scoring logic, and repository interfaces.
- `app/application`: Use cases (Store, Retrieve, Context Builder).
- `app/infrastructure`: Concrete adapters (Ollama httpx, Qdrant, Postgres, Redis).
- `app/interfaces`: FastAPI HTTP routes and Pydantic schemas.

## 🛠 Features
- **Working Memory**: Fast Redis-based sliding window.
- **Semantic Memory**: Vector-based long-term retrieval via Qdrant.
- **Time Decay**: Exponential decay for memory importance.
- **Context Builder**: Orchestration of multiple memory types into dense context.
- **Observability**: Centralized OTel Collector routing to Jaeger (Tracing), Prometheus (Metrics), and Loki (Logs).

## 📦 Infrastructure
Everything runs locally via Docker Compose:
- **Ollama**: Local LLM and Embeddings.
- **Qdrant**: Vector Database.
- **PostgreSQL**: Metadata and Timelines.
- **Redis**: Cache and Working Memory.
- **OTel Stack**: Jaeger, Prometheus, Grafana, Loki.

## 🚦 How to Run
1. `make install`
2. `make docker-up`
3. `make run`

## 🧪 Testing
`make test`
`make coverage`

## 📊 Observability
- **Grafana**: http://localhost:3000
- **Jaeger**: http://localhost:16686
- **Prometheus**: http://localhost:9090
