# Auto-revisão adversarial — Fase 0 (engenharia de requisitos)

Sessão autônoma de 2026-06-11/12. Postura: tentar derrubar os próprios documentos.

## Achados REAIS (corrigidos)

| # | Achado | Correção |
|---|---|---|
| 1 | Exemplo do golden em `plano_eval.md` citava `art. 27` da IN 77 como se fosse fato verificado — risco de número inventado virar referência | Exemplo marcado explicitamente como ilustrativo (`art. NN`); números reais só após ingestão |
| 2 | No diagrama Mermaid, o nó "Pipeline de retrieval" era declarado fora do subgraph do sistema — renderizaria fora da fronteira | Nó movido para dentro do subgraph |
| 3 | Decisão Ragas × implementação própria estava só no `plano_eval.md`, sem ADR (viola a disciplina "decisão registrada em decisoes.md") | ADR-012 criado com justificativa e trade-off |
| 4 | `PROGRESSO.md` não refletia a conclusão da fase | Atualizado |

## Achados avaliados e DESCARTADOS (com motivo)

| # | Suspeita | Por que não é problema |
|---|---|---|
| 5 | RNF-02 inclui rerank local no p50 ≤ 4 s; o brief diz "sem rerank pago" | Leitura correta do brief: exclui rerank *pago*; o local conta no orçamento de latência — interpretação registrada na própria tabela de RNFs |
| 6 | RF-09 não existia na lista RF-01..08 do brief | Promover a premissa inegociável nº 2 a RF dá rastreabilidade a teste/eval (TEST-INJ-*, EVAL-PAGA-INJ); ganho > desvio |
| 7 | Front como Should (brief agrupa API+front em RF-07) | Priorização explícita: numa noite finita, API Must > front Should; risco aceito e visível |
| 8 | Golden construído pelo autor do sistema (viés de circularidade) | Inerente ao formato; mitigação documentada (5 itens p/ revisão humana, categoria `sem_base`, caveat no plano) — não é eliminável hoje |

## Riscos em aberto (carregados para a Fase 1)

- **Corpus:** fontes oficiais primárias inalcançáveis desta rede (ADR-005); dependemos de
  `www.gov.br` (com UA de navegador), espelho UFPel e Embrapa. Mitigação: validação por
  âncora textual + SHA-256 no manifesto; mínimo viável = 2 documentos.
- **RIISPOA é grande** (≈500+ artigos): chunking e tempo de embedding podem exigir poda
  (ex.: indexar Títulos pertinentes a leite/laticínios) — se podar, registrar ADR e
  refletir no golden.
- Alvo recall@5 ≥ 0,80 foi fixado **antes** de medir (correto metodologicamente), mas
  pode se revelar fácil/difícil demais neste golden; se falhar, a regra é investigar e
  reportar com honestidade, não afrouxar o alvo silenciosamente.
