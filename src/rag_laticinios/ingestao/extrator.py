"""Extração de texto estruturado das fontes brutas (DOU, Planalto, PDF).

Saída comum: lista de `Bloco` na ordem do documento. O chunker (chunker.py) é quem
agrupa blocos em chunks — este módulo só extrai e limpa.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class Bloco:
    texto: str
    pagina: int | None = None  # só para PDF
    eh_tabela: bool = False


_RE_ESPACOS = re.compile(r"\s+")


def _limpar(texto: str) -> str:
    """Colapsa TODO whitespace interno (o HTML do Planalto quebra linha dentro de <p>,
    gerando o mesmo artigo com grafias diferentes — achado da sessão 2026-06-11)."""
    return _RE_ESPACOS.sub(" ", texto).strip()


def decodificar_html(conteudo: bytes) -> str:
    """UTF-8 estrito primeiro; Planalto usa windows-1252 (achado da sessão 2026-06-11).
    iso-8859-1 fecha a cascata porque decodifica qualquer byte (nunca falha)."""
    for enc in ("utf-8", "windows-1252"):
        try:
            return conteudo.decode(enc)
        except UnicodeDecodeError:
            continue
    return conteudo.decode("iso-8859-1")


def _tabela_para_texto(tabela) -> str:
    """Achata <table> em linhas 'cel | cel | cel' — preserva os limites numéricos dos anexos."""
    linhas = []
    for tr in tabela.find_all("tr"):
        celulas = [_limpar(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
        celulas = [c for c in celulas if c]
        if celulas:
            linhas.append(" | ".join(celulas))
    return "\n".join(linhas)  # tabela é o único lugar onde \n interno sobrevive (linhas)


def extrair_dou(conteudo: bytes) -> list[Bloco]:
    """Página de matéria do DOU (in.gov.br): conteúdo em div.texto-dou."""
    soup = BeautifulSoup(decodificar_html(conteudo), "lxml")
    raiz = soup.select_one("div.texto-dou") or soup
    blocos: list[Bloco] = []
    for el in raiz.find_all(["p", "table"]):
        if el.name == "table":
            txt = _tabela_para_texto(el)
            if txt:
                blocos.append(Bloco(texto=txt, eh_tabela=True))
            continue
        if el.find_parent("table") is not None:
            continue  # células já cobertas pela tabela
        txt = _limpar(el.get_text(" ", strip=True))
        if txt:
            blocos.append(Bloco(texto=txt))
    return blocos


def extrair_planalto(conteudo: bytes) -> list[Bloco]:
    """Página do Planalto: HTML legado; texto revogado vem em <strike>/<s> e é removido."""
    soup = BeautifulSoup(decodificar_html(conteudo), "lxml")
    for morto in soup.find_all(["strike", "s", "del"]):
        morto.decompose()
    # O Planalto também marca redação revogada com estilo inline (achado 2026-06-11):
    # <span style="... text-decoration:line-through">Art. 11. (texto antigo)</span>
    for morto in soup.find_all(style=lambda s: s and "line-through" in s):
        morto.decompose()
    blocos: list[Bloco] = []
    for el in soup.find_all(["p", "table"]):
        if el.name == "table":
            txt = _tabela_para_texto(el)
            if txt:
                blocos.append(Bloco(texto=txt, eh_tabela=True))
            continue
        if el.find_parent("table") is not None:
            continue
        txt = _limpar(el.get_text(" ", strip=True))
        if txt:
            blocos.append(Bloco(texto=txt))
    return blocos


def extrair_pdf(conteudo: bytes) -> list[Bloco]:
    """PDF com camada de texto: um bloco por página não vazia."""
    from io import BytesIO

    from pypdf import PdfReader

    reader = PdfReader(BytesIO(conteudo))
    blocos: list[Bloco] = []
    for i, page in enumerate(reader.pages, start=1):
        txt = _limpar((page.extract_text() or "").strip())
        if txt:
            blocos.append(Bloco(texto=txt, pagina=i))
    return blocos


EXTRATORES = {
    "dou": extrair_dou,
    "planalto": extrair_planalto,
    "pdf": extrair_pdf,
}


def extrair(conteudo: bytes, fonte: str) -> list[Bloco]:
    if fonte not in EXTRATORES:
        raise ValueError(f"fonte desconhecida: {fonte!r} (use {sorted(EXTRATORES)})")
    return EXTRATORES[fonte](conteudo)
