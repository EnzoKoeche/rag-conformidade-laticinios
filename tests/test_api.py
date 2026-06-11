"""TEST-API: rotas /ask, /ingest e /health via TestClient com grafo fake (RF-07)."""

import pytest
from fastapi.testclient import TestClient

from rag_laticinios.api.main import criar_app
from rag_laticinios.grafo.construir import construir_grafo
from rag_laticinios.grafo.dependencias import dependencias_demo
from tests.test_grafo import CHUNK_CCS, RetrievalFake


@pytest.fixture()
def client():
    def fabrica(estrategia, k):
        return construir_grafo(
            RetrievalFake([CHUNK_CCS]), dependencias_demo(com_reranker=False),
            estrategia=estrategia, k=k,
        )

    return TestClient(criar_app(fabrica_grafo=fabrica))


def test_ask_feliz(client):
    r = client.post("/ask", json={"pergunta": "Qual o limite de células somáticas do leite cru?"})
    assert r.status_code == 200
    corpo = r.json()
    assert "500.000" in corpo["resposta"]
    assert corpo["citacoes"][0]["rotulo"] == "IN 76/2018, art. 7º"
    assert corpo["metricas"]["estrategia"] == "hibrida_rerank"


def test_ask_estrategia_explicita_e_invalida(client):
    ok = client.post("/ask", json={"pergunta": "limite de CCS do leite?", "estrategia": "bm25"})
    assert ok.status_code == 200 and ok.json()["metricas"]["estrategia"] == "bm25"
    ruim = client.post("/ask", json={"pergunta": "limite de CCS?", "estrategia": "magica"})
    assert ruim.status_code == 422


def test_ask_validacao_de_corpo(client):
    assert client.post("/ask", json={"pergunta": "oi"}).status_code == 422  # curta demais
    assert client.post("/ask", json={}).status_code == 422


def test_ingest_doc_inexistente(client):
    r = client.post("/ingest", json={"doc_id": "doc-que-nao-existe"})
    assert r.status_code == 404


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["modo"] == "demo"
    assert "hibrida_rerank" in corpo["estrategias"]
