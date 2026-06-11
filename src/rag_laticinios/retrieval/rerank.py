"""Reranking local com cross-encoder multilíngue (ADR-003) — nenhuma chamada de API."""

from __future__ import annotations

from rag_laticinios import config
from rag_laticinios.retrieval.base import Resultado


class Reranker:
    def __init__(self, nome_modelo: str | None = None):
        self.nome_modelo = nome_modelo or config.MODELO_RERANK
        self._modelo = None

    def _carregar(self):
        if self._modelo is None:
            from sentence_transformers import CrossEncoder

            self._modelo = CrossEncoder(self.nome_modelo)

    def reordenar(
        self, pergunta: str, resultados: list[Resultado], top_k: int = 10
    ) -> list[Resultado]:
        if not resultados:
            return []
        self._carregar()
        pares = [(pergunta, r.chunk["texto"]) for r in resultados]
        scores = self._modelo.predict(pares)
        reordenado = sorted(
            zip(resultados, scores), key=lambda par: (-float(par[1]), par[0].chunk_id)
        )
        saida = []
        for r, s in reordenado[:top_k]:
            saida.append(
                Resultado(
                    chunk_id=r.chunk_id,
                    score=float(s),
                    chunk=r.chunk,
                    origem="hibrida_rerank",
                    detalhes={**r.detalhes, "score_pre_rerank": r.score},
                )
            )
        return saida
