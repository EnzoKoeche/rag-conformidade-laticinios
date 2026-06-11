# PROGRESSO — rag-conformidade-laticinios

> Espelho vivo da sessão overnight de 2026-06-11/12. Atualizado a cada marco.

## Status das fases

- [x] Sondagem de ambiente e rede
- [ ] **Fase 0 — Engenharia de requisitos** (em andamento)
- [ ] Fase 1 — Ingestão e retrieval (4 estratégias)
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
