from __future__ import annotations


def truncate(text: str, max_chars: int = 650) -> str:
    text = " ".join((text or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def format_local_evidence(local_hits: list[dict], limit: int = 8) -> list[dict]:
    formatted = []
    for hit in local_hits[:limit]:
        formatted.append(
            {
                "source": hit.get("file_name") or hit.get("source"),
                "chunk_index": hit.get("chunk_index"),
                "query": hit.get("query"),
                "snippet": truncate(hit.get("text", "")),
            }
        )
    return formatted


def format_pubmed_evidence(pubmed_hits: list[dict], limit: int = 12) -> list[dict]:
    formatted = []
    for hit in pubmed_hits[:limit]:
        if hit.get("error"):
            formatted.append({"query": hit.get("query"), "error": hit.get("error")})
            continue
        formatted.append(
            {
                "pmid": hit.get("pmid"),
                "title": hit.get("title"),
                "journal": hit.get("journal"),
                "year": hit.get("year"),
                "query": hit.get("query"),
                "abstract_snippet": truncate(hit.get("abstract", ""), 900),
                "url": hit.get("url"),
            }
        )
    return formatted


def compact_evidence_text(local_evidence: list[dict], pubmed_evidence: list[dict]) -> str:
    lines = ["LOCAL EVIDENCE:"]
    for idx, item in enumerate(local_evidence, start=1):
        lines.append(f"{idx}. Source: {item.get('source')} | Snippet: {item.get('snippet')}")

    lines.append("\nPUBMED EVIDENCE:")
    for idx, item in enumerate(pubmed_evidence, start=1):
        if item.get("error"):
            lines.append(f"{idx}. Query failed: {item.get('query')} | Error: {item.get('error')}")
        else:
            lines.append(
                f"{idx}. PMID: {item.get('pmid')} | {item.get('title')} | "
                f"{item.get('journal')} {item.get('year')} | Abstract: {item.get('abstract_snippet')}"
            )
    return "\n".join(lines)
