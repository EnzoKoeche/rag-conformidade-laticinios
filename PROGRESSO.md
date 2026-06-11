# PROGRESSO — rag-conformidade-laticinios

> Espelho vivo da sessão overnight de 2026-06-11/12. Atualizado a cada marco.

## Status das fases

- [x] Sondagem de ambiente e rede
- [x] Fase 0 — Engenharia de requisitos (7 docs em `docs/` + auto-revisão `docs/revisoes/fase-0.md`)
- [x] Fase 1 — Ingestão e retrieval: 5 docs baixados (Wayback p/ fontes bloqueadas),
      685 chunks estruturais, 4 estratégias, golden 30 itens validado, EVAL-RET-01
      (híbrida+rerank recall@5=1,00 · MRR 0,91; p50 re-medido em 2026-06-11: 322 ms)
      + `docs/revisoes/fase-1.md`
- [x] Fase 2 — Grafo corrective RAG (LangGraph) com modo demo/real injetável, verificador
      de groundedness real, guard de custo; EVAL-GRD-01 verde (0 violações de citação,
      3/3 recusas honestas; p50 re-medido em 2026-06-11: 272 ms); dry-run pago
      US$0,005/pergunta de sistema; 72 testes, 100% cobertura nos módulos-alvo
      + `docs/revisoes/fase-2.md`
- [x] Fase 3 — API FastAPI (/ask /ingest /health, validada com curl no índice real),
      front Streamlit, Dockerfile + compose (app + chroma), CI GitHub Actions, README
      final e secret-scan limpo + `docs/revisoes/fase-3.md`

**Sessão overnight concluída.** 74 testes verdes · 10 commits · US$ 0,00 gastos em API.

## Sessão 2026-06-11 (manhã) — revisão, validação Docker e publicação

Instrução do Enzo: "revise tudo que falta pra revisar (...) veja o que falta pra
terminar, não se esqueça do Notion e GitHub (...) e depois volte a codar".

- [x] **Revisão da amostra do golden (delegada):** 5/5 itens confrontados com o texto
      cru dos chunks-fonte — 4 `ok`, **G-12 corrigido** (paráfrase infiel ao art. 373
      do RIISPOA). Registro auditável com citações: `docs/revisoes/revisao-golden.md`.
      Validador entende o campo `revisado` (protocolo do plano_eval §1) e segue verde.
- [x] **fix(densa):** cache de embeddings 100% quente dispensa carregar o modelo —
      ingestão incremental no container ficou sem download (antes: 2,3 GB à toa).
- [x] **Docker validado de verdade** (não estava no ar à noite): build ok; compose up;
      `/ingest` ×5 popula o Chroma http com 685 chunks em **3,8 s** via cache npz do
      volume; `/ask` bm25 (1ª chamada 57 s = download do cross-encoder; groundedness
      aprovado citando IN 77 art. 30) e `/ask` hibrida_rerank (1ª chamada 130 s =
      download do BGE-m3; aprovado). Receita de população documentada no cabeçalho do
      `docker-compose.yml`. Cache HF do volume: 3,1 GB. Observado: paráfrase do G-05
      no modo demo prioriza chunk certo-mas-menos-específico (limitação documentada do
      gerador extrativo; gerador LLM é medido nas evals pagas).
- [x] **Evals re-medidas pós-mudanças:** qualidade idêntica (recall@5 1,00 · MRR 0,91 ·
      0 violações · 3/3 recusas · 24/24 fonte esperada); latências do dia: rerank p50
      322 ms, grafo p50 272 ms (README sincronizado; docs históricos mantêm os valores
      da noite).
- [x] **Secret-scan** re-rodado (12 commits: limpo) + re-scan final antes do push.
- [x] **Push:** repo público `github.com/EnzoKoeche/rag-conformidade-laticinios`
      criado via `gh` (api.github.com voltou a funcionar nesta máquina em 2026-06-11).
- [x] **Notion:** página "Estado do Projeto" criada no padrão do projeto 1.

## Bloqueios

Nenhum.

## Pendências (dependem do Enzo)

1. **Evals pagas** (modo real, supervisão): criar `.env` com a chave +
   `RAG_PERMITIR_CUSTO=1`, depois `uv run python eval/run_pagas.py --executar`
   (estimativa US$ 0,126 · teto US$ 0,50). Atenção a G-12/G-20/G-27 (falsos negativos
   do grader demo — hipótese: o grader LLM resolve).
2. Opcional: re-auditar a revisão delegada do golden (`docs/revisoes/revisao-golden.md`
   tem as citações-fonte; leva minutos).
3. Opcional: deploy do Streamlit no Community Cloud, como no projeto 1.

## Achados de ambiente (2026-06-11, noite)

- Python do sistema: 3.14.4 → **Python 3.12.13 instalado via uv** (alvo do projeto).
- Hardware: 20 cores, 31 GB RAM, 951 GB livres → BGE-m3 local é viável.
- Docker 29.1.3 funcional no WSL.
- Rede: PyPI ✓ · HuggingFace ✓ · Embrapa (infoteca/ainfo) ✓ · **in.gov.br e
  planalto.gov.br INALCANÇÁVEIS** (bloqueio de rede, não DNS — conexão morre mesmo com
  IP resolvido via DoH) · `www.gov.br` responde **200 com User-Agent de navegador**
  (403 com UA curl) · espelho UFPel/inspleite localizado para normas de leite fluido.
- Orçamento de API da sessão: **US$ 0,00 em geração paga** — tudo roda em modo demo/mock.
