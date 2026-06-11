"""BM25 sobre o corpus de chunks, com pré-processamento PT-BR leve e determinístico."""

from __future__ import annotations

import re
import unicodedata

from rank_bm25 import BM25Okapi

from rag_laticinios.retrieval.base import Resultado

# Stopwords mínimas PT (lista curta proposital: stemming/stopwords agressivos podem
# apagar termos de norma como "não" em "não conforme")
STOPWORDS = {
    "a", "o", "as", "os", "um", "uma", "de", "do", "da", "dos", "das", "no", "na",
    "nos", "nas", "em", "e", "ou", "para", "por", "com", "que", "se", "ao", "aos",
    "à", "às", "é", "ser", "sua", "seu", "suas", "seus", "este", "esta", "deste",
    "desta", "qual", "quais", "como", "sobre",
}

_RE_TOKEN = re.compile(r"[a-z0-9]+")


def _sem_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def tokenizar(texto: str) -> list[str]:
    """lowercase → remove acentos → tokens alfanuméricos → remove stopwords."""
    bruto = _RE_TOKEN.findall(_sem_acentos(texto.lower()))
    return [t for t in bruto if t not in {_sem_acentos(s) for s in STOPWORDS}]


class IndiceBM25:
    def __init__(self, chunks: list[dict]):
        self._chunks = list(chunks)
        self._por_id = {c["chunk_id"]: c for c in self._chunks}
        corpus_tokens = [tokenizar(c["texto"]) for c in self._chunks]
        self._bm25 = BM25Okapi(corpus_tokens)

    def __len__(self) -> int:
        return len(self._chunks)

    def buscar(self, pergunta: str, k: int = 10) -> list[Resultado]:
        tokens = tokenizar(pergunta)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        ordenado = sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:k]
        return [
            Resultado(
                chunk_id=self._chunks[i]["chunk_id"],
                score=float(scores[i]),
                chunk=self._chunks[i],
                origem="bm25",
            )
            for i in ordenado
            if scores[i] > 0.0
        ]
