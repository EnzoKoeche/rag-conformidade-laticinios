"""TEST-CHUNK: chunking estrutural (RF-01) — alvo: 100% de cobertura do chunker."""

import pytest

from rag_laticinios.ingestao.chunker import (
    Chunk,
    chunk_documento,
    chunk_legislacao,
    chunk_manual,
    normalizar_artigo,
    rotulo_curto,
    _dividir_em_partes,
)
from rag_laticinios.ingestao.extrator import Bloco


def B(texto, pagina=None, eh_tabela=False):
    return Bloco(texto=texto, pagina=pagina, eh_tabela=eh_tabela)


# ---------- unidades puras ----------

def test_rotulo_curto_mapeado_e_fallback():
    assert rotulo_curto("in-76-2018") == "IN 76/2018"
    assert rotulo_curto("riispoa-2017").startswith("RIISPOA")
    assert rotulo_curto("embrapa-ordenha-manual") == "Embrapa Ordenha Manual"


def test_normalizar_artigo():
    assert normalizar_artigo("7", "º") == "art. 7º"
    assert normalizar_artigo("27", None) == "art. 27"
    assert normalizar_artigo("10", "-A") == "art. 10-A"


def test_dividir_em_partes():
    assert _dividir_em_partes(["aa", "bb"], max_chars=100) == ["aa\nbb"]
    assert _dividir_em_partes(["aa", "bb"], max_chars=4) == ["aa", "bb"]
    # parágrafo único maior que o limite fica sozinho (não é quebrado no meio)
    assert _dividir_em_partes(["x" * 50], max_chars=10) == ["x" * 50]
    assert _dividir_em_partes([], max_chars=10) == []


# ---------- legislação ----------

BLOCOS_NORMA = [
    B("INSTRUÇÃO NORMATIVA Nº 99, DE 1º DE JANEIRO DE 2026 — o preâmbulo da norma de teste"),
    B("CAPÍTULO I"),
    B("REGULAMENTO TÉCNICO DA QUALIDADE DO LEITE DE TESTE"),
    B("Art. 1º Fica aprovado o regulamento de teste."),
    B("§ 1º Primeiro parágrafo do artigo."),
    B("I - inciso um;"),
    B("Seção I"),
    B("Da Temperatura"),
    B("Art. 2º A temperatura máxima é de 4,0 °C."),
    B("TÍTULO II"),
    B("DAS DISPOSIÇÕES FINAIS"),
    B("Art. 3º Esta norma entra em vigor na data de sua publicação."),
    B("ANEXO ÚNICO"),
    B("PARÂMETRO | LIMITE\nCCS | 500.000", eh_tabela=True),
]


def test_legislacao_estrutura_completa():
    chunks = chunk_legislacao(BLOCOS_NORMA, doc_id="in-76-2018", doc_titulo="IN teste")
    por_unidade = {c.chunk_id: c for c in chunks}

    pre = por_unidade["in-76-2018:preâmbulo"]
    assert "INSTRUÇÃO NORMATIVA Nº 99" in pre.texto and pre.artigo is None

    a1 = por_unidade["in-76-2018:art._1º"]
    assert a1.artigo == "art. 1º"
    assert "§ 1º" in a1.texto and "inciso um" in a1.texto  # caput+parágrafos+incisos juntos
    assert a1.capitulo == "CAPÍTULO I — REGULAMENTO TÉCNICO DA QUALIDADE DO LEITE DE TESTE"
    assert a1.rotulo == "IN 76/2018, art. 1º"

    a2 = por_unidade["in-76-2018:art._2º"]
    assert a2.secao == "Seção I — Da Temperatura"

    a3 = por_unidade["in-76-2018:art._3º"]
    assert a3.secao is None and a3.capitulo is None  # TÍTULO II resetou capítulo/seção

    anexo = por_unidade["in-76-2018:anexo_único"]
    assert anexo.eh_tabela and "500.000" in anexo.texto and anexo.artigo is None


def test_legislacao_anotacao_solta_e_intersticial():
    blocos = [
        B("Art. 1º Texto original."),
        B("Seção II"),
        B("(Revogado pelo Decreto nº 10.468, de 2020)"),  # anotação solta: vira contexto, não chunk
        B("Art. 2º Outro artigo."),
        B("(Redação dada pelo Decreto nº 10.468, de 2020)"),  # dentro de artigo: preservada
    ]
    chunks = chunk_legislacao(blocos, doc_id="d", doc_titulo="t")
    ids = [c.chunk_id for c in chunks]
    assert ids == ["d:art._1º", "d:art._2º"]
    assert "(Redação dada" in chunks[1].texto


def test_legislacao_intersticial_longo_vira_intro_e_curto_e_descartado():
    blocos = [
        B("Art. 1º Abre."),
        B("CAPÍTULO II"),
        B("DOS TESTES"),
        B("Texto intersticial longo o bastante para sobreviver ao filtro de tamanho mínimo, com contexto."),
        B("Art. 2º Fecha."),
        B("TÍTULO IX"),
        B("resto curto"),  # vira descrição do título (aguardando_desc), não chunk
    ]
    chunks = chunk_legislacao(blocos, doc_id="d", doc_titulo="t")
    intro = [c for c in chunks if c.chunk_id.startswith("d:intro_—_")]
    assert len(intro) == 1 and intro[0].texto.startswith("Texto intersticial")
    assert all("resto curto" not in c.texto for c in chunks)


def test_legislacao_artigo_em_anexo_cita_anexo_no_rotulo():
    blocos = [
        B("ANEXO I"),
        B("Art. 1º Norma do anexo com numeração própria."),
    ]
    chunks = chunk_legislacao(blocos, doc_id="in-77-2018", doc_titulo="t")
    art = [c for c in chunks if c.artigo][0]
    assert art.rotulo == "IN 77/2018, anexo i, art. 1º"
    assert art.anexo == "ANEXO I"


def test_legislacao_tabela_apos_capitulo_nao_vira_descricao():
    blocos = [
        B("CAPÍTULO I"),
        B("A | B", eh_tabela=True),
        B("mais conteúdo da tabela em contexto suficiente para passar do filtro de sessenta chars."),
    ]
    chunks = chunk_legislacao(blocos, doc_id="d", doc_titulo="t")
    assert len(chunks) == 1 and chunks[0].eh_tabela


def test_legislacao_artigo_longo_subdividido():
    paragrafos = [B("Art. 4º Caput.")] + [B(f"§ {i}º " + "x" * 90) for i in range(1, 8)]
    chunks = chunk_legislacao(list(paragrafos), doc_id="d", doc_titulo="t", max_chars=200)
    partes = [c for c in chunks if c.artigo == "art. 4º"]
    assert len(partes) > 1
    assert partes[0].parte == 1 and partes[0].n_partes == len(partes)
    assert "(parte 1/" in partes[0].rotulo
    assert partes[0].chunk_id == "d:art._4º:1"


# ---------- manual ----------

def test_manual_funde_paginas_curtas():
    blocos = [B("curto", pagina=1), B("ainda curto", pagina=2), B("agora um texto bem maior " * 12, pagina=3)]
    chunks = chunk_manual(blocos, doc_id="m", doc_titulo="t", min_chars_pagina=200)
    assert len(chunks) == 1
    assert chunks[0].rotulo.endswith("p. 1-3")
    assert chunks[0].pagina == 1


def test_manual_pagina_unica_e_resto_final():
    blocos = [B("conteúdo grande o suficiente para fechar sozinho " * 8, pagina=1), B("resto final curto", pagina=2)]
    chunks = chunk_manual(blocos, doc_id="m", doc_titulo="t", min_chars_pagina=100)
    assert len(chunks) == 2
    assert chunks[0].rotulo.endswith("p. 1")
    assert chunks[1].rotulo.endswith("p. 2")


def test_manual_vazio():
    assert chunk_manual([], doc_id="m", doc_titulo="t") == []


def test_manual_descarta_ficha_catalografica():
    blocos = [
        B("Exemplares desta publicação podem ser adquiridos na Embrapa. Caixa Postal 44 Fone: 79", pagina=1),
        B("Conteúdo técnico real sobre a ordenha higiênica com tamanho suficiente para chunk próprio aqui.", pagina=2),
    ]
    chunks = chunk_manual(blocos, doc_id="m", doc_titulo="t", min_chars_pagina=50)
    assert len(chunks) == 1
    assert chunks[0].texto.startswith("Conteúdo técnico real")


# ---------- chunk_documento ----------

def test_chunk_documento_tipo_invalido():
    with pytest.raises(ValueError, match="tipo desconhecido"):
        chunk_documento([], doc_id="d", doc_titulo="t", tipo="planilha")


def test_chunk_documento_dedup_identico_e_sufixo_para_diferentes():
    blocos = [
        B("Art. 5º Mesma redação, duplicada pelo HTML da fonte."),
        B("Art. 5º Mesma redação, duplicada pelo HTML da fonte."),
        B("Art. 5º Redação DIFERENTE (numeração reiniciada em anexo, por exemplo)."),
    ]
    chunks = chunk_documento(blocos, doc_id="d", doc_titulo="t", tipo="legislacao")
    ids = [c.chunk_id for c in chunks]
    assert ids == ["d:art._5º", "d:art._5º~1"]  # idêntico deduplicado; diferente ganha sufixo


def test_chunk_documento_roteia_manual():
    chunks = chunk_documento(
        [B("página de manual com texto suficiente para um chunk próprio aqui mesmo", pagina=1)],
        doc_id="m", doc_titulo="t", tipo="manual",
    )
    assert len(chunks) == 1 and chunks[0].tipo == "manual"


def test_chunk_dataclass_dict():
    c = Chunk(chunk_id="x", doc_id="d", doc_titulo="t", tipo="legislacao", rotulo="r", texto="txt")
    d = c.dict()
    assert d["chunk_id"] == "x" and d["eh_tabela"] is False
