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

---

# Sessão 2026-06-11 (manhã) — revisão, Docker validado e publicação

**Data:** 2026-06-11

**O que foi feito:**

- `2bb2d0f` revisão delegada da amostra do golden: 4 itens `ok`, **G-12 corrigido** (fidelidade ao art. 373 do RIISPOA); registro auditável com citações-fonte em `docs/revisoes/revisao-golden.md`; validador entende `revisado` (0 pendências)
- `8d51e1b` fix(densa): cache de embeddings quente dispensa carregar o modelo + fluxo real de população do Chroma http documentado (compose/README)
- **Docker validado ao vivo:** build ok → compose up → `/ingest` ×5 = 685 chunks no Chroma http em 3,8 s (cache npz do volume, sem download de modelo) → `/ask` bm25 e híbrida+rerank aprovados pelo verificador (1ª chamada baixa CE 0,5 GB / BGE-m3 2,3 GB p/ o volume, como documentado)
- Evals re-medidas após as mudanças: **qualidade idêntica** (recall@5 1,00 · MRR 0,91 · 0 violações · 3/3 recusas honestas); latências do dia (rerank p50 322 ms, grafo p50 272 ms) sincronizadas no README
- Secret-scan ×2 (histórico completo + árvore): **limpo**
- **Push público:** github.com/EnzoKoeche/rag-conformidade-laticinios (repo criado via `gh` — api.github.com voltou a funcionar no WSL em 2026-06-11)

**Decisões:**

- Revisão do golden **delegada ao agente** por instrução do Enzo; cada veredito carrega a citação literal da fonte p/ re-auditoria rápida (G-04/G-05/G-21/G-23 `ok`, G-12 `corrigido`)
- Latências publicadas = medição do dia na mesma máquina (322/272 ms); valores da noite (181/270 ms) preservados nos docs históricos de fase
- Evals pagas **não executadas** (sem `.env`/chave no ambiente — regra: execução paga só com Enzo presente e custo autorizado)

**Próximo passo:**

1. Evals pagas com supervisão: `.env` + `RAG_PERMITIR_CUSTO=1` → `uv run python eval/run_pagas.py --executar` (US$ 0,126 estimado, teto US$ 0,50); conferir G-12/G-20/G-27 no grader LLM.
2. Opcional: re-auditar a revisão delegada (`docs/revisoes/revisao-golden.md`).
3. Opcional: deploy do Streamlit no Community Cloud + screenshot no README.
