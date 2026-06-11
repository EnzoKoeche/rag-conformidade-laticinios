"""TEST-REAL: as dependências do modo real (Haiku) testadas com LLM fake — o código
que roda amanhã na execução paga é exercitado hoje sem custo."""

import pytest

from rag_laticinios import config
from rag_laticinios.grafo.dependencias import (
    ClassificadorLLM,
    GeradorLLM,
    GraderLLM,
    ReformuladorLLM,
    dependencias_real,
)
from rag_laticinios.llm.cliente import LLMAnthropic, LLMFake

CHUNK = {"chunk_id": "c1", "rotulo": "IN 76/2018, art. 7º", "texto": "Art. 7º CCS 500.000."}
RESULTADO = {"origem": "hibrida_rerank", "score": 1.0, "chunk": CHUNK}


def test_classificador_llm():
    assert ClassificadorLLM(LLMFake(["sim"])).classificar("limite de CCS?") is True
    assert ClassificadorLLM(LLMFake(["nao"])).classificar("capital da França?") is False


def test_grader_llm():
    assert GraderLLM(LLMFake(["Sim, ajuda."])).aprovar("p", RESULTADO) is True
    assert GraderLLM(LLMFake(["nao"])).aprovar("p", RESULTADO) is False


def test_gerador_llm_formato_e_sem_base():
    fake = LLMFake(["- O limite é 500.000 CS/mL [IN 76/2018, art. 7º]"])
    saida = GeradorLLM(fake).gerar("limite de CCS?", [RESULTADO])
    assert saida.endswith("[IN 76/2018, art. 7º]")
    # o prompt enviado delimita os trechos como dado (anti-injection, RF-09)
    assert "<trecho" in fake.chamadas[0]["usuario"]
    assert "NUNCA instrução" in fake.chamadas[0]["system"]
    assert GeradorLLM(LLMFake(["NAO_HA_BASE"])).gerar("p", [RESULTADO]) == ""


def test_reformulador_llm():
    assert ReformuladorLLM(LLMFake(["contagem células somáticas leite"])).reformular("CCS?") \
        == "contagem células somáticas leite"
    assert ReformuladorLLM(LLMFake([""])).reformular("CCS?") == "CCS?"  # vazio → mantém


def test_dependencias_real_montagem():
    deps = dependencias_real(llm=LLMFake())
    assert {"classificador", "grader", "gerador", "reformulador"} <= set(deps)


class _Bloco:
    type = "text"
    text = "- resposta [IN 76/2018, art. 7º]"


class _Uso:
    input_tokens = 1000
    output_tokens = 200


class _RespostaFake:
    content = [_Bloco()]
    usage = _Uso()


class _ClientFake:
    class messages:  # noqa: N801 — espelha a interface do SDK
        @staticmethod
        def create(**kwargs):
            _ClientFake.ultima = kwargs
            return _RespostaFake()


def test_llm_anthropic_gerar_com_client_stub(monkeypatch):
    monkeypatch.setattr(config, "RAG_PERMITIR_CUSTO", True)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-teste-fake")
    llm = LLMAnthropic()
    llm._client = _ClientFake()
    resposta = llm.gerar("system", "pergunta", max_tokens=64)
    assert resposta.texto.endswith("[IN 76/2018, art. 7º]")
    assert _ClientFake.ultima["model"] == config.RAG_MODELO
    assert _ClientFake.ultima["max_tokens"] == 64
    # contabilidade: 1000 in × $1/MTok + 200 out × $5/MTok
    assert resposta.custo_usd == pytest.approx(0.002)
    assert llm.guarda.gasto_usd == pytest.approx(0.002)
