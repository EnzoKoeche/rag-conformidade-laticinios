# data/

- `raw/` — documentos públicos baixados por `scripts/baixar_documentos.py` (**não versionado**;
  manifesto com URLs e SHA-256 em `data/manifesto.json`, este sim versionado).
- `processed/` — chunks estruturados (JSONL). Versionamos apenas o derivado de **legislação**
  (texto de norma legal não tem proteção autoral — art. 8º, I, da Lei 9.610/1998). Conteúdo
  Embrapa não é redistribuído no repositório: obtém-se via script.
- `index/` — índice vetorial persistente (regenerável; não versionado).
- `cache/` — cache de embeddings (não versionado).
