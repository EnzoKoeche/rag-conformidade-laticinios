"""Tipos comuns do retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Resultado:
    chunk_id: str
    score: float
    chunk: dict
    origem: str = ""              # bm25 | densa | hibrida | hibrida_rerank
    detalhes: dict = field(default_factory=dict)
