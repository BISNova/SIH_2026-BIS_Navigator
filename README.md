# BISNova — AI-powered Assistant for Indian Standards & BIS Services

An AI-powered conversational assistant that helps MSMEs, manufacturers, and consumers
identify applicable Indian Standards, certification requirements, and BIS compliance
information through natural language — every answer grounded in curated BIS sources
with citations, never guessed.

**Current status: fully working end-to-end, tested (30/30 automated tests). The only
remaining step before this is production/demo-ready is adding more Knowledge Base
data — see "Adding more Knowledge Base data" below. Everything else (matching,
confidence scoring, clarification, RAG, citations, the full UI including Explore
Standards and real lab data) already works.**

## New since the internal hackathon

Post-hackathon, based on judges' feedback and product requests, this round added:

- **Multilingual input** - non-English queries (Hindi, Tamil, Bengali, etc.) are
  detected and translated to English before matching, using free tools only (no
  Gemini/OpenAI cost) - see `product_intelligence/src/language.py`.
- **Conversation memory** - follow-up questions ("what tests are needed") resolve
  against the last matched product in the same chat session.
- **Query-result caching**, **list/aggregate query handling** ("list all mandatory
  standards"), **feedback capture** (👍/👎), a **"last verified" timestamp** on every
  standard, and a **KB auto-update scraper with a staging/review queue** - all
  directly answering the three pieces of judges' feedback from the internal
  hackathon (see below).
- **Frontend**: realistic chat history (no fake pre-seeded conversations, matching
  Claude/ChatGPT), free non-AI chat auto-naming, markdown-to-plain-text answers,
  confidence badges, and fixed navigation bugs (Standards link, FAQ page
  navigation).

**See `learning.md` for a plain-English explanation of the tech/approach behind
every one of these**, written for a beginner developer picking up this codebase.

## Judges' feedback from the internal hackathon - what was addressed

1. *"No caching system"* → query-result cache built (`backend/query_cache.py`).
   Semantic/embedding caching noted as a documented next step (needs an embedding
   model, which lives on P1's side, not P2's).
2. *"Fails on 'give me 5 certifications on X' style queries"* → list-query detection
   routes to a structured KB filter instead of RAG (`backend/list_query.py`).
3. *"No auto-update from BIS sources"* → scraper + content-hash change detection +
   staging/review queue built (`backend/kb_updater/`). The live scrape against
   bis.gov.in couldn't be tested from this project's development sandbox (see that
   module's docstring) - the page was confirmed genuinely scrapable via a separate
   tool, and the code is fully unit-tested with mocked HTML.

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

**P1 and P2 are two separately running services**, not one monolith — P2 calls P1
over real HTTP (see `integration/p1_client.py`). Both need to be running for the
chat to return a real answer.

## Repository structure

```
BISNova/
├── frontend/               React + Vite chat UI, landing page, FAQ page,
│                            Explore Standards catalog page
├── backend/                 P2's API - Product Intelligence's HTTP layer,
│                            plus catalog endpoints (standards, labs)
├── product_intelligence/    Product → Standard matching engine (P2)
├── p1_service/               P1's Evidence/RAG service - a separate deployable app
├── integration/               The adapter + HTTP client connecting P2's output
│                              to P1's HTTP API
├── knowledge_base/            P2's copy of the curated BIS data (products, standards,
│                              mappings, labs, etc.) - P1 has its own copy at
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
- A [Gemini API key](https://aistudio.google.com/apikey) (for real answers — see the
  sandbox-mock fallback below if you don't have one yet, e.g. for a quick demo
  without setting anything up)

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

**No Gemini key / no internet yet?** Use the sandbox-mocked version instead — it
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

Open `http://localhost:5173`.

## Trying it out

- **Chat**: ask *"I manufacture domestic pressure cookers for household use"* — you
  should get the matched product, applicable standards (mandatory ones flagged), and
  a real cited answer.
- **Explore Standards** (Hero section button, sidebar nav item, or the "Standards &
  Labs" section on the landing page): browse every standard currently in the
  knowledge base, searchable by name/category/IS number, with a one-click "Ask
  BISNova" on each card.
- **Testing & Labs** (landing page): real, searchable list of BIS-recognized
  laboratories — filter by city or state.
- **FAQ page**: static reference content for common BIS questions.

## Running tests

```bash
pip install -r requirements.txt
python3 -m pytest product_intelligence/tests/ tests/ backend/tests/ -v
```

94 tests. The integration and backend test files each boot P1's real service
(sandbox-mocked) as a live subprocess automatically — you don't need P1 running
manually to run tests.

## Adding more Knowledge Base data

`knowledge_base/raw/` now contains real BIS source documents (standards, product
manuals, QCOs, certification guidelines, hallmarking pages) — 36 standards' worth,
though only 7 are currently wired into the structured tables and real RAG ingestion
(see `integration/ingest_real_documents.py`'s `FILE_TO_STANDARD_MAP`). To add more:

1. Add rows to **both** `knowledge_base/structured/*.json` (P2's copy) and
   `p1_service/data/adapter/*.json` (P1's copy — keep them identical; no automated
   sync yet) for the new product/standard/mapping.
2. If a matching raw document exists in `knowledge_base/raw/`, add an entry to
   `FILE_TO_STANDARD_MAP` in `integration/ingest_real_documents.py`, then re-run:
   ```bash
   python3 -m integration.ingest_real_documents
   cd p1_service && python3 rag/embeddings/embed.py   # needs real internet for the model
   ```
   (indexing into Chroma happens via `vectorstore/chroma_store.py` — see that file's
   `main()` block or wire it into your own run script).
3. No other code changes needed — Product Intelligence, the Explore Standards
   catalog, and P1's RAG pipeline all pick up new structured/embedded data
   automatically on next restart.

See `knowledge_base/manifest.csv` for the full schema reference across all 16
tables, and `INTEGRATION_NOTES.md` for exactly which fields flow from P2 to P1, and
for the real-data-ingestion bug found and fixed in this project's most recent round.

## Known gaps (by design, not oversights)

- General knowledge questions ("What is BIS?") aren't routed anywhere yet — Product
  Intelligence only handles product-matching queries, so these currently return
  "not found" rather than a general answer. The FAQ page covers common questions
  statically in the meantime. Worth an intent-routing pass later.
- No conversation memory across turns — each query is handled statelessly
  (clarification follow-ups work by resending an augmented query, not by server-side
  session state).

## Fixes applied to P1's delivered code during integration

A few small but real issues were found and fixed while wiring this together — noted
here so nothing looks like an unexplained diff:
- `p1_service/rag/pipeline/evidence_pipeline.py` had a dual-import-path bug (bare
  imports like `from answer.gemini_generator import ...` resolved to a *different*
  module object than the `rag.`-prefixed imports used everywhere else in the
  codebase, so mocking/patching one didn't affect the other). Normalized to one
  consistent import style.
- `google-genai` was used (`from google import genai`) but missing from
  `requirements.txt`.
- `p1_service/.gitignore` patterns pointed at `rag/data/...` but the actual
  generated data lives at `data/...` (project root) — none of the original patterns
  ever matched.
- Frontend had a broken import (`./components/HowBisiHelps`, renamed to
  `HowBisNovaHelps.jsx` in a later edit but the import wasn't updated) that failed
  the production build entirely.

See `INTEGRATION_NOTES.md` for the full P2↔P1 contract details, field-by-field
mapping, and open questions still worth confirming with the team.
