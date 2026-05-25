# 🧠 Análise Profunda: Mecanismos de Memória e Recuperação (Search/Retrieval)

Este documento apresenta uma análise detalhada da arquitetura do projeto **Agent Memory Engine**. O objetivo aqui é explicar conceitos complexos de forma simples, mostrando como cada peça foi construída, quais decisões foram tomadas e como o sistema se comporta como uma engine de nível Sênior.

---

## 📊 Tabela de Mapeamento Geral (Checklist)

| Categoria | Tipo de Mecanismo | Status | Tecnologia Utilizada | Arquivo Principal |
| :--- | :--- | :---: | :--- | :--- |
| **Memory** | [Working Memory](#1-working-memory) | ✅ Implementado | Redis | [main.py](app/interfaces/http/main.py) |
| **Memory** | [Semantic Memory](#2-semantic-memory) | ✅ Implementado | Qdrant + Ollama | [store_memory.py](app/application/store_memory.py) |
| **Memory** | [Episodic Memory](#3-episodic-memory) | ✅ Implementado | PostgreSQL | [repository.py](app/infrastructure/storage/postgres/repository.py) |
| **Memory** | [Reflection Memory](#4-reflection-memory) | ✅ Implementado | Ollama (Llama3) | [scheduler.py](app/workers/scheduler.py) |
| **Memory** | [Hierarchical Memory](#6-hierarchical-memory) | ✅ Implementado | Summarization + DB | [hierarchy_builder.py](app/application/hierarchy_builder.py) |
| **Memory** | [Contextual Memory](#7-contextual-memory) | ✅ Implementado | Orquestração Python | [context_builder.py](app/application/context_builder.py) |
| **Memory** | [Temporal Memory](#8-temporal-memory) | ✅ Implementado | Qdrant Filters | [adapter.py](app/infrastructure/storage/qdrant/adapter.py) |
| **Memory** | [Compressed Memory](#9-compressed-memory) | ✅ Implementado | Ollama (Llama3) | [summarize_memories.py](app/application/summarize_memories.py) |
| **Memory** | [Adaptive/Decay Memory](#10-adaptivedecay-memory) | ✅ Implementado | Algoritmo Matemático | [services.py](app/domain/services.py) |
| **Search** | [Semantic Search](#11-semantic-search) | ✅ Implementado | Embeddings + Qdrant | [retrieve_memory.py](app/application/retrieve_memory.py) |
| **Search** | [Vector Search](#12-vector-search) | ✅ Implementado | Qdrant | [adapter.py](app/infrastructure/storage/qdrant/adapter.py) |
| **Search** | [Top-K Retrieval](#13-top-k-retrieval) | ✅ Implementado | Qdrant Limit | [adapter.py](app/infrastructure/storage/qdrant/adapter.py) |
| **Search** | [Metadata Filtering](#14-metadata-filtering) | ✅ Implementado | Qdrant Payload | [adapter.py](app/infrastructure/storage/qdrant/adapter.py) |
| **Search** | [Hybrid Search](#15-hybrid-search) | ✅ Implementado | BM25 + Embeddings + RRF | [adapter.py](app/infrastructure/storage/qdrant/adapter.py) |
| **Search** | [Time-Weighted Retrieval](#16-time-weighted-retrieval) | ✅ Implementado | Recency Score | [services.py](app/domain/services.py) |
| **Search** | [MMR Retrieval](#17-mmr-retrieval) | ✅ Implementado | Diversidade (MMR) | [services.py](app/domain/services.py) |
| **Search** | [Context-Aware Retrieval](#18-context-aware-retrieval) | ✅ Implementado | Redis + Qdrant | [context_builder.py](app/application/context_builder.py) |
| **Search** | [Personalized Retrieval](#19-personalized-retrieval) | ✅ Implementado | User Profile Blend | [user_profile_service.py](app/application/user_profile_service.py) |
| **Search** | [Hierarchical Retrieval](#20-hierarchical-retrieval) | ✅ Implementado | Multi-level Fetch | [hierarchical_retrieval.py](app/application/hierarchical_retrieval.py) |

---

## 🧠 Parte 1: Tipos de Memória (Memory)

### 1. Working Memory
*   **Conceito:** É a "Memória RAM". É o que o agente está conversando **agora**. Ela é rápida, mas pequena.
*   **Como funciona:** Quando você envia uma mensagem, o sistema salva no Redis usando uma lista. Ele mantém apenas as últimas 10 mensagens (janela deslizante). Se chegar a 11ª, a 1ª é apagada do Redis (mas continua no Postgres para sempre).
*   **Código:** `RedisCache.push_to_list` no arquivo `app/infrastructure/storage/redis/cache.py`.

### 2. Semantic Memory
*   **Conceito:** É a memória baseada em **significado**. Se você disser "Eu amo gatos", e depois perguntar "Quais animais eu gosto?", o sistema sabe que gato é um animal.
*   **Como funciona:** Usamos o Ollama para transformar o texto em um vetor (uma lista de 768 números). Salvamos esse vetor no Qdrant. Na hora de buscar, transformamos sua pergunta em vetor também e vemos quais vetores estão "perto" um do outro.

### 3. Episodic Memory
*   **Conceito:** É o "Diário". Ele guarda a sequência exata do que aconteceu, um passo de cada vez.
*   **Como funciona:** Adicionamos um `sequence_index` no banco de dados. Toda vez que uma memória nova entra em uma sessão, o sistema olha qual foi o último número e soma +1. Isso garante que saibamos exatamente a ordem das falas.
*   **Código:** `get_next_sequence_index` em `app/infrastructure/storage/postgres/repository.py`.

### 4. Reflection Memory
*   **Conceito:** É o agente "parando para pensar". Ele olha o que aconteceu nas últimas horas e tira uma conclusão.
*   **Como funciona:** Um agendador (Scheduler) roda a cada 4 horas. Ele pega as memórias do diário (Episódicas), manda para o Llama3 e pergunta: "O que podemos aprender sobre o usuário aqui?". O resultado é salvo como uma nova memória de Reflexão.

### 6. Hierarchical Memory
*   **Conceito:** Organização em níveis. Nível 1 é o detalhe, Nível 2 é o resumo da conversa, Nível 3 é o resumo de tudo sobre o usuário.
*   **Como funciona:** O `HierarchyBuilder` consolida memórias. Ele pega várias memórias de Nível 1 e cria um "pai" de Nível 2 que é um resumo delas. Depois, pega vários pais e cria um "avô" de Nível 3.

### 8. Temporal Memory
*   **Conceito:** Memória que entende o tempo. "O que aconteceu ontem?"
*   **Como funciona:** O Qdrant agora aceita filtros de `since` (desde) e `until` (até). Quando você busca, pode dizer que quer apenas coisas de uma data específica. Além disso, o sistema dá mais "nota" para coisas que aconteceram há 5 minutos do que coisas de 5 meses atrás.

### 10. Adaptive/Decay Memory
*   **Conceito:** Esquecimento natural. Coisas pouco importantes vão perdendo força com o tempo.
*   **Como funciona:** Usamos uma fórmula de decaimento exponencial. A cada hora, o sistema diminui um pouco a nota de importância de todas as memórias. Se algo era nota 1.0, depois de um dia pode virar 0.5.

---

## 🔎 Parte 2: Mecanismos de Busca (Search)

### 15. Hybrid Search
*   **Conceito:** É o melhor dos dois mundos. Busca por **significado** (Vetor) + Busca por **palavra exata** (Keyword/BM25).
*   **Como funciona:** Se você buscar "Erro 404", a busca por significado pode trazer coisas sobre "problemas de rede", mas a busca por palavra exata vai achar o "404" específico. Usamos **RRF (Reciprocal Rank Fusion)** para misturar esses dois resultados em uma lista única perfeita.

### 16. Time-Weighted Retrieval
*   **Conceito:** Ponderação por tempo. "O que é novo é mais relevante".
*   **Como funciona:** O `MemoryRanker` calcula um `recency_score`. Se a memória é nova, ganha 1.0. Se é antiga, ganha 0.1. Esse valor é multiplicado pelo score de similaridade, fazendo com que coisas novas subam no ranking.

### 17. MMR (Maximal Marginal Relevance)
*   **Conceito:** Diversidade. Evita que o agente receba 5 vezes a mesma informação.
*   **Como funciona:** Se a busca retornar 3 resultados quase iguais, o algoritmo MMR percebe a repetição e "pula" as cópias, pegando o próximo resultado que seja diferente e traga informação nova.

### 19. Personalized Retrieval
*   **Conceito:** Busca que te conhece.
*   **Como funciona:** O sistema mantém um "Perfil do Usuário" (User Profile). Na hora de buscar, nós misturamos (blend) o que você perguntou com quem você é. Se você é um "Desenvolvedor Python" e pergunta sobre "bibliotecas", o sistema prioriza bibliotecas Python em vez de Java.

### 20. Hierarchical Retrieval
*   **Conceito:** Busca em camadas.
*   **Como funciona:** O sistema primeiro busca nos resumos globais (Nível 3). Se achar algo interessante, ele olha os resumos daquela sessão (Nível 2) e finalmente as falas específicas (Nível 1). É como navegar em pastas no computador.

---

## 🛠️ Tecnologias e Decisões

1.  **FastAPI:** Escolhido por ser assíncrono e muito rápido para APIs de IA.
2.  **Qdrant:** Banco vetorial que suporta busca híbrida nativa, o que facilitou a implementação do BM25.
3.  **Redis:** Perfeito para Working Memory por causa da latência de microssegundos.
4.  **SQLAlchemy Async:** Permite que o banco de dados Postgres não trave a aplicação enquanto salva dados pesados.
5.  **FastEmbed:** Biblioteca leve para gerar os vetores esparsos (BM25) sem precisar de um servidor gigante.
