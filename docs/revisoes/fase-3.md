# Auto-revisão adversarial — Fase 3 (API, front, publicação)

## Achados REAIS (corrigidos antes do commit)

| # | Achado | Correção |
|---|---|---|
| 1 | A API montava um grafo por (estratégia, k) e cada grafo carregava SUA cópia do BGE-m3 (~2,3 GB) e do reranker → 2 estratégias = 2× RAM e 2× cold-start | `_infra_compartilhada()` com `lru_cache(1)`: retrieval e dependências únicos por processo; grafos por estratégia são casca fina |
| 2 | Mesmo defeito no Streamlit (`st.cache_resource` por estratégia) | `carregar_infra()` cacheada uma vez; trocar de estratégia não recarrega modelos |
| 3 | Container baixaria modelos HF para `./data/hf-cache` (volume) e o diretório não estava no `.gitignore` | ignorado + documentado no compose |
| 4 | `tests/` não era pacote → `from tests.test_grafo import` quebrava a coleta | `tests/__init__.py` |

## Validação real (não só teste unitário)

- `uvicorn` de verdade + `curl`: `/health` (685 chunks, 5 docs) e `/ask` sobre
  temperatura de recepção → resposta citando **IN 77/2018, art. 30 + IN 76/2018,
  art. 3º** (exatamente as fontes do item multi-doc do golden), groundedness aprovada.
- Primeira chamada paga o carregamento dos modelos (~15 s); depois p50 ~300 ms
  (documentado no README).

## Riscos/limitações deixados explícitos

- **Imagem Docker não foi construída nesta sessão** (torch CPU → build de vários GB;
  arquivos prontos e sintaxe validada, mas `docker compose up --build` fica para
  amanhã — primeiro build baixa ~3 GB de modelos no volume).
- `/ingest` cobre reindexação incremental de documentos DO MANIFESTO (RF-08); upload
  de arquivo arbitrário ficou fora do escopo da noite (registrado na API por validação
  de `doc_id`).
- Front é fino de propósito (RF-07 Should): pergunta → resposta citada → métricas;
  sem histórico/multi-turno (fora de escopo desde a visão).
- O CI roda a suíte sem corpus (testes de índice usam `skipif`) — gate de cobertura
  100% só nos módulos determinísticos, como definido na rastreabilidade.
