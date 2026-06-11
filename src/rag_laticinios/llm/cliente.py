"""Cliente LLM com guard de custo (RNF-03/RNF-07).

Invariantes:
- NENHUMA chamada paga acontece sem `RAG_PERMITIR_CUSTO=1` + ANTHROPIC_API_KEY.
- Todo uso é contabilizado em US$ (preços por MTok versionados em config) e a execução
  ABORTA ao atingir o teto (`RAG_TETO_CUSTO_USD`).
- Testes usam `LLMFake` — o SDK nem é importado no modo demo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from rag_laticinios import config


class CustoNaoPermitidoErro(RuntimeError):
    """Chamada paga sem permissão explícita — bloqueio por design."""


class TetoDeCustoErro(RuntimeError):
    """Orçamento da execução foi atingido — abortar é o comportamento correto."""


def estimar_tokens(texto: str) -> int:
    """Estimativa local p/ dry-run (~3,5 chars/token em PT). A execução real usa o
    `usage` devolvido pela API — esta estimativa serve só para planejar custo."""
    return max(1, int(len(texto) / 3.5))


def custo_usd(modelo: str, tokens_entrada: int, tokens_saida: int) -> float:
    preco_in, preco_out = config.PRECOS_USD_POR_MTOK[modelo]
    return tokens_entrada * preco_in / 1e6 + tokens_saida * preco_out / 1e6


@dataclass
class GuardaCusto:
    teto_usd: float = config.RAG_TETO_CUSTO_USD
    gasto_usd: float = 0.0
    chamadas: int = 0
    # None = lê de config (default seguro: bloqueado sem RAG_PERMITIR_CUSTO=1).
    # True = opt-in explícito (ex.: visitante traz a própria chave no front BYOK).
    permitir: bool | None = None

    def autorizar(self, *, tem_chave_explicita: bool = False) -> None:
        permitido = config.RAG_PERMITIR_CUSTO if self.permitir is None else self.permitir
        if not permitido:
            raise CustoNaoPermitidoErro(
                "chamada paga bloqueada: defina RAG_PERMITIR_CUSTO=1 explicitamente"
            )
        if not (tem_chave_explicita or os.getenv("ANTHROPIC_API_KEY")):
            raise CustoNaoPermitidoErro("ANTHROPIC_API_KEY ausente no ambiente/.env")
        if self.gasto_usd >= self.teto_usd:
            raise TetoDeCustoErro(
                f"teto de custo atingido: US${self.gasto_usd:.4f} ≥ US${self.teto_usd:.2f}"
            )

    def registrar(self, modelo: str, tokens_entrada: int, tokens_saida: int) -> float:
        gasto = custo_usd(modelo, tokens_entrada, tokens_saida)
        self.gasto_usd += gasto
        self.chamadas += 1
        return gasto


@dataclass
class RespostaLLM:
    texto: str
    tokens_entrada: int = 0
    tokens_saida: int = 0
    custo_usd: float = 0.0


class LLMFake:
    """Determinístico p/ testes: devolve respostas enfileiradas e grava as chamadas."""

    def __init__(self, respostas: list[str] | None = None):
        self.respostas = list(respostas or [])
        self.chamadas: list[dict] = []

    def gerar(self, system: str, usuario: str, max_tokens: int = 512) -> RespostaLLM:
        self.chamadas.append({"system": system, "usuario": usuario, "max_tokens": max_tokens})
        texto = self.respostas.pop(0) if self.respostas else ""
        return RespostaLLM(texto=texto)


class LLMAnthropic:
    """Haiku via SDK oficial, atrás do GuardaCusto. Só é instanciado no modo real."""

    def __init__(
        self,
        guarda: GuardaCusto | None = None,
        modelo: str | None = None,
        api_key: str | None = None,
    ):
        self.modelo = modelo or config.RAG_MODELO
        self.guarda = guarda or GuardaCusto()
        self._api_key = api_key  # BYOK: nunca persistido, só repassado ao SDK
        self.guarda.autorizar(tem_chave_explicita=bool(api_key))  # falha cedo
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    def gerar(self, system: str, usuario: str, max_tokens: int = config.RAG_MAX_TOKENS_RESPOSTA) -> RespostaLLM:
        self.guarda.autorizar(tem_chave_explicita=bool(self._api_key))
        resposta = self._client.messages.create(
            model=self.modelo,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": usuario}],
        )
        texto = next((b.text for b in resposta.content if b.type == "text"), "")
        gasto = self.guarda.registrar(
            self.modelo, resposta.usage.input_tokens, resposta.usage.output_tokens
        )
        return RespostaLLM(
            texto=texto,
            tokens_entrada=resposta.usage.input_tokens,
            tokens_saida=resposta.usage.output_tokens,
            custo_usd=gasto,
        )
