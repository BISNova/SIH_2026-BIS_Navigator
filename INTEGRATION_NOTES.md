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

## Confirmed bug: P1's RAG was retrieving synthetic test data, not real BIS content

**This was a real, verified bug, not a hunch.** Direct inspection of
`p1_service/data/embeddings/all_embeddings.json` (P1's shipped, pre-built
ChromaDB source) showed all 102 embedded records were P1's own synthetic
test fixtures ("Sample BIS Product Standard A/B/C... Synthetic dataset
for BIS Navigator RAG testing. Not an official BIS document."), aliased
to our real `STD-001`/`STD-002`/`STD-003` via a hardcoded dict in
`chroma_store.py`. Every semantic-retrieval answer was therefore grounded
in fake placeholder text - the only genuinely real content reaching
answers was via `P4EvidenceBuilder`'s structured evidence (test
requirements, certification steps), which was always correctly sourced.

**Fixed** once real raw source documents (36 real standard PDFs, 21
product manuals, 22 QCOs, 13 guidelines, 2 hallmarking HTML pages) were
delivered:
1. `integration/ingest_real_documents.py` - runs P1's own (already
   well-written, just never exercised against real data before)
   `extract_text_from_pdf` → `clean_text` → `chunk_text` functions
   against the real files, mapped to their correct real `standard_id`.
   Produced 220 real chunks across 6 of our 7 structured standards.
2. `chroma_store.py`'s hardcoded `SYN-STD-*` alias removed - real
   content is now embedded and queried under its own real canonical ID
   directly, no translation needed.
3. The old synthetic chunk files moved to
   `p1_service/data/synthetic_test_data_backup/` (kept for her own
   isolated unit tests, no longer part of the live knowledge base).

**Verified for real**, not just by re-running tests: queried the
regenerated ChromaDB directly and confirmed genuine extracted BIS
Product Manual/Certification Guideline text comes back, not synthetic
placeholder text. Added `tests/test_real_kb_ingestion.py`, including a
regression test that explicitly asserts the synthetic marker text never
appears in ingested content again.

**What this delivery does NOT include:** structured `products.json`/
`standards.json`/`product_standard_mapping.json` entries. The raw
delivery covers ~36 standards (helmets, toys, cement, LPG cylinders,
footwear, tyres, and more), but only 7 are represented in the curated
structured tables (3 products). The other ~29 raw documents are real
and sitting ready to use, but adding them requires actual curation
(product categorization, mandatory flags, confidence scores) - not
something to silently infer. See the root README's "Adding more
Knowledge Base data" section.

**Two data-quality mismatches surfaced while mapping files to
standard_ids** (used anyway - real content beats none - but worth
Person 4 double-checking): `STD-001`'s structured record says edition
2023, the matching raw file is filenamed 2017 (though the file's own
header text says "AS PER IS 2347:2023"); `STD-006`'s structured record
says edition 2024, the matching raw file is the 2009 edition. `STD-007`
(IS 1418:2009) has no corresponding raw file in this delivery at all.

## KB sync

`knowledge_base/` (P2's copy) and `p1_service/data/adapter/` (P1's copy)
were verified byte-for-byte identical across every shared table
(`products`, `standards`, `product_standard_mapping`,
`conformity_routes`, `certification_steps`, `tests`, `schemes`, `qcos`,
`product_attributes`, `documents`) at integration time. There's no
automated sync between them - if Person 4 updates one, the other needs
updating manually until/unless a shared single source of truth is set
up.
