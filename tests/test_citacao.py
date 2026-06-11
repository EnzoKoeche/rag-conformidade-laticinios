"""TEST-CIT: parsing/resolução de citações e verificador de groundedness (RF-04/05)."""

from rag_laticinios.citacao import (
    Verificacao,
    parse_citacoes,
    resolver_citacao,
    suporte_lexical,
    verificar_groundedness,
)

CHUNKS = [
    {"chunk_id": "in-76-2018:art._7º", "rotulo": "IN 76/2018, art. 7º",
     "texto": "Art. 7º O leite cru refrigerado deve apresentar médias geométricas de "
              "Contagem de Células Somáticas de no máximo 500.000 CS/mL."},
    {"chunk_id": "in-77-2018:art._27", "rotulo": "IN 77/2018, art. 27",
     "texto": "Art. 27. O tempo transcorrido entre as coletas de leite nas propriedades "
              "rurais não deve ser superior a quarenta e oito horas."},
    {"chunk_id": "x", "texto": "chunk sem rótulo"},
]


def test_parse_citacoes():
    assert parse_citacoes("- afirmação [IN 76/2018, art. 7º]") == ["IN 76/2018, art. 7º"]
    assert parse_citacoes("x [A; B] y [C]") == ["A", "B", "C"]
    assert parse_citacoes("sem citação nenhuma") == []
    assert parse_citacoes("vazia [ ; ]") == []


def test_resolver_citacao():
    assert resolver_citacao("IN 76/2018, art. 7º", CHUNKS)["chunk_id"] == "in-76-2018:art._7º"
    # casamento por substring (citação mais curta que o rótulo e vice-versa)
    assert resolver_citacao("in 76/2018, ART. 7º", CHUNKS) is not None
    assert resolver_citacao("RIISPOA, art. 999", CHUNKS) is None


def test_suporte_lexical():
    linha = "- Contagem de Células Somáticas de no máximo 500.000 CS/mL [IN 76/2018, art. 7º]"
    assert suporte_lexical(linha, CHUNKS[0]["texto"]) == 1.0
    assert suporte_lexical(linha, CHUNKS[1]["texto"]) < 0.4
    # linha cujo conteúdo é só citação/stopwords não acusa alucinação
    assert suporte_lexical("de o a [X]", "qualquer") == 1.0


def test_verificacao_aprovada():
    resposta = (
        "- O leite cru refrigerado deve apresentar Contagem de Células Somáticas de no "
        "máximo 500.000 CS/mL [IN 76/2018, art. 7º]\n"
        "- O tempo entre as coletas não deve ser superior a quarenta e oito horas "
        "[IN 77/2018, art. 27]\n"
        "Fontes: IN 76/2018; IN 77/2018"
    )
    v = verificar_groundedness(resposta, CHUNKS)
    assert v.aprovado and v.cobertura == 1.0 and v.linhas_avaliadas == 2
    assert v.dict()["aprovado"] is True


def test_reprova_linha_sem_citacao():
    v = verificar_groundedness("- O limite de células somáticas é de 500.000 CS/mL", CHUNKS)
    assert not v.aprovado
    assert any("sem citação" in p for p in v.problemas)


def test_reprova_citacao_nao_resolvida():
    v = verificar_groundedness(
        "- O limite máximo é de 500.000 células por mililitro [RIISPOA, art. 999]", CHUNKS
    )
    assert not v.aprovado
    assert any("não resolve" in p for p in v.problemas)
    assert v.cobertura == 0.0


def test_reprova_alucinacao_com_citacao_valida():
    # cita um chunk real, mas afirma coisa que não está nele
    v = verificar_groundedness(
        "- A multa aplicável por descumprimento contratual é de quinhentos salários "
        "mínimos vigentes [IN 76/2018, art. 7º]",
        CHUNKS,
    )
    assert not v.aprovado
    assert any("suporte lexical insuficiente" in p for p in v.problemas)


def test_resposta_vazia_reprova():
    v = verificar_groundedness("", CHUNKS)
    assert not v.aprovado and v.linhas_avaliadas == 0
    v2 = verificar_groundedness("ok.\ncurta.", CHUNKS)  # linhas < 15 chars ignoradas
    assert not v2.aprovado


def test_dataclass_dict():
    v = Verificacao(aprovado=True, cobertura=1.0, linhas_avaliadas=2)
    assert v.dict() == {"aprovado": True, "cobertura": 1.0, "problemas": [], "linhas_avaliadas": 2}
