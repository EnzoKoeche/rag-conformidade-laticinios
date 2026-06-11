# Plano de avaliação (eval ANTES do código)

Princípio herdado do projeto 1: definir **o que é "bom"** e **como medir** antes de
implementar, e documentar para cada métrica **o que ela prova e o que NÃO prova**.

## 1. Golden dataset (30 perguntas)

Arquivo: `eval/golden/golden.jsonl` — 1 item por linha:

```json
{
  "id": "G-07",
  "pergunta": "Qual a temperatura máxima do leite cru refrigerado na recepção do estabelecimento?",
  "categoria": "limite_numerico",
  "doc_esperado": "in-77-2018",
  "artigos_esperados": ["art. NN  ← exemplo ILUSTRATIVO; números reais só após a ingestão"],
  "modo_acerto": "qualquer",
  "resposta_referencia": "…",
  "revisao_humana": false,
  "respondivel": true
}
```

- **Categorias** (estratificadas): `limite_numerico`, `definicao`, `procedimento`,
  `prazo_responsabilidade`, `multi_doc` (pergunta cujo gabarito aceita artigos de mais de
  um documento) e `sem_base` (pergunta de domínio **sem** resposta no corpus — gabarito é
  recusar; `respondivel: false`).
- **Construção:** as perguntas são escritas **a partir dos chunks reais** após a ingestão
  (Fase 1) — nunca de memória. Cada `resposta_referencia` só pode conter fatos presentes
  no(s) chunk(s) esperado(s).
- **Validação automática** (`eval/golden/validar_golden.py`, roda no pytest):
  (a) todo `(doc_esperado, artigo)` resolve para chunk existente no índice;
  (b) números e termos-chave da `resposta_referencia` aparecem no texto cru dos chunks
  esperados; (c) schema válido e ids únicos. Golden inválido = suíte vermelha.
- **5 itens com `revisao_humana: true`** — amostra estratificada (≥ 1 por categoria
  difícil, priorizando `limite_numerico` e `multi_doc`) para o Enzo conferir amanhã,
  marcando no próprio JSONL: `"revisado": "ok" | "corrigido"`.
- **Viés conhecido (caveat):** autor das perguntas = autor do sistema, e as perguntas
  nascem dos próprios chunks → mede **comparação entre estratégias e regressão**, tende a
  superestimar qualidade absoluta. Mitigação: revisão humana de amanhã + categorias
  `sem_base` que punem otimismo.

## 2. Evals grátis de retrieval (o coração do portfólio)

Script: `eval/run_retrieval.py` → `eval/results/RESULTS.md` + `RESULTS.json` (bruto).

- **Estratégias (mesmas perguntas, mesmo corpus, k=10 candidatos):**
  1. só BM25; 2. só densa; 3. híbrida (RRF k=60); 4. híbrida + rerank local.
- **Unidade de acerto:** o **artigo** (ADR-011) — acerto se algum chunk recuperado
  pertence a um `(doc, artigo)` esperado. Itens `sem_base` ficam **fora** das métricas de
  recall (não têm gabarito de retrieval); são avaliados na eval de groundedness.
- **Métricas por estratégia:** recall@1, @3, @5, @10 · MRR@10 · hit rate@10 · latência
  p50/p95 por consulta (medida no mesmo processo, hardware registrado).
- **Tabela comparativa OBRIGATÓRIA** no RESULTS.md, com: modelo de embedding usado,
  nº de chunks do índice, data, hash do golden e breakdown por categoria.
- **O que prova:** qual estratégia recupera melhor **neste corpus e golden**; justifica
  com número a escolha da estratégia default. **O que NÃO prova:** qualidade da resposta
  final (geração), generalização para outros corpora, robustez a paráfrase fora do estilo
  das perguntas do golden.

## 3. Eval grátis de groundedness/citação (modo demo)

Script: `eval/run_groundedness.py` (roda o **grafo completo** em modo demo sobre o golden).

- Checa por item: resposta afirmativa ⇒ **toda sentença com citação resolvível** para
  chunk recuperado (RNF-04: alvo 0 violações); itens `sem_base` ⇒ rota de recusa honesta
  acionada; itens `respondivel` ⇒ taxa de resposta (não-recusa) reportada.
- **O que prova:** o contrato de citação e as rotas do corrective RAG funcionam de ponta
  a ponta sem LLM. **O que NÃO prova:** qualidade/fluência da geração real (o gerador
  demo é extrativo por construção) — isso é papel das evals pagas.

## 4. Evals pagas (implementadas hoje, EXECUTADAS amanhã)

Script: `eval/run_pagas.py` — implementação própria (sem dependência do Ragas; decisão:
menos uma dependência pesada, métricas transparentes e auditáveis), juiz = **Haiku**.

- **Métricas:** `faithfulness` (cada afirmação da resposta é suportada pelos chunks
  citados? juiz LLM por sentença) e `answer_relevancy` (a resposta endereça a pergunta?).
  Amostra: 10 itens estratificados do golden (custo controlado), modo real de geração.
- **Guard de custo (inegociável):** `--dry-run` é o **default** — imprime plano, nº de
  chamadas e custo estimado (tokens estimados × preço vigente do modelo) e **não chama
  API**. Execução real exige `--executar` + `RAG_PERMITIR_CUSTO=1` + chave no `.env` +
  estimativa ≤ `RAG_TETO_CUSTO_USD` (default US$ 0,50); custo real é contabilizado
  durante a execução e aborta ao atingir o teto.
- **Nesta sessão:** harness + testes do guard (com transporte fake) + dry-run executado e
  registrado. **Nenhuma chamada paga.**

## 5. Critérios de pronto da avaliação

| Gate | Critério |
|---|---|
| G1 | Golden com 30 itens, validação automática verde, 5 marcados p/ revisão humana |
| G2 | RESULTS.md com a tabela das 4 estratégias e recall@5 da campeã ≥ 0,80 (RNF-01) |
| G3 | Groundedness demo: 0 afirmações sem citação válida (RNF-04) |
| G4 | Dry-run das evals pagas com estimativa ≤ US$ 0,005/pergunta projetada (RNF-03) |
