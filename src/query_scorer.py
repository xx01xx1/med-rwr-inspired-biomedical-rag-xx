from __future__ import annotations


TARGET_WORDS = {
    "target",
    "gene",
    "protein",
    "receptor",
    "channel",
    "cytokine",
    "chemokine",
    "pathway",
    "mechanism",
    "validation",
}

PAIN_WORDS = {
    "neuropathic pain",
    "allodynia",
    "hyperalgesia",
    "dorsal root ganglion",
    "spinal dorsal horn",
    "microglia",
    "astrocyte",
}


def score_query(query: str) -> dict:
    """Approximate Query Semantic Reward with transparent rules."""
    q = query.lower()
    score = 0
    reasons: list[str] = []

    for phrase in PAIN_WORDS:
        if phrase in q:
            score += 3
            reasons.append(f"pain-domain term: {phrase}")
    for word in TARGET_WORDS:
        if word in q:
            score += 2
            reasons.append(f"mechanism/target term: {word}")

    token_count = len(q.split())
    if 5 <= token_count <= 16:
        score += 2
        reasons.append("good query length")
    elif token_count > 24:
        score -= 2
        reasons.append("too long")

    if '"' in query:
        score += 1
        reasons.append("uses phrase constraints")

    return {"query": query, "score": score, "reasons": reasons}


def select_best_queries(queries: list[str], top_k: int = 6) -> list[dict]:
    scored = [score_query(query) for query in queries]
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]
