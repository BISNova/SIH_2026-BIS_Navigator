# Learning Notes

A running log of what got built, which tools/techniques were used, and *why* -
written so you (a beginner developer) can actually understand and maintain this
codebase, not just have it work. New entries get added to the top as features are
built going forward.

---

## Session: Real knowledge base data + fixing a confirmed RAG bug

### 1. The bug: RAG was retrieving fake data, not real BIS content

**Files:** `p1_service/rag/vectorstore/chroma_store.py`,
`integration/ingest_real_documents.py`

**How I actually confirmed it** (not just suspected it): opened
`p1_service/data/embeddings/all_embeddings.json` directly and read the text of the
first few records. Every one said things like *"Synthetic dataset for BIS Navigator
RAG testing. Not an official BIS document."* That's a concrete, checkable fact, not
a guess - the vector database (the thing that finds "similar" text to a user's
question) only ever contained made-up placeholder content.

**Why this happened:** P1's code had a hardcoded translation table mapping our real
standard IDs (`STD-001`) to fake test IDs (`SYN-STD-101`) purely so her own
development/testing could proceed before real documents existed. That's a completely
reasonable thing to do *during development* - the problem is only that it was still
in place once treated as "done."

**The fix, in plain terms:**
1. Took the real PDF/HTML files just delivered (real Indian Standards, product
   manuals, QCOs, certification guidelines).
2. Ran them through **PDF text extraction** (`pymupdf` library - reads a PDF and
   gives you back plain text, page by page) and **HTML text extraction**
   (`BeautifulSoup` library - same idea, but for saved web pages, and also strips
   out menus/scripts/styling you don't want).
3. Split that text into smaller "chunks" (a few paragraphs each) - this matters
   because embedding models work best on focused, medium-length text, not
   ultra-long documents.
4. Generated real "embeddings" for those chunks (see below for what that means) and
   loaded them into the vector database *under their real standard ID* - no more
   fake-ID translation table needed.
5. **Proved it worked** by directly querying the database afterward and reading
   back real extracted sentences from an actual BIS Product Manual - not by just
   assuming the pipeline "should" work now.

**What "embeddings" actually are, if this is new to you:** a way of turning text
into a list of numbers (a vector) such that texts with *similar meaning* end up with
*similar numbers*. That's what lets the system find "which paragraphs are relevant
to this question" without literally matching exact words.

### 2. Why some things stayed the same on purpose

I did **not** rewrite the structured `products.json`/`standards.json` tables to
cover all ~36 standards found in the new raw files - only 7 of them already had
curated entries (product category, whether it's mandatory, etc.), and the other ~29
would need someone to actually make those judgment calls. Real content existing
isn't the same as it being correctly *classified* - mixing those up would mean me
guessing at things a domain-curator should decide. Flagged clearly in the README
instead of silently doing it.

### 3. A subtle testing lesson: identical scoring, different outcome

While checking the fix worked, I found that for some questions, the *old* real
evidence source (structured test-requirement data, always real, never the bug) kept
winning over my *newly real* document chunks in the final answer. My first instinct
was "did I break something?" Checking the actual scoring code showed both sources
go through the exact same comparison function - the difference was just the
sandbox's fake stand-in embedding model (see `p1_service/sandbox_mocks/`) producing
essentially random scores, since it has no real understanding of text. On a real
machine with the real model, genuinely relevant content will properly score higher.
The lesson: before assuming "my change didn't work," check whether the *test
conditions themselves* (a mocked component) could fully explain what you're seeing.

---

## Session: Post-hackathon feature batch

### 1. Non-English query detection + translation (no paid API)

**Files:** `product_intelligence/src/language.py`

**Tech used:**
- **Unicode script detection** - every character in a computer has a numeric "code
  point." Hindi (Devanagari), Tamil, Bengali, etc. each live in their own reserved
  numeric range (e.g. Devanagari is 0x0900–0x097F). Checking "does this character's
  code point fall in the Hindi range?" is a simple, 100%-reliable way to detect
  those scripts - no library, no guessing, no ambiguity.
- **`langdetect`** (pip package) - a statistical language detector, used only as a
  *secondary* check for long Latin-script text. Real bug found while building this:
  `langdetect.detect("domestic pressure cooker")` returns `"fr"` (French) - wrong!
  Short strings genuinely confuse it. Fix: only trust it for 8+ word Latin text, and
  always default to English otherwise.
- **`deep-translator`** (pip package) - a free wrapper around Google's public
  translate page (not the paid Cloud Translation API - no billing, no API key).
  Every call is wrapped in try/except: if the free endpoint is ever down or rate-
  limited, we silently keep the original text rather than crashing.

**Why this design:** detecting language and translating are two *separate*
concerns. Script detection is deterministic and free; translation depends on an
external, unofficial service that could fail - so it has to degrade gracefully.

**What I couldn't test here:** the actual network call to the translation service -
this sandbox can't reach it (same restriction as a few other things in this
project, see `INTEGRATION_NOTES.md`). It's tested with the real library mocked out,
proving the *wiring* is correct; the live call itself just needs normal internet.

---

### 2. Conversation memory (session-based)

**Files:** `backend/session_store.py`, `product_intelligence/src/pipeline.py`
(`context_hint` parameter)

**Tech used:** a plain Python dictionary, keyed by `session_id`, storing only the
last matched product's name per session. Deliberately minimal - the temptation is
to store the whole conversation, but more stored context means more chances a
follow-up question gets resolved against the *wrong* earlier turn.

**How it works:** if "what tests are needed" doesn't match anything on its own,
the pipeline retries once with the last matched product's name appended (e.g.
"what tests are needed domestic pressure cooker"). This reuses the exact same
matching logic - no new AI model, just a smarter second attempt.

**Real bug found while testing this:** the query cache (see #3) was caching
"what tests are needed" → answer, using only the literal query text as the key.
That meant User A's session-specific answer would incorrectly get served to
User B, who asked the same words but has different conversation history. Fixed by
never caching an answer that depended on session context.

**Frontend side:** each chat's own ID doubles as the `session_id` sent to the
backend - no separate ID generator needed, and conversation memory is naturally
scoped to "this specific chat conversation."

---

### 3. Query-result caching

**Files:** `backend/query_cache.py`

**Tech used:** an in-memory dictionary with SHA-256-hashed keys (so long queries
don't create huge dictionary keys), a time-to-live (1 hour), and a simple "evict the
oldest entry" rule if the cache grows past a size limit.

**Why hash the key?** Two reasons: fixed, predictable key size regardless of query
length, and it naturally handles case/whitespace differences if you lowercase and
trim before hashing (which we do).

**Production upgrade path:** this is deliberately simple (a dict, not Redis) so it
works with zero extra setup for a demo. The interface (`get_or_none()` / `set()`)
is small enough that swapping in a real Redis client later is a one-file change,
not a redesign.

---

### 4. List/aggregate query handling

**Files:** `backend/list_query.py`

**Tech used:** regular expressions (regex) - patterns like `\blist\s+(all|every)\b`
or `\btop\s+\d+\b` that match common phrasings of "give me a list" questions.

**Why regex instead of an AI classifier?** For a first version, a transparent rule
you can read and tweak is easier to debug than a trained model, and it's instant
(no API call, no latency). If real usage shows regex isn't catching enough
phrasings, upgrading to a small classifier is a natural next step - but starting
simple and provably-correct is the right call here.

**What it does:** instead of asking the RAG pipeline to "list all mandatory
standards" (which RAG is genuinely bad at - it retrieves relevant *passages*, not
"count and enumerate every row in a table"), it filters the same structured catalog
data directly - a normal pandas filter, not a language model.

---

### 5. Feedback capture (👍/👎)

**Files:** `backend/feedback_store.py`, `backend/routers_feedback.py`

**Tech used:** JSONL (JSON Lines) file format - each feedback entry is one line of
JSON, appended to a file. Simple to write, simple to read back, simple to inspect
by hand (`cat backend/data/feedback.jsonl`).

---

### 6. "Last verified" timestamp

**Files:** `product_intelligence/src/pipeline.py` (`_last_verified()`)

**Tech used:** a fallback chain - try `last_updated`, then `retrieved_at`, then
`publication_date`, use whichever is populated first. The knowledge base's
`last_updated`/`retrieved_at` fields aren't filled in yet (Person 4 hasn't gotten to
that), so without a fallback this would show "unknown" everywhere. With it, the UI
shows *something* honest today, and automatically gets more precise the moment
those fields get real data - no code change needed later.

---

### 7. Auto-update scraper + staging/review queue

**Files:** `backend/kb_updater/scraper.py`, `backend/kb_updater/staging.py`,
`backend/routers_admin.py`

**Tech used:**
- **`requests`** - fetches a web page's HTML.
- **`BeautifulSoup`** - parses HTML and strips out navigation/script/style tags, so
  we're only looking at the actual readable content.
- **SHA-256 hashing** - turns the page's text into a short, fixed fingerprint. Two
  fetches of unchanged content produce the *identical* hash; any real content
  change produces a different one. This is what "content-hash based change
  detection" means in practice.
- **A staging queue** (another JSON file) - a detected change is never applied
  automatically. It sits as "pending" until a human calls the review endpoint to
  approve or reject it. For a compliance tool, this human checkpoint matters more
  than the automation itself.

**What I verified vs. what I couldn't:** I confirmed a real BIS page is genuinely
fetchable and has real "last updated" metadata (checked directly during
development). The scraper code itself is fully unit-tested with fake HTML - what
couldn't be tested from inside this project's environment is the *actual* live
network call, because this sandbox can't reach bis.gov.in. On a normal computer
with regular internet access, this will just work.

---

### 8. Chat title auto-naming (no AI)

**Files:** `frontend/src/chatNaming.js`

**Tech used:** pure string processing - strip punctuation, remove a fixed list of
"filler words" (I, the, a, want, please, etc. - the same idea used in
`product_intelligence/src/normalize.py` for matching products), keep the first few
remaining words, capitalize them.

**Why not AI?** You explicitly asked for a free, non-AI approach - and honestly, a
short rule-based title ("Domestic Pressure Cookers" from "I want to manufacture
domestic pressure cookers for home use") works well enough for a chat sidebar label
without needing a model call (which would also add latency to every first message).

---

### 9. Markdown → plain text

**Files:** `frontend/src/markdownToPlainText.js`

**Tech used:** a series of regular expressions that recognize markdown syntax
(`**bold**`, `` `code` ``, `- bullet`, `# heading`, `[link](url)`) and strip the
syntax characters while keeping the actual text. No markdown-rendering library
used on purpose - simpler, no risk of accidentally rendering raw HTML, and matches
what was asked for ("simple to human read format," not "rendered rich text").

---

### 10. Realistic chat history (no fake pre-seeded chats)

**Files:** `frontend/src/App.jsx`

**Tech used:** no new library - just changing *when* a chat record gets created.
Previously, the app started with 5 fake example conversations already in the
sidebar, and clicking "New Chat" immediately added a placeholder entry even before
you typed anything. Now: `chats` starts as an empty list, and a chat only gets
added to that list the moment you actually send your first message (this is also
exactly when the auto-naming in #8 runs). This matches how Claude and ChatGPT
actually behave.

---

## Concepts worth understanding if any of this is new to you

- **Unicode code points** - every character has a number; ranges of numbers are
  reserved for different scripts/alphabets. This is how script detection (#1)
  works without needing to "understand" any language.
- **Regex (regular expressions)** - a pattern language for matching text shapes
  (used in #4 and #9). Worth learning `\b` (word boundary), `+`/`*` (repeat), and
  `()` (grouping) first - that covers most of what's used here.
- **Hashing** - turning any amount of data into a short, fixed-size fingerprint,
  where the *same* input always produces the *same* output, and any change in the
  input produces a completely different output. Used for both caching (#3) and
  change detection (#7).
- **In-memory vs. persistent storage** - a plain Python dictionary lives only as
  long as the program is running and resets on restart. That's fine for a demo
  (#2, #3) but the README notes where "the real production version needs a
  database/Redis instead" for each one - worth knowing which pieces of this project
  are demo-grade vs. production-grade.
