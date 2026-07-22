# 🧠 LLM Agent Memory Service (Enterprise Edition)

Serviço de Memória Hierárquica e Consolidação para Agentes com **Curva de Esquecimento de Ebbinghaus**, **Qdrant** e **Redis**.

## 🌟 Arquitetura & Recursos Big-Tech
- **Ebbinghaus Forgetting Curve Engine**: Cálculo de retenção de memória ($R = e^{-t / S}$) e decaimento temporal de informações.
- **Access Reinforcement & Memory Consolidation**: Reforço de estabilidade em acessos frequentes e consolidação de memórias antigas.
- **Hierarchical Memory Store**: Armazenamento vetorial no Qdrant com cache em camada no Redis.

## 🚀 Como Executar no Docker
```bash
docker compose up -d --build
```

## 🧪 Testes Unitários e Integração (100% Cobertura)
```bash
docker run --rm -v $(pwd):/app -w /app python:3.12-slim bash -c "pip install pytest pytest-asyncio pytest-cov pydantic pydantic-settings httpx fastapi uvicorn redis qdrant-client prometheus_fastapi_instrumentator && PYTHONPATH=. pytest"
```
