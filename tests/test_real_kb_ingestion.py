import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integration.ingest_real_documents import (
    FILE_TO_STANDARD_MAP,
    build_chunks_for_file,
    extract_html_text,
    KB_RAW_DIR,
)


def test_file_map_only_references_real_standard_ids():
    """Every mapped standard_id must actually exist in our structured
    KB - this is the guardrail against silently inventing a standard_id
    that isn't curated anywhere."""
    import json
    standards = json.load(open(Path(__file__).resolve().parent.parent / "knowledge_base" / "structured" / "standards.json"))
    valid_ids = {s["standard_id"] for s in standards}

    for entry in FILE_TO_STANDARD_MAP:
        assert entry["standard_id"] in valid_ids, f"{entry['path']} maps to unknown {entry['standard_id']}"


def test_all_mapped_files_actually_exist():
    """Catches a stale mapping entry pointing at a file that was
    renamed/removed - fails loudly instead of silently skipping."""
    missing = [e["path"] for e in FILE_TO_STANDARD_MAP if not (KB_RAW_DIR / e["path"]).exists()]
    assert missing == [], f"Mapped files not found on disk: {missing}"


def test_build_chunks_for_file_produces_real_extracted_text():
    entry = next(e for e in FILE_TO_STANDARD_MAP if e["standard_id"] == "STD-001" and e["path"].endswith(".pdf"))
    chunks = build_chunks_for_file(entry, doc_id="TEST-DOC-001")

    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk["standard_id"] == "STD-001"
        assert chunk["document_id"] == "TEST-DOC-001"
        assert len(chunk["text"].strip()) >= 25  # MIN_CHUNK_LENGTH enforced
        assert chunk["authority_level"] == 1


def test_html_extraction_strips_scripts_and_nav():
    html_entry = next(e for e in FILE_TO_STANDARD_MAP if e["path"].endswith(".html"))
    text = extract_html_text(KB_RAW_DIR / html_entry["path"])
    assert len(text.strip()) > 0
    assert "<script" not in text.lower()
    assert "<style" not in text.lower()


def test_ingested_chunks_are_not_synthetic_placeholder_text():
    """The actual regression test for the bug found in this session:
    confirms real ingested content doesn't contain the synthetic
    dataset's marker text."""
    entry = FILE_TO_STANDARD_MAP[0]
    chunks = build_chunks_for_file(entry, doc_id="TEST-DOC-002")
    combined_text = " ".join(c["text"] for c in chunks)
    assert "Synthetic dataset for BIS Navigator RAG testing" not in combined_text
    assert "Not an official BIS document" not in combined_text
