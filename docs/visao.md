# Visão — rag-conformidade-laticinios

## Problema

Quem trabalha com qualidade e conformidade em laticínios (analistas de qualidade,
consultores, responsáveis técnicos, estudantes de ciência de alimentos) precisa responder
com frequência a perguntas como *"qual o limite de CCS do leite cru refrigerado?"* ou
*"com que temperatura o leite pode chegar ao laticínio?"*. A resposta está espalhada em
normas longas (IN 76/2018, IN 77/2018, RIISPOA) e manuais técnicos. A busca manual em PDF
é lenta e sujeita a erro; um LLM puro responde rápido, mas **inventa artigos e números** —
inaceitável num domínio regulatório.

## Solução

Um sistema de **RAG agêntico** (LangGraph) sobre um corpus 100% público, com três
compromissos que um chat comum não dá:

1. **Toda afirmação cita a fonte** (documento + artigo/seção), com o trecho original
   exibível ao lado da resposta.
2. **Auto-verificação de groundedness** (padrão *corrective RAG*): a resposta é conferida
   contra os chunks recuperados; se não se sustenta, o sistema reformula a busca (até 2
   ciclos) e, persistindo a falha, responde **"não encontrei base nos documentos"** em vez
   de inventar.
3. **Retrieval medido, não chutado**: quatro estratégias (BM25, densa, híbrida RRF,
   híbrida+rerank) comparadas com métricas num golden set versionado.

## Escopo

- Perguntas **factuais** em PT-BR sobre o corpus indexado: limites numéricos, definições,
  procedimentos, prazos e responsabilidades (ex.: padrões do leite cru, transporte,
  ordenha, registro de estabelecimentos).
- Corpus alvo: **IN 76/2018** e **IN 77/2018** (MAPA), **RIISPOA** (Decreto 9.013/2017) e
  1–2 manuais públicos da **Embrapa** — mínimo de 2 documentos se a rede bloquear o resto.
- API REST (FastAPI) + front mínimo (Streamlit) com citações clicáveis e métricas da consulta.
- Ingestão incremental: adicionar documento novo sem reindexar tudo.
- Modo **demo** (gerador extrativo local, custo zero) e modo **real** (Haiku, com guard de custo).

## Fora de escopo

- **Aconselhamento jurídico** ou decisão de conformidade — o sistema localiza e cita a
  norma; interpretar é responsabilidade humana (disclaimer permanente na interface).
- Documentos privados ou internos de qualquer empresa (premissa inegociável do projeto).
- Vigência e atualização automática da legislação (alterações posteriores às versões
  baixadas; a data/versão de cada documento fica registrada no manifesto).
- Multi-turno com memória de conversa; perguntas opinativas ou comparativas abertas.
- OCR de PDFs escaneados (corpus alvo tem camada de texto).

## Métricas de sucesso

| Métrica | Alvo | Onde é medida |
|---|---|---|
| recall@5 (estratégia campeã) | ≥ 0,80 no golden set | `eval/results/RESULTS.md` |
| Latência p50 (modo demo, sem LLM pago) | ≤ 4 s | eval de retrieval + `/ask` |
| Custo por pergunta (modo real) | ≤ US$ 0,005 | harness de evals pagas |
| Respostas afirmativas sem citação no eval | 0 | eval de groundedness |
