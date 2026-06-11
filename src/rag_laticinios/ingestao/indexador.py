"""Indexação: raw → chunks.jsonl → embeddings (cache) → Chroma; BM25 é derivado.

RF-08 (ingestão incremental): `ingerir_doc` processa UM documento e faz upsert por
doc_id; embeddings dos demais não são recalculados (cache por hash do texto, ADR-010).
"""

from __future__ import annotations

import json
from pathlib import Path

from rag_laticinios import config
from rag_laticinios.ingestao.chunker import chunk_documento
from rag_laticinios.ingestao.extrator import extrair
from rag_laticinios.retrieval.bm25 import IndiceBM25
from rag_laticinios.retrieval.densa import BuscaDensa, Embedder, VetorStore

FONTE_POR_URL = (
    ("in.gov.br", "dou"),
    ("planalto.gov.br", "planalto"),
)


def _fonte_do_doc(entrada_manifesto: dict) -> str:
    if entrada_manifesto["formato"] == "pdf":
        return "pdf"
    referencia = entrada_manifesto.get("fonte_oficial", "") + entrada_manifesto.get("url_usada", "")
    for marcador, fonte in FONTE_POR_URL:
        if marcador in referencia:
            return fonte
    return "dou"


def carregar_manifesto() -> dict:
    return json.loads(config.MANIFESTO.read_text(encoding="utf-8"))


def chunks_do_documento(entrada: dict, raiz: Path | None = None) -> list[dict]:
    raiz = raiz or config.RAIZ
    raw = (raiz / entrada["arquivo"]).read_bytes()
    blocos = extrair(raw, _fonte_do_doc(entrada))
    chunks = chunk_documento(
        blocos,
        doc_id=entrada["doc_id"],
        doc_titulo=entrada["titulo"],
        tipo=entrada["tipo"],
    )
    return [c.dict() for c in chunks]


def carregar_chunks_jsonl() -> list[dict]:
    if not config.CHUNKS_JSONL.exists():
        return []
    with config.CHUNKS_JSONL.open(encoding="utf-8") as fh:
        return [json.loads(linha) for linha in fh if linha.strip()]


def _gravar_chunks_jsonl(chunks: list[dict]) -> None:
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    with config.CHUNKS_JSONL.open("w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")


def ingerir_doc(
    doc_id: str,
    *,
    embedder: Embedder | None = None,
    store: VetorStore | None = None,
) -> dict:
    """Ingestão incremental de UM documento já presente no manifesto."""
    manifesto = carregar_manifesto()
    entradas = {d["doc_id"]: d for d in manifesto["documentos"] if d["status"] == "ok"}
    if doc_id not in entradas:
        raise ValueError(f"doc_id {doc_id!r} não está no manifesto com status ok")
    embedder = embedder or Embedder()
    store = store or VetorStore()

    novos = chunks_do_documento(entradas[doc_id])
    embeddings = embedder.embutir([c["texto"] for c in novos], tipo="passage")
    store.upsert_doc(doc_id, novos, embeddings)

    # atualiza o JSONL (fonte da verdade p/ BM25 e citações)
    demais = [c for c in carregar_chunks_jsonl() if c["doc_id"] != doc_id]
    _gravar_chunks_jsonl(demais + novos)
    return {"doc_id": doc_id, "chunks": len(novos), "modelo_embedding": embedder.nome_modelo}


def ingerir_tudo(
    *, embedder: Embedder | None = None, store: VetorStore | None = None
) -> list[dict]:
    embedder = embedder or Embedder()
    store = store or VetorStore()
    manifesto = carregar_manifesto()
    relatorios = []
    for entrada in manifesto["documentos"]:
        if entrada["status"] != "ok":
            continue
        relatorios.append(ingerir_doc(entrada["doc_id"], embedder=embedder, store=store))
    return relatorios


def montar_retrieval(embedder: Embedder | None = None, store: VetorStore | None = None):
    """Constrói a fachada Retrieval a partir do estado persistido."""
    from rag_laticinios.retrieval.estrategias import Retrieval

    chunks = carregar_chunks_jsonl()
    if not chunks:
        raise RuntimeError("índice vazio — rode scripts/ingerir.py primeiro")
    embedder = embedder or Embedder()
    store = store or VetorStore()
    return Retrieval(IndiceBM25(chunks), BuscaDensa(embedder, store))
