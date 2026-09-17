"""
THE FIX for the confirmed bug: P1's shipped ChromaDB only ever contained
synthetic test data ("Sample BIS Product Standard A/B/C... Not an
official BIS document") aliased to our real STD-001/002/003 via a
hardcoded dict in chroma_store.py. Every semantic-retrieval answer was
therefore grounded in fake text, not real BIS content - confirmed by
directly inspecting p1_service/data/embeddings/all_embeddings.json.

This script uses P1's REAL ingestion functions (extract_text_from_pdf,
clean_text, chunk_text - already well-written and generic, just never
run against real documents before) against the real raw PDFs/HTML now
in knowledge_base/raw/, and produces real chunks in the exact format
her embed.py expects.

SCOPE - read this before assuming every raw file is covered:
knowledge_base/raw/ contains far more documents (36 standards) than our
structured knowledge_base/structured/*.json currently covers (7
standards, 3 products). Only files that map to an EXISTING structured
standard_id are ingested here - see FILE_TO_STANDARD_MAP below. The
rest are real, genuine BIS documents sitting ready to use, but adding
them requires new products.json/standards.json/product_standard_mapping.json
entries first (real curation - product categorization, mandatory
flags, confidence) which isn't something to silently invent. See the
root README's "Adding more Knowledge Base data" section.

Known data-quality notes surfaced while building this mapping (flagged,
not silently papered over):
  - STD-001 (structured edition_year=2023) matches raw file
    STD_IS_2347_2017.pdf by IS number, but the file is actually the
    Product Manual (its own header reads "AS PER IS 2347:2023") rather
    than the bare standard text - used anyway since it's real, correctly
    attributed content, just filed under the wrong subfolder upstream.
  - STD-006 (structured edition_year=2024) matches raw file
    STD_IS_15820_2009.pdf - an older edition than the structured record
    claims. Used anyway (real content beats no content), but worth
    Person 4 double-checking which edition is actually current.
  - STD-007 (IS 1418:2009) has NO corresponding raw file in this
    delivery - remains without real ingested text; P4EvidenceBuilder's
    structured evidence (test/cert-step summaries) is still real and
    still used for it, just no raw clause text.
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
P1_SERVICE_ROOT = PROJECT_ROOT / "p1_service"
KB_RAW_DIR = PROJECT_ROOT / "knowledge_base" / "raw"

sys.path.insert(0, str(P1_SERVICE_ROOT))

MIN_CHUNK_LENGTH = 25  # drop table-fragment/noise chunks shorter than this

# --- Real file -> real standard_id mapping (see module docstring) ---
# Each entry: relative path under knowledge_base/raw/ -> metadata
FILE_TO_STANDARD_MAP = [
    # Pressure Cooker - STD-001
    {"path": "standards/STD_IS_2347_2017.pdf", "standard_id": "STD-001",
     "document_type": "PRODUCT_MANUAL", "title": "Product Manual for Domestic Pressure Cooker (IS 2347)"},
    {"path": "guidelines/GUIDELINE_IS_2347_2017.pdf", "standard_id": "STD-001",
     "document_type": "CERTIFICATION_GUIDELINE", "title": "Certification Guideline - IS 2347 Pressure Cooker"},
    {"path": "qcos/QCO_PRESSURE_COOKERS.pdf", "standard_id": "STD-001",
     "document_type": "QCO", "title": "Quality Control Order - Pressure Cookers"},

    # Electric Water Heater - STD-002
    {"path": "standards/STD_IS_2082_2018.pdf", "standard_id": "STD-002",
     "document_type": "INDIAN_STANDARD", "title": "IS 2082:2018 - Stationary Storage Type Electric Water Heaters"},
    {"path": "product_manuals/PM_IS_2082_2018.pdf", "standard_id": "STD-002",
     "document_type": "PRODUCT_MANUAL", "title": "Product Manual for Electric Water Heaters (IS 2082)"},
    {"path": "guidelines/GUIDELINE_IS_2082_2018.pdf", "standard_id": "STD-002",
     "document_type": "CERTIFICATION_GUIDELINE", "title": "Certification Guideline - IS 2082 Water Heaters"},
    {"path": "qcos/QCO_DOMESTIC_WATER_HEATERS.pdf", "standard_id": "STD-002",
     "document_type": "QCO", "title": "Quality Control Order - Domestic Water Heaters"},

    # IS 302 Part 1 - STD-003
    {"path": "standards/STD_IS_302_PART1_2024.pdf", "standard_id": "STD-003",
     "document_type": "INDIAN_STANDARD", "title": "IS 302 Part 1:2024 - Household Electrical Appliances Safety"},

    # IS 302 Part 2 Section 21 - STD-004
    {"path": "standards/STD_IS_302_PART2_SEC21_2024.pdf", "standard_id": "STD-004",
     "document_type": "INDIAN_STANDARD", "title": "IS 302 Part 2 Section 21:2024 - Household Electrical Appliances Safety"},

    # Gold Jewellery Fineness - STD-005
    {"path": "standards/STD_IS_1417_2016.pdf", "standard_id": "STD-005",
     "document_type": "INDIAN_STANDARD", "title": "IS 1417:2016 - Gold and Gold Alloys Fineness and Marking"},
    {"path": "guidelines/JEWELLER_GUIDELINES.pdf", "standard_id": "STD-005",
     "document_type": "CERTIFICATION_GUIDELINE", "title": "BIS Jeweller Guidelines"},

    # Hallmarking A&H Centres - STD-006
    {"path": "standards/STD_IS_15820_2009.pdf", "standard_id": "STD-006",
     "document_type": "INDIAN_STANDARD", "title": "IS 15820:2009 - Assaying and Hallmarking Centres"},
    {"path": "guidelines/HALLMARKING_OVERVIEW.html", "standard_id": "STD-006",
     "document_type": "SCHEME_GUIDELINE", "title": "BIS Hallmarking Overview"},
    {"path": "guidelines/HALLMARKING_FAQS.html", "standard_id": "STD-006",
     "document_type": "FAQ", "title": "BIS Hallmarking FAQs"},

    # STD-007 (IS 1418:2009) - no matching raw file in this delivery, skipped
]


def extract_html_text(path: Path) -> str:
    from bs4 import BeautifulSoup
    with open(path, encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def build_chunks_for_file(entry: dict, doc_id: str) -> list[dict]:
    from rag.ingestion.extract import extract_text_from_pdf
    from rag.ingestion.clean import clean_text
    from rag.ingestion.chunk import chunk_text

    full_path = KB_RAW_DIR / entry["path"]
    if not full_path.exists():
        print(f"  SKIPPED (file not found): {full_path}")
        return []

    if full_path.suffix.lower() == ".pdf":
        pages = extract_text_from_pdf(str(full_path))
        page_texts = [(p["page_number"], clean_text(p["text"])) for p in pages]
    else:  # .html
        page_texts = [(1, clean_text(extract_html_text(full_path)))]

    chunks = []
    counter = 1
    for page_number, text in page_texts:
        for raw_chunk in chunk_text(text):
            if len(raw_chunk["text"].strip()) < MIN_CHUNK_LENGTH:
                continue
            chunks.append({
                "chunk_id": f"{doc_id}_chunk_{counter}",
                "text": raw_chunk["text"],
                "section": raw_chunk["section"],
                "section_header": raw_chunk["section_header"],
                "document_id": doc_id,
                "standard_id": entry["standard_id"],
                "document_title": entry["title"],
                "document_type": entry["document_type"],
                "version": "as provided in knowledge_base/raw/",
                "authority_level": 1,  # official BIS primary source document
                "source_url": None,   # local file, no public URL captured for this copy
                "page_number": page_number,
            })
            counter += 1
    return chunks


def main():
    all_chunks = []
    print(f"Ingesting real documents from {KB_RAW_DIR} ...\n")

    for i, entry in enumerate(FILE_TO_STANDARD_MAP, start=1):
        doc_id = f"REAL-DOC-{i:03d}"
        print(f"[{entry['standard_id']}] {entry['path']}")
        chunks = build_chunks_for_file(entry, doc_id)
        print(f"  -> {len(chunks)} chunks")
        all_chunks.extend(chunks)

    output_dir = P1_SERVICE_ROOT / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "real_kb_chunks.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"chunks": all_chunks}, f, indent=2, ensure_ascii=False)

    covered_standards = sorted(set(c["standard_id"] for c in all_chunks))
    print(f"\nTotal: {len(all_chunks)} real chunks across {len(covered_standards)} standards: {covered_standards}")
    print(f"Written to: {output_path}")
    print("\nNext: regenerate embeddings (embed.py) and reindex ChromaDB, then")
    print("delete/rename the old synthetic chunk file so it isn't embedded again -")
    print("see integration/reindex_real_kb.py for the full one-command version.")


if __name__ == "__main__":
    main()
