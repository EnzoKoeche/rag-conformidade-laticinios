"""Front mínimo (RF-07): pergunta → resposta com citações clicáveis → métricas.

Dois modos:
- **Demo** (default, custo zero): gerador extrativo + grader cross-encoder local.
- **Real — BYOK**: o visitante cola a PRÓPRIA chave Anthropic e paga as chamadas (Haiku).
  A chave fica só na sessão do navegador — repassada ao SDK, nunca gravada/logada/cacheada.

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
def carregar_retrieval():
    """Retrieval (BM25 + denso) é caro — carrega UMA vez por processo, compartilhado
    entre demo e real e entre todas as estratégias."""
    from rag_laticinios.ingestao.indexador import montar_retrieval

    return montar_retrieval()


@st.cache_resource(show_spinner=False)
def _deps_demo():
    from rag_laticinios.grafo.dependencias import dependencias_demo

    return dependencias_demo()


@st.cache_resource(show_spinner=False)
def carregar_grafo_demo(estrategia: str):
    from rag_laticinios.grafo.construir import construir_grafo

    return construir_grafo(carregar_retrieval(), _deps_demo(), estrategia=estrategia)


@st.cache_resource(show_spinner=False)
def estrategias_disponiveis() -> list[str]:
    """Sem índice denso (ex.: demo no Streamlit Cloud, onde o BGE-m3 não cabe na RAM),
    só BM25 — o modelo de embedding nunca chega a ser carregado."""
    if carregar_retrieval().densa.store.contar() == 0:
        return ["bm25"]
    return list(ESTRATEGIAS)


st.title("🥛 RAG de conformidade em laticínios")
st.caption(
    "Respostas com **citação obrigatória** sobre IN 76/2018, IN 77/2018, RIISPOA e manuais "
    "públicos da Embrapa. *Não é aconselhamento jurídico — confira sempre a norma citada.*"
)

with st.sidebar:
    st.header("Configuração")
    modo_ui = st.radio(
        "Modo de geração",
        ["Demo (grátis, local)", "Real — Haiku (sua chave)"],
        help="Demo: gerador extrativo local, custo zero. Real (BYOK): usa a API Anthropic "
             "com a SUA chave — você paga as chamadas.",
    )
    usar_real = modo_ui.startswith("Real")

    chave_usuario, teto_usd = "", 0.50
    if usar_real:
        chave_usuario = st.text_input(
            "Sua ANTHROPIC_API_KEY", type="password", placeholder="sk-ant-…",
            help="Fica só nesta sessão do navegador; não é gravada, logada nem enviada a "
                 "lugar nenhum além da Anthropic.",
        )
        teto_usd = st.number_input(
            "Teto de custo por pergunta (US$)", min_value=0.01, max_value=5.0,
            value=0.50, step=0.05,
        )
        st.caption(
            "🔑 **BYOK** — a chave é repassada direto ao SDK e descartada com a sessão; "
            "o guard de custo aborta no teto. Na nuvem o modo real roda sobre **BM25** e, "
            "pela eval, o grader LLM recusa mais que o cross-encoder do demo — o modo real "
            "rende melhor **localmente**, com o índice denso (`eval/results/RESULTS_PAGAS.md`)."
        )

    opcoes = estrategias_disponiveis()
    estrategia = st.selectbox("Estratégia de retrieval", opcoes, index=len(opcoes) - 1)
    if len(opcoes) == 1:
        st.caption(
            "⚠️ Demo pública: índice denso indisponível — rodando **só BM25**. "
            "Localmente (`scripts/ingerir.py`) as 4 estratégias ficam ativas "
            "(híbrida+rerank: recall@5 = 1,00 no golden)."
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


def _responder_real(estrategia: str, chave: str, teto: float, pergunta: str):
    """Modo BYOK: grafo real com a chave do visitante. NÃO cacheado — a chave só
    transita por esta função e pelo SDK; devolve também o guard para mostrar o custo."""
    from rag_laticinios.grafo.construir import construir_grafo, responder
    from rag_laticinios.grafo.dependencias import dependencias_real
    from rag_laticinios.llm.cliente import GuardaCusto, LLMAnthropic

    guarda = GuardaCusto(teto_usd=teto, permitir=True)
    llm = LLMAnthropic(guarda=guarda, api_key=chave)
    grafo = construir_grafo(carregar_retrieval(), dependencias_real(llm=llm), estrategia=estrategia)
    return responder(grafo, pergunta), guarda


if pergunta and len(pergunta.strip()) >= 3:
    from rag_laticinios.grafo.construir import responder

    saida, guarda = None, None
    if usar_real and not chave_usuario.strip():
        st.warning("Cole sua **ANTHROPIC_API_KEY** na barra lateral para usar o modo real "
                   "— ou troque para **Demo** (grátis).")
        st.stop()
    try:
        if usar_real:
            with st.spinner("Consultando o grafo (modo real — Haiku, sua chave)…"):
                saida, guarda = _responder_real(
                    estrategia, chave_usuario.strip(), teto_usd, pergunta.strip()
                )
        else:
            with st.spinner("Consultando o grafo…"):
                saida = responder(carregar_grafo_demo(estrategia), pergunta.strip())
    except Exception as exc:  # chave inválida, sem saldo, teto — sem vazar a chave
        st.error(
            f"Não consegui responder no modo real (`{type(exc).__name__}`). "
            "Verifique a chave e o saldo da Anthropic, ou use o modo **Demo** (grátis)."
        )
        st.stop()

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
        if guarda is not None:
            st.metric("Custo desta pergunta", f"US$ {guarda.gasto_usd:.4f}")
            st.caption(f"{guarda.chamadas} chamadas Haiku · teto US$ {teto_usd:.2f}")
        if saida.get("verificacao"):
            v = saida["verificacao"]
            st.metric("Groundedness", "aprovada" if v["aprovado"] else "reprovada")
            st.caption(f"cobertura {v['cobertura']:.0%} em {v['linhas_avaliadas']} linha(s)")
        st.caption("Trace: " + " → ".join(met["trace"]))
