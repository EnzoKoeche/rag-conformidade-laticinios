"""TEST-GOLDEN: o gabarito precisa estar ancorado no corpus real (plano_eval §1)."""

import sys
from pathlib import Path

import pytest

from rag_laticinios import config

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval" / "golden"))


@pytest.mark.skipif(
    not config.CHUNKS_JSONL.exists(),
    reason="requer corpus ingerido (scripts/baixar_documentos.py + scripts/ingerir.py)",
)
def test_golden_valido():
    from validar_golden import validar

    assert validar() == []
