"""
retrieval/ingest.py
----------------------
"Ingesta" es el proceso de leer todos los documentos, partirlos en chunks, y guardarlos en el
buscador. Es lo primero que hay que correr para que el sistema tenga algo para buscar.

Uso:
    python -m retrieval.ingest --docs data/docs_ejemplo
"""
from __future__ import annotations

import argparse
import pickle
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from retrieval.chunking import load_and_chunk_directory
from retrieval.embeddings import LocalTfidfEmbeddingFunction
from retrieval.vector_store import COLLECTION_NAME, DEFAULT_DB_PATH, EMBEDDER_PATH, get_client

BM25_INDEX_PATH = Path(__file__).resolve().parent.parent / "data" / "bm25_index.pkl"

_TOKEN_RE = re.compile(r"[a-záéíóúñ0-9]+", re.IGNORECASE)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def ingest(
    docs_dir: str | Path,
    db_path: str | Path = DEFAULT_DB_PATH,
    embedder_path: str | Path = EMBEDDER_PATH,
    bm25_path: str | Path = BM25_INDEX_PATH,
) -> int:
    docs_dir = Path(docs_dir)
    chunks = load_and_chunk_directory(docs_dir)
    if not chunks:
        raise ValueError(f"No se encontraron documentos (.md/.txt) en {docs_dir}")

    print(f"[ingest] {len(chunks)} chunks generados desde {docs_dir}")

    texts = [c.text for c in chunks]
    ids = [f"{c.source}::chunk-{i}" for i, c in enumerate(chunks)]
    metadatas = []
    for c in chunks:
        meta = {"source": c.source}
        for k, v in c.metadata.items():
            meta[k] = str(v)
        metadatas.append(meta)

    embedder = LocalTfidfEmbeddingFunction().fit(texts)
    embedder.save(embedder_path)
    print(f"[ingest] embedder entrenado y guardado en {embedder_path}")

    client = get_client(db_path)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME, embedding_function=embedder, metadata={"hnsw:space": "cosine"}
    )
    collection.add(ids=ids, documents=texts, metadatas=metadatas)
    print(f"[ingest] {collection.count()} chunks indexados en Chroma ('{COLLECTION_NAME}')")

    bm25 = BM25Okapi([_tokenize(t) for t in texts])
    with open(bm25_path, "wb") as f:
        pickle.dump({"bm25": bm25, "ids": ids, "texts": texts, "metadatas": metadatas}, f)
    print(f"[ingest] índice BM25 guardado en {bm25_path}")

    return len(chunks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingesta documentos a la base de conocimiento de MIFE")
    parser.add_argument("--docs", default="data/docs_ejemplo")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    args = parser.parse_args()
    ingest(args.docs, args.db_path)
