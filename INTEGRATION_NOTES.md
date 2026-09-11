# Integration Notes — P2 ↔ P1 (HTTP-based)

## Architecture: two separate services, not a monolith

P1 (Evidence/RAG) is now a standalone deployed FastAPI service
(`p1_service/`), not something P2 imports in-process. P2's backend
(`backend/`) calls it over real HTTP via `integration/p1_client.py`.
This replaced an earlier in-process integration - if you find references
to that elsewhere (old chat history, old docs), they're superseded by
this document.

## The contract

`integration/p1_contract.py` mirrors P1's actual
`p1_service/rag/schemas/p1_input.py` / `p1_output.py` field-for-field,
defined independently (no shared Python import between the two
services - just a matching JSON shape). If P1's schema changes, this
file needs a matching update.

### P2 → P1 (`P1InputPayload`)

| Field | Type | Notes |
|---|---|---|
| `query` | str | verbatim user query |
| `normalized_query` | str | cleaned version |
| `status` | str | `"matched"` / `"clarification_needed"` / `"not_found"` |
| `matched_product` | object | `{product_id, canonical_name, attributes}` |
| `applicable_standards` | list | see below |
| `confidence_score` / `confidence_label` | float / str | product-match confidence |
| `needs_clarification` / `clarification_question` | bool / str | |
| `language` | str | defaults `"en"` - not yet wired to a frontend toggle |

Each `applicable_standards` entry carries **both** the rich fields
(`is_number`, `title`, `relationship_type`, `status`, `source_url`,
`curated_confidence`) and older compatibility fields (`standard_title`,
`relevance`, `mandatory`) kept in sync with the rich ones, since P1's
schema retains both for backward compatibility with her own earlier code/tests.

### P1 → P2 (`P1OutputPayload`)

`answer`, `evidence[]`, `sources[]`, `confidence_score`,
`confidence_label`, `evidence_sufficient`, `clarification_needed`,
`clarification_question` - unchanged shape from earlier integration
rounds.

## Two real, still-open questions for P1

1. **`mandatory` is a plain, non-optional `bool`** in her schema. Our
   real data has a genuine third state - `is_mandatory=None` means "no
   conformity route on file for this standard yet," which is different
   from "confirmed not mandatory." The adapter collapses `None → False`
   to fit her schema (see `adapter.py`'s docstring). The full tri-state
   value is only visible in the rich fields, not the compatibility
   ones. Worth asking whether `mandatory` should become
   `Optional[bool]`.

2. **`curated_confidence` is a string** in her schema; our real KB
   stores a raw float (0.0–1.0). The adapter buckets it
   (high ≥0.75, medium ≥0.45, else low) - reasonable, but the exact
   thresholds are a judgment call worth confirming, not a spec either
   side agreed on explicitly.

## Bugs found and fixed in P1's delivered code

See the root `README.md`'s "Fixes applied to P1's delivered code"
section - the dual-import-path bug in `evidence_pipeline.py`, the
missing `google-genai` dependency, and the `.gitignore` path mismatch.
All three were found by actually booting her service and testing it
live, not by code review alone.

## Testing approach

Both `tests/test_full_integration.py` and `backend/tests/test_backend_api.py`
boot P1's real service as a live subprocess (`sandbox_mocks.run_mocked_server` -
only the embedding model and Gemini calls are mocked, everything else, including
real P4 evidence retrieval, is genuine). This is deliberately a real HTTP
round-trip against her actual code, not a hand-written stub of what we assume her
API does.

One thing worth knowing if you extend these tests: running both test files
together in one pytest invocation used to hang, because both subprocess servers
open the same ChromaDB SQLite file sequentially, and a hard `SIGKILL` didn't give
ChromaDB a chance to release its lock before the next process tried to open it.
Fixed by using a graceful `terminate()` (SIGTERM) with a `kill()` fallback only if
that doesn't work within 10s. If you add a third test file with its own P1
subprocess fixture, copy that shutdown pattern, not a bare `kill()`.

## KB sync

`knowledge_base/` (P2's copy) and `p1_service/data/adapter/` (P1's copy)
were verified byte-for-byte identical across every shared table
(`products`, `standards`, `product_standard_mapping`,
`conformity_routes`, `certification_steps`, `tests`, `schemes`, `qcos`,
`product_attributes`, `documents`) at integration time. There's no
automated sync between them - if Person 4 updates one, the other needs
updating manually until/unless a shared single source of truth is set
up.
