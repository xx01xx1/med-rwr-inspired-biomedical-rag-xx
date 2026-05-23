from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from src.ingest import build_or_update_knowledge_base
from src.retriever import is_local_kb_empty, local_kb_count
from src.workflow import run_target_discovery


load_dotenv()

PAPERS_DIR = os.getenv("PAPERS_DIR", "data/my_papers")
CHROMA_DIR = os.getenv("CHROMA_DIR", "db/chroma")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "local_med_library")


st.set_page_config(page_title="Med-RwR-inspired Target Finder", layout="wide")

st.title("Med-RwR-inspired Neuropathic Pain Target Finder")
st.caption("Lightweight research RAG prototype: local papers + PubMed + reasoning with retrieval.")

with st.sidebar:
    st.header("Local Knowledge Base")
    st.write(f"Paper folder: `{PAPERS_DIR}`")
    st.write(f"Chroma DB: `{CHROMA_DIR}`")

    if st.button("Build / Update Local Knowledge Base", type="primary"):
        with st.spinner("Reading PDF/TXT/MD files and updating Chroma..."):
            stats = build_or_update_knowledge_base(PAPERS_DIR, CHROMA_DIR, CHROMA_COLLECTION)
        st.success(f"Indexed {stats.files_indexed}/{stats.files_seen} files, added or updated {stats.chunks_added} chunks.")
        if stats.skipped_files:
            st.warning("Some files were skipped:")
            for item in stats.skipped_files:
                st.write(f"- {item}")

    try:
        count = local_kb_count()
        st.metric("Local chunks", count)
    except Exception as exc:
        st.warning(f"Local KB is not ready yet: {exc}")

    st.header("Retrieval Settings")
    top_queries = st.slider("Top scored queries", 3, 10, 6)
    local_per_query = st.slider("Local chunks per query", 1, 8, 4)
    pubmed_per_query = st.slider("PubMed papers per query", 1, 10, 5)
    enable_reretrieval = st.checkbox("Enable confidence-driven re-retrieval", value=True)


default_question = """I study neuropathic pain after peripheral nerve injury.
My experiment suggests microglial activation and inflammatory cytokines increase in spinal dorsal horn,
but one candidate pathway seems inconsistent across time points.
Please identify candidate molecular targets and validation experiments."""

question = st.text_area("Research question / experimental observation", value=default_question, height=180)

if is_local_kb_empty():
    st.info(
        "Your local knowledge base is empty. Put PDF/TXT/MD files into "
        f"`{PAPERS_DIR}`, then click **Build / Update Local Knowledge Base**. "
        "You can still run PubMed-based discovery, but local evidence will be absent."
    )

if st.button("Run Med-RwR-inspired Target Discovery", type="primary"):
    if not question.strip():
        st.error("Please enter a research question or experimental observation.")
    else:
        with st.spinner("Running Observe -> Query -> Retrieve -> Reason -> Confidence -> Re-retrieval..."):
            try:
                output = run_target_discovery(
                    question,
                    local_per_query=local_per_query,
                    pubmed_per_query=pubmed_per_query,
                    top_queries=top_queries,
                    enable_reretrieval=enable_reretrieval,
                )
            except Exception as exc:
                st.exception(exc)
                st.stop()

        if output.get("demo_mode"):
            st.warning(output.get("api_warning", "OpenAI API unavailable, using demo rule-based output"))
            st.caption("Demo output only. Candidate targets below are rule-based placeholders, not formal OpenAI model inference results.")
        elif output.get("api_warning"):
            st.info(output["api_warning"])

        st.subheader("Observe")
        st.json(output["observations"])

        st.subheader("Generated Queries")
        for query in output.get("generated_queries", []):
            st.write(f"- {query}")

        st.subheader("Query Scores")
        st.dataframe(output["scored_queries"], use_container_width=True)

        st.subheader("Re-retrieval Trace")
        trace = output.get("reretrieval_trace", [])
        if trace:
            st.dataframe(trace, use_container_width=True)
        else:
            st.info("No re-retrieval trace was recorded.")

        st.subheader("Confidence-driven Re-retrieval Queries")
        if output["second_round_queries"]:
            for query in output["second_round_queries"]:
                st.write(f"- {query}")
        else:
            st.info("No second-round queries were generated.")

        st.subheader("Retrieved Evidence")
        tabs = st.tabs(["Local Evidence", "PubMed Evidence", "Second-round PubMed"])
        with tabs[0]:
            local_items = output["retrieved_evidence"]["local"]
            if not local_items:
                st.info("No local evidence was retrieved. Build the local knowledge base or add more relevant files.")
            for item in local_items:
                st.markdown(f"**{item.get('source')}** | chunk `{item.get('chunk_index')}`")
                st.write(item.get("snippet"))
        with tabs[1]:
            for item in output["retrieved_evidence"]["pubmed"]:
                if item.get("error"):
                    st.warning(f"Query failed: {item.get('query')} | {item.get('error')}")
                else:
                    st.markdown(f"**PMID {item.get('pmid')}**: {item.get('title')}")
                    st.write(f"{item.get('journal')} {item.get('year')} | {item.get('url')}")
                    st.write(item.get("abstract_snippet"))
        with tabs[2]:
            items = output["retrieved_evidence"]["second_round_pubmed"]
            if not items:
                st.info("No second-round retrieval was triggered or no new evidence was found.")
            for item in items:
                if item.get("error"):
                    st.warning(f"Query failed: {item.get('query')} | {item.get('error')}")
                else:
                    st.markdown(f"**PMID {item.get('pmid')}**: {item.get('title')}")
                    st.write(f"{item.get('journal')} {item.get('year')} | {item.get('url')}")
                    st.write(item.get("abstract_snippet"))

        result = output["result"]
        st.subheader("Model Interpretation")
        if result.get("is_demo_output"):
            st.warning("Demo output only. This section was generated by rules because the OpenAI API was unavailable.")
        st.write(result.get("mechanism_gap_analysis", "No mechanism gap analysis returned."))

        st.subheader("Confidence")
        confidence_rows = [
            {
                "priority": candidate.get("priority"),
                "target": candidate.get("target_name"),
                "confidence": candidate.get("confidence"),
                "demo_output": bool(candidate.get("is_demo_output") or result.get("is_demo_output")),
            }
            for candidate in result.get("candidates", [])
        ]
        if confidence_rows:
            st.dataframe(confidence_rows, use_container_width=True)
        else:
            st.info("No candidate confidence values were returned.")

        st.subheader("Candidate Target Ranking")
        candidates = sorted(result.get("candidates", []), key=lambda x: x.get("priority", 999))
        for candidate in candidates:
            demo_label = " | DEMO OUTPUT" if candidate.get("is_demo_output") or result.get("is_demo_output") else ""
            title = f"#{candidate.get('priority', '?')} {candidate.get('target_name', 'Unknown target')} | Confidence: {candidate.get('confidence', 'Unknown')}{demo_label}"
            with st.expander(title, expanded=True):
                if candidate.get("is_demo_output") or result.get("is_demo_output"):
                    st.warning("Demo output only. Not a formal model reasoning result.")

                st.markdown("**Mechanistic rationale (Model Interpretation)**")
                st.write(candidate.get("mechanistic_rationale", ""))

                st.markdown("**Local evidence (Retrieved Evidence)**")
                local_evidence = candidate.get("local_evidence", []) or []
                if not local_evidence:
                    st.write("No candidate-specific local evidence provided.")
                for ev in local_evidence:
                    st.write(f"- {ev.get('source', 'local source')}: {ev.get('snippet', '')}")

                st.markdown("**PubMed evidence with PMID (Retrieved Evidence)**")
                pubmed_evidence = candidate.get("pubmed_evidence", []) or []
                if not pubmed_evidence:
                    st.write("No candidate-specific PubMed evidence provided.")
                for ev in pubmed_evidence:
                    st.write(f"- PMID {ev.get('pmid', 'N/A')}: {ev.get('title', '')} - {ev.get('evidence_summary', '')}")

                st.markdown("**Experimental validation plan (Model Interpretation)**")
                for step in candidate.get("experimental_validation_plan", []) or []:
                    st.write(f"- {step}")

                st.markdown("**Limitations (Model Interpretation)**")
                for limitation in candidate.get("limitations", []) or []:
                    st.write(f"- {limitation}")

        with st.expander("Raw JSON output"):
            st.json(output)
