"""Reciprocal Rank Fusion (ADR-008). Função pura, testável sem modelo — alvo 100% cobertura."""

from __future__ import annotations

from rag_laticinios.config import RRF_K


def rrf(rankings: list[list[str]], k: int = RRF_K) -> list[tuple[str, float]]:
    """Funde rankings (listas ordenadas de chunk_ids) em um ranking único.

    score(id) = Σ_r 1/(k + posicao_r(id)), posição 1-indexada.
    Empate de score é desfeito de forma determinística pela ordem (posição mínima
    entre os rankings, depois ordem alfabética do id).
    """
    if k <= 0:
        raise ValueError(f"k deve ser positivo, recebi {k}")
    scores: dict[str, float] = {}
    melhor_posicao: dict[str, int] = {}
    for ranking in rankings:
        for pos, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + pos)
            melhor_posicao[chunk_id] = min(melhor_posicao.get(chunk_id, pos), pos)
    return sorted(
        scores.items(),
        key=lambda item: (-item[1], melhor_posicao[item[0]], item[0]),
    )
