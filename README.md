# MedCite Sentinel Prototype

MedCite Sentinel is a local medical evidence RAG prototype. It lets anyone ask a medical question, retrieves trusted medical literature, checks whether the evidence is strong enough, and returns a grounded answer with citations and a workflow trace.

## Tech Stack

- React 18 frontend
- Tailwind CSS utility styling
- Vanilla browser JavaScript, no build step
- Python `ThreadingHTTPServer` backend
- PubMed / NCBI E-utilities retrieval
- Optional Gemini or OpenAI synthesis

## Project Structure

```text
MedCite-Sentinel/
├── backend/
│   ├── server.py
│   ├── retrieval.py
│   └── agents/
│       ├── query_agent.py
│       ├── retrieval_agent.py
│       ├── ranking_agent.py
│       └── hallucination_guard.py
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── docs/
│   ├── ARCHITECTURE.md
│   ├── medcite-sentinel-workflow.docx
│   └── workflow-chart.svg
├── screenshots/
│   ├── home-page.png
│   ├── result-summary.png
│   ├── result-sources.png
│   └── workflow.png
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── run-server.bat
```

## Run Locally

From this folder:

```powershell
.\run-server.bat
```

Then open:

```text
http://127.0.0.1:8000
```

If you prefer to run it directly:

```powershell
C:\Users\sruth\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe backend\server.py
```

## What It Does

- Accepts medical questions from any user.
- Rewrites questions into retrieval-friendly medical searches.
- Searches trusted sources through PubMed-indexed literature.
- Filters weak or irrelevant evidence.
- Ranks accepted sources by relevance.
- Refuses to answer when evidence is insufficient.
- Returns citations and the agent workflow trace with each answer.

## Agent Workflow

The prototype follows this pipeline:

1. `QueryUnderstandingAgent`
2. `ClarificationAgent`
3. `ClinicalQueryRewriterAgent`
4. `RetrievalAgent`
5. `TrustedSourceFilterAgent`
6. `RelevanceRankingAgent`
7. `HallucinationGuardAgent`
8. `ResponseGenerationAgent`
9. `CitationAgent`

The visual workflow chart is included as:

```text
docs/workflow-chart.svg
```

## Answer Length

The backend now keeps grounded answers complete while still cleaning extra whitespace.

## Frontend Notes

The React and Tailwind frontend is served from:

```text
frontend/index.html
frontend/app.js
frontend/styles.css
```

This prototype uses CDN-loaded React and Tailwind so it can run without an npm build step.

## Screenshots

Screenshots are stored in:

```text
screenshots/
```

- `home-page.png`
- `workflow.png`
- `result-summary.png`
- `result-sources.png`

## Optional Environment Variables

Create a `.env` file or set environment variables before running:

- `GEMINI_API_KEY`: enables Gemini query rewriting and grounded answer generation.
- `GEMINI_MODEL`: defaults to `gemini-1.5-flash`.
- `OPENAI_API_KEY`: enables OpenAI grounded answer synthesis.
- `OPENAI_MODEL`: defaults to `gpt-4.1-mini`.
- `NCBI_EMAIL`: recommended by NCBI for E-utilities requests.

Without an LLM API key, the app still retrieves trusted evidence and can return extractive citation-backed answers.

## Important Note

This is a prototype for evidence lookup and summarization. It is not a substitute for professional medical care or emergency guidance.
