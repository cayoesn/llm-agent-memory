# 🧠 LLM Agent Memory Service (Enterprise Edition)

Serviço de Memória Hierárquica, Esquecimento Contínuo e Recuperação Diversificada com **Curva de Esquecimento de Ebbinghaus**, **Vectorized MMR**, **Qdrant**, **PostgreSQL** e **Redis**.

---

## 🌟 Arquitetura & Recursos Big-Tech

- **Ebbinghaus Forgetting Curve Engine**: Modelagem cognitiva de retenção mnemônica:
  $$R = e^{-\frac{t}{S}}$$
  onde $t$ é o tempo decorrido em horas e $S$ é a estabilidade mnemônica reforçada por repetição espaçada:
  $$S_{novo} = S \cdot (1 + \alpha \cdot \text{access\_count})$$
- **Consolidação Contínua & Poda Tri-Tier**:
  - `ACTIVE` ($R \ge 0.50$): Memórias quentes em cache Redis e índice vetorial rápido.
  - `CONSOLIDATING` ($0.20 \le R < 0.50$): Candidatas a reflexão, agregação hierárquica e sumarização.
  - `ARCHIVED_COLD` ($R < 0.20$): Poda e arquivamento em cold storage assíncrono.
- **Maximal Marginal Relevance (MMR) Vetorizado**: Redução de redundância e diversificação em nível de produto:
  $$\text{MMR} = \arg\max_{D_i \in R \setminus S} \left[ \lambda \cdot \text{Sim}_1(D_i, Q) - (1-\lambda) \max_{D_j \in S} \text{Sim}_2(D_i, D_j) \right]$$
  acelerado via matrizes normalizadas e produtos escalares em NumPy BLAS/SIMD.
- **Hierarquia Mnemônica em 3 Níveis**:
  - Nível 1: Memórias episódicas e interações brutas.
  - Nível 2: Insights consolidados e perfis de usuário.
  - Nível 3: Princípios globais e regras comportamentais persistentes.

---

## 📊 Complexidade Algorítmica

| Operação | Abordagem Anterior | Abordagem Otimizada (Staff) | Estrutura de Dados |
| :--- | :--- | :--- | :--- |
| **Cálculo de Retenção** | Sob demanda em lookup | Em lote $\mathcal{O}(N)$ particionado | Linear Partitioning |
| **Diversidade MMR** | $\mathcal{O}(K \cdot N \cdot D)$ loops Python | $\mathcal{O}(K \cdot N)$ NumPy MatMul | Normalized Array $(N \times D)$ |
| **Seleção de Candidatos** | `list.remove()` $\mathcal{O}(N)$ | Boolean Masking $\mathcal{O}(1)$ | NumPy Boolean Mask |

---

## 🚀 Como Executar no Docker

```bash
docker compose up -d --build
```

---

## 🧪 Testes Automatizados (28 Testes / 100% Hermético)

Execução hermética da suíte de testes unitários:

```bash
docker run --rm -v $(pwd):/workspace -w /workspace -e PYTHONPATH=/workspace portfolio-spec-engine:test pytest tests/unit -v --cov=app/domain
```
