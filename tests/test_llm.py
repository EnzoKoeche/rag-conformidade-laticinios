"""TEST-GUARD: guard de custo bloqueia por default e aborta no teto (RNF-03/07)."""

import pytest

from rag_laticinios import config
from rag_laticinios.llm.cliente import (
    CustoNaoPermitidoErro,
    GuardaCusto,
    LLMFake,
    TetoDeCustoErro,
    custo_usd,
    estimar_tokens,
)


def test_estimativa_e_custo():
    assert estimar_tokens("x" * 35) == 10
    assert estimar_tokens("") == 1
    # Haiku: $1/MTok entrada, $5/MTok saída
    assert custo_usd("claude-haiku-4-5", 1_000_000, 0) == pytest.approx(1.00)
    assert custo_usd("claude-haiku-4-5", 0, 1_000_000) == pytest.approx(5.00)


def test_guard_bloqueia_sem_permissao(monkeypatch):
    monkeypatch.setattr(config, "RAG_PERMITIR_CUSTO", False)
    with pytest.raises(CustoNaoPermitidoErro, match="RAG_PERMITIR_CUSTO"):
        GuardaCusto().autorizar()


def test_guard_exige_chave(monkeypatch):
    monkeypatch.setattr(config, "RAG_PERMITIR_CUSTO", True)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(CustoNaoPermitidoErro, match="ANTHROPIC_API_KEY"):
        GuardaCusto().autorizar()


def test_guard_aborta_no_teto(monkeypatch):
    monkeypatch.setattr(config, "RAG_PERMITIR_CUSTO", True)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-teste-fake")
    guarda = GuardaCusto(teto_usd=0.001)
    guarda.autorizar()  # abaixo do teto: ok
    gasto = guarda.registrar("claude-haiku-4-5", 500_000, 100_000)  # US$ 1,00
    assert gasto == pytest.approx(1.00)
    assert guarda.chamadas == 1
    with pytest.raises(TetoDeCustoErro):
        guarda.autorizar()


def test_llm_anthropic_nao_constroi_sem_permissao(monkeypatch):
    monkeypatch.setattr(config, "RAG_PERMITIR_CUSTO", False)
    from rag_laticinios.llm.cliente import LLMAnthropic

    with pytest.raises(CustoNaoPermitidoErro):
        LLMAnthropic()


def test_guard_byok_opt_in_explicito(monkeypatch):
    """Front BYOK: sem RAG_PERMITIR_CUSTO e sem env key, o opt-in explícito do visitante
    (que trouxe a própria chave) autoriza — sem afrouxar o default bloqueado."""
    monkeypatch.setattr(config, "RAG_PERMITIR_CUSTO", False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # opt-in + chave explícita do visitante: autoriza
    GuardaCusto(permitir=True).autorizar(tem_chave_explicita=True)
    # opt-in mas sem chave: continua bloqueando
    with pytest.raises(CustoNaoPermitidoErro, match="ANTHROPIC_API_KEY"):
        GuardaCusto(permitir=True).autorizar()
    # chave mas sem opt-in (default lê config=False): continua bloqueando
    with pytest.raises(CustoNaoPermitidoErro, match="RAG_PERMITIR_CUSTO"):
        GuardaCusto().autorizar(tem_chave_explicita=True)


def test_llm_fake_registra_chamadas():
    fake = LLMFake(respostas=["sim"])
    r1 = fake.gerar("sys", "pergunta", max_tokens=5)
    r2 = fake.gerar("sys", "outra")
    assert r1.texto == "sim" and r2.texto == ""
    assert len(fake.chamadas) == 2 and fake.chamadas[0]["max_tokens"] == 5
