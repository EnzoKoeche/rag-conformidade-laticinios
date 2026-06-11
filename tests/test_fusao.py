"""TEST-FUSAO: RRF exato, empates determinísticos, validação de k (RF-02)."""

import pytest

from rag_laticinios.retrieval.fusao import rrf


def test_score_rrf_exato():
    # a: pos 1 e 2 -> 1/61 + 1/62 ; b: pos 2 e 1 -> mesmo score (simétrico)
    resultado = rrf([["a", "b"], ["b", "a"]], k=60)
    scores = dict(resultado)
    assert scores["a"] == pytest.approx(1 / 61 + 1 / 62)
    assert scores["b"] == pytest.approx(1 / 62 + 1 / 61)


def test_empate_desfeito_por_posicao_e_id():
    # a e b com scores idênticos: ambos pos1 num ranking e pos2 no outro
    resultado = rrf([["a", "b"], ["b", "a"]], k=60)
    assert [cid for cid, _ in resultado] == ["a", "b"]  # melhor posição igual → ordem por id


def test_id_exclusivo_de_um_ranking_entra():
    resultado = rrf([["a", "c"], ["b"]], k=60)
    ids = [cid for cid, _ in resultado]
    assert set(ids) == {"a", "b", "c"}
    # a e b são pos1 (1/61); c é pos2 (1/62)
    assert ids[2] == "c"


def test_ranking_unico_preserva_ordem():
    resultado = rrf([["x", "y", "z"]])
    assert [cid for cid, _ in resultado] == ["x", "y", "z"]


def test_rankings_vazios():
    assert rrf([]) == []
    assert rrf([[], []]) == []


def test_k_invalido():
    with pytest.raises(ValueError):
        rrf([["a"]], k=0)
