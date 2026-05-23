from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET
from typing import Any

import requests


BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _ncbi_params() -> dict[str, str]:
    params = {"tool": "med_rwr_target_finder"}
    email = os.getenv("NCBI_EMAIL")
    api_key = os.getenv("NCBI_API_KEY")
    if email:
        params["email"] = email
    if api_key:
        params["api_key"] = api_key
    return params


def search_pubmed(query: str, retmax: int = 8, sleep_seconds: float = 0.34) -> list[dict[str, Any]]:
    """Search PubMed and return title/abstract evidence with PMID."""
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": str(retmax),
        "sort": "relevance",
        **_ncbi_params(),
    }
    search_resp = requests.get(f"{BASE_URL}/esearch.fcgi", params=search_params, timeout=20)
    search_resp.raise_for_status()
    pmids = search_resp.json().get("esearchresult", {}).get("idlist", [])
    if not pmids:
        return []

    time.sleep(sleep_seconds)
    fetch_params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        **_ncbi_params(),
    }
    fetch_resp = requests.get(f"{BASE_URL}/efetch.fcgi", params=fetch_params, timeout=30)
    fetch_resp.raise_for_status()
    return parse_pubmed_xml(fetch_resp.text, query)


def parse_pubmed_xml(xml_text: str, query: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    articles: list[dict[str, Any]] = []

    for article in root.findall(".//PubmedArticle"):
        medline = article.find("MedlineCitation")
        if medline is None:
            continue

        pmid = medline.findtext("PMID", default="")
        article_node = medline.find("Article")
        if article_node is None:
            continue

        title_node = article_node.find("ArticleTitle")
        title = " ".join("".join(title_node.itertext()).split()) if title_node is not None else ""

        abstract_parts = []
        for abstract_text in article_node.findall(".//AbstractText"):
            label = abstract_text.attrib.get("Label")
            text = "".join(abstract_text.itertext())
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        abstract = " ".join(" ".join(abstract_parts).split())

        journal = article_node.findtext("Journal/Title", default="")
        year = (
            article_node.findtext("Journal/JournalIssue/PubDate/Year")
            or article_node.findtext("Journal/JournalIssue/PubDate/MedlineDate")
            or ""
        )

        articles.append(
            {
                "query": query,
                "pmid": pmid,
                "title": title,
                "journal": journal,
                "year": year,
                "abstract": abstract,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
            }
        )
    return articles


def search_pubmed_for_queries(queries: list[str], per_query: int = 5) -> list[dict[str, Any]]:
    seen_pmids = set()
    merged: list[dict[str, Any]] = []
    for query in queries:
        try:
            hits = search_pubmed(query, retmax=per_query)
        except Exception as exc:
            merged.append({"query": query, "error": str(exc), "pmid": "", "title": "", "abstract": ""})
            continue
        for hit in hits:
            pmid = hit.get("pmid")
            if pmid and pmid not in seen_pmids:
                seen_pmids.add(pmid)
                merged.append(hit)
    return merged
