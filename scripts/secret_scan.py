"""Secret-scan do HISTÓRICO git completo + árvore atual (RNF-06, premissa nº 3).

Procura padrões de credenciais conhecidos em todos os diffs de todos os commits.
Uso: uv run python scripts/secret_scan.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PADROES = {
    "anthropic": re.compile(r"sk-ant-[A-Za-z0-9_-]{8,}"),
    "openai": re.compile(r"sk-[A-Za-z0-9]{40,}"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    "google_api": re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    "slack": re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"),
    "webhook_secret": re.compile(r"whsec_[A-Za-z0-9]{16,}"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "atribuicao_generica": re.compile(
        r"(?i)(api[_-]?key|secret|token|senha|password)\s*[:=]\s*['\"][A-Za-z0-9+/_-]{24,}['\"]"
    ),
}
# Falsos positivos conhecidos e auditados (testes usam chaves obviamente falsas)
PERMITIDOS = re.compile(r"(sk-ant-teste-fake|exemplo|placeholder|EXEMPLO)")


def varrer(texto: str, origem: str) -> list[str]:
    achados = []
    for nome, padrao in PADROES.items():
        for m in padrao.finditer(texto):
            trecho = m.group(0)
            contexto = texto[max(0, m.start() - 40): m.end() + 20].replace("\n", " ")
            if PERMITIDOS.search(contexto):
                continue
            achados.append(f"[{origem}] {nome}: …{trecho[:24]}… | contexto: {contexto[:90]}")
    return achados


def main() -> int:
    raiz = Path(__file__).resolve().parents[1]
    historico = subprocess.run(
        ["git", "log", "-p", "--all", "--no-color"],
        cwd=raiz, capture_output=True, text=True, errors="replace",
    ).stdout
    achados = varrer(historico, "historico-git")

    for arq in raiz.rglob("*"):
        if arq.is_file() and ".git" not in arq.parts and ".venv" not in arq.parts \
                and "data" not in arq.parts and arq.suffix not in (".npz", ".sqlite3", ".pdf", ".html"):
            try:
                achados += varrer(arq.read_text(errors="replace"), str(arq.relative_to(raiz)))
            except (UnicodeDecodeError, OSError):
                continue

    n_commits = subprocess.run(
        ["git", "rev-list", "--count", "--all"], cwd=raiz, capture_output=True, text=True
    ).stdout.strip()
    print(f"commits varridos: {n_commits} | padrões: {len(PADROES)}")
    if achados:
        print(f"✗ {len(achados)} possíveis segredos:")
        for a in achados:
            print("  -", a)
        return 1
    print("✓ nenhum segredo encontrado no histórico nem na árvore atual")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
