"""Validação automática do golden set (plano_eval §1): roda como script e no pytest.

Garante que o gabarito está ancorado no corpus REAL:
(a) schema e ids únicos; (b) toda fonte esperada resolve para chunk existente;
(c) todo número afirmativo da resposta de referência consta no texto cru de algum
chunk esperado; (d) estratificação (30 itens, 5 p/ revisão humana, sem_base coerente).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rag_laticinios.eval_util import (  # noqa: E402
    CATEGORIAS_VALIDAS,
    carregar_golden,
    chunk_casa_com_fonte,
    numeros_da_resposta,
)
from rag_laticinios.ingestao.indexador import carregar_chunks_jsonl  # noqa: E402

CAMPOS = {
    "id", "pergunta", "categoria", "fontes_esperadas", "modo_acerto",
    "resposta_referencia", "respondivel", "revisao_humana",
}


def validar() -> list[str]:
    erros: list[str] = []
    golden = carregar_golden()
    chunks = carregar_chunks_jsonl()
    if not chunks:
        return ["corpus vazio — rode scripts/ingerir.py antes de validar o golden"]

    if len(golden) != 30:
        erros.append(f"golden tem {len(golden)} itens (esperado: 30)")
    ids = [g["id"] for g in golden]
    if len(set(ids)) != len(ids):
        erros.append("ids duplicados no golden")
    if sum(1 for g in golden if g["revisao_humana"]) != 5:
        erros.append("deve haver exatamente 5 itens com revisao_humana=true")

    for item in golden:
        rid = item.get("id", "?")
        faltam = CAMPOS - set(item)
        if faltam:
            erros.append(f"{rid}: campos ausentes {sorted(faltam)}")
            continue
        if item["categoria"] not in CATEGORIAS_VALIDAS:
            erros.append(f"{rid}: categoria inválida {item['categoria']!r}")
        if item["categoria"] == "sem_base":
            if item["respondivel"] or item["fontes_esperadas"]:
                erros.append(f"{rid}: sem_base exige respondivel=false e fontes vazias")
            continue
        if not item["fontes_esperadas"]:
            erros.append(f"{rid}: item respondível sem fontes_esperadas")
            continue

        textos_esperados = []
        for fonte in item["fontes_esperadas"]:
            casados = [c for c in chunks if chunk_casa_com_fonte(c, fonte)]
            if not casados:
                erros.append(f"{rid}: fonte {fonte} não resolve para nenhum chunk do índice")
            textos_esperados.extend(c["texto"] for c in casados)

        uniao = " ".join(textos_esperados)
        for numero in numeros_da_resposta(item["resposta_referencia"]):
            if numero not in uniao:
                erros.append(
                    f"{rid}: número {numero!r} da resposta de referência não consta "
                    "no texto dos chunks esperados"
                )
    return erros


def main() -> int:
    erros = validar()
    golden = carregar_golden()
    n_sem_base = sum(1 for g in golden if g["categoria"] == "sem_base")
    n_rev = sum(1 for g in golden if g["revisao_humana"])
    print(f"golden: {len(golden)} itens | sem_base: {n_sem_base} | revisão humana: {n_rev}")
    if erros:
        print(f"\n✗ {len(erros)} erro(s):")
        for e in erros:
            print("  -", e)
        return 1
    print("✓ golden válido — todas as fontes resolvem e todos os números estão ancorados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
