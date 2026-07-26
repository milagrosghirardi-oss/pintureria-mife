"""
retrieval/vector_store.py
----------------------------
Una "base de datos vectorial" es un archivero especial que guarda textos junto con sus
embeddings (los números que representan su significado), para poder buscar "lo más parecido
a esto" muy rápido. Usamos Chroma, que corre local en tu compu (no necesita internet ni un
servidor aparte).
"""
from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.config import Settings

from retrieval.embeddings import LocalTfidfEmbeddingFunction

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "chroma_db"
EMBEDDER_PATH = Path(__file__).resolve().parent.parent / "data" / "embedder.pkl"
COLLECTION_NAME = "mife_conocimiento"


def get_client(db_path: str | Path = DEFAULT_DB_PATH) -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=str(db_path), settings=Settings(anonymized_telemetry=False))


def get_collection(
    db_path: str | Path = DEFAULT_DB_PATH,
    embedder_path: str | Path = EMBEDDER_PATH,
):
    client = get_client(db_path)
    embedder = LocalTfidfEmbeddingFunction.load(embedder_path)
    return client.get_collection(name=COLLECTION_NAME, embedding_function=embedder)
