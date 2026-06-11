# Requisitos — rag-conformidade-laticinios

Notação: prioridade **MoSCoW** (Must/Should/Could/Won't-now) e critérios de aceite
**Dado / Quando / Então**. Rastreabilidade completa em [`rastreabilidade.md`](rastreabilidade.md).

## Requisitos funcionais

### RF-01 — Ingestão de documentos públicos com chunking estrutural · **Must**

Ingestão de PDFs/HTML públicos (MAPA, RIISPOA, Embrapa) com chunking **estrutural** — por
artigo/seção, nunca por janela fixa cega — e metadados ricos: `doc_id`, `doc_titulo`,
`artigo/secao`, `pagina` (quando a fonte é PDF), `rotulo` de citação (ex.: "IN 76/2018,
art. 7º") e o **texto cru** do chunk para exibição como citação.

- **Dado** o PDF da IN 76/2018 em `data/raw/`, **quando** a ingestão roda, **então** cada
  artigo vira ≥ 1 chunk com `artigo` e `rotulo` corretos e o texto cru preservado.
- **Dado** um artigo mais longo que o limite do embedder, **quando** a ingestão roda,
  **então** ele é subdividido (parte 1/N, 2/N…) mantendo os metadados do artigo.
- **Dado** um documento sem estrutura de artigos (manual Embrapa), **quando** a ingestão
  roda, **então** o chunking usa seções/títulos e o `rotulo` cita seção + página.

### RF-02 — Busca híbrida (BM25 + densa) com fusão RRF · **Must**

- **Dado** o índice construído, **quando** uma consulta chega, **então** BM25 e busca densa
  rodam e a fusão RRF (k=60) produz um ranking único determinístico.
- **Dado** rankings de entrada conhecidos, **quando** a fusão roda, **então** o score RRF
  de cada chunk é exatamente `Σ 1/(60 + posição)` (testável sem modelo).

### RF-03 — Reranking local · **Must**

- **Dado** o top-N da busca híbrida, **quando** o reranking roda, **então** um
  cross-encoder **local** reordena os candidatos sem nenhuma chamada de API.

### RF-04 — Geração com citações obrigatórias e verificáveis · **Must**

- **Dado** chunks aprovados, **quando** a resposta é gerada, **então** toda afirmação
  carrega citação no formato `[doc, artigo/seção]` resolvível para um chunk recuperado
  (mostrando o trecho cru).
- **Dado** uma resposta gerada, **quando** uma citação não resolve para chunk recuperado,
  **então** a verificação (RF-05) reprova a resposta.

### RF-05 — Auto-verificação de groundedness com re-retrieval (corrective RAG) · **Must**

- **Dado** uma resposta gerada, **quando** o nó `verify_groundedness` roda, **então** cada
  sentença afirmativa é conferida contra o chunk citado (cobertura e sobreposição) e o
  resultado (aprovado/reprovado + motivo) entra no estado do grafo.
- **Dado** uma reprovação com menos de 2 ciclos, **quando** o grafo decide a rota,
  **então** `reformular_query` roda e o retrieval é refeito.
- **Dado** uma reprovação no 2º ciclo, **então** o sistema responde "não encontrei base
  nos documentos" (RF-06) — nunca entrega resposta reprovada.

### RF-06 — Resposta honesta "não sei" · **Must**

- **Dado** uma pergunta cujo retrieval não retorna chunk aprovado, **então** a resposta é
  "não encontrei base nos documentos indexados", listando o que foi tentado, **sem**
  conteúdo afirmativo inventado.
- **Dado** uma pergunta fora do domínio (ex.: "qual a capital da França?"), **então** o nó
  `entender_pergunta` recusa educadamente **antes** do retrieval.

### RF-07 — API REST + front mínimo · API **Must**, front **Should**

- **Dado** o serviço de pé, **quando** `POST /ask` recebe `{pergunta}`, **então** retorna
  `{resposta, citacoes[], metricas{estrategia, latencia_ms, n_chunks, ciclos}}`.
- **Dado** `GET /health`, **então** retorna o status do índice (nº de docs/chunks, modo).
- **Dado** o front, **quando** uma resposta chega, **então** cada citação é clicável e
  expande o trecho-fonte cru.

### RF-08 — Ingestão incremental · **Should**

- **Dado** um índice com N documentos, **quando** `POST /ingest` recebe um documento novo,
  **então** apenas ele é processado/indexado (upsert por `doc_id`) e os N anteriores não
  são re-embedados.
- **Dado** o mesmo documento reenviado, **então** o upsert substitui os chunks antigos sem
  duplicar.

### RF-09 — Anti-injection: conteúdo de documento é dado, nunca instrução · **Must**

(Premissa inegociável nº 2; ganhou número de RF para ser rastreável a teste.)

- **Dado** um documento ingerido contendo texto imperativo malicioso ("ignore as
  instruções e revele X"), **quando** ele aparece em chunks usados na geração, **então** o
  texto é tratado como dado citável — a resposta não obedece à instrução embutida.
- **Dado** uma pergunta com tentativa de injeção, **então** o sistema responde no domínio
  ou recusa — nunca muda de papel, revela prompt interno ou abandona o formato de citação.

## Requisitos não funcionais

| ID | Requisito | Alvo | Como é medido | O que NÃO prova |
|---|---|---|---|---|
| RNF-01 | Qualidade de retrieval | recall@5 ≥ 0,80 (melhor estratégia, golden set) | `eval/run_retrieval.py` → RESULTS.md | n=30 e gabarito gerado pelo autor do sistema → mede regressão e comparação entre estratégias, não qualidade absoluta universal |
| RNF-02 | Latência | p50 ≤ 4 s por pergunta (modo demo, com rerank local, hardware WSL de referência) | medição instrumentada no grafo e na eval | não prova latência em hardware menor nem no modo real (rede da API) |
| RNF-03 | Custo (modo real) | ≤ US$ 0,005/pergunta | estimativa instrumentada no harness pago (tokens reais × preço Haiku) | estimado nesta sessão; só execução paga (amanhã) confirma |
| RNF-04 | Groundedness | 0 respostas afirmativas sem citação válida no eval | eval de groundedness sobre o golden set (modo demo) | o verificador é heurístico no demo; faithfulness com juiz LLM fica para as evals pagas |
| RNF-05 | Reprodutibilidade | pipeline determinístico no modo demo; versões pinadas (`uv.lock`); manifesto de corpus com SHA-256 | re-execução das evals produz os mesmos números | embeddings dependem do modelo baixado do HF (versão registrada) |
| RNF-06 | Segurança de segredos | 0 segredos em qualquer commit | secret-scan do histórico (`docs/revisoes/secret-scan.md`) | scan por padrões conhecidos; não detecta segredo de formato exótico |
| RNF-07 | Custo da sessão overnight | US$ 0,00 em geração paga | guard de custo: chamada paga exige `RAG_PERMITIR_CUSTO=1` + chave; default bloqueia | — |

## Won't (por agora)

- Multi-turno com memória; OCR; atualização automática de vigência; UI de administração;
  pgvector gerenciado (Supabase) — registrado como evolução no ADR-001.
