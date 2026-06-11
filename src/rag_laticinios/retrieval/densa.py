"""Busca densa: embeddings locais (sentence-transformers) + Chroma (ADR-001/002)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from rag_laticinios import config
from rag_laticinios.retrieval.base import Resultado


class Embedder:
    """Embeddings locais com fallback em cascata (ADR-002) e cache em disco.

    Modelos e5 exigem prefixos query:/passage:; BGE-m3 não usa prefixo.
    """

    def __init__(self, nome_modelo: str | None = None, cache_dir: Path | None = None):
        self.nome_modelo = nome_modelo or config.MODELO_EMBEDDING
        self._cache_dir = cache_dir if cache_dir is not None else config.DATA_CACHE
        self._modelo = None

    def _carregar(self):
        if self._modelo is not None:
            return
        from sentence_transformers import SentenceTransformer

        candidatos = [self.nome_modelo, *config.MODELOS_EMBEDDING_FALLBACK]
        erros = []
        for nome in candidatos:
            try:
                self._modelo = SentenceTransformer(nome)
                self.nome_modelo = nome
                return
            except Exception as exc:  # download/RAM podem falhar — cascata documentada
                erros.append(f"{nome}: {exc}")
        raise RuntimeError("nenhum modelo de embedding carregou: " + " | ".join(erros))

    @property
    def _eh_e5(self) -> bool:
        return "e5" in self.nome_modelo.lower()

    def _chave_cache(self, texto: str, tipo: str) -> str:
        h = hashlib.sha256(f"{self.nome_modelo}|{tipo}|{texto}".encode()).hexdigest()
        return h[:32]

    def _cache_path(self) -> Path:
        slug = self.nome_modelo.replace("/", "__")
        return self._cache_dir / f"embeddings-{slug}.npz"

    def embutir(self, textos: list[str], tipo: str = "passage") -> np.ndarray:
        """tipo: 'passage' (indexação) ou 'query' (consulta). Usa cache por texto."""
        self._carregar()
        chaves = [self._chave_cache(t, tipo) for t in textos]
        cache: dict[str, np.ndarray] = {}
        path = self._cache_path()
        if path.exists():
            with np.load(path) as npz:
                cache = {k: npz[k] for k in npz.files}
        faltando = [i for i, ch in enumerate(chaves) if ch not in cache]
        if faltando:
            entrada = [textos[i] for i in faltando]
            if self._eh_e5:
                prefixo = "query: " if tipo == "query" else "passage: "
                entrada = [prefixo + t for t in entrada]
            novos = self._modelo.encode(
                entrada, normalize_embeddings=True, show_progress_bar=len(entrada) > 50
            )
            for i, vec in zip(faltando, novos):
                cache[chaves[i]] = np.asarray(vec, dtype=np.float32)
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(path, **cache)
        return np.stack([cache[ch] for ch in chaves])


class VetorStore:
    """Interface fina sobre o Chroma (embedded por padrão; http no docker-compose)."""

    def __init__(self, modo: str | None = None, caminho: Path | None = None):
        import chromadb

        modo = modo or config.CHROMA_MODE
        if modo == "http":
            self._client = chromadb.HttpClient(host=config.CHROMA_HOST, port=config.CHROMA_PORT)
        else:
            destino = caminho if caminho is not None else config.DATA_INDEX
            destino.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(destino))
        self._col = self._client.get_or_create_collection(
            config.COLECAO_CHUNKS, metadata={"hnsw:space": "cosine"}
        )

    def contar(self) -> int:
        return self._col.count()

    def upsert_doc(self, doc_id: str, chunks: list[dict], embeddings: np.ndarray) -> None:
        """RF-08: substitui todos os chunks de um doc sem tocar nos demais."""
        existentes = self._col.get(where={"doc_id": doc_id}, include=[])["ids"]
        if existentes:
            self._col.delete(ids=existentes)
        metadatas = []
        for c in chunks:
            md = {k: v for k, v in c.items() if k not in ("texto",) and v is not None}
            metadatas.append(md)
        self._col.add(
            ids=[c["chunk_id"] for c in chunks],
            embeddings=embeddings.tolist(),
            documents=[c["texto"] for c in chunks],
            metadatas=metadatas,
        )

    def buscar(self, embedding_query: np.ndarray, k: int = 10) -> list[Resultado]:
        res = self._col.query(
            query_embeddings=[embedding_query.tolist()],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        saida = []
        for cid, doc, md, dist in zip(
            res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]
        ):
            chunk = dict(md)
            chunk["texto"] = doc
            chunk["chunk_id"] = cid
            saida.append(
                Resultado(chunk_id=cid, score=1.0 - dist, chunk=chunk, origem="densa")
            )
        return saida


class BuscaDensa:
    def __init__(self, embedder: Embedder, store: VetorStore):
        self.embedder = embedder
        self.store = store

    def buscar(self, pergunta: str, k: int = 10) -> list[Resultado]:
        vec = self.embedder.embutir([pergunta], tipo="query")[0]
        return self.store.buscar(vec, k=k)
