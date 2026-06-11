# PROGRESSO — rag-conformidade-laticinios

> Espelho vivo da sessão overnight de 2026-06-11/12. Atualizado a cada marco.

## Status das fases

- [x] Sondagem de ambiente e rede
- [x] Fase 0 — Engenharia de requisitos (7 docs em `docs/` + auto-revisão `docs/revisoes/fase-0.md`)
- [x] Fase 1 — Ingestão e retrieval: 5 docs baixados (Wayback p/ fontes bloqueadas),
      685 chunks estruturais, 4 estratégias, golden 30 itens validado, EVAL-RET-01
      (híbrida+rerank recall@5=1,00 · MRR 0,91 · p50 181 ms) + `docs/revisoes/fase-1.md`
- [x] Fase 2 — Grafo corrective RAG (LangGraph) com modo demo/real injetável, verificador
      de groundedness real, guard de custo; EVAL-GRD-01 verde (0 violações de citação,
      3/3 recusas honestas, p50 270 ms); dry-run pago US$0,005/pergunta de sistema;
      72 testes, 100% cobertura nos módulos-alvo + `docs/revisoes/fase-2.md`
- [ ] **Fase 3 — API, front, Docker, README, secret-scan** (em andamento)
- [ ] Fase 2 — Grafo agêntico + evals grátis
- [ ] Fase 3 — API, front, Docker, README, secret-scan

## Bloqueios

Nenhum no momento.

## Achados de ambiente (2026-06-11, noite)

- Python do sistema: 3.14.4 → **Python 3.12.13 instalado via uv** (alvo do projeto).
- Hardware: 20 cores, 31 GB RAM, 951 GB livres → BGE-m3 local é viável.
- Docker 29.1.3 funcional no WSL.
- Rede: PyPI ✓ · HuggingFace ✓ · Embrapa (infoteca/ainfo) ✓ · **in.gov.br e
  planalto.gov.br INALCANÇÁVEIS** (bloqueio de rede, não DNS — conexão morre mesmo com
  IP resolvido via DoH) · `www.gov.br` responde **200 com User-Agent de navegador**
  (403 com UA curl) · espelho UFPel/inspleite localizado para normas de leite fluido.
- Orçamento de API da sessão: **US$ 0,00 em geração paga** — tudo roda em modo demo/mock.
