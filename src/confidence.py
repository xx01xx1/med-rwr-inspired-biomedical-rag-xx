from __future__ import annotations


def estimate_confidence(candidate: dict) -> str:
    """Assign a transparent confidence level from evidence availability and specificity."""
    local_count = len(candidate.get("local_evidence", []) or [])
    pubmed_count = len(candidate.get("pubmed_evidence", []) or [])
    rationale = (candidate.get("mechanistic_rationale") or "").lower()
    limitations = " ".join(candidate.get("limitations", []) or []).lower()

    score = 0
    if local_count >= 2:
        score += 2
    elif local_count == 1:
        score += 1

    if pubmed_count >= 3:
        score += 3
    elif pubmed_count >= 1:
        score += 1

    if any(word in rationale for word in ["pathway", "receptor", "channel", "cytokine", "chemokine", "microglia", "astrocyte", "drg"]):
        score += 1

    if any(word in limitations for word in ["indirect", "unclear", "limited", "conflicting", "no direct"]):
        score -= 1

    if score >= 5:
        return "High"
    if score >= 3:
        return "Medium"
    return "Low"


def needs_retrieval(confidence: str) -> bool:
    return confidence in {"Low", "Medium"}
