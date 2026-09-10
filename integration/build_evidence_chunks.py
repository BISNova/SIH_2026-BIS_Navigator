"""
Builds evidence chunks for Person 1's RAG pipeline, in the exact format
her rag/embeddings/embed.py expects (data/processed/*_chunks.json with a
top-level {"chunks": [...]}).

IMPORTANT - READ THIS BEFORE TREATING THIS AS REAL BIS TEXT:

Person 4's real KB delivery (knowledge_base/) has metadata about
standards (scope_summary), certification steps, and test requirements -
but NOT the actual verbatim text of any BIS standard document. There is
no raw PDF/text corpus to extract real clauses from yet.

Every chunk this script produces is built from Person 4's OWN curated,
paraphrased summaries already sitting in the KB (scope_summary,
certification step descriptions, test requirements) - never from
scraped or reproduced BIS document text. This is intentional and
copyright-safe, but it means these chunks are NOT a substitute for the
real thing: they're coarser and less complete than actual extracted
clause text would be. Replace this script's output with real
extract.py -> clean.py -> chunk.py output (from actual BIS PDFs) the
moment Person 4/the team has legitimate access to real document text.

Usage:
    python3 -m integration.build_evidence_chunks
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KB_DIR = PROJECT_ROOT / "knowledge_base"
OUTPUT_DIR = PROJECT_ROOT / "evidence_engine" / "rag" / "data" / "processed"


def load(name):
    with open(KB_DIR / "structured" / f"{name}.json", encoding="utf-8") as f:
        return json.load(f)


def load_documents():
    with open(KB_DIR / "documents" / "documents.json", encoding="utf-8") as f:
        return {d["document_id"]: d for d in json.load(f)}


def build_chunks():
    standards = load("standards")
    cert_steps = load("certification_steps")
    tests = load("tests")
    documents = load_documents()

    cert_steps_by_std = {c["standard_id"]: c["steps"] for c in cert_steps}
    tests_by_std = {}
    for t in tests:
        tests_by_std.setdefault(t["standard_id"], []).append(t)

    chunks = []
    chunk_counter = 1

    for std in standards:
        std_id = std["standard_id"]

        # Every standard gets at least a scope-summary chunk, since that's
        # always present. Document metadata is looked up via the FIRST
        # document that references this standard (documents.json has a
        # standard_id field per doc).
        doc = next((d for d in documents.values() if d.get("standard_id") == std_id), None)

        def doc_meta():
            if doc:
                return {
                    "document_id": doc["document_id"],
                    "document_title": doc["title"],
                    "document_type": doc["document_type"],
                    "version": doc.get("version") or "unknown",
                    "authority_level": doc.get("authority_level") or 4,
                    "source_url": doc.get("source_url") or std.get("source_url"),
                }
            # No specific document on file yet - fall back to the standard's
            # own general source_url, and be honest that we don't have a
            # proper document record for it.
            return {
                "document_id": f"NO-DOC-{std_id}",
                "document_title": std["title"],
                "document_type": "INDIAN_STANDARD",
                "version": "unknown",
                "authority_level": 4,
                "source_url": std.get("source_url"),
            }

        meta = doc_meta()

        # --- Chunk 1: scope summary (always available) ---
        scope_text = (
            f"[Curated summary - not verbatim BIS text] "
            f"Scope of {std['is_number']} ({std['title']}): {std['scope_summary']}"
        )
        chunks.append({
            "chunk_id": f"chunk_{chunk_counter}",
            "text": scope_text,
            "section": "scope",
            "section_header": f"Scope - {std['title']}",
            "standard_id": std_id,
            "page_number": 1,
            **meta,
        })
        chunk_counter += 1

        # --- Chunk(s): certification steps, if we have them ---
        for step in cert_steps_by_std.get(std_id, []):
            step_text = (
                f"[Curated summary - not verbatim BIS text] "
                f"Certification step {step['step_no']} ({step['title']}): {step['description']}"
            )
            chunks.append({
                "chunk_id": f"chunk_{chunk_counter}",
                "text": step_text,
                "section": f"cert_step_{step['step_no']}",
                "section_header": f"Certification Process - {step['title']}",
                "standard_id": std_id,
                "page_number": 1,
                **meta,
            })
            chunk_counter += 1

        # --- Chunk(s): test requirements, if we have them ---
        for test in tests_by_std.get(std_id, []):
            test_text = (
                f"[Curated summary - not verbatim BIS text] "
                f"Test '{test['test_name']}' ({test['clause_reference']}): "
                f"{test['requirement']} Acceptance criteria: {test['acceptance_criteria']}"
            )
            chunks.append({
                "chunk_id": f"chunk_{chunk_counter}",
                "text": test_text,
                "section": test["clause_reference"],
                "section_header": f"Testing - {test['test_name']}",
                "standard_id": std_id,
                "page_number": 1,
                **meta,
            })
            chunk_counter += 1

    return chunks


def main():
    chunks = build_chunks()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "bis_kb_chunks.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"chunks": chunks}, f, indent=2, ensure_ascii=False)

    print(f"Built {len(chunks)} chunks across "
          f"{len(set(c['standard_id'] for c in chunks))} standards")
    print(f"Written to: {output_path}")
    print("\nReminder: these are curated/paraphrased summaries from Person "
          "4's KB, not verbatim BIS standard text. Replace with real "
          "extract.py -> clean.py -> chunk.py output once real document "
          "text is available.")


if __name__ == "__main__":
    main()
