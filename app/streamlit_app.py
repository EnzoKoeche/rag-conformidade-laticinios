"""Front mínimo (RF-07): pergunta → resposta com citações clicáveis → métricas.

Rodar: uv run streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_laticinios import config  # noqa: E402
from rag_laticinios.retrieval.estrategias import ESTRATEGIAS  # noqa: E402

st.set_page_config(page_title="RAG Conformidade Laticínios", page_icon="🥛", layout="wide")


@st.cache_resource(show_spinner="Carregando índice e modelos locais…")
def carregar_infra():
    """Modelos pesados carregam UMA vez; trocar de estratégia não recarrega nada."""
    from rag_laticinios.grafo.dependencias import dependencias_demo
    from rag_laticinios.ingestao.indexador import montar_retrieval

    return montar_retrieval(), dependencias_demo()


@st.cache_resource(show_spinner=False)
def carregar_grafo(estrategia: str):
    from rag_laticinios.grafo.construir import construir_grafo

    retrieval, deps = carregar_infra()
    return construir_grafo(retrieval, deps, estrategia=estrategia)


@st.cache_resource(show_spinner=False)
def estrategias_disponiveis() -> list[str]:
    """Sem índice denso (ex.: demo no Streamlit Cloud, onde o BGE-m3 não cabe na
    RAM), só BM25 — o modelo de embedding nunca chega a ser carregado."""
    retrieval, _ = carregar_infra()
    if retrieval.densa.store.contar() == 0:
        return ["bm25"]
    return list(ESTRATEGIAS)


st.title("🥛 RAG de conformidade em laticínios")
st.caption(
    "Respostas com **citação obrigatória** sobre IN 76/2018, IN 77/2018, RIISPOA e manuais "
    "públicos da Embrapa. *Não é aconselhamento jurídico — confira sempre a norma citada.*"
)

with st.sidebar:
    st.header("Configuração")
    opcoes = estrategias_disponiveis()
    estrategia = st.selectbox("Estratégia de retrieval", opcoes, index=len(opcoes) - 1)
    if len(opcoes) == 1:
        st.caption(
            "⚠️ Demo pública: índice denso indisponível — rodando **só BM25**. "
            "Localmente (`scripts/ingerir.py`) as 4 estratégias ficam ativas "
            "(híbrida+rerank: recall@5 = 1,00 no golden)."
        )
    st.markdown(
        f"**Modo:** `{config.RAG_MODO}` (demo = gerador extrativo local, custo zero)\n\n"
        "A tabela comparativa das estratégias está em `eval/results/RESULTS.md`."
    )

# Exemplos testados (funcionam no modo BM25 da nuvem) — clique para preencher.
# O último demonstra a recusa honesta (sem base no corpus).
EXEMPLOS = [
    ("🌡️ Temperatura na recepção",
     "Qual a temperatura máxima do leite cru refrigerado no momento da recepção pelo estabelecimento?"),
    ("🧪 Limite de CCS",
     "Qual o limite máximo de Contagem de Células Somáticas (CCS) para o leite cru refrigerado?"),
    ("📖 Leite tipo A",
     "O que é leite pasteurizado tipo A e onde ele deve ser produzido?"),
    ("🥛 Teste da caneca",
     "Para que serve o teste da caneca de fundo escuro na ordenha?"),
    ("🚫 Recusa honesta",
     "Qual o prazo de validade do leite pasteurizado?"),
]

if "pergunta" not in st.session_state:
    st.session_state.pergunta = ""

st.caption("Exemplos (clique para preencher) — veja mais em `docs/exemplos_de_perguntas.md`:")
for col, (rotulo, texto) in zip(st.columns(len(EXEMPLOS)), EXEMPLOS):
    if col.button(rotulo, help=texto, use_container_width=True):
        st.session_state.pergunta = texto

pergunta = st.text_input(
    "Pergunta",
    key="pergunta",
    placeholder="Ex.: Qual o limite máximo de células somáticas do leite cru refrigerado?",
)

if pergunta and len(pergunta.strip()) >= 3:
    from rag_laticinios.grafo.construir import responder

    with st.spinner("Consultando o grafo…"):
        saida = responder(carregar_grafo(estrategia), pergunta.strip())

    st.markdown("### Resposta")
    st.markdown(saida["resposta"])

    if saida["citacoes"]:
        st.markdown("### Fontes citadas")
        for cit in saida["citacoes"]:
            with st.expander(f"📄 {cit['rotulo']}"):
                st.text(cit["trecho"])

    met = saida["metricas"]
    with st.sidebar:
        st.header("Métricas da consulta")
        st.metric("Latência total", f"{met['latencia_total_ms']:.0f} ms")
        st.metric("Ciclos de correção", met["ciclos"])
        st.metric("Chunks citados", len(saida["citacoes"]))
        if saida.get("verificacao"):
            v = saida["verificacao"]
            st.metric("Groundedness", "aprovada" if v["aprovado"] else "reprovada")
            st.caption(f"cobertura {v['cobertura']:.0%} em {v['linhas_avaliadas']} linha(s)")
        st.caption("Trace: " + " → ".join(met["trace"]))
