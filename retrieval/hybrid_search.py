"""
retrieval/hybrid_search.py
-----------------------------
"Búsqueda híbrida" combina dos formas de buscar:
  1. Por significado (vectorial): encuentra cosas parecidas aunque no compartan las mismas
     palabras exactas (ej. "pared que absorbe mucho" encuentra el documento que dice "pared
     que chupa").
  2. Por palabra exacta (léxica, BM25): necesaria para cosas como nombres de marca o colores
     puntuales, donde el significado no alcanza y hace falta la coincidencia justa.

Combinamos ambos resultados con un método llamado RRF (Reciprocal Rank Fusion), que no
requiere que los dos buscadores usen la misma escala de puntaje.
"""
from __future__ import annotations

import pickle
from pathlib import Path

from retrieval.ingest import BM25_INDEX_PATH, _tokenize
from retrieval.types import RetrievedChunk
from retrieval.vector_store import EMBEDDER_PATH, get_collection


class HybridRetriever:
    RRF_K = 60

    def __init__(
        self,
        db_path: str | Path | None = None,
        bm25_path: str | Path = BM25_INDEX_PATH,
        embedder_path: str | Path = EMBEDDER_PATH,
    ):
        kwargs = {"embedder_path": embedder_path}
        if db_path is not None:
            kwargs["db_path"] = db_path
        self.collection = get_collection(**kwargs)
        with open(bm25_path, "rb") as f:
            data = pickle.load(f)
        self.bm25 = data["bm25"]
        self.bm25_ids = data["ids"]
        self.bm25_texts = data["texts"]
        self.bm25_metadatas = data["metadatas"]

    def _vector_search(self, query: str, top_k: int):
        res = self.collection.query(query_texts=[query], n_results=top_k)
        return list(zip(res["ids"][0], res["documents"][0], res["metadatas"][0]))

    def _lexical_search(self, query: str, top_k: int):
        scores = self.bm25.get_scores(_tokenize(query))
        ranked_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [
            (self.bm25_ids[i], self.bm25_texts[i], self.bm25_metadatas[i])
            for i in ranked_idx
            if scores[i] > 0
        ]

    def search(self, query: str, top_k: int = 10) -> list[RetrievedChunk]:
        vector_results = self._vector_search(query, top_k)
        lexical_results = self._lexical_search(query, top_k)

        chunks: dict[str, RetrievedChunk] = {}
        for rank, (cid, text, meta) in enumerate(vector_results):
            chunks[cid] = RetrievedChunk(id=cid, text=text, source=meta.get("source", "?"), metadata=meta, vector_rank=rank)
        for rank, (cid, text, meta) in enumerate(lexical_results):
            if cid in chunks:
                chunks[cid].lexical_rank = rank
            else:
                chunks[cid] = RetrievedChunk(id=cid, text=text, source=meta.get("source", "?"), metadata=meta, lexical_rank=rank)

        for c in chunks.values():
            score = 0.0
            if c.vector_rank is not None:
                score += 1.0 / (self.RRF_K + c.vector_rank + 1)
            if c.lexical_rank is not None:
                score += 1.0 / (self.RRF_K + c.lexical_rank + 1)
            c.rrf_score = score

        return sorted(chunks.values(), key=lambda c: c.rrf_score, reverse=True)[:top_k]
