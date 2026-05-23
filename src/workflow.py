from __future__ import annotations

from typing import Any

from dotenv import load_dotenv

from src.confidence import needs_retrieval
from src.demo_mode import DEMO_NOTICE, build_demo_result
from src.evidence import compact_evidence_text, format_local_evidence, format_pubmed_evidence
from src.prompts import rerank_prompt, target_discovery_prompt
from src.pubmed import search_pubmed_for_queries
from src.query_generator import extract_observations, generate_queries
from src.query_scorer import select_best_queries
from src.retriever import retrieve_local_for_queries
from src.target_ranker import rank_targets


def _openai_error_summary(exc: Exception) -> str:
    text = str(exc) or exc.__class__.__name__
    lowered = text.lower()
    if "insufficient_quota" in lowered or "quota" in lowered:
        return f"insufficient_quota: {text}"
    if "rate limit" in lowered or "ratelimit" in lowered or "429" in lowered:
        return f"rate limit: {text}"
    if "authentication" in lowered or "api key" in lowered or "401" in lowered:
        return f"authentication error: {text}"
    return text


def _demo_fallback_output(
    *,
    user_question: str,
    observations: dict[str, Any],
    generated_queries: list[str],
    scored_queries: list[dict[str, Any]],
    selected_queries: list[str],
    local_evidence: list[dict[str, Any]],
    pubmed_evidence: list[dict[str, Any]],
    api_error: Exception,
    stage: str,
    enable_reretrieval: bool,
    pubmed_per_query: int,
) -> dict[str, Any]:
    result = build_demo_result(user_question, observations, local_evidence, pubmed_evidence)
    second_round_queries: list[str] = []
    second_round_pubmed_evidence: list[dict[str, Any]] = []
    reretrieval_trace: list[dict[str, Any]] = [
        {
            "stage": stage,
            "status": "openai_unavailable",
            "message": DEMO_NOTICE,
            "error": _openai_error_summary(api_error),
        }
    ]

    if enable_reretrieval:
        second_round_queries = build_second_round_queries(result.get("candidates", []), user_question)
        reretrieval_trace.append(
            {
                "stage": "demo_retrieval_planning",
                "status": "generated_demo_queries",
                "query_count": len(second_round_queries),
            }
        )
        if second_round_queries:
            second_hits = search_pubmed_for_queries(second_round_queries, per_query=pubmed_per_query)
            second_round_pubmed_evidence = format_pubmed_evidence(second_hits)
            reretrieval_trace.append(
                {
                    "stage": "demo_second_round_pubmed",
                    "status": "retrieved",
                    "evidence_count": len(second_round_pubmed_evidence),
                }
            )
    else:
        reretrieval_trace.append(
            {
                "stage": "demo_retrieval_planning",
                "status": "disabled",
                "query_count": 0,
            }
        )

    return {
        "observations": observations,
        "generated_queries": generated_queries,
        "scored_queries": scored_queries,
        "selected_queries": selected_queries,
        "retrieved_evidence": {
            "local": local_evidence,
            "pubmed": pubmed_evidence,
            "second_round_pubmed": second_round_pubmed_evidence,
        },
        "second_round_queries": second_round_queries,
        "reretrieval_trace": reretrieval_trace,
        "result": result,
        "demo_mode": True,
        "api_warning": DEMO_NOTICE,
        "api_error": _openai_error_summary(api_error),
    }


def build_second_round_queries(candidates: list[dict[str, Any]], user_question: str, max_queries: int = 6) -> list[str]:
    queries: list[str] = []
    for candidate in candidates:
        if needs_retrieval(candidate.get("confidence", "Low")):
            target = candidate.get("target_name", "")
            if target:
                queries.append(f'"{target}" "neuropathic pain" mechanism')
                queries.append(f'"{target}" microglia astrocyte dorsal root ganglion pain')
                queries.append(f'"{target}" allodynia hyperalgesia validation')

    if not queries:
        return []

    # Keep a little context from the original question without making queries too long.
    if "diabetic" in user_question.lower():
        queries.append('"diabetic neuropathy" target mechanism validation')

    deduped = []
    seen = set()
    for query in queries:
        key = query.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(query)
    return deduped[:max_queries]


def run_target_discovery(
    user_question: str,
    local_per_query: int = 4,
    pubmed_per_query: int = 5,
    top_queries: int = 6,
    enable_reretrieval: bool = True,
) -> dict[str, Any]:
    """Run the full Observe-Reason-Query-Retrieve-Answer-Confidence loop."""
    load_dotenv()

    observations = extract_observations(user_question)
    generated_queries = generate_queries(user_question, observations)
    scored_queries = select_best_queries(generated_queries, top_k=top_queries)
    selected_queries = [item["query"] for item in scored_queries]

    local_hits = retrieve_local_for_queries(selected_queries, per_query=local_per_query)
    pubmed_hits = search_pubmed_for_queries(selected_queries, per_query=pubmed_per_query)

    local_evidence = format_local_evidence(local_hits)
    pubmed_evidence = format_pubmed_evidence(pubmed_hits)
    evidence_text = compact_evidence_text(local_evidence, pubmed_evidence)

    first_prompt = target_discovery_prompt(user_question, observations, scored_queries, evidence_text)
    try:
        first_result = rank_targets(first_prompt)
    except Exception as exc:
        return _demo_fallback_output(
            user_question=user_question,
            observations=observations,
            generated_queries=generated_queries,
            scored_queries=scored_queries,
            selected_queries=selected_queries,
            local_evidence=local_evidence,
            pubmed_evidence=pubmed_evidence,
            api_error=exc,
            stage="first_openai_reasoning",
            enable_reretrieval=enable_reretrieval,
            pubmed_per_query=pubmed_per_query,
        )

    second_round_queries: list[str] = []
    second_round_pubmed_evidence: list[dict[str, Any]] = []
    final_result = first_result
    reretrieval_trace: list[dict[str, Any]] = []

    if enable_reretrieval:
        second_round_queries = build_second_round_queries(first_result.get("candidates", []), user_question)
        reretrieval_trace.append(
            {
                "stage": "confidence_check",
                "status": "generated_queries" if second_round_queries else "not_needed",
                "query_count": len(second_round_queries),
            }
        )
        if second_round_queries:
            second_hits = search_pubmed_for_queries(second_round_queries, per_query=pubmed_per_query)
            second_round_pubmed_evidence = format_pubmed_evidence(second_hits)
            second_evidence_text = compact_evidence_text([], second_round_pubmed_evidence)
            try:
                final_result = rank_targets(rerank_prompt(user_question, first_result, second_evidence_text))
                reretrieval_trace.append(
                    {
                        "stage": "second_openai_rerank",
                        "status": "completed",
                        "evidence_count": len(second_round_pubmed_evidence),
                    }
                )
            except Exception as exc:
                fallback = _demo_fallback_output(
                    user_question=user_question,
                    observations=observations,
                    generated_queries=generated_queries,
                    scored_queries=scored_queries,
                    selected_queries=selected_queries,
                    local_evidence=local_evidence,
                    pubmed_evidence=pubmed_evidence,
                    api_error=exc,
                    stage="second_openai_rerank",
                    enable_reretrieval=False,
                    pubmed_per_query=pubmed_per_query,
                )
                fallback["second_round_queries"] = second_round_queries
                fallback["retrieved_evidence"]["second_round_pubmed"] = second_round_pubmed_evidence
                fallback["reretrieval_trace"] = reretrieval_trace + fallback["reretrieval_trace"]
                return fallback
    else:
        reretrieval_trace.append({"stage": "confidence_check", "status": "disabled", "query_count": 0})

    return {
        "observations": observations,
        "generated_queries": generated_queries,
        "scored_queries": scored_queries,
        "selected_queries": selected_queries,
        "retrieved_evidence": {
            "local": local_evidence,
            "pubmed": pubmed_evidence,
            "second_round_pubmed": second_round_pubmed_evidence,
        },
        "second_round_queries": second_round_queries,
        "reretrieval_trace": reretrieval_trace,
        "result": final_result,
        "demo_mode": False,
    }
