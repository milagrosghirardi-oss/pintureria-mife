"""
retrieval/chunking.py
------------------------
"Chunking" es partir un documento largo en pedacitos ("chunks") más chicos y manejables, para
que el buscador pueda encontrar justo la parte relevante en vez de traer el documento entero.
Partimos respetando los títulos/secciones del documento (no por cantidad fija de caracteres),
así cada pedacito tiene sentido completo por sí solo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

HEADERS_TO_SPLIT_ON = [("#", "titulo"), ("##", "seccion"), ("###", "subseccion")]

_fallback_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800, chunk_overlap=120, separators=["\n\n", "\n", ". ", " ", ""]
)


@dataclass
class Chunk:
    text: str
    source: str
    metadata: dict = field(default_factory=dict)


def chunk_markdown(text: str, source: str) -> list[Chunk]:
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS_TO_SPLIT_ON)
    docs = splitter.split_text(text)
    chunks = []
    for d in docs:
        content = d.page_content.strip()
        if not content:
            continue
        if len(content) > 1200:
            for sub in _fallback_splitter.split_text(content):
                chunks.append(Chunk(text=sub, source=source, metadata=dict(d.metadata)))
        else:
            chunks.append(Chunk(text=content, source=source, metadata=dict(d.metadata)))
    return chunks


def load_and_chunk_directory(directory: str | Path) -> list[Chunk]:
    directory = Path(directory)
    all_chunks: list[Chunk] = []
    for path in sorted(directory.glob("**/*")):
        if path.suffix.lower() in {".md", ".txt"}:
            texto = path.read_text(encoding="utf-8")
            chunks = chunk_markdown(texto, path.name) if "#" in texto else [
                Chunk(text=t, source=path.name) for t in _fallback_splitter.split_text(texto)
            ]
            all_chunks.extend(chunks)
    return all_chunks


def chunk_historial_consultas(pares: list[dict]) -> list[Chunk]:
    """Convierte consultas anteriores ya cotizadas en chunks buscables — mismo patrón que un
    vendedor con memoria que se acuerda de casos parecidos que ya resolvió."""
    chunks = []
    for par in pares:
        texto = f"Consulta similar ya cotizada: {par['consulta']}\nCotización que se armó: {par['respuesta']}"
        chunks.append(
            Chunk(text=texto, source=f"historial::{par.get('fuente', 'vendedor')}", metadata={"tipo": "historial_consulta"})
        )
    return chunks
