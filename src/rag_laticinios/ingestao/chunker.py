"""Chunking estrutural (ADR-007): 1 artigo = 1 chunk, com contexto hierárquico.

Módulo determinístico e puro — alvo de cobertura: 100%.

Regras:
- Norma legal: chunks por artigo (caput + parágrafos + incisos), preâmbulo e anexos
  como chunks próprios; cabeçalhos (TÍTULO/CAPÍTULO/Seção/ANEXO) viram contexto, não chunk.
- Artigo longo é subdividido em partes no limite de parágrafo, herdando metadados.
- Manual (PDF): chunk por página, fundindo páginas curtas na seguinte.
- O texto CRU do chunk é preservado para exibição como citação (RF-01).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from rag_laticinios.ingestao.extrator import Bloco

MAX_CHARS_CHUNK = 4000   # bge-m3 aceita bem mais; limite p/ rerank e exibição
MIN_CHARS_PAGINA = 200   # páginas de manual menores que isso fundem com a seguinte

RE_ARTIGO = re.compile(r"^Art\.?\s*(\d+)\s*([ºo°.]|-[A-Z])?", re.IGNORECASE)
RE_TITULO = re.compile(r"^T[ÍI]TULO\s+[IVXLC\d]+", re.IGNORECASE)
RE_CAPITULO = re.compile(r"^CAP[ÍI]TULO\s+[IVXLC\d]+", re.IGNORECASE)
RE_SECAO = re.compile(r"^Se[çc][ãa]o\s+[IVXLC\d]+", re.IGNORECASE)
RE_ANEXO = re.compile(r"^ANEXO(\s+[IVXLC\d]+|\s+ÚNICO)?\b", re.IGNORECASE)
RE_PARAGRAFO_LEGAL = re.compile(r"^(§|Parágrafo único|[IVXLC]+\s*[-–—]|[a-z]\))")
RE_ANOTACAO_SOLTA = re.compile(r"^\((Revogad|Redação dada|Incluíd|Vide)[^)]*\)\s*$", re.IGNORECASE)
MIN_CHARS_CHUNK_NAO_ARTIGO = 60  # descarta restos (assinaturas, marcas soltas) fora de artigo

# Ficha catalográfica/créditos de publicações (Embrapa): ≥2 marcadores → não é conteúdo
MARCADORES_CREDITOS = (
    "ISBN", "CGPE", "Tiragem", "Exemplares desta publicação", "Caixa Postal",
    "Fone:", "Impressão e acabamento", "Revisão de texto", "Diagramação",
)


def _eh_pagina_de_creditos(texto: str) -> bool:
    return sum(1 for m in MARCADORES_CREDITOS if m in texto) >= 2

def _eh_nome_de_header(t: str, eh_tabela: bool) -> bool:
    """Linha curta logo após TÍTULO/CAPÍTULO/Seção = nome do agrupador, não conteúdo."""
    return (
        not eh_tabela
        and len(t) < 120
        and not RE_ARTIGO.match(t)
        and not RE_PARAGRAFO_LEGAL.match(t)
        and not RE_ANOTACAO_SOLTA.match(t)
    )


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    doc_titulo: str
    tipo: str               # legislacao | manual
    rotulo: str             # ex.: "IN 76/2018, art. 7º" — usado na citação
    texto: str              # texto CRU
    artigo: str | None = None     # ex.: "art. 7º"
    anexo: str | None = None
    capitulo: str | None = None
    secao: str | None = None
    pagina: int | None = None
    parte: int | None = None
    n_partes: int | None = None
    eh_tabela: bool = False

    def dict(self) -> dict:
        return asdict(self)


@dataclass
class _Contexto:
    titulo: str | None = None
    capitulo: str | None = None
    capitulo_desc: str | None = None
    secao: str | None = None
    anexo: str | None = None


def rotulo_curto(doc_id: str) -> str:
    """doc_id → rótulo humano de citação."""
    mapa = {
        "in-76-2018": "IN 76/2018",
        "in-77-2018": "IN 77/2018",
        "riispoa-2017": "RIISPOA (Dec. 9.013/2017)",
    }
    if doc_id in mapa:
        return mapa[doc_id]
    return doc_id.replace("-", " ").title()


def normalizar_artigo(numero: str, sufixo: str | None) -> str:
    suf = ""
    if sufixo and sufixo.startswith("-"):
        suf = sufixo  # artigos tipo "Art. 10-A"
    return f"art. {numero}º{suf}" if int(numero) < 10 else f"art. {numero}{suf}"


def _dividir_em_partes(paragrafos: list[str], max_chars: int) -> list[str]:
    """Agrupa parágrafos em partes ≤ max_chars (1 parágrafo gigante fica sozinho)."""
    partes: list[str] = []
    atual: list[str] = []
    tamanho = 0
    for p in paragrafos:
        if atual and tamanho + len(p) + 1 > max_chars:
            partes.append("\n".join(atual))
            atual, tamanho = [], 0
        atual.append(p)
        tamanho += len(p) + 1
    if atual:
        partes.append("\n".join(atual))
    return partes


def _emitir(
    chunks: list[Chunk],
    *,
    doc_id: str,
    doc_titulo: str,
    tipo: str,
    unidade: str,            # "art. 7º" | "anexo único" | "preâmbulo"
    eh_artigo: bool,
    paragrafos: list[str],
    ctx: _Contexto,
    pagina: int | None = None,
    eh_tabela: bool = False,
    max_chars: int = MAX_CHARS_CHUNK,
) -> None:
    if not paragrafos:
        return
    partes = _dividir_em_partes(paragrafos, max_chars)
    base_rotulo = f"{rotulo_curto(doc_id)}, {unidade}"
    if ctx.anexo and eh_artigo:
        base_rotulo = f"{rotulo_curto(doc_id)}, {ctx.anexo.lower()}, {unidade}"
    for i, texto in enumerate(partes, start=1):
        sufixo_id = f":{i}" if len(partes) > 1 else ""
        rotulo = base_rotulo + (f" (parte {i}/{len(partes)})" if len(partes) > 1 else "")
        chunks.append(
            Chunk(
                chunk_id=f"{doc_id}:{unidade.replace(' ', '_')}{sufixo_id}",
                doc_id=doc_id,
                doc_titulo=doc_titulo,
                tipo=tipo,
                rotulo=rotulo,
                texto=texto,
                artigo=unidade if eh_artigo else None,
                anexo=ctx.anexo,
                capitulo=ctx.capitulo_desc or ctx.capitulo,
                secao=ctx.secao,
                pagina=pagina,
                parte=i if len(partes) > 1 else None,
                n_partes=len(partes) if len(partes) > 1 else None,
                eh_tabela=eh_tabela,
            )
        )


def chunk_legislacao(
    blocos: list[Bloco],
    *,
    doc_id: str,
    doc_titulo: str,
    max_chars: int = MAX_CHARS_CHUNK,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    ctx = _Contexto()
    unidade_atual: str | None = None   # None = preâmbulo/intersticial
    eh_artigo_atual = False
    acumulado: list[str] = []
    contem_tabela = False
    aguardando_desc: str | None = None  # header recém-aberto aguarda a linha com seu nome
    houve_emissao = False

    def _unidade_intersticial() -> str:
        ancora = ctx.secao or ctx.capitulo_desc or ctx.capitulo or ctx.titulo
        if not houve_emissao or not ancora:
            return "preâmbulo"
        return f"intro — {ancora.lower()[:50]}"

    def fechar() -> None:
        nonlocal acumulado, contem_tabela, houve_emissao
        antes = len(chunks)
        _emitir(
            chunks,
            doc_id=doc_id, doc_titulo=doc_titulo, tipo="legislacao",
            unidade=unidade_atual or _unidade_intersticial(),
            eh_artigo=eh_artigo_atual,
            paragrafos=acumulado, ctx=ctx,
            eh_tabela=contem_tabela, max_chars=max_chars,
        )
        if len(chunks) > antes:
            houve_emissao = True
        acumulado, contem_tabela = [], False

    for bloco in blocos:
        t = bloco.texto
        m_art = RE_ARTIGO.match(t)
        if m_art:
            fechar()
            unidade_atual = normalizar_artigo(m_art.group(1), m_art.group(2))
            eh_artigo_atual = True
            aguardando_desc = None
            acumulado.append(t)
            continue
        if RE_ANEXO.match(t):
            fechar()
            ctx.anexo = t[:60].strip()
            ctx.secao = None
            unidade_atual = ctx.anexo.lower()
            eh_artigo_atual = False
            aguardando_desc = None
            continue
        if RE_TITULO.match(t):
            fechar()
            ctx.titulo, ctx.capitulo, ctx.capitulo_desc, ctx.secao = t, None, None, None
            unidade_atual, eh_artigo_atual, aguardando_desc = None, False, "titulo"
            continue
        if RE_CAPITULO.match(t):
            fechar()
            ctx.capitulo, ctx.capitulo_desc, ctx.secao = t, None, None
            unidade_atual, eh_artigo_atual, aguardando_desc = None, False, "capitulo"
            continue
        if RE_SECAO.match(t):
            fechar()
            ctx.secao = t
            unidade_atual, eh_artigo_atual, aguardando_desc = None, False, "secao"
            continue
        if aguardando_desc and _eh_nome_de_header(t, bloco.eh_tabela):
            if aguardando_desc == "titulo":
                ctx.titulo = f"{ctx.titulo} — {t[:90]}"
            elif aguardando_desc == "capitulo":
                ctx.capitulo_desc = f"{ctx.capitulo} — {t[:90]}"
            else:
                ctx.secao = f"{ctx.secao} — {t[:90]}"
            aguardando_desc = None
            continue
        aguardando_desc = None
        if unidade_atual is None and RE_ANOTACAO_SOLTA.match(t):
            continue  # "(Revogado pelo Decreto X)" solto entre headers: contexto, não conteúdo
        if bloco.eh_tabela:
            contem_tabela = True
        acumulado.append(t)

    fechar()
    # Restos intersticiais minúsculos (assinaturas, fechos) não viram chunk
    return [
        c for c in chunks
        if c.artigo or c.eh_tabela or len(c.texto) >= MIN_CHARS_CHUNK_NAO_ARTIGO
    ]


def chunk_manual(
    blocos: list[Bloco],
    *,
    doc_id: str,
    doc_titulo: str,
    max_chars: int = MAX_CHARS_CHUNK,
    min_chars_pagina: int = MIN_CHARS_PAGINA,
) -> list[Chunk]:
    """Manuais (PDF): chunk por página; páginas curtas fundem com a seguinte."""
    chunks: list[Chunk] = []
    ctx = _Contexto()
    pendente: list[str] = []
    pagina_inicio: int | None = None

    def fechar(pagina_fim: int | None) -> None:
        nonlocal pendente, pagina_inicio
        if not pendente:
            return
        if pagina_fim is not None and pagina_inicio is not None and pagina_fim != pagina_inicio:
            unidade = f"p. {pagina_inicio}-{pagina_fim}"
        else:
            unidade = f"p. {pagina_inicio}"
        _emitir(
            chunks,
            doc_id=doc_id, doc_titulo=doc_titulo, tipo="manual",
            unidade=unidade, eh_artigo=False,
            paragrafos=pendente, ctx=ctx,
            pagina=pagina_inicio, max_chars=max_chars,
        )
        pendente, pagina_inicio = [], None

    ultima_pagina: int | None = None
    for bloco in blocos:
        if pagina_inicio is None:
            pagina_inicio = bloco.pagina
        pendente.append(bloco.texto)
        ultima_pagina = bloco.pagina
        if sum(len(p) for p in pendente) >= min_chars_pagina:
            fechar(bloco.pagina)
    fechar(ultima_pagina)
    # Ficha catalográfica/créditos não viram chunk (achado da revisão da fase 1)
    return [c for c in chunks if not _eh_pagina_de_creditos(c.texto)]


def chunk_documento(
    blocos: list[Bloco], *, doc_id: str, doc_titulo: str, tipo: str,
    max_chars: int = MAX_CHARS_CHUNK,
) -> list[Chunk]:
    """Entrada única usada pelo indexador; garante chunk_ids únicos no documento."""
    if tipo == "legislacao":
        chunks = chunk_legislacao(blocos, doc_id=doc_id, doc_titulo=doc_titulo, max_chars=max_chars)
    elif tipo == "manual":
        chunks = chunk_manual(blocos, doc_id=doc_id, doc_titulo=doc_titulo, max_chars=max_chars)
    else:
        raise ValueError(f"tipo desconhecido: {tipo!r}")
    # Dedup: o HTML do Planalto traz o MESMO artigo duas vezes (grafias de whitespace
    # diferentes, já colapsadas no extrator) — mantém a primeira ocorrência idêntica.
    vistos_texto: set[tuple[str, str]] = set()
    unicos: list[Chunk] = []
    for c in chunks:
        chave = (c.chunk_id, c.texto)
        if chave in vistos_texto:
            continue
        vistos_texto.add(chave)
        unicos.append(c)
    # Colisões legítimas restantes (ex.: numeração reiniciada em anexo) ganham sufixo
    vistos: dict[str, int] = {}
    for c in unicos:
        if c.chunk_id in vistos:
            vistos[c.chunk_id] += 1
            c.chunk_id = f"{c.chunk_id}~{vistos[c.chunk_id]}"
        else:
            vistos[c.chunk_id] = 0
    return unicos
