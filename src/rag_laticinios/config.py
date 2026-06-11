"""Configuração central: caminhos, constantes e leitura de ambiente."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")

DATA_RAW = RAIZ / "data" / "raw"
DATA_PROCESSED = RAIZ / "data" / "processed"
DATA_INDEX = RAIZ / "data" / "index"
DATA_CACHE = RAIZ / "data" / "cache"
MANIFESTO = RAIZ / "data" / "manifesto.json"
CHUNKS_JSONL = DATA_PROCESSED / "chunks.jsonl"
GOLDEN_JSONL = RAIZ / "eval" / "golden" / "golden.jsonl"

# Retrieval
RRF_K = 60  # constante canônica do paper de Reciprocal Rank Fusion (ADR-008)
TOP_K_CANDIDATOS = 10
TOP_N_PARA_RERANK = 20

# Modelos locais (ADR-002/003) — fallback em cascata se indisponível
MODELO_EMBEDDING = os.getenv("RAG_MODELO_EMBEDDING", "BAAI/bge-m3")
MODELOS_EMBEDDING_FALLBACK = [
    "intfloat/multilingual-e5-base",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
]
MODELO_RERANK = os.getenv("RAG_MODELO_RERANK", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")

# Grafo (corrective RAG)
MAX_CICLOS_CORRECAO = 2
MSG_SEM_BASE = "Não encontrei base nos documentos indexados para responder a essa pergunta."

# LLM pago (modo real) — guard de custo é inegociável
RAG_MODO = os.getenv("RAG_MODO", "demo")
RAG_MODELO = os.getenv("RAG_MODELO", "claude-haiku-4-5")
RAG_PERMITIR_CUSTO = os.getenv("RAG_PERMITIR_CUSTO", "0") == "1"
RAG_TETO_CUSTO_USD = float(os.getenv("RAG_TETO_CUSTO_USD", "0.50"))
RAG_MAX_TOKENS_RESPOSTA = 1024

# Preços US$/MTok (entrada, saída) — fonte: tabela de modelos Anthropic, 2026-06
PRECOS_USD_POR_MTOK: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-4-6": (3.00, 15.00),
}

# Chroma (ADR-001)
CHROMA_MODE = os.getenv("CHROMA_MODE", "embedded")
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))
COLECAO_CHUNKS = "chunks_laticinios"

UA_NAVEGADOR = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
)
