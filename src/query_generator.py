from __future__ import annotations

import re


NEUROPATHIC_PAIN_TERMS = [
    "neuropathic pain",
    "allodynia",
    "hyperalgesia",
    "dorsal root ganglion",
    "spinal dorsal horn",
    "microglia",
    "astrocyte",
    "neuron",
    "neuroinflammation",
    "ion channel",
    "cytokine",
    "chemokine",
]


def extract_observations(user_question: str) -> dict[str, list[str]]:
    """Rule-based Observe step: find likely disease, cell, phenomenon, and contradiction terms."""
    text = user_question.lower()
    observations = {
        "diseases": [],
        "cell_types": [],
        "experimental_phenomena": [],
        "mechanistic_contradictions": [],
    }

    disease_patterns = ["neuropathic pain", "chronic pain", "sciatic nerve injury", "cci", "sni", "spared nerve injury", "diabetic neuropathy"]
    cell_patterns = ["microglia", "astrocyte", "neuron", "macrophage", "schwann cell", "dorsal root ganglion", "drg", "spinal dorsal horn"]
    phenomenon_patterns = ["allodynia", "hyperalgesia", "upregulated", "downregulated", "rna-seq", "proteomics", "inflammation", "oxidative stress", "sensitization"]
    contradiction_patterns = ["however", "but", "paradox", "contradict", "inconsistent", "opposite", "conflict", "矛盾", "但是", "然而"]

    for term in disease_patterns:
        if term in text:
            observations["diseases"].append(term)
    for term in cell_patterns:
        if term in text:
            observations["cell_types"].append(term)
    for term in phenomenon_patterns:
        if term in text:
            observations["experimental_phenomena"].append(term)
    for term in contradiction_patterns:
        if term in text:
            observations["mechanistic_contradictions"].append(term)

    gene_like = sorted(set(re.findall(r"\b[A-Z][A-Z0-9]{2,8}\b", user_question)))
    if gene_like:
        observations["experimental_phenomena"].extend([f"mentioned gene/protein: {g}" for g in gene_like])

    if not observations["diseases"]:
        observations["diseases"].append("neuropathic pain")
    return observations


def generate_queries(user_question: str, observations: dict[str, list[str]], max_queries: int = 12) -> list[str]:
    """Generate PubMed/local retrieval queries without training a model."""
    disease = observations["diseases"][0] if observations["diseases"] else "neuropathic pain"
    cells = observations["cell_types"] or ["microglia", "astrocyte", "dorsal root ganglion"]
    phenomena = observations["experimental_phenomena"] or ["neuroinflammation", "central sensitization"]

    queries = [
        user_question,
        f'"{disease}" molecular target mechanism',
        f'"{disease}" candidate gene target validation',
        f'"{disease}" neuroinflammation cytokine chemokine pathway',
    ]

    for cell in cells[:4]:
        queries.append(f'"{disease}" "{cell}" molecular mechanism target')
    for phenomenon in phenomena[:5]:
        clean = phenomenon.replace("mentioned gene/protein: ", "")
        queries.append(f'"{disease}" "{clean}" mechanism target')

    queries.extend(
        [
            f'"{disease}" dorsal root ganglion ion channel target',
            f'"{disease}" spinal dorsal horn microglia astrocyte signaling',
            f'"{disease}" transcriptomics proteomics target discovery',
        ]
    )

    deduped: list[str] = []
    seen = set()
    for query in queries:
        normalized = " ".join(query.split()).lower()
        if normalized not in seen:
            seen.add(normalized)
            deduped.append(" ".join(query.split()))
    return deduped[:max_queries]
