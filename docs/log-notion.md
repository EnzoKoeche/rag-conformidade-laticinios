# Log de sessão — pronto para colar no Notion

**Data:** 2026-06-11 → 2026-06-12 (overnight, sessão autônoma)

**O que foi feito** (10 commits, 74 testes verdes, US$ 0,00 em API):

- `575bfbf` chore: estrutura inicial (.env ignorado desde o commit zero, MIT, PROGRESSO)
- `b781960` docs(fase-0): visão, requisitos RF-01..09/RNFs, UCs, diagrama, rastreabilidade, plano de eval, ADRs 001-012 + revisão adversarial
- `d2805ec` feat(fase-1): downloader com Wayback p/ fontes oficiais bloqueadas (manifesto SHA-256), chunking estrutural por artigo (685 chunks de 5 docs), 4 estratégias de retrieval — 100% cobertura em chunker/extrator/fusao/bm25
- `e8aa75e` feat(eval): golden 30 perguntas ancoradas + validador automático; EVAL-RET-01 → híbrida+rerank recall@5=1,00 · MRR@10=0,91 · p50 181 ms
- `2963ff2` fix(fase-1): revisão — filtro de ficha catalográfica Embrapa, API pública do Retrieval
- `d955888` feat(fase-2): grafo corrective RAG (LangGraph) demo/real injetável, verificador de groundedness, cliente Haiku com guard de custo — 100% cobertura em citacao/grafo/llm
- `dd887fb` feat(fase-2): EVAL-GRD-01 verde (0 respostas sem citação, 3/3 recusas honestas, p50 270 ms) + harness pago com dry-run (US$ 0,005/pergunta projetado)
- `0b8b463` docs(fase-2): revisão adversarial
- `f74ed08` feat(fase-3): API FastAPI validada com curl no índice real, Streamlit, Docker/compose, CI, secret-scan limpo, README final
- (+ commit final: revisão fase-3, PROGRESSO, este log)

**Decisões** (ADRs em `docs/decisoes.md`; 🌙 = tomadas de madrugada, revisáveis):

- 🌙 Corpus via **Wayback Machine** das páginas oficiais (in.gov.br/planalto bloqueados nesta rede) com âncora textual + SHA-256; RIISPOA = consolidado do Planalto (redação 2020)
- 🌙 **Chroma embedded** (pgvector/Supabase como evolução) · **BGE-m3** (mpnet trunca em 128 tokens) · reranker **mMARCO** multilíngue
- 🌙 Grading/geração **sempre contra a pergunta original** (reformulada só no retrieval) — senão a expansão dilui o termo sem resposta e o sistema responde o que não devia
- 🌙 Limiar do grader demo = 0,5 no cross-encoder, calibrado em dados: prioriza recusa honesta ao custo de 3/27 falsos negativos (documentado; grader LLM medido amanhã)
- 🌙 Evals pagas próprias em vez de Ragas (guard conta cada chamada; métrica auditável)

**Próximo passo:**

1. Revisar 5 itens do golden (`revisao_humana: true`) e revalidar.
2. Rodar evals pagas supervisionado: `uv run python eval/run_pagas.py --executar` (estimativa US$ 0,126, teto US$ 0,50) — conferir se o grader LLM resolve G-12/G-20/G-27.
3. Secret-scan de novo + revisar `git log --stat` → criar repo e push.
4. Opcional: build do Docker; deploy do Streamlit (como no projeto 1).
