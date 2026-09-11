# BISNova — AI-powered Assistant for Indian Standards & BIS Services

An AI-powered conversational assistant that helps MSMEs, manufacturers, and consumers
identify applicable Indian Standards, certification requirements, and BIS compliance
information through natural language — every answer grounded in curated BIS sources
with citations, never guessed.

## Architecture

```
FRONTEND (React + Vite)
   │  user query
   ▼
P2 API (backend/)                    ← Product Intelligence
   │  matches product, looks up applicable standards,
   │  scores confidence, decides: matched / needs clarification / not found
   ▼
P1Input  (integration/adapter.py builds this)
   │
   ▼  HTTP POST /p1/process
P1 API (p1_service/)                 ← Evidence / RAG service, runs as its OWN process
   │
   ▼
P1Service → RAG pipeline → P4 knowledge base + Gemini
   │
   ▼
P1Output  (HTTP response back to P2)
   │
   ▼
P2 orchestration layer               ← merges P2's product/standards data
   │                                    with P1's answer/evidence/citations
   ▼
FRONTEND
```

**P1 and P2 are two separately running services**, not one monolith - P2 calls P1
over real HTTP (see `integration/p1_client.py`). Both need to be running for the
chat to return a real answer.

## Repository structure

```
BISNova/
├── frontend/               React + Vite chat UI (P5)
├── backend/                 P2's API - Product Intelligence's HTTP layer
├── product_intelligence/    Product → Standard matching engine (P2)
├── p1_service/               P1's Evidence/RAG service - a separate deployable app
├── integration/               The adapter + HTTP client connecting P2's output
│                              to P1's HTTP API
├── knowledge_base/            P2's copy of the curated BIS data (products, standards,
│                              mappings, etc.) - P1 has its own copy at
│                              p1_service/data/adapter/, kept in sync with this one
├── tests/                     End-to-end integration tests across P2 + P1
└── requirements.txt            Single pip install for P2 + integration
```

## Local setup — full walkthrough

You need **three things running at once**: P1's service (port 8001), P2's backend
(port 8000), and the frontend (port 5173).

### 0. Prerequisites

- Python 3.10+
- Node.js 18+
- A [Gemini API key](https://aistudio.google.com/apikey) (for real answers - see the
  sandbox-mock fallback below if you don't have one yet)

### 1. Set up P1 (the Evidence/RAG service)

```bash
cd p1_service
pip install -r requirements.txt

cp .env.example .env
# then edit .env and paste your real GEMINI_API_KEY
```

Run it:
```bash
uvicorn api.server:app --port 8001
```

Leave this running. Verify it's up: `curl http://127.0.0.1:8001/health`

**No Gemini key / no internet yet?** Use the sandbox-mocked version instead - it
mocks only the embedding model and the Gemini call, everything else (real P4
evidence retrieval, reranking, citations) is real:
```bash
uvicorn sandbox_mocks.run_mocked_server:app --port 8001
```

### 2. Set up P2 (Product Intelligence backend)

In a **new terminal**, from the repo root:
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Verify it's up and can see P1: `curl http://127.0.0.1:8000/api/health` — check
`"p1_service_reachable": true` in the response.

### 3. Set up the frontend

In a **third terminal**:
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Try asking: *"I manufacture domestic pressure cookers
for household use"* - it should come back with the matched product, applicable
standards (mandatory ones flagged), and a real cited answer.

## Running tests

```bash
pip install -r requirements.txt
python3 -m pytest product_intelligence/tests/ tests/test_full_integration.py backend/tests/ -v
```

27 tests. The integration and backend test files each boot P1's real service (sandbox-mocked)
as a live subprocess automatically - you don't need P1 running manually to run tests.

## Current scope

Real, curated data exists for **3 products** (domestic pressure cookers, electric water
heaters, gold jewellery/hallmarking) across **7 standards**. Matching, confidence
scoring, clarification, multi-standard handling, and real RAG retrieval/citation are
all functional against this set - extending to more products/standards is a data
task (add rows to `knowledge_base/`, mirrored in `p1_service/data/adapter/`), not a
code change.

**Known gaps, intentionally not built yet:**
- "Explore Standards" catalog page - the button exists in the UI (Hero section,
  sidebar, standards card) but currently opens the chatbot with a canned query
  rather than a dedicated browsable page.
- Testing labs data (`knowledge_base/structured/labs.json` has real entries) isn't
  wired into the frontend's lab list yet - `StandardsAndLabs.jsx` still shows
  placeholder lab entries.
- General knowledge questions ("What is BIS?") aren't routed anywhere yet - Product
  Intelligence only handles product-matching queries, so these currently return
  "not found" rather than a general answer. Worth an intent-routing pass later.

## Fixes applied to P1's delivered code during integration

A few small but real issues were found and fixed while wiring this together - noted
here so nothing looks like an unexplained diff:
- `p1_service/rag/pipeline/evidence_pipeline.py` had a dual-import-path bug (bare
  imports like `from answer.gemini_generator import ...` resolved to a *different*
  module object than the `rag.`-prefixed imports used everywhere else in the
  codebase, so mocking/patching one didn't affect the other). Normalized to one
  consistent import style.
- `google-genai` was used (`from google import genai`) but missing from
  `requirements.txt`.
- `.gitignore` patterns pointed at `rag/data/...` but the actual generated data
  lives at `data/...` (project root) - none of the original patterns ever matched.

See `INTEGRATION_NOTES.md` for the full contract details, field-by-field mapping
between P2 and P1, and open questions still worth confirming with the team.
