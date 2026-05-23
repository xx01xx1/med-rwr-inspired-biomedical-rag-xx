from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


@dataclass
class IngestStats:
    files_seen: int = 0
    files_indexed: int = 0
    chunks_added: int = 0
    skipped_files: list[str] | None = None

    def __post_init__(self) -> None:
        if self.skipped_files is None:
            self.skipped_files = []


def get_embedding_function(model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    """Return a local sentence-transformers embedding function for Chroma."""
    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)


def get_chroma_collection(
    chroma_dir: str = "db/chroma",
    collection_name: str = "local_med_library",
):
    """Open or create the persistent local Chroma collection."""
    client = chromadb.PersistentClient(path=chroma_dir)
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=get_embedding_function(),
        metadata={"description": "Local papers, notes, experimental results, and references"},
    )


def read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages: list[str] = []
    for page_index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"\n[Page {page_index}]\n{text}")
    return "\n".join(pages)


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def read_document(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return read_pdf(path)
    return read_text_file(path)


def iter_supported_files(papers_dir: str) -> Iterable[Path]:
    root = Path(papers_dir)
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 180) -> list[str]:
    """Simple character-based chunking that is easy to inspect and modify."""
    clean = " ".join(text.split())
    if not clean:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + chunk_size, len(clean))
        chunks.append(clean[start:end])
        if end == len(clean):
            break
        start = max(0, end - overlap)
    return chunks


def stable_chunk_id(path: Path, chunk_index: int, text: str) -> str:
    raw = f"{path.as_posix()}::{chunk_index}::{hashlib.sha1(text.encode('utf-8')).hexdigest()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def build_or_update_knowledge_base(
    papers_dir: str = "data/my_papers",
    chroma_dir: str = "db/chroma",
    collection_name: str = "local_med_library",
) -> IngestStats:
    """Read PDF/TXT/MD files and upsert their chunks into Chroma."""
    os.makedirs(papers_dir, exist_ok=True)
    os.makedirs(chroma_dir, exist_ok=True)

    collection = get_chroma_collection(chroma_dir, collection_name)
    stats = IngestStats()

    for path in iter_supported_files(papers_dir):
        stats.files_seen += 1
        try:
            text = read_document(path)
            chunks = chunk_text(text)
        except Exception as exc:  # Keep one bad PDF from stopping the whole build.
            stats.skipped_files.append(f"{path.name}: {exc}")
            continue

        if not chunks:
            stats.skipped_files.append(f"{path.name}: no extractable text")
            continue

        ids = [stable_chunk_id(path, i, chunk) for i, chunk in enumerate(chunks)]
        metadatas = [
            {
                "source": str(path),
                "file_name": path.name,
                "chunk_index": i,
                "document_type": path.suffix.lower().lstrip("."),
            }
            for i, _ in enumerate(chunks)
        ]

        collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)
        stats.files_indexed += 1
        stats.chunks_added += len(chunks)

    return stats
