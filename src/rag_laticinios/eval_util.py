"""Utilidades compartilhadas pelas evals: golden set e casamento chunk↔fonte (ADR-011)."""

from __future__ import annotations

import json
import re

from rag_laticinios import config

CATEGORIAS_VALIDAS = {
    "limite_numerico", "definicao", "procedimento",
    "prazo_responsabilidade", "multi_doc", "sem_base",
}


def carregar_golden() -> list[dict]:
    with config.GOLDEN_JSONL.open(encoding="utf-8") as fh:
        return [json.loads(linha) for linha in fh if linha.strip()]


def chunk_casa_com_fonte(chunk: dict, fonte: dict) -> bool:
    """Unidade de acerto = artigo/página (ADR-011), robusta a subdivisão de chunks."""
    if chunk.get("doc_id") != fonte["doc"]:
        return False
    if chunk.get("artigo") == fonte["artigo"]:
        return True
    unidade = chunk["chunk_id"].split(":", 1)[1]
    alvo = fonte["artigo"].replace(" ", "_")
    return unidade == alvo or unidade.startswith(alvo + ":")


def resultado_acerta_item(chunks_recuperados: list[dict], item: dict) -> int | None:
    """Posição (1-indexada) do primeiro chunk que casa com alguma fonte esperada; None se nenhum."""
    for pos, chunk in enumerate(chunks_recuperados, start=1):
        if any(chunk_casa_com_fonte(chunk, fonte) for fonte in item["fontes_esperadas"]):
            return pos
    return None


_RE_CITACAO = re.compile(r"\[[^\]]*\]")
_RE_NUMERO = re.compile(r"\d+(?:[.,]\d+)*")


def numeros_da_resposta(resposta: str) -> list[str]:
    """Números afirmativos da resposta de referência (fora das citações [doc, art.])."""
    sem_citacoes = _RE_CITACAO.sub(" ", resposta)
    return _RE_NUMERO.findall(sem_citacoes)
