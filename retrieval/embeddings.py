"""
retrieval/embeddings.py
--------------------------
"Embeddings" es la forma de convertir un texto en una lista de números que representan su
significado, para poder comparar qué tan parecidos son dos textos matemáticamente. Los
sistemas grandes usan modelos de IA descargados de internet para esto; acá usamos una técnica
más simple y liviana (TF-IDF + reducción de dimensiones) que corre 100% local, sin necesitar
descargar nada ni pagar ninguna API — ideal para este proyecto académico.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
from chromadb import EmbeddingFunction
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

EMBEDDING_DIM = 128


class LocalTfidfEmbeddingFunction(EmbeddingFunction):
    """Convierte texto en vectores usando TF-IDF (frecuencia de palabras/subcadenas) +
    SVD (reduce a una cantidad fija de dimensiones). Se "entrena" (fit) una vez sobre todos
    los documentos, y después se usa para convertir cualquier texto nuevo al mismo espacio."""

    def __init__(self, vectorizer: TfidfVectorizer | None = None, svd: TruncatedSVD | None = None):
        self.vectorizer = vectorizer
        self.svd = svd

    def __call__(self, input: list[str]) -> list[list[float]]:
        if self.vectorizer is None or self.svd is None:
            raise RuntimeError(
                "El embedder no fue entrenado/cargado. Corré retrieval/ingest.py primero."
            )
        tfidf = self.vectorizer.transform(input)
        dense = self.svd.transform(tfidf)
        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (dense / norms).tolist()

    def name(self) -> str:
        return "mife_local_tfidf_svd_v1"

    def fit(self, corpus: list[str]) -> "LocalTfidfEmbeddingFunction":
        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5), min_df=1, max_features=20000, sublinear_tf=True
        )
        tfidf = self.vectorizer.fit_transform(corpus)
        n_components = max(2, min(EMBEDDING_DIM, tfidf.shape[0] - 1, tfidf.shape[1] - 1))
        self.svd = TruncatedSVD(n_components=n_components, random_state=42)
        self.svd.fit(tfidf)
        return self

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"vectorizer": self.vectorizer, "svd": self.svd}, f)

    @classmethod
    def load(cls, path: str | Path) -> "LocalTfidfEmbeddingFunction":
        with open(path, "rb") as f:
            data = pickle.load(f)
        return cls(vectorizer=data["vectorizer"], svd=data["svd"])
