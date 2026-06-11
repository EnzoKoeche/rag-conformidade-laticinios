"""EVAL-RET-01: compara as 4 estratégias de retrieval no golden set (RNF-01).

Gera eval/results/RESULTS.md (tabela comparativa) e RESULTS.json (dados brutos).
Itens `sem_base` ficam fora (não têm gabarito de retrieval — ver plano_eval §2).

Uso: uv run python eval/run_retrieval.py
"""

from __future__ import annotations

import hashlib
import json
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_laticinios import config  # noqa: E402
from rag_laticinios.eval_util import carregar_golden, resultado_acerta_item  # noqa: E402
from rag_laticinios.ingestao.indexador import carregar_chunks_jsonl, montar_retrieval  # noqa: E402
from rag_laticinios.retrieval.estrategias import ESTRATEGIAS  # noqa: E402

K_AVALIACAO = (1, 3, 5, 10)
K_BUSCA = 10


def avaliar_estrategia(retrieval, itens: list[dict], estrategia: str) -> dict:
    retrieval.buscar("aquecimento do índice", estrategia=estrategia, k=K_BUSCA)  # warm-up
    posicoes: list[int | None] = []
    latencias: list[float] = []
    por_item = {}
    for item in itens:
        inicio = time.perf_counter()
        resultados, _ = retrieval.buscar(item["pergunta"], estrategia=estrategia, k=K_BUSCA)
        latencias.append((time.perf_counter() - inicio) * 1000)
        pos = resultado_acerta_item([r.chunk for r in resultados], item)
        posicoes.append(pos)
        por_item[item["id"]] = pos
    n = len(itens)
    metricas = {
        f"recall@{k}": sum(1 for p in posicoes if p is not None and p <= k) / n
        for k in K_AVALIACAO
    }
    metricas["mrr@10"] = sum(1 / p for p in posicoes if p is not None) / n
    metricas["hit_rate@10"] = metricas["recall@10"]
    metricas["latencia_p50_ms"] = statistics.median(latencias)
    metricas["latencia_p95_ms"] = statistics.quantiles(latencias, n=20)[18]
    return {"metricas": metricas, "posicoes_por_item": por_item}


def main() -> int:
    golden = carregar_golden()
    itens = [g for g in golden if g["respondivel"]]
    chunks = carregar_chunks_jsonl()
    retrieval = montar_retrieval()
    hash_golden = hashlib.sha256(config.GOLDEN_JSONL.read_bytes()).hexdigest()[:12]

    resultados = {}
    for estrategia in ESTRATEGIAS:
        print(f"avaliando: {estrategia} …")
        resultados[estrategia] = avaliar_estrategia(retrieval, itens, estrategia)

    embedder = retrieval._densa.embedder
    contexto = {
        "data_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_itens_avaliados": len(itens),
        "n_chunks_indice": len(chunks),
        "modelo_embedding": embedder.nome_modelo,
        "modelo_rerank": retrieval._reranker.nome_modelo,
        "k_busca": K_BUSCA,
        "hash_golden": hash_golden,
        "hardware": f"{platform.machine()} / CPU only / WSL2",
    }

    # breakdown por categoria (recall@5)
    categorias = sorted({g["categoria"] for g in itens})
    breakdown = {}
    for cat in categorias:
        ids_cat = [g["id"] for g in itens if g["categoria"] == cat]
        breakdown[cat] = {
            est: sum(
                1 for i in ids_cat
                if (p := resultados[est]["posicoes_por_item"][i]) is not None and p <= 5
            ) / len(ids_cat)
            for est in ESTRATEGIAS
        }

    config.RAIZ.joinpath("eval/results").mkdir(parents=True, exist_ok=True)
    (config.RAIZ / "eval/results/RESULTS.json").write_text(
        json.dumps({"contexto": contexto, "resultados": resultados, "breakdown_recall5": breakdown},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    linhas = [
        "# EVAL-RET-01 — Comparativo de estratégias de retrieval",
        "",
        f"Golden: **{len(itens)} perguntas respondíveis** (hash `{hash_golden}`) · índice: "
        f"**{contexto['n_chunks_indice']} chunks** · embeddings: `{contexto['modelo_embedding']}` · "
        f"reranker: `{contexto['modelo_rerank']}` · k={K_BUSCA} · {contexto['data_utc']} · "
        f"{contexto['hardware']}",
        "",
        "| Estratégia | recall@1 | recall@3 | recall@5 | recall@10 | MRR@10 | p50 (ms) | p95 (ms) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for est in ESTRATEGIAS:
        m = resultados[est]["metricas"]
        linhas.append(
            f"| {est} | {m['recall@1']:.2f} | {m['recall@3']:.2f} | **{m['recall@5']:.2f}** | "
            f"{m['recall@10']:.2f} | {m['mrr@10']:.2f} | {m['latencia_p50_ms']:.0f} | "
            f"{m['latencia_p95_ms']:.0f} |"
        )
    linhas += ["", "## recall@5 por categoria", "",
               "| Categoria | " + " | ".join(ESTRATEGIAS) + " |",
               "|---|" + "---|" * len(ESTRATEGIAS)]
    for cat, vals in breakdown.items():
        linhas.append(f"| {cat} | " + " | ".join(f"{vals[e]:.2f}" for e in ESTRATEGIAS) + " |")
    linhas += [
        "",
        "## O que isto prova — e o que não prova",
        "",
        "- **Prova:** qual estratégia recupera melhor o artigo-fonte correto *neste corpus e "
        "neste golden* (n=" + str(len(itens)) + "), com unidade de acerto = artigo (ADR-011); "
        "justifica a estratégia default do sistema com número, não opinião.",
        "- **Não prova:** qualidade da resposta final (medida na eval de groundedness e nas "
        "evals pagas), generalização para outros corpora/domínios, robustez a paráfrases fora "
        "do estilo do golden. O golden foi escrito pelo autor do sistema a partir dos próprios "
        "chunks (viés documentado no plano_eval §1; 5 itens aguardam revisão humana).",
        "- Latências medidas **a quente** (modelos carregados; o primeiro carregamento de "
        "modelo leva segundos e está fora destas medições), em CPU/WSL2.",
    ]
    (config.RAIZ / "eval/results/RESULTS.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")

    print("\n" + "\n".join(linhas[4 : 6 + len(ESTRATEGIAS)]))
    melhor = max(ESTRATEGIAS, key=lambda e: resultados[e]["metricas"]["recall@5"])
    r5 = resultados[melhor]["metricas"]["recall@5"]
    print(f"\nmelhor recall@5: {melhor} = {r5:.2f} (alvo RNF-01: ≥ 0,80) → "
          + ("✓ ATINGIDO" if r5 >= 0.80 else "✗ ABAIXO DO ALVO"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
