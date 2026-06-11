"""API REST (RF-07): /ask, /ingest, /health.

Sobe em modo demo por default (custo zero). `criar_app()` aceita dependências
injetadas para teste; em produção monta o grafo real na primeira chamada.

Rodar: uv run uvicorn rag_laticinios.api.main:app --reload --app-dir src
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag_laticinios import config
from rag_laticinios.retrieval.estrategias import ESTRATEGIAS


class PerguntaIn(BaseModel):
    pergunta: str = Field(min_length=3, max_length=2000)
    estrategia: str = Field(default="hibrida_rerank")
    k: int = Field(default=config.TOP_K_CANDIDATOS, ge=1, le=20)


class IngestIn(BaseModel):
    doc_id: str = Field(min_length=2, max_length=120)


@lru_cache(maxsize=1)
def _infra_compartilhada():
    """Retrieval e dependências são caros (modelos locais) — UMA instância por
    processo, compartilhada entre os grafos de todas as estratégias."""
    from rag_laticinios.grafo.dependencias import dependencias_demo, dependencias_real
    from rag_laticinios.ingestao.indexador import montar_retrieval

    deps = dependencias_real() if config.RAG_MODO == "real" else dependencias_demo()
    return montar_retrieval(), deps


def _montar_grafo_real(estrategia: str, k: int):
    from rag_laticinios.grafo.construir import construir_grafo

    retrieval, deps = _infra_compartilhada()
    return construir_grafo(retrieval, deps, estrategia=estrategia, k=k)


def criar_app(fabrica_grafo=None) -> FastAPI:
    """`fabrica_grafo(estrategia, k) -> app_grafo` — injetável p/ teste."""
    fabrica = fabrica_grafo or _montar_grafo_real
    app = FastAPI(
        title="rag-conformidade-laticinios",
        description="RAG agêntico de conformidade em laticínios — toda afirmação cita a fonte. "
                    "NÃO é aconselhamento jurídico: interpretar a norma é responsabilidade humana.",
        version="0.1.0",
    )

    @lru_cache(maxsize=8)
    def _grafo(estrategia: str, k: int):
        return fabrica(estrategia, k)

    @app.post("/ask")
    def ask(corpo: PerguntaIn) -> dict:
        if corpo.estrategia not in ESTRATEGIAS:
            raise HTTPException(422, f"estrategia deve ser uma de {ESTRATEGIAS}")
        from rag_laticinios.grafo.construir import responder

        try:
            grafo = _grafo(corpo.estrategia, corpo.k)
        except RuntimeError as exc:  # índice vazio
            raise HTTPException(503, str(exc)) from exc
        return responder(grafo, corpo.pergunta)

    @app.post("/ingest")
    def ingest(corpo: IngestIn) -> dict:
        """RF-08: (re)indexa UM documento do manifesto sem reindexar o resto."""
        from rag_laticinios.ingestao.indexador import ingerir_doc

        try:
            relatorio = ingerir_doc(corpo.doc_id)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(404, str(exc)) from exc
        # corpus mudou: BM25 e grafos são reconstruídos na próxima pergunta
        _infra_compartilhada.cache_clear()
        _grafo.cache_clear()
        return relatorio

    @app.get("/health")
    def health() -> dict:
        from rag_laticinios.ingestao.indexador import carregar_chunks_jsonl

        chunks = carregar_chunks_jsonl()
        docs = sorted({c["doc_id"] for c in chunks})
        return {
            "status": "ok" if chunks else "indice_vazio",
            "modo": config.RAG_MODO,
            "n_chunks": len(chunks),
            "documentos": docs,
            "estrategias": list(ESTRATEGIAS),
        }

    return app


app = criar_app()
