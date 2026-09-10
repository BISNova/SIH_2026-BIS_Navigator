# Integration Notes v3 — Real KB + Real RAG

## The one real limitation - read this before running anything

Two things were built to work around this **for testing only**:

1. **`integration/mock_embedder.py`** - a deterministic hash-based fake embedder with the same
   `.encode()` interface as `sentence_transformers.SentenceTransformer`. It has **zero semantic
   understanding** - it's only good for proving the wiring works (chunks index, retrieval returns
   results, the full pipeline runs without crashing), never for judging answer quality.
2. **`integration/generate_mock_embeddings_and_index.py`** - runs Person 1's *actual*
   `embed.py`/`chroma_store.py` code with only the model swapped, so her real ingestion/indexing
   logic gets exercised for real.

**You saw this limitation in action already**: the "electric geyser" test query got "I don't have
enough reliable evidence to answer this question" - that's her real sufficiency checker correctly
refusing to answer on noisy, non-semantic mock embeddings. That's a good sign (the honesty
safeguard works), not a bug. **On a machine with real internet access, delete the
`mock.patch(...)` blocks in `run_pipeline.py` / test files, run `embed.py` normally, and every
answer will be grounded in actually-relevant evidence.**

## What's real and copyright-safe about the evidence text

Person 4's KB delivery has structured metadata and curated summaries (`scope_summary`,
certification steps, test requirements) but **no raw extracted document text** - no PDFs, no
verbatim clauses. `integration/build_evidence_chunks.py` builds 52 evidence chunks (covering all
7 real standards) entirely from Person 4's own paraphrased summaries, each chunk explicitly
prefixed `"[Curated summary - not verbatim BIS text]"` so nobody mistakes this for real extracted
clause text in a demo.

**You mentioned Person 4 may add raw source files later.** When that happens, the correct pipeline
becomes: `raw file -> ingestion/extract.py -> clean.py -> chunk.py -> merge with documents.json
metadata -> embed.py -> chroma_store.py`, which **replaces** `build_evidence_chunks.py` entirely -
her `chunk.py` already outputs a compatible shape (chunk_id/text/section/section_header), it just
needs the same document-metadata merge step our script does now. Nothing else in the integration
layer (adapter, orchestrator) needs to change - they only care about `P1Input`/`P1Output`, not
where the chunks came from.

## Two questions to Person 1 - still open from last round

Her `schemas/p1_input.py` is **unchanged** since the last integration - both flagged questions
are still live:

1. `matched_product` is still a plain string, not an object. The full object rides along as an
   additive `matched_product_details` field for now.
2. `clarification_options` still doesn't exist in her schema at all - additive-only on our side.

**One new thing to flag, discovered while wiring the real data**: her `ApplicableStandard.mandatory`
is a plain `bool`, but our real data has a genuine third state - `is_mandatory=None` meaning "no
conformity route on file for this standard yet," which is very different from "confirmed not
mandatory." The adapter currently collapses `None -> False` to fit her schema, which means her
`mandatory=False` can now mean either "actually not mandatory" or "we don't know." The full
tri-state value is preserved on `applicable_standards_full` regardless. Worth asking her whether
`mandatory` should become `Optional[bool]` on her end too.

## Running it

```bash
pip install -r product_intelligence/requirements.txt
pip install chromadb sentence-transformers   # needs real internet for the model itself

# One-time setup (sandbox: uses mock embedder; real machine: run her embed.py directly instead)
python3 -m integration.build_evidence_chunks
python3 -m integration.generate_mock_embeddings_and_index

# Tests
python3 -m pytest product_intelligence/tests/ tests/ -v    # 17 passing

# See it live
python3 -m integration.run_pipeline
```

## On a real machine with internet access

1. Skip `generate_mock_embeddings_and_index.py` entirely.
2. `cd evidence_engine/rag && python3 embeddings/embed.py` (her real code, real model, downloads
   ~90MB once).
3. `python3 vectorstore/chroma_store.py` (or however she wires indexing into her own runner).
4. In `integration/run_pipeline.py`, replace `build_evidence_pipeline()`'s mock-patched
   construction with a plain `EvidencePipeline()` call.
5. Everything else - the adapter, the orchestrator, the short-circuit logic for
   clarification/not_found - is already real and doesn't change.
