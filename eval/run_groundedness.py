"""EVAL-GRD-01: grafo COMPLETO em modo demo sobre o golden set (RNF-04, gate G3).

Mede: (a) 0 respostas afirmativas sem citação válida; (b) rota de recusa honesta nos
itens sem_base; (c) taxa de resposta nos itens respondíveis; (d) latência p50 do /ask.

Uso: uv run python eval/run_groundedness.py
"""

from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_laticinios import config  # noqa: E402
from rag_laticinios.eval_util import carregar_golden, resultado_acerta_item  # noqa: E402
from rag_laticinios.grafo.construir import construir_grafo, responder  # noqa: E402
from rag_laticinios.grafo.dependencias import dependencias_demo  # noqa: E402
from rag_laticinios.ingestao.indexador import montar_retrieval  # noqa: E402


def main() -> int:
    golden = carregar_golden()
    app = construir_grafo(montar_retrieval(), dependencias_demo())
    responder(app, "aquecimento do índice e dos modelos")  # warm-up fora das medições

    violacoes_citacao = []      # respostas afirmativas reprovadas pelo verificador
    recusas_corretas = 0        # itens sem_base que caíram na rota honesta
    respondidos = 0             # itens respondíveis com resposta aprovada
    respostas_com_fonte_certa = 0
    latencias = []
    detalhes = {}

    for item in golden:
        saida = responder(app, item["pergunta"])
        latencias.append(saida["metricas"]["latencia_total_ms"])
        verificacao = saida["verificacao"]
        tem_resposta = verificacao is not None and verificacao["aprovado"]
        if item["categoria"] == "sem_base":
            recusou = config.MSG_SEM_BASE.split(".")[0] in saida["resposta"] or not tem_resposta
            recusas_corretas += int(recusou)
            detalhes[item["id"]] = "recusa_honesta" if recusou else "RESPONDEU_SEM_BASE"
            if not recusou and verificacao and not verificacao["aprovado"]:
                violacoes_citacao.append(item["id"])
            continue
        if tem_resposta:
            respondidos += 1
            chunks_citados = [
                {"doc_id": c["chunk_id"].split(":")[0], "chunk_id": c["chunk_id"],
                 "artigo": None, "rotulo": c["rotulo"]}
                for c in saida["citacoes"]
            ]
            acertou = resultado_acerta_item(chunks_citados, item) is not None
            respostas_com_fonte_certa += int(acertou)
            detalhes[item["id"]] = "ok_fonte_esperada" if acertou else "ok_outra_fonte"
        else:
            detalhes[item["id"]] = "sem_resposta_aprovada"

    n_sem_base = sum(1 for g in golden if g["categoria"] == "sem_base")
    n_resp = len(golden) - n_sem_base
    resumo = {
        "data_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "modo": "demo (gerador extrativo; verificador real)",
        "violacoes_citacao": len(violacoes_citacao),
        "recusas_honestas_sem_base": f"{recusas_corretas}/{n_sem_base}",
        "taxa_resposta_respondiveis": f"{respondidos}/{n_resp}",
        "respostas_citando_fonte_esperada": f"{respostas_com_fonte_certa}/{respondidos or 1}",
        "latencia_p50_ms": round(statistics.median(latencias), 1),
        "latencia_p95_ms": round(statistics.quantiles(latencias, n=20)[18], 1),
        "detalhes": detalhes,
    }
    destino = config.RAIZ / "eval/results/GROUNDEDNESS.json"
    destino.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"violações de citação (RNF-04, alvo 0): {len(violacoes_citacao)} {violacoes_citacao or ''}")
    print(f"recusas honestas em sem_base:          {recusas_corretas}/{n_sem_base}")
    print(f"respondíveis com resposta aprovada:    {respondidos}/{n_resp}")
    print(f"  …citando uma fonte esperada:         {respostas_com_fonte_certa}/{respondidos}")
    print(f"latência p50/p95 do grafo:             {resumo['latencia_p50_ms']:.0f}/{resumo['latencia_p95_ms']:.0f} ms"
          f" (alvo RNF-02: p50 ≤ 4000 ms)")
    print(f"→ {destino}")
    gates_ok = not violacoes_citacao and recusas_corretas == n_sem_base \
        and resumo["latencia_p50_ms"] <= 4000
    print("G3:", "✓" if gates_ok else "✗")
    return 0 if gates_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
