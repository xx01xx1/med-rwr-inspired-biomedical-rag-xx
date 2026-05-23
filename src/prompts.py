from __future__ import annotations


SYSTEM_PROMPT = """You are a biomedical RAG assistant for neuropathic pain target discovery.
You must separate retrieved evidence from model interpretation.
Do not claim a finding is experimentally proven unless the evidence supports it.
Prefer conservative language and clear limitations.
Return valid JSON only."""


def target_discovery_prompt(user_question: str, observations: dict, scored_queries: list[dict], evidence_text: str) -> str:
    return f"""
Task: Produce Med-RwR-inspired candidate molecular targets for neuropathic pain research.

User question:
{user_question}

Observe step:
{observations}

Selected retrieval queries and rule scores:
{scored_queries}

Retrieved evidence:
{evidence_text}

Return JSON with this exact top-level schema:
{{
  "mechanism_gap_analysis": "short paragraph",
  "candidates": [
    {{
      "target_name": "gene/protein/pathway name",
      "priority": 1,
      "mechanistic_rationale": "model interpretation only",
      "local_evidence": [
        {{"source": "file name", "snippet": "short evidence snippet"}}
      ],
      "pubmed_evidence": [
        {{"pmid": "PMID", "title": "paper title", "evidence_summary": "short summary"}}
      ],
      "experimental_validation_plan": [
        "specific experiment 1",
        "specific experiment 2"
      ],
      "confidence": "High/Medium/Low",
      "limitations": [
        "specific limitation"
      ]
    }}
  ]
}}

Rules:
- Include 3 to 6 candidates.
- Every candidate must include target name, priority, mechanistic rationale, local evidence, PubMed evidence with PMID, experimental validation plan, confidence, and limitations.
- Retrieved Evidence fields must only contain details present in the evidence above.
- Model Interpretation belongs in mechanistic_rationale, mechanism_gap_analysis, validation plans, and limitations.
- If local evidence is weak or absent, say that explicitly in limitations.
"""


def rerank_prompt(user_question: str, first_result: dict, new_evidence_text: str) -> str:
    return f"""
User question:
{user_question}

Initial candidate result:
{first_result}

Additional retrieved evidence from confidence-driven re-retrieval:
{new_evidence_text}

Update and rerank the candidates. Keep the same JSON schema:
{{
  "mechanism_gap_analysis": "short paragraph",
  "candidates": [
    {{
      "target_name": "gene/protein/pathway name",
      "priority": 1,
      "mechanistic_rationale": "model interpretation only",
      "local_evidence": [],
      "pubmed_evidence": [
        {{"pmid": "PMID", "title": "paper title", "evidence_summary": "short summary"}}
      ],
      "experimental_validation_plan": [],
      "confidence": "High/Medium/Low",
      "limitations": []
    }}
  ]
}}

Rules:
- Preserve separation between Retrieved Evidence and Model Interpretation.
- Use the additional evidence only when it supports or weakens a candidate.
- Reassign priority and confidence conservatively.
"""
