# Matriz de rastreabilidade

RF/RNF ↔ caso de uso ↔ componente/nó do grafo ↔ teste/eval. IDs de teste são prefixos de
arquivos/casos em `tests/`; IDs de eval em `eval/`.

| Req | UC | Componente / nó | Testes | Evals |
|---|---|---|---|---|
| RF-01 chunking estrutural | UC-06 | `ingestao/parser_*.py`, `ingestao/chunker.py` | TEST-CHUNK-01..NN (estrutura, subdivisão, metadados, texto cru, anexos) | indireto: qualidade entra em EVAL-RET-01 |
| RF-02 híbrida RRF | UC-01, UC-07 | `retrieval/bm25.py`, `retrieval/densa.py`, `retrieval/fusao.py` | TEST-FUSAO-01..NN (RRF exato, empates, listas disjuntas) | EVAL-RET-01 (linhas bm25/densa/híbrida) |
| RF-03 reranking local | UC-01, UC-07 | `retrieval/rerank.py` | TEST-RERANK-01 (ordenação local, sem rede) | EVAL-RET-01 (linha híbrida+rerank) |
| RF-04 citações obrigatórias | UC-01 | nó `generate`, `citacao.py` | TEST-CIT-01..NN (parsing, resolução p/ chunk, formato) | EVAL-GRD-01 (0 afirmações sem citação) |
| RF-05 corrective RAG | UC-01 A1, UC-03 | nós `verify_groundedness`, `reformular_query`; rotas condicionais | TEST-ROTA-01..NN (cada aresta isolada; limite de 2 ciclos) | EVAL-GRD-01; EVAL-PAGA-FAITH (amanhã) |
| RF-06 "não sei" honesto | UC-02, UC-03 | nós `entender_pergunta`, `sem_base` | TEST-ROTA-FORA, TEST-E2E-SEMBASE | EVAL-GRD-01 (itens sem-resposta do golden) |
| RF-07 API + front | UC-01 | `api/main.py`, `app/streamlit_app.py` | TEST-API-01..NN (`/ask`, `/ingest`, `/health` via TestClient) | — |
| RF-08 ingestão incremental | UC-06 | `ingestao/indexador.py` (upsert + cache de embeddings) | TEST-INC-01..NN (upsert sem duplicar; cache evita re-embedding) | — |
| RF-09 anti-injection | UC-04, UC-05 | prompt de geração; gerador extrativo; pipeline de ingestão | TEST-INJ-PERGUNTA, TEST-INJ-DOC | EVAL-PAGA-INJ (amanhã) |
| RNF-01 recall@5 ≥ 0,8 | UC-07 | pipeline de retrieval | — | EVAL-RET-01 |
| RNF-02 p50 ≤ 4 s | UC-01 | grafo instrumentado | — | EVAL-RET-01 (coluna latência) + métricas do `/ask` |
| RNF-03 custo ≤ US$ 0,005/perg. | — | `llm/cliente.py` (contagem de tokens) | TEST-GUARD-01 (estimativa) | EVAL-PAGA-* dry-run (estimativa) |
| RNF-04 0 resposta sem citação | UC-01 | `verify_groundedness` | TEST-CIT-*, TEST-E2E-* | EVAL-GRD-01 |
| RNF-05 reprodutibilidade | — | `uv.lock`, `data/manifesto.json`, seeds | suíte inteira re-executável | re-run das evals = mesmos números |
| RNF-06 sem segredos | — | `.gitignore`, scan | — | `docs/revisoes/secret-scan.md` |
| RNF-07 US$ 0 na sessão | — | guard de custo em `llm/cliente.py` | TEST-GUARD-02 (bloqueio por default) | dry-run only |

**Cobertura exigida:** módulos determinísticos `chunker`, `fusao`, `citacao` (e o
verificador de groundedness) → **100%** de cobertura de linhas; demais módulos, melhor
esforço reportado.
