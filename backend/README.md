# BISNova Backend — P2 API (FastAPI)

Product Intelligence's HTTP layer. Calls P1's service over real HTTP for evidence/
answers - see `integration/p1_client.py`. Does not import P1's code in-process.

## Running it

See the root `README.md` for the full three-service local setup (P1 → P2 →
frontend). Quick version, assuming P1 is already running on port 8001:

```bash
pip install -r requirements.txt   # from repo root
uvicorn backend.main:app --reload --port 8000
```

Override P1's address if it's not on the default local port:
```bash
P1_API_BASE_URL=http://your-p1-host:8001 uvicorn backend.main:app --reload --port 8000
```

## Endpoints

### `POST /api/chat` - the one endpoint the chat UI needs
```json
// request
{ "query": "I manufacture domestic pressure cookers for household use" }

// response (matched case)
{
  "status": "matched",
  "answer": "Based on the available evidence: ...",
  "matched_product_name": "Domestic Pressure Cooker",
  "standards": [
    {
      "standard_id": "STD-001", "is_number": "IS 2347:2023",
      "title": "Domestic Pressure Cooker — Specification",
      "status": "current", "relationship_type": "primary",
      "is_mandatory": true, "source_url": "https://...", "confidence": 1.0
    }
  ],
  "confidence_score": 0.66, "confidence_label": "medium",
  "evidence_sufficient": true,
  "evidence": [ { "chunk_id": "...", "text": "...", "source_url": "..." } ],
  "sources": ["https://..."],
  "needs_clarification": false,
  "clarification_question": null,
  "clarification_options": []
}
```

For `clarification_needed`, `standards`/`evidence` are empty, `needs_clarification` is
`true`, and `clarification_options` is a list of `{label, query}` - **`query` is a
ready-to-send follow-up string** (original query + the option's label appended), so
the frontend can wire these directly into whatever "click to send a message" handler
it already has, with zero clarification-specific UI logic.

For `not_found`, everything is empty and `answer` is an honest "we don't have this
yet" message - never a guess.

### `GET /api/health`
Reports how many products/standards Product Intelligence loaded, and whether P1's
service is currently reachable (`p1_service_reachable`) - useful for confirming both
services are actually talking to each other.

### `POST /api/debug/match-product`
Product Intelligence only, no call to P1 - useful for testing product matching in
isolation, without needing P1's service running at all. **Not for the actual chat
UI** - always use `/api/chat` there.

## Design notes

- **Stateless by design.** No session/conversation state is kept server-side. A
  clarification follow-up works because `clarification_options[].query` already
  contains the augmented query text (original + chosen option) - sending it as a
  fresh `/api/chat` call re-runs Product Intelligence with enough context to resolve
  confidently.
- **P1 is a separate service, reached over real HTTP** (`integration/p1_client.py`),
  matching the team's "P2 API" / "P1 API" architecture diagram. This backend has no
  RAG/embedding dependencies at all - `requirements.txt` is just FastAPI + httpx.
- **The external API contract (`backend/models.py`) is deliberately its own set of
  models**, separate from `ProductMatchResult`/P1's `P1Output`. Internals on either
  side can keep changing without breaking whatever the frontend is built against.
