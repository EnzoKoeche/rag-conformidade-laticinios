"""TEST-BM25: tokenização PT e busca lexical (RF-02)."""

from rag_laticinios.retrieval.bm25 import IndiceBM25, tokenizar


def _chunk(cid, texto):
    return {"chunk_id": cid, "texto": texto, "rotulo": cid, "doc_id": "d"}


def test_tokenizar_acentos_stopwords_e_numeros():
    tokens = tokenizar("A Contagem de Células Somáticas é 500.000 células/mL")
    assert "celulas" in tokens and "contagem" in tokens
    assert "500" in tokens and "000" in tokens
    assert "a" not in tokens and "de" not in tokens and "e" not in tokens


def test_busca_retorna_mais_relevante_primeiro():
    indice = IndiceBM25(
        [
            _chunk("c1", "A temperatura máxima de conservação do leite é 4 graus."),
            _chunk("c2", "O registro do estabelecimento é obrigatório no departamento."),
            _chunk("c3", "A ordenha deve seguir boas práticas de higiene."),
        ]
    )
    res = indice.buscar("qual a temperatura de conservação do leite?", k=2)
    assert res[0].chunk_id == "c1"
    assert res[0].origem == "bm25"
    assert len(indice) == 3


def test_busca_query_so_stopwords_retorna_vazio():
    indice = IndiceBM25([_chunk("c1", "qualquer texto")])
    assert indice.buscar("de a o é", k=5) == []


def test_busca_sem_match_score_zero_filtrado():
    indice = IndiceBM25([_chunk("c1", "ordenha higiênica do rebanho leiteiro")])
    assert indice.buscar("astronomia quasar", k=5) == []
