"""Citações e verificação de groundedness (RF-04/RF-05) — determinístico, alvo 100% cobertura.

Contrato de formato: a resposta é composta de LINHAS afirmativas (bullets), cada uma
terminando com ≥1 citação `[rótulo]` (ex.: `[IN 76/2018, art. 7º]`). O gerador demo
produz isso por construção; o prompt do modo real exige o mesmo formato. O verificador
é CÓDIGO REAL nos dois modos (ADR-009): nada de mock aqui.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rag_laticinios.retrieval.bm25 import tokenizar

RE_CITACAO = re.compile(r"\[([^\[\]]+)\]")
LIMIAR_SUPORTE_LEXICAL = 0.4  # fração dos termos da linha presentes no chunk citado


def _norm(texto: str) -> str:
    return " ".join(texto.lower().split())


def parse_citacoes(linha: str) -> list[str]:
    """Extrai rótulos citados numa linha; `[A; B]` vira duas citações."""
    saida: list[str] = []
    for grupo in RE_CITACAO.findall(linha):
        for parte in grupo.split(";"):
            parte = parte.strip()
            if parte:
                saida.append(parte)
    return saida


def resolver_citacao(citacao: str, chunks: list[dict]) -> dict | None:
    """Resolve um rótulo citado para um chunk RECUPERADO (citação verificável, RF-04)."""
    alvo = _norm(citacao)
    for chunk in chunks:
        rotulo = _norm(chunk.get("rotulo", ""))
        if not rotulo:
            continue
        if alvo == rotulo or alvo in rotulo or rotulo in alvo:
            return chunk
    return None


def suporte_lexical(linha: str, texto_chunk: str) -> float:
    """Fração dos termos afirmativos da linha (fora das citações) presentes no chunk."""
    sem_citacoes = RE_CITACAO.sub(" ", linha)
    termos = set(tokenizar(sem_citacoes))
    if not termos:
        return 1.0  # linha sem conteúdo lexical próprio não acusa alucinação
    chunk_tokens = set(tokenizar(texto_chunk))
    return len(termos & chunk_tokens) / len(termos)


@dataclass
class Verificacao:
    aprovado: bool
    cobertura: float                 # fração de linhas afirmativas plenamente suportadas
    problemas: list[str] = field(default_factory=list)
    linhas_avaliadas: int = 0

    def dict(self) -> dict:
        return {
            "aprovado": self.aprovado,
            "cobertura": round(self.cobertura, 3),
            "problemas": self.problemas,
            "linhas_avaliadas": self.linhas_avaliadas,
        }


def _eh_linha_afirmativa(linha: str) -> bool:
    """Ignora linhas vazias, cabeçalhos curtos e a linha de fontes."""
    limpa = linha.strip().strip("-•* ").strip()
    if len(limpa) < 15:
        return False
    if limpa.lower().startswith(("fontes:", "fonte:")):
        return False
    return True


def verificar_groundedness(
    resposta: str,
    chunks_recuperados: list[dict],
    limiar_suporte: float = LIMIAR_SUPORTE_LEXICAL,
) -> Verificacao:
    """Toda linha afirmativa precisa: (a) citar; (b) citação resolver para chunk
    recuperado; (c) ter suporte lexical no chunk citado. Reprovou → corrective RAG."""
    linhas = [ln for ln in resposta.splitlines() if _eh_linha_afirmativa(ln)]
    if not linhas:
        return Verificacao(aprovado=False, cobertura=0.0,
                           problemas=["resposta sem linhas afirmativas"], linhas_avaliadas=0)
    problemas: list[str] = []
    suportadas = 0
    for ln in linhas:
        citacoes = parse_citacoes(ln)
        if not citacoes:
            problemas.append(f"linha sem citação: {ln.strip()[:70]!r}")
            continue
        chunks_citados = []
        for cit in citacoes:
            chunk = resolver_citacao(cit, chunks_recuperados)
            if chunk is None:
                problemas.append(f"citação não resolve para chunk recuperado: {cit!r}")
            else:
                chunks_citados.append(chunk)
        if not chunks_citados:
            continue
        melhor = max(suporte_lexical(ln, c["texto"]) for c in chunks_citados)
        if melhor < limiar_suporte:
            problemas.append(
                f"suporte lexical insuficiente ({melhor:.2f} < {limiar_suporte}): "
                f"{ln.strip()[:70]!r}"
            )
            continue
        suportadas += 1
    cobertura = suportadas / len(linhas)
    return Verificacao(
        aprovado=not problemas,
        cobertura=cobertura,
        problemas=problemas,
        linhas_avaliadas=len(linhas),
    )
