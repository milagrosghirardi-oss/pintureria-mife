"""
ranking/reranker.py
----------------------
El "re-ranker" es un segundo filtro más estricto: agarra los resultados del buscador y los
reordena para quedarse solo con los 2-3 mejores, priorizando los que de verdad se relacionan
con lo que se preguntó (en vez de confiar ciegamente en el orden que dio la primera búsqueda).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from retrieval.types import RetrievedChunk


@dataclass
class RankedChunk:
    chunk: RetrievedChunk
    score: float


class HeuristicReranker:
    def rerank(self, query: str, candidatos: list[RetrievedChunk], top_k: int = 3) -> list[RankedChunk]:
        query_tokens = set(re.findall(r"[a-záéíóúñ0-9]+", query.lower()))
        resultado = []
        for c in candidatos:
            texto_tokens = set(re.findall(r"[a-záéíóúñ0-9]+", c.text.lower()))
            overlap = len(query_tokens & texto_tokens) / max(len(query_tokens), 1)
            score = (0.6 * c.rrf_score * 100) + (0.4 * overlap)
            resultado.append(RankedChunk(chunk=c, score=score))
        resultado.sort(key=lambda r: r.score, reverse=True)
        return resultado[:top_k]
