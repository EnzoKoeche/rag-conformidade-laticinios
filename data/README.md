# data/

- `raw/` — documentos públicos baixados por `scripts/baixar_documentos.py` (**não versionado**;
  manifesto com URLs e SHA-256 em `data/manifesto.json`, este sim versionado).
- `processed/` — chunks estruturados (JSONL; **não versionado**). O arquivo mistura
  legislação (domínio público — art. 8º, I, Lei 9.610/1998) com conteúdo Embrapa
  (protegido); para não redistribuir o segundo, nada de `processed/` vai ao repo —
  `scripts/baixar_documentos.py` + `scripts/ingerir.py` reproduzem tudo a partir do
  manifesto versionado.
- `index/` — índice vetorial persistente (regenerável; não versionado).
- `cache/` — cache de embeddings (não versionado).
