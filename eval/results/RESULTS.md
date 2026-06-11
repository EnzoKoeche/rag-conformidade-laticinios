# EVAL-RET-01 — Comparativo de estratégias de retrieval

Golden: **27 perguntas respondíveis** (hash `bf18bbad4912`) · índice: **685 chunks** · embeddings: `BAAI/bge-m3` · reranker: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` · k=10 · 2026-06-11T04:43:18+00:00 · x86_64 / CPU only / WSL2

| Estratégia | recall@1 | recall@3 | recall@5 | recall@10 | MRR@10 | p50 (ms) | p95 (ms) |
|---|---|---|---|---|---|---|---|
| bm25 | 0.70 | 0.78 | **0.85** | 0.89 | 0.76 | 1 | 1 |
| densa | 0.81 | 0.96 | **0.96** | 0.96 | 0.89 | 39 | 41 |
| hibrida | 0.81 | 0.89 | **0.93** | 1.00 | 0.87 | 39 | 42 |
| hibrida_rerank | 0.85 | 1.00 | **1.00** | 1.00 | 0.91 | 181 | 189 |

## recall@5 por categoria

| Categoria | bm25 | densa | hibrida | hibrida_rerank |
|---|---|---|---|---|
| definicao | 0.71 | 1.00 | 1.00 | 1.00 |
| limite_numerico | 0.71 | 0.86 | 0.71 | 1.00 |
| multi_doc | 1.00 | 1.00 | 1.00 | 1.00 |
| prazo_responsabilidade | 1.00 | 1.00 | 1.00 | 1.00 |
| procedimento | 1.00 | 1.00 | 1.00 | 1.00 |

## O que isto prova — e o que não prova

- **Prova:** qual estratégia recupera melhor o artigo-fonte correto *neste corpus e neste golden* (n=27), com unidade de acerto = artigo (ADR-011); justifica a estratégia default do sistema com número, não opinião.
- **Não prova:** qualidade da resposta final (medida na eval de groundedness e nas evals pagas), generalização para outros corpora/domínios, robustez a paráfrases fora do estilo do golden. O golden foi escrito pelo autor do sistema a partir dos próprios chunks (viés documentado no plano_eval §1; 5 itens aguardam revisão humana).
- Latências medidas **a quente** (modelos carregados; o primeiro carregamento de modelo leva segundos e está fora destas medições), em CPU/WSL2.
