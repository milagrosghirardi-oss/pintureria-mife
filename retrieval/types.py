"""
retrieval/types.py
---------------------
Tipo de dato que representa un fragmento de texto encontrado por el buscador, con sus
puntajes de relevancia. Separado en su propio archivo (sin dependencias pesadas) para que
otras partes del sistema lo puedan usar sin necesitar cargar toda la maquinaria de búsqueda.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetrievedChunk:
    id: str
    text: str
    source: str
    metadata: dict
    vector_rank: int | None = None
    lexical_rank: int | None = None
    rrf_score: float = 0.0
