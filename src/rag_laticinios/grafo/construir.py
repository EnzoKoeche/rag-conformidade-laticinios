"""Grafo LangGraph do corrective RAG (RF-05).

entender_pergunta ─fora──────────────► fora_dominio ─► END
        │em domínio
        ▼
     retrieve ─► grade_chunks ─sem aprovado e ciclos<MAX─► reformular ─► retrieve
                     │aprovados                │ciclos≥MAX
                     ▼                         ▼
                  generate ─► verify ─ok─► END   sem_base ─► END
                                │falha: ciclos<MAX → reformular | senão → sem_base
"""

from __future__ import annotations

import time

from langgraph.graph import END, StateGraph

from rag_laticinios import config
from rag_laticinios.citacao import parse_citacoes, resolver_citacao, verificar_groundedness
from rag_laticinios.grafo.estado import EstadoRAG

MSG_FORA_DOMINIO = (
    "Essa pergunta está fora do escopo deste assistente, que cobre conformidade e "
    "qualidade na indústria de laticínios com base nos documentos indexados "
    "(IN 76/2018, IN 77/2018, RIISPOA e manuais públicos da Embrapa)."
)


def _serializar(resultado) -> dict:
    return {
        "chunk_id": resultado.chunk_id,
        "score": float(resultado.score),
        "origem": resultado.origem,
        "chunk": resultado.chunk,
    }


def construir_grafo(retrieval, deps: dict, estrategia: str = "hibrida_rerank", k: int = config.TOP_K_CANDIDATOS):
    """`retrieval` = fachada Retrieval; `deps` = dependencias_demo() ou dependencias_real()."""

    def entender_pergunta(estado: EstadoRAG) -> dict:
        em_dominio = deps["classificador"].classificar(estado["pergunta"])
        return {
            "em_dominio": em_dominio,
            "pergunta_atual": estado["pergunta"],
            "ciclos": 0,
            "estrategia": estrategia,
            "trace": [f"entender_pergunta:{'dominio' if em_dominio else 'fora'}"],
        }

    def retrieve(estado: EstadoRAG) -> dict:
        inicio = time.perf_counter()
        resultados, met = retrieval.buscar(estado["pergunta_atual"], estrategia=estrategia, k=k)
        met["latencia_ms"] = round((time.perf_counter() - inicio) * 1000, 1)
        return {
            "resultados": [_serializar(r) for r in resultados],
            "metricas": {**estado.get("metricas", {}), f"retrieve_{estado.get('ciclos', 0)}": met},
            "trace": estado["trace"] + [f"retrieve:{len(resultados)}"],
        }

    def grade_chunks(estado: EstadoRAG) -> dict:
        # Relevância SEMPRE contra a pergunta ORIGINAL: a reformulação serve ao
        # retrieval; usá-la no grading dilui o termo sem resposta e derrota a recusa
        # honesta (achado da eval de groundedness, 2026-06-12).
        grader = deps["grader"]
        if hasattr(grader, "aprovar_lote"):
            vereditos = grader.aprovar_lote(estado["pergunta"], estado["resultados"])
        else:
            vereditos = [grader.aprovar(estado["pergunta"], r) for r in estado["resultados"]]
        aprovados = [r for r, ok in zip(estado["resultados"], vereditos) if ok]
        return {"aprovados": aprovados, "trace": estado["trace"] + [f"grade:{len(aprovados)}"]}

    def generate(estado: EstadoRAG) -> dict:
        resposta = deps["gerador"].gerar(estado["pergunta"], estado["aprovados"])
        return {"resposta": resposta, "trace": estado["trace"] + ["generate"]}

    def verify_groundedness(estado: EstadoRAG) -> dict:
        chunks = [r["chunk"] for r in estado["resultados"]]
        verificacao = verificar_groundedness(estado["resposta"], chunks)
        citacoes = []
        for linha in estado["resposta"].splitlines():
            for cit in parse_citacoes(linha):
                chunk = resolver_citacao(cit, chunks)
                if chunk and all(c["chunk_id"] != chunk["chunk_id"] for c in citacoes):
                    citacoes.append(
                        {"rotulo": chunk["rotulo"], "chunk_id": chunk["chunk_id"],
                         "trecho": chunk["texto"]}
                    )
        return {
            "verificacao": verificacao.dict(),
            "citacoes": citacoes,
            "trace": estado["trace"] + [f"verify:{'ok' if verificacao.aprovado else 'falha'}"],
        }

    def reformular(estado: EstadoRAG) -> dict:
        nova = deps["reformulador"].reformular(estado["pergunta_atual"])
        return {
            "pergunta_atual": nova,
            "ciclos": estado["ciclos"] + 1,
            "trace": estado["trace"] + [f"reformular:{estado['ciclos'] + 1}"],
        }

    def fora_dominio(estado: EstadoRAG) -> dict:
        return {"resposta": MSG_FORA_DOMINIO, "citacoes": [],
                "trace": estado["trace"] + ["fora_dominio"]}

    def sem_base(estado: EstadoRAG) -> dict:
        tentadas = estado["ciclos"] + 1
        resposta = (
            f"{config.MSG_SEM_BASE}\n\n"
            f"Foram tentadas {tentadas} formulação(ões) de busca nos documentos "
            "indexados sem encontrar trechos que sustentem uma resposta. "
            "Tente reformular com termos da norma (ex.: 'leite cru refrigerado', 'CCS')."
        )
        return {"resposta": resposta, "citacoes": [],
                "trace": estado["trace"] + ["sem_base"]}

    # ---------------- rotas condicionais (funções puras de estado, testáveis) ----------------

    def rota_apos_entender(estado: EstadoRAG) -> str:
        return "retrieve" if estado["em_dominio"] else "fora_dominio"

    def rota_apos_grade(estado: EstadoRAG) -> str:
        if estado["aprovados"]:
            return "generate"
        if estado["ciclos"] < config.MAX_CICLOS_CORRECAO:
            return "reformular"
        return "sem_base"

    def rota_apos_verify(estado: EstadoRAG) -> str:
        if estado["verificacao"]["aprovado"]:
            return "fim"
        if estado["ciclos"] < config.MAX_CICLOS_CORRECAO:
            return "reformular"
        return "sem_base"

    grafo = StateGraph(EstadoRAG)
    grafo.add_node("entender_pergunta", entender_pergunta)
    grafo.add_node("retrieve", retrieve)
    grafo.add_node("grade_chunks", grade_chunks)
    grafo.add_node("generate", generate)
    grafo.add_node("verify_groundedness", verify_groundedness)
    grafo.add_node("reformular", reformular)
    grafo.add_node("fora_dominio", fora_dominio)
    grafo.add_node("sem_base", sem_base)

    grafo.set_entry_point("entender_pergunta")
    grafo.add_conditional_edges("entender_pergunta", rota_apos_entender,
                                {"retrieve": "retrieve", "fora_dominio": "fora_dominio"})
    grafo.add_edge("retrieve", "grade_chunks")
    grafo.add_conditional_edges("grade_chunks", rota_apos_grade,
                                {"generate": "generate", "reformular": "reformular",
                                 "sem_base": "sem_base"})
    grafo.add_edge("generate", "verify_groundedness")
    grafo.add_conditional_edges("verify_groundedness", rota_apos_verify,
                                {"fim": END, "reformular": "reformular", "sem_base": "sem_base"})
    grafo.add_edge("reformular", "retrieve")
    grafo.add_edge("fora_dominio", END)
    grafo.add_edge("sem_base", END)

    app = grafo.compile()
    # rotas expostas p/ teste isolado (TEST-ROTA-*)
    app.rotas = {
        "apos_entender": rota_apos_entender,
        "apos_grade": rota_apos_grade,
        "apos_verify": rota_apos_verify,
    }
    return app


def responder(app, pergunta: str) -> dict:
    """Executa o grafo e devolve um payload pronto para a API/front."""
    inicio = time.perf_counter()
    estado = app.invoke({"pergunta": pergunta})
    total_ms = round((time.perf_counter() - inicio) * 1000, 1)
    return {
        "pergunta": pergunta,
        "resposta": estado.get("resposta", ""),
        "citacoes": estado.get("citacoes", []),
        "verificacao": estado.get("verificacao"),
        "metricas": {
            **estado.get("metricas", {}),
            "latencia_total_ms": total_ms,
            "ciclos": estado.get("ciclos", 0),
            "estrategia": estado.get("estrategia"),
            "trace": estado.get("trace", []),
        },
    }
