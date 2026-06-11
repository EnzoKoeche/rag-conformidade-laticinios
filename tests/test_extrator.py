"""TEST-EXTRATOR: extração DOU/Planalto/PDF (RF-01)."""

import pytest

from rag_laticinios.ingestao.extrator import (
    decodificar_html,
    extrair,
    extrair_dou,
    extrair_pdf,
    extrair_planalto,
)


def test_decodificar_utf8_e_windows1252():
    assert decodificar_html("café".encode("utf-8")) == "café"
    assert decodificar_html("café".encode("windows-1252")) == "café"
    # byte indefinido em windows-1252 (0x81) cai no iso-8859-1, que nunca falha
    assert decodificar_html(b"a\x81b") == "a\x81b"


def test_extrair_dou_paragrafos_tabela_e_vazios():
    html = """
    <html><body>
      <p>fora do container — ignorado</p>
      <div class="texto-dou">
        <p class="identifica">INSTRUÇÃO NORMATIVA Nº 76</p>
        <p>Art. 1º   Texto   com    espaços.</p>
        <p>   </p>
        <table><tr><th>PARÂMETRO</th><th>LIMITE</th></tr>
               <tr><td><p>CCS</p></td><td>500.000</td></tr></table>
      </div>
    </body></html>"""
    blocos = extrair_dou(html.encode("utf-8"))
    textos = [b.texto for b in blocos]
    assert "fora do container — ignorado" not in textos
    assert "Art. 1º Texto com espaços." in textos  # whitespace colapsado
    tabelas = [b for b in blocos if b.eh_tabela]
    assert len(tabelas) == 1 and "CCS | 500.000" in tabelas[0].texto
    # o <p> dentro da tabela não vira bloco próprio
    assert sum(1 for t in textos if t == "CCS") == 0


def test_extrair_dou_sem_container_usa_documento_inteiro():
    html = "<html><body><p>Art. 1º Solto.</p></body></html>"
    blocos = extrair_dou(html.encode("utf-8"))
    assert [b.texto for b in blocos] == ["Art. 1º Solto."]


def test_extrair_planalto_remove_revogados():
    html = """
    <html><body>
      <p><strike>Art. 9º Redação revogada via strike.</strike></p>
      <p><span style="color: black; text-decoration:line-through">Art. 11. Redação antiga.</span></p>
      <p>Art. 11. Redação atual. (Redação dada pelo Decreto nº 10.468, de 2020)</p>
      <table><tr><td><p>X</p></td><td>Y</td></tr></table>
    </body></html>"""
    blocos = extrair_planalto(html.encode("windows-1252"))
    textos = [b.texto for b in blocos]
    assert all("revogada via strike" not in t for t in textos)
    assert all("Redação antiga" not in t for t in textos)
    assert any(t.startswith("Art. 11. Redação atual.") for t in textos)
    assert any(b.eh_tabela and b.texto == "X | Y" for b in blocos)


def test_extrair_pdf_pagina_em_branco():
    from io import BytesIO

    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = BytesIO()
    writer.write(buf)
    assert extrair_pdf(buf.getvalue()) == []


def _pdf_minimo_com_texto(texto: str) -> bytes:
    """PDF de 1 página, escrito à mão com xref calculado — determinístico p/ teste."""
    stream = f"BT /F1 12 Tf 10 100 Td ({texto}) Tj ET".encode()
    corpos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R"
        b" /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    saida = b"%PDF-1.4\n"
    offsets = []
    for i, corpo in enumerate(corpos, start=1):
        offsets.append(len(saida))
        saida += f"{i} 0 obj\n".encode() + corpo + b"\nendobj\n"
    inicio_xref = len(saida)
    saida += f"xref\n0 {len(corpos)+1}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        saida += f"{off:010d} 00000 n \n".encode()
    saida += (
        f"trailer\n<< /Size {len(corpos)+1} /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF".encode()
    )
    return saida


def test_extrair_pdf_com_texto_e_numero_de_pagina():
    blocos = extrair_pdf(_pdf_minimo_com_texto("Ordenha pagina um"))
    assert len(blocos) == 1
    assert blocos[0].texto == "Ordenha pagina um"
    assert blocos[0].pagina == 1


def test_extrair_dispatch_e_fonte_invalida():
    assert extrair(b"<p>Oi tudo bem</p>", "dou")[0].texto == "Oi tudo bem"
    with pytest.raises(ValueError, match="fonte desconhecida"):
        extrair(b"", "docx")
