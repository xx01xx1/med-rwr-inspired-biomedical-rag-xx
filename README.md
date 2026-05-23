# Med-RwR-inspired Research RAG Target Finder

This is a lightweight, runnable prototype for neuropathic pain target discovery. It is inspired by the reasoning-with-retrieval idea in Med-RwR, but it does not reproduce the paper and does not train a model.

The system:

- reads your local PDF/TXT/MD papers and notes;
- builds a Chroma local vector database with sentence-transformers embeddings;
- generates and scores retrieval queries with transparent rules;
- retrieves local evidence and PubMed/NCBI evidence;
- uses the OpenAI API for final biomedical reasoning;
- separates **Retrieved Evidence** from **Model Interpretation**;
- triggers a second PubMed retrieval round when candidate confidence is Low or Medium.

## 1. Project Structure

```text
research-rag-target-finder/
  app.py
  requirements.txt
  .env.example
  data/
    my_papers/
  db/
  src/
    ingest.py
    retriever.py
    pubmed.py
    prompts.py
    query_generator.py
    query_scorer.py
    evidence.py
    confidence.py
    target_ranker.py
    workflow.py
```

Put your papers, experiment notes, and reference files in:

```text
data/my_papers/
```

Supported file types: `.pdf`, `.txt`, `.md`.

## 2. Install Dependencies

Open a terminal in this project folder.

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install packages:

```powershell
pip install -r requirements.txt
```

The first knowledge-base build may download the local embedding model `sentence-transformers/all-MiniLM-L6-v2`.

## 3. Configure API Keys

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Open `.env` and fill in:

```text
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
NCBI_EMAIL=your_email@example.com
```

`NCBI_API_KEY` is optional. It can improve rate limits if you have one.

## 4. Add Your Papers

Copy your PDFs, TXT files, or Markdown notes into:

```text
data/my_papers/
```

Examples:

```text
data/my_papers/neuropathic_pain_review.pdf
data/my_papers/my_rnaseq_notes.md
data/my_papers/experiment_results.txt
```

## 5. Build the Local Knowledge Base

Run the web app:

```powershell
streamlit run app.py
```

In the sidebar, click:

```text
Build / Update Local Knowledge Base
```

This reads your files, chunks the text, embeds the chunks locally, and stores them in Chroma under `db/chroma`.

If the local knowledge base is empty, the app gives a friendly prompt. You can still run PubMed-only discovery, but local evidence will be absent.

## 6. Run Target Discovery

In the main text box, enter your research question or experimental observation, for example:

```text
I study neuropathic pain after peripheral nerve injury.
My experiment suggests microglial activation and inflammatory cytokines increase in spinal dorsal horn,
but one candidate pathway seems inconsistent across time points.
Please identify candidate molecular targets and validation experiments.
```

Then click:

```text
Run Med-RwR-inspired Target Discovery
```

The app will run:

1. **Observe**: extracts disease, cell type, experimental phenomenon, and possible mechanism contradiction terms.
2. **Reason**: identifies likely mechanism gaps through the final OpenAI reasoning prompt.
3. **Query**: generates multiple retrieval queries.
4. **Query Scoring**: scores queries with transparent rules that approximate Query Semantic Reward.
5. **Retrieve**: retrieves local Chroma evidence and PubMed evidence through NCBI E-utilities.
6. **Reason**: ranks candidate molecular targets.
7. **Answer**: outputs target ranking, evidence, mechanism explanation, and validation experiments.
8. **Confidence**: gives each target High/Medium/Low confidence.
9. **Re-retrieval**: if confidence is Low or Medium, generates second-round PubMed queries and reranks candidates.

## 7. Output Format

Each candidate target includes:

- target name;
- priority;
- mechanistic rationale;
- local evidence;
- PubMed evidence with PMID;
- experimental validation plan;
- confidence;
- limitations.

The interface explicitly separates:

- **Retrieved Evidence**: local snippets and PubMed records;
- **Model Interpretation**: mechanism rationale, target prioritization, validation suggestions, and limitations.

## 8. Important Notes

This is a research-assistance prototype, not a clinical decision system.

The query scorer and confidence estimator are rule-based and intentionally simple. They are designed to be readable and editable by beginners.

PubMed evidence quality depends on the generated query terms and NCBI availability. Always read the original papers before making experimental decisions.
