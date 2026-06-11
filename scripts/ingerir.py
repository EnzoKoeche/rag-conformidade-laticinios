"""Ingere o corpus inteiro (ou um doc com --doc) no índice local.

Uso: uv run python scripts/ingerir.py [--doc in-76-2018]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_laticinios.ingestao.indexador import ingerir_doc, ingerir_tudo  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc", help="ingestão incremental de um único doc_id")
    args = parser.parse_args()
    inicio = time.perf_counter()
    if args.doc:
        relatorios = [ingerir_doc(args.doc)]
    else:
        relatorios = ingerir_tudo()
    for r in relatorios:
        print(f"✓ {r['doc_id']}: {r['chunks']} chunks (modelo: {r['modelo_embedding']})")
    print(f"Total: {sum(r['chunks'] for r in relatorios)} chunks em {time.perf_counter()-inicio:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
