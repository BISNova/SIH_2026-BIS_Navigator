# Person 2 — Product Intelligence Module (v2.1 — answers Person 1's contract questions)

**v2.1 change:** added the two fields Person 1 requested after reviewing
the v2 contract:
- `ProductCandidate.attributes` (subcategory/material/typical_use) — the
  matched product's own curated attributes, not NLP-extracted from the
  user's exact phrasing
- `ApplicableStandard.curated_confidence` — Person 4's own confidence in
  that specific mapping's correctness (high/medium/low), distinct from
  the product-match `confidence_score` at the top level

See "Answers to Person 1's contract questions" near the bottom of this
file for the full reasoning on each field she asked about, including the
one deliberate divergence from her proposed shape (a list of applicable
standards, not one `selected_standard_id`).

**v2 change:** rebuilt around Person 4's real KB schema doc. The
biggest structural change from v1: `products` and `standards` are now
separate tables joined by `product_standard_mapping` (many-to-many),
so one product can have multiple applicable standards
(e.g. mandatory safety + related performance) instead of being forced
into a single standard_id. This is a two-stage pipeline now:
**identify the product → look up all its standards.**

Still built against placeholder data (`IS-XXXX-DEMO-*` standard IDs).
Swap the four CSVs in `data/` for Person 4's real, verified data —
nothing else needs to change (see "The data contract" below).

## Folder structure

```
person2_product_intelligence/
├── data/
│   ├── products.csv                   <- PLACEHOLDER. What queries match against.
│   ├── standards.csv                  <- PLACEHOLDER. First-class entity, has status/versioning.
│   ├── product_standard_mapping.csv   <- PLACEHOLDER. Many-to-many, relationship_type.
│   ├── documents.csv                  <- PLACEHOLDER. Source/provenance for citations.
│   └── clarification_bank.json        <- pre-written questions for known-ambiguous pairs
├── src/
│   ├── config.py         <- all tunable thresholds + file paths live here
│   ├── schemas.py         <- THE CONTRACT: what this module returns to Person 1/5
│   ├── normalize.py       <- text cleanup before matching
│   ├── data_loader.py     <- reads/validates all four CSVs
│   ├── matcher.py         <- TF-IDF + cosine similarity, matches against `products`
│   ├── confidence.py      <- decides matched / clarification_needed / not_found
│   ├── clarification.py   <- looks up the right question for ambiguous product pairs
│   └── pipeline.py        <- the ONE class Person 5 imports; runs both stages
├── tests/
│   └── test_pipeline.py   <- 8 passing tests, including the multi-standard case
├── demo.py                <- interactive CLI to test queries by hand
├── requirements.txt
└── README.md              <- this file
```

## Running it

```bash
pip install -r requirements.txt
python3 -m pytest tests/ -v      # should show 8 passed
python3 demo.py                  # interactive testing
```

Try in `demo.py`:
- `"stainless steel pressure cooker for home use"` → matched, high confidence, **two** standards shown (mandatory + related)
- `"bottle"` → clarification_needed (plastic vs glass)
- `"interstellar rocket engine"` → not_found

## The data contract (read this before touching anything else)

`src/schemas.py` defines `ProductMatchResult`. Three possible outcomes:

| `status` | Meaning | What Person 5 should do |
|---|---|---|
| `matched` | Confident product identification | Pass `applicable_standards` (a **list**, not one ID) to Person 1's RAG module |
| `clarification_needed` | Top-2 product candidates too close together | Show `clarification_question` + `clarification_options`; re-run `process()` with the user's answer appended |
| `not_found` | Best score didn't clear the floor | Tell the user honestly — don't call RAG with a guessed product |

`applicable_standards` items carry `relationship_type` (`mandatory` /
`related`), `status` (`current` / `withdrawn`), and `source_url` for
citation. Mandatory standards are always sorted first — the UI should
lead with those, not bury them among related ones.

## Why two separate tables now, and why it's worth understanding

Person 4's schema treats a product and its standards as a many-to-many
relationship on purpose: **real products often need more than one
standard** (a safety requirement AND a separate performance
requirement, for instance). The old v1 design silently assumed exactly
one standard per product — technically simpler, but wrong for several
real cases. `pipeline.py`'s `_lookup_standards()` is the join that
makes this work: identify the product first (same matching logic as
before), then pull every row in `product_standard_mapping` for that
`product_id`.

## Why two thresholds, not one (unchanged from v1 — still your core trust mechanism)

`src/confidence.py` still uses two checks: an **absolute floor**
(is the best score even plausible?) and a **relative gap** (is the top
score clearly ahead of #2, or genuinely competing?). See the inline
comments in `confidence.py` for the full reasoning.

**A real bug we hit twice while building this, worth internalizing:**
the "bottle" clarification test kept silently breaking because the
keyword/synonym text for the plastic vs glass bottle products wasn't
perfectly balanced — an extra mention of the word "bottle" in one
product's synonyms column was enough to make TF-IDF favor it, killing
the ambiguity we wanted to demonstrate. **This is not a code bug — it's
a data curation issue**, and it will keep happening with real data too.
Whenever a clarification case that should trigger doesn't (or vice
versa), the first thing to check is word-frequency balance across the
competing products' `keywords`/`synonyms`/`typical_use` fields, not the
threshold values. Use `demo.py` to print raw scores and inspect
`search_text` directly (see `data_loader.py`'s `search_text` construction)
before touching `config.py`.

Current threshold values (`0.12` floor, `0.09` gap, `0.45` high-confidence)
are still placeholder-tuned. Re-tune on Day 2 against real data the same
way.

## What's deliberately NOT built (per the master plan's + Person 4's own scope cuts)

- `product_attributes`, `conformity_routes`, `inspection_requirements`,
  `lab_scope`, `hallmarking_products`, `jewellers`, `ah_centres` —
  all schema-designed by Person 4, intentionally not built/populated
  this round. Mention as roadmap, not omission, if judges ask.
- Attribute extraction as separate structured fields — folded into the
  product's search text instead.
- Both rapidfuzz AND embeddings — TF-IDF+cosine chosen as the one
  approach (see design note in `matcher.py`).
- Conversation memory — clarification is handled by the caller
  re-invoking `process()` with an appended query string.

## What you (Person 2) still need to do

1. Swap in Person 4's real `products.csv`, `standards.csv`,
   `product_standard_mapping.csv`, `documents.csv` as soon as ready —
   loaders validate column names, so a format mismatch throws a clear
   error, not a silent bug.
2. Re-tune the three thresholds in `config.py` against real data.
3. Watch for the keyword-balance issue above as real keyword lists grow
   — it's the most likely source of "why didn't this trigger
   clarification" confusion.
4. Add more pairs to `clarification_bank.json` as real ambiguous cases
   surface.
5. Extend `tests/test_pipeline.py` with real product descriptions once
   real data lands.

## Concepts worth understanding to take this over confidently

Same core list as before, now with the two-stage design added:

1. **TF-IDF + cosine similarity** — still the one piece of theory that
   matters most; everything else is plumbing.
2. **Why word-frequency balance across fields matters** — see the
   "bottle" story above. This is the practical, not-in-a-textbook skill
   you'll use most on Day 2.
3. **Precision/recall-style threshold tuning** — same as before.
4. **Why relational (many-to-many) beats flat-table design here** — the
   pressure-cooker case is the clearest illustration: one product,
   two standards, one relationship_type field to tell them apart.
5. **Pydantic models** (`schemas.py`) — the typed contract that lets 5
   people build in parallel.
6. **pytest basics** — extend `test_pipeline.py` as real data lands.

## Handoff shape for Person 1

Person 1 should receive the **whole** `ProductMatchResult`, including
`applicable_standards` as a list. If a product has 2 mandatory
standards, Person 1's RAG module needs to either answer about both or
ask which one the user cares about — that's Group A/Group B's
integration decision to make together, not something to hardcode here.

## Answers to Person 1's contract questions

Person 1's AI reviewed our v2 contract and asked 12 specific questions
about what P2 provides. Answers, field by field:

| Question | Answer |
|---|---|
| Original user query | `query` (verbatim) + `normalized_query` (cleaned) |
| Detected product / product ID | `matched_product.product_id` — `null` unless `status == "matched"` |
| Product attributes | `matched_product.attributes` (subcategory/material/typical_use) — curated from Person 4's data, **not** extracted from the user's specific wording |
| Candidate standard IDs / titles | `applicable_standards[].standard_id` / `.is_number` / `.title` — see divergence note below |
| Confidence per candidate standard | `applicable_standards[].curated_confidence` — Person 4's confidence in the *mapping*, not a per-standard match score |
| Selected/recommended standard | **No single field — see divergence note below** |
| Overall confidence | `confidence_score` (raw) + `confidence_label` (bucketed) |
| Clarification required | `needs_clarification` (bool) |
| Clarification question | `clarification_question` + `clarification_options` (pre-written buttons, not free text) |
| Relevant context | `normalized_query` + `matched_product.attributes` |

**The one deliberate divergence from her proposed schema:** she proposed
a single `selected_standard_id` with per-candidate confidence scores.
We don't do this, on purpose — our matching happens at the *product*
level, not the standard level. Once a product is confidently matched,
`applicable_standards` returns **every** standard actually mapped to
it (sorted mandatory-first), because real products often need more
than one (a pressure cooker needs both a mandatory safety standard and
a related performance standard — see the sample JSON below). Collapsing
this to one `selected_standard_id` would silently lose a standard a
user actually needs to comply with. If her RAG genuinely needs one
standard to scope a single retrieval call, `applicable_standards[0]` is
always the mandatory one when one exists.

