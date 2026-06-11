# Decisões de arquitetura (ADRs)

Formato: Contexto → Decisão → Alternativas → Consequências. Status `aceita` salvo nota.
Decisões tomadas em sessão autônoma (2026-06-11/12) são marcadas 🌙 — revisáveis de manhã.

---

## ADR-001 🌙 — Vector store: ChromaDB embedded (pgvector como evolução)

**Contexto.** O critério do projeto é "o que roda liso no WSL hoje". Docker 29.1.3 está
funcional (pgvector seria viável), mas a sessão é overnight e a suíte de testes precisa
rodar hermética, sem depender de serviço de pé.

**Decisão.** ChromaDB **embedded** persistente (`data/index/`) como armazenamento padrão,
atrás de uma interface própria (`VetorStore`) para troca futura. O `docker-compose` sobe
o Chroma em modo servidor (`CHROMA_MODE=http`) para o cenário conteinerizado.

**Alternativas.** (a) pgvector via Docker — mais "produção", porém acrescenta migração de
schema e um serviço obrigatório para testes; (b) Supabase/pgvector gerenciado — fica como
**evolução registrada**: a interface `VetorStore` é o ponto de troca, e o índice é
regenerável a partir de `data/processed/`.

**Consequências.** Testes e evals rodam sem infra externa; perde-se SQL/joins sobre os
vetores (irrelevante no escopo atual).

---

## ADR-002 🌙 — Embeddings: BGE-m3 local, com fallback documentado

**Contexto.** Embeddings devem ser locais e multilíngues. O ambiente comporta modelo
grande (31 GB RAM, 20 cores). O `paraphrase-multilingual-mpnet-base-v2` sugerido no brief
tem `max_seq_length=128` tokens — **trunca chunks de artigo inteiro**, que é justamente a
unidade do nosso chunking.

**Decisão.** `BAAI/bge-m3` (multilíngue, janela longa, forte em PT) como padrão.
Fallback em cascata se download/RAM falhar: `intfloat/multilingual-e5-base` (512 tokens) →
`paraphrase-multilingual-MiniLM-L12-v2`. O modelo efetivamente usado fica registrado nos
resultados das evals.

**Alternativas.** mpnet multilíngue (descartado pela janela de 128); API de embeddings
paga (viola o orçamento e a premissa de embeddings locais).

**Consequências.** Encoding inicial mais lento (CPU), mitigado por cache de embeddings;
qualidade de recuperação em PT tende a ser melhor — a eval comparativa mede.

---

## ADR-003 🌙 — Reranker: cross-encoder multilíngue mMARCO

**Contexto.** RF-03 exige reranking local; o corpus é PT-BR. Os cross-encoders
`ms-marco-*` clássicos são treinados em inglês.

**Decisão.** `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (treinado no mMARCO,
multilíngue com PT). Roda em CPU sobre top-20 candidatos.

**Alternativas.** `bge-reranker-v2-m3` (mais forte, ~2 GB — upgrade futuro se a eval
mostrar ganho insuficiente); sem rerank (vira só uma linha da tabela comparativa).

---

## ADR-004 — Python 3.12 via uv (sistema tem 3.14)

**Contexto.** O brief fixa Python 3.12; o WSL tem 3.14.4 como sistema e não há 3.12.

**Decisão.** `uv` instala CPython 3.12.13 e gerencia o venv; `uv.lock` versionado para
reprodutibilidade. (O projeto 1 declarou "3.12 alvo / validado em 3.14"; aqui pinamos o
alvo exato.)

---

## ADR-005 🌙 — Aquisição do corpus por espelhos públicos + manifesto com SHA-256

**Contexto.** Evidência da sondagem desta noite: `www.in.gov.br`, `planalto.gov.br`,
`lexml.gov.br` e `sistemasweb.agricultura.gov.br` estão **inalcançáveis desta rede**
(conexão morre mesmo resolvendo IP via DNS-over-HTTPS — bloqueio de rota, não DNS;
mesmo padrão já conhecido de `api.github.com` neste WSL). `www.gov.br` responde com
User-Agent de navegador; Embrapa (infoteca/ainfo) e espelho UFPel/inspleite respondem.

**Decisão.** `scripts/baixar_documentos.py` tenta, por documento, uma lista ordenada de
URLs candidatas (oficial primeiro, espelhos institucionais depois), usa User-Agent de
navegador, **valida o conteúdo baixado** (âncoras textuais, ex.: "INSTRUÇÃO NORMATIVA
Nº 76" + "Art. 1º") e grava `data/manifesto.json` com URL vencedora, SHA-256, data e
tamanho. Falhou tudo → registra e segue (mínimo 2 documentos).

**Consequências.** Reprodutível e auditável (hash), resiliente à rede; espelho pode
divergir do DOU — mitigado pela âncora textual e registrado como caveat honesto.

---

## ADR-006 🌙 — Versionamento de dados: legislação processada sim, Embrapa não

**Contexto.** Reprodutibilidade pede dados no repo; direitos autorais pedem cuidado.

**Decisão.** `data/raw/` e `data/processed/` nunca são versionados. O JSONL processado
mistura legislação (domínio público — art. 8º, I, Lei 9.610/1998) com material Embrapa
(protegido); separar os dois só para versionar metade não compensa — o repo guarda o
**manifesto** (URLs + SHA-256) e os scripts reproduzem o restante em ~1 min.
*(Revisado durante a Fase 1: a redação original previa versionar a parte de legislação.)*

---

## ADR-007 — Chunking estrutural por artigo, com subdivisão controlada

**Contexto.** RF-01. A unidade natural de citação em norma é o **artigo** (com caput,
parágrafos e incisos); anexos trazem tabelas de limites (críticas no domínio).

**Decisão.** Parser de estrutura legislativa BR (CAPÍTULO/Seção/Art./§/inciso/ANEXO).
1 artigo = 1 chunk; artigos longos são subdivididos com sub-rótulo (`art. 12 — parte
2/3`) herdando metadados; anexos viram chunks próprios com tabelas achatadas em texto
"Parâmetro: valor". Manuais (Embrapa) usam hierarquia de seções. O texto cru é sempre
preservado junto ao chunk.

**Alternativas.** Janela fixa com overlap (descartada: quebra artigo no meio e produz
citação imprecisa — exatamente o que o projeto quer evitar).

---

## ADR-008 — Fusão híbrida: Reciprocal Rank Fusion com k=60

**Decisão.** RRF clássico (`score = Σ 1/(60+rank)`) sobre os rankings BM25 e denso.
k=60 é o valor canônico do paper original; fica como constante nomeada e a eval
comparativa pode varrê-lo depois. Determinístico e testável sem modelo (RF-02).

---

## ADR-009 — Modo demo/real por injeção de dependência

**Contexto.** Orçamento da noite é US$ 0,00 em geração paga, mas o grafo inteiro precisa
rodar e ser testável.

**Decisão.** Os nós que usariam LLM (`grade_chunks`, `generate`, `reformular_query`,
classificação de domínio) recebem implementações injetáveis: **demo** = determinística
local (gerador extrativo que monta resposta citada a partir dos chunks; grading por
cross-encoder local + heurística; reformulação por dicionário de sinônimos do domínio);
**real** = Haiku via SDK Anthropic, atrás de guard de custo (`RAG_PERMITIR_CUSTO=1`
obrigatório + teto configurável). O verificador de groundedness é **código real nos dois
modos** (não mock): parsing de citações + cobertura/sobreposição contra os chunks.

**Consequências.** Testes e evals grátis exercitam o grafo de verdade; a qualidade de
*geração* do modo demo não representa o modo real (caveat documentado) — faithfulness do
modo real é medida nas evals pagas (amanhã).

---

## ADR-010 — Ingestão incremental: upsert por doc_id + rebuild do BM25 em memória

**Contexto.** RF-08 exige adicionar documento sem reindexar tudo. Embeddings são o custo
dominante; o BM25 é barato.

**Decisão.** Upsert no Chroma por `doc_id` (delete+add dos chunks do documento);
embeddings dos demais documentos não são recalculados (cache por hash do chunk). O índice
BM25 (`rank-bm25`) é reconstruído em memória a partir do corpus JSONL — O(corpus), milissegundos
nesta escala.

**Consequências.** Honesto sobre o limite: "incremental" refere-se a embeddings (o custo
real); BM25 rebuild documentado. Em corpus muito maior, trocar por índice léxico
persistente (evolução).

---

## ADR-011 — Unidade de acerto nas evals de retrieval: o artigo

**Contexto.** Um artigo pode virar vários chunks (subdivisão); medir acerto por chunk
penalizaria injustamente.

**Decisão.** Item do golden set declara `(doc_id, artigo)` esperado(s); um resultado
conta como acerto se qualquer chunk recuperado pertence a um par esperado. MRR usa a
primeira posição em que isso ocorre.

---

## ADR-012 🌙 — Evals pagas: implementação própria em vez de Ragas

**Contexto.** O brief permite "Ragas ou implementação própria" para faithfulness e
answer relevancy.

**Decisão.** Implementação própria: juiz Haiku com prompt por sentença (faithfulness) e
por par pergunta-resposta (relevancy), saída estruturada.

**Justificativa.** (a) o guard de custo precisa contar e limitar **cada** chamada — mais
simples quando o loop é nosso; (b) menos uma dependência pesada (Ragas puxa langchain +
datasets); (c) métrica auditável linha a linha no portfólio — dá para explicar exatamente
o que o número significa.

**Consequências.** Perde-se comparabilidade direta com papers que citam Ragas; mitigado
documentando a definição exata de cada métrica no RESULTS das evals pagas.
