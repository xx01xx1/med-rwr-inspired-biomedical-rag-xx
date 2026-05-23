from __future__ import annotations

import os
from typing import Any

import chromadb

from src.ingest import get_chroma_collection


def get_collection_from_env():
    return get_chroma_collection(
        chroma_dir=os.getenv("CHROMA_DIR", "db/chroma"),
        collection_name=os.getenv("CHROMA_COLLECTION", "local_med_library"),
    )


def local_kb_count() -> int:
    # Counting documents does not require loading the sentence-transformers model.
    client = chromadb.PersistentClient(path=os.getenv("CHROMA_DIR", "db/chroma"))
    collection = client.get_or_create_collection(
        name=os.getenv("CHROMA_COLLECTION", "local_med_library"),
        metadata={"description": "Local papers, notes, experimental results, and references"},
    )
    return int(collection.count())


def is_local_kb_empty() -> bool:
    return local_kb_count() == 0


def retrieve_local(query: str, n_results: int = 6) -> list[dict[str, Any]]:
    """Return local Chroma matches in a normalized evidence shape."""
    collection = get_collection_from_env()
    if collection.count() == 0:
        return []

    results = collection.query(query_texts=[query], n_results=n_results)
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    matches: list[dict[str, Any]] = []
    for doc, meta, distance in zip(documents, metadatas, distances):
        matches.append(
            {
                "query": query,
                "source": meta.get("source", ""),
                "file_name": meta.get("file_name", ""),
                "chunk_index": meta.get("chunk_index", ""),
                "text": doc,
                "distance": distance,
            }
        )
    return matches


def retrieve_local_for_queries(queries: list[str], per_query: int = 4) -> list[dict[str, Any]]:
    seen = set()
    merged: list[dict[str, Any]] = []
    for query in queries:
        for item in retrieve_local(query, per_query):
            key = (item["source"], item["chunk_index"], item["text"][:80])
            if key not in seen:
                seen.add(key)
                merged.append(item)
    return merged
