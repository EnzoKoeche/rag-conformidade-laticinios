"""Baixa o corpus público para data/raw/ e grava data/manifesto.json.

Contexto (ADR-005): nesta rede, www.in.gov.br e planalto.gov.br são inalcançáveis
(bloqueio de rota). Usamos snapshots do Wayback Machine das páginas OFICIAIS (DOU e
Planalto) — proveniência auditável: URL original + timestamp do snapshot + SHA-256 —
com espelhos institucionais como fallback. Conteúdo baixado é validado por âncoras
textuais antes de ser aceito.

Uso: uv run python scripts/baixar_documentos.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import unicodedata
from datetime import datetime, timezone
from io import BytesIO

import httpx

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))
from rag_laticinios.config import DATA_RAW, MANIFESTO, UA_NAVEGADOR  # noqa: E402

WAYBACK = "http://web.archive.org/web"

DOCUMENTOS = [
    {
        "doc_id": "in-76-2018",
        "titulo": "Instrução Normativa MAPA nº 76/2018 — identidade e qualidade de leite cru refrigerado, leite pasteurizado e leite pasteurizado tipo A",
        "tipo": "legislacao",
        "formato": "html",
        "fonte_oficial": "https://www.in.gov.br/materia/-/asset_publisher/Kujrw0TZC2Mb/content/id/52750137",
        "urls": [
            f"{WAYBACK}/20220307233253id_/https://www.in.gov.br/materia/-/asset_publisher/Kujrw0TZC2Mb/content/id/52750137",
        ],
        "ancoras": ["INSTRUÇÃO NORMATIVA Nº 76", "leite cru refrigerado"],
        "observacoes": "Snapshot Wayback de 2022-03-07 da página oficial do DOU (publicação 2018-11-30).",
    },
    {
        "doc_id": "in-77-2018",
        "titulo": "Instrução Normativa MAPA nº 77/2018 — critérios e procedimentos para produção, acondicionamento, conservação, transporte, seleção e recepção do leite cru",
        "tipo": "legislacao",
        "formato": "html",
        "fonte_oficial": "https://www.in.gov.br/materia/-/asset_publisher/Kujrw0TZC2Mb/content/id/52750141",
        "urls": [
            f"{WAYBACK}/20240416040822id_/https://www.in.gov.br/materia/-/asset_publisher/Kujrw0TZC2Mb/content/id/52750141/",
        ],
        "ancoras": ["INSTRUÇÃO NORMATIVA Nº 77", "leite cru refrigerado"],
        "observacoes": "Snapshot Wayback de 2024-04-16 da página oficial do DOU (publicação 2018-11-30).",
    },
    {
        "doc_id": "riispoa-2017",
        "titulo": "Decreto nº 9.013/2017 (RIISPOA) — regulamento da inspeção industrial e sanitária de produtos de origem animal",
        "tipo": "legislacao",
        "formato": "html",
        "fonte_oficial": "https://planalto.gov.br/ccivil_03/_ato2015-2018/2017/decreto/d9013.htm",
        "urls": [
            f"{WAYBACK}/20260109154813id_/https://planalto.gov.br/ccivil_03/_ato2015-2018/2017/Decreto/D9013.htm",
            # Fallback: texto ORIGINAL (sem alterações posteriores) na Câmara
            "https://www2.camara.leg.br/legin/fed/decret/2017/decreto-9013-29-marco-2017-784536-publicacaooriginal-152253-pe.html",
        ],
        "ancoras": ["DECRETO Nº 9.013", "produtos de origem animal"],
        "observacoes": "Snapshot Wayback de 2026-01-09 da página do Planalto, que anota as alterações (Dec. 9.069/2017, 10.468/2020 etc.). O fallback da Câmara é a publicação ORIGINAL.",
    },
    {
        "doc_id": "embrapa-ordenha-manual",
        "titulo": "Embrapa — Boas práticas na ordenha manual: procedimentos para assegurar a qualidade do leite e derivados",
        "tipo": "manual",
        "formato": "pdf",
        "fonte_oficial": "https://www.infoteca.cnptia.embrapa.br/infoteca/handle/doc/511230",
        "urls": [
            "https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/511230/1/boaspraticasaloisio.pdf",
        ],
        "ancoras": ["ordenha"],
        "observacoes": "Publicação pública da Embrapa (Infoteca-e). Não redistribuída no repositório (ADR-006).",
    },
    {
        "doc_id": "embrapa-passo-a-passo-ordenha",
        "titulo": "Embrapa — O passo a passo da ordenha higiênica manual",
        "tipo": "manual",
        "formato": "pdf",
        "fonte_oficial": "https://www.infoteca.cnptia.embrapa.br/infoteca/handle/doc/1063391",
        "urls": [
            "https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1063391/1/Agreste.pdf",
        ],
        "ancoras": ["ordenha"],
        "observacoes": "Publicação pública da Embrapa (Infoteca-e). Não redistribuída no repositório (ADR-006).",
    },
]


def _normalizar(texto: str) -> str:
    return unicodedata.normalize("NFC", texto)


def decodificar_html(conteudo: bytes) -> str:
    """Decodifica HTML tentando UTF-8 estrito antes dos legados (Planalto é windows-1252)."""
    for enc in ("utf-8", "windows-1252", "iso-8859-1"):
        try:
            return conteudo.decode(enc)
        except UnicodeDecodeError:
            continue
    return conteudo.decode("utf-8", errors="replace")


def _texto_para_validacao(conteudo: bytes, formato: str) -> str:
    if formato == "pdf":
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(conteudo))
        paginas = reader.pages[: min(5, len(reader.pages))]
        return _normalizar("\n".join((p.extract_text() or "") for p in paginas)).lower()
    return _normalizar(decodificar_html(conteudo)).lower()


def _validar(conteudo: bytes, doc: dict) -> list[str]:
    erros = []
    if doc["formato"] == "pdf" and not conteudo.startswith(b"%PDF"):
        return ["não é um PDF (magic bytes ausentes)"]
    if len(conteudo) < 10_000:
        erros.append(f"suspeito de truncado ({len(conteudo)} bytes)")
    texto = _texto_para_validacao(conteudo, doc["formato"])
    for ancora in doc["ancoras"]:
        if _normalizar(ancora).lower() not in texto:
            erros.append(f"âncora ausente: {ancora!r}")
    return erros


def baixar_documento(client: httpx.Client, doc: dict) -> dict:
    destino = DATA_RAW / f"{doc['doc_id']}.{doc['formato']}"
    entrada = {k: doc[k] for k in ("doc_id", "titulo", "tipo", "formato", "fonte_oficial", "observacoes")}
    tentativas = []
    for url in doc["urls"]:
        try:
            resp = client.get(url)
            resp.raise_for_status()
            erros = _validar(resp.content, doc)
            if erros:
                tentativas.append({"url": url, "resultado": f"conteúdo inválido: {erros}"})
                continue
            destino.write_bytes(resp.content)
            entrada.update(
                status="ok",
                url_usada=url,
                tentativas_anteriores=tentativas or None,
                sha256=hashlib.sha256(resp.content).hexdigest(),
                bytes=len(resp.content),
                arquivo=str(destino.relative_to(MANIFESTO.parent.parent)),
                baixado_em=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
            return entrada
        except httpx.HTTPError as exc:
            tentativas.append({"url": url, "resultado": f"{type(exc).__name__}: {exc}"})
    entrada.update(status="falha", tentativas=tentativas)
    return entrada


def main() -> int:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    entradas = []
    with httpx.Client(
        headers={"User-Agent": UA_NAVEGADOR}, timeout=90, follow_redirects=True
    ) as client:
        for doc in DOCUMENTOS:
            entrada = baixar_documento(client, doc)
            entradas.append(entrada)
            simbolo = "✓" if entrada["status"] == "ok" else "✗"
            print(f"{simbolo} {doc['doc_id']}: {entrada['status']}"
                  + (f" ({entrada['bytes']} bytes)" if entrada["status"] == "ok" else f" — {entrada.get('tentativas')}"))

    manifesto = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "documentos": entradas,
    }
    MANIFESTO.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for e in entradas if e["status"] == "ok")
    legislacao_ok = sum(1 for e in entradas if e["status"] == "ok" and e["tipo"] == "legislacao")
    print(f"\n{ok}/{len(entradas)} documentos baixados ({legislacao_ok} de legislação). Manifesto: {MANIFESTO}")
    if ok < 2:
        print("ERRO: mínimo de 2 documentos não atingido.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
