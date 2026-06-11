"""Estado tipado do grafo de corrective RAG."""

from __future__ import annotations

from typing import TypedDict


class EstadoRAG(TypedDict, total=False):
    pergunta: str               # pergunta original do usuário (imutável)
    pergunta_atual: str         # pergunta efetiva da busca (muda no reformular)
    em_dominio: bool
    resultados: list[dict]      # chunks recuperados (dicts serializáveis) + score
    aprovados: list[dict]       # chunks que passaram no grade
    resposta: str
    citacoes: list[dict]        # [{rotulo, chunk_id, trecho}]
    verificacao: dict           # saída de verificar_groundedness().dict()
    ciclos: int                 # ciclos de correção já executados
    estrategia: str
    trace: list[str]            # nós/decisões percorridos (observabilidade)
    metricas: dict
