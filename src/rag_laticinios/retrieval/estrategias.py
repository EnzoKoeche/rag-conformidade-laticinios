"""As 4 estratégias comparáveis de retrieval (RF-02/03) com latência instrumentada."""

from __future__ import annotations

import time

from rag_laticinios import config
from rag_laticinios.retrieval.base import Resultado
from rag_laticinios.retrieval.bm25 import IndiceBM25
from rag_laticinios.retrieval.densa import BuscaDensa
from rag_laticinios.retrieval.fusao import rrf
from rag_laticinios.retrieval.rerank import Reranker

ESTRATEGIAS = ("bm25", "densa", "hibrida", "hibrida_rerank")


class Retrieval:
    """Fachada única: `buscar(pergunta, estrategia, k)` → (resultados, métricas)."""

    def __init__(self, bm25: IndiceBM25, densa: BuscaDensa, reranker: Reranker | None = None):
        self.bm25 = bm25
        self.densa = densa
        self.reranker = reranker or Reranker()

    def _hibrida(self, pergunta: str, k: int) -> list[Resultado]:
        # listas maiores que k entram na fusão para dar chance a divergências
        n = max(k, config.TOP_N_PARA_RERANK)
        r_bm25 = self.bm25.buscar(pergunta, k=n)
        r_densa = self.densa.buscar(pergunta, k=n)
        por_id = {r.chunk_id: r for r in [*r_densa, *r_bm25]}  # bm25 sobrescreve p/ ter chunk
        fundido = rrf([[r.chunk_id for r in r_bm25], [r.chunk_id for r in r_densa]])
        return [
            Resultado(
                chunk_id=cid,
                score=score,
                chunk=por_id[cid].chunk,
                origem="hibrida",
                detalhes={"rrf": score},
            )
            for cid, score in fundido[:k]
        ]

    def buscar(
        self, pergunta: str, estrategia: str = "hibrida_rerank", k: int = config.TOP_K_CANDIDATOS
    ) -> tuple[list[Resultado], dict]:
        if estrategia not in ESTRATEGIAS:
            raise ValueError(f"estratégia desconhecida: {estrategia!r} (use {ESTRATEGIAS})")
        inicio = time.perf_counter()
        if estrategia == "bm25":
            resultados = self.bm25.buscar(pergunta, k=k)
        elif estrategia == "densa":
            resultados = self.densa.buscar(pergunta, k=k)
        elif estrategia == "hibrida":
            resultados = self._hibrida(pergunta, k=k)
        else:  # hibrida_rerank
            candidatos = self._hibrida(pergunta, k=config.TOP_N_PARA_RERANK)
            resultados = self.reranker.reordenar(pergunta, candidatos, top_k=k)
        latencia_ms = (time.perf_counter() - inicio) * 1000
        return resultados, {
            "estrategia": estrategia,
            "latencia_ms": round(latencia_ms, 1),
            "n_resultados": len(resultados),
        }
