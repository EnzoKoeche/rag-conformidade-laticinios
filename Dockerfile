# Imagem da API (modo demo por default). Atenção: torch CPU + chromadb tornam a
# imagem grande (~2,5 GB) — aceito para demo local; otimizações ficam como evolução.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    HF_HOME=/data/hf-cache

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY scripts ./scripts
RUN uv sync --frozen --no-dev

# data/ (corpus, índice, cache de embeddings) entra por volume — ver docker-compose.yml
EXPOSE 8000
CMD ["uv", "run", "--no-dev", "uvicorn", "rag_laticinios.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
