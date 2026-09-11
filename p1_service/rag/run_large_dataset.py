from pathlib import Path
import json
import re

from ingestion.extract import extract_text_from_pdf
from ingestion.clean import clean_text
from ingestion.chunk import chunk_text


# ============================================================
# PATHS
# ============================================================

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# DOCUMENT METADATA
# ============================================================

DOCUMENTS = [
    {
        "file": "large_synthetic_bis_standard_A.pdf",
        "document_id": "SYN-BIS-STD-A",
        "standard_id": "SYN-STD-101",
        "document_title": "Sample BIS Product Standard A",
        "document_type": "synthetic_standard",
        "version": "1.0",
        "authority_level": 1,
        "source_url": "synthetic://bis-navigator/standard-A",
    },
    {
        "file": "large_synthetic_bis_standard_B.pdf",
        "document_id": "SYN-BIS-STD-B",
        "standard_id": "SYN-STD-202",
        "document_title": "Sample BIS Product Standard B",
        "document_type": "synthetic_standard",
        "version": "1.0",
        "authority_level": 1,
        "source_url": "synthetic://bis-navigator/standard-B",
    },
    {
        "file": "large_synthetic_bis_standard_C.pdf",
        "document_id": "SYN-BIS-STD-C",
        "standard_id": "SYN-STD-303",
        "document_title": "Sample BIS Product Standard C",
        "document_type": "synthetic_standard",
        "version": "1.0",
        "authority_level": 1,
        "source_url": "synthetic://bis-navigator/standard-C",
    },
]


# ============================================================
# VALIDATION
# ============================================================

REQUIRED_FIELDS = {
    "chunk_id",
    "section",
    "section_header",
    "text",
    "document_id",
    "standard_id",
    "document_title",
    "document_type",
    "version",
    "authority_level",
    "source_url",
    "page_number",
}

NUMBERED_SECTION_RE = re.compile(
    r"^\d+\.\d+(?:\.\d+)*$"
)

PAGE_RE = re.compile(
    r"^Page\s+\d+$",
    re.IGNORECASE
)


def validate_chunks(chunks: list[dict], metadata: dict) -> list[str]:
    """
    Validate the output of the extraction -> cleaning -> chunking pipeline.
    """

    errors = []

    # --------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------

    if not chunks:
        errors.append("No chunks were generated.")
        return errors

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    for index, chunk in enumerate(chunks, start=1):

        missing_fields = REQUIRED_FIELDS - set(chunk.keys())

        if missing_fields:
            errors.append(
                f"Chunk {index}: missing fields: "
                f"{sorted(missing_fields)}"
            )

        # ----------------------------------------------------
        # Text validation
        # ----------------------------------------------------

        text = str(chunk.get("text", "")).strip()

        if not text:
            errors.append(
                f"Chunk {index}: empty text."
            )

        # ----------------------------------------------------
        # Section validation
        # ----------------------------------------------------

        section = str(chunk.get("section", "")).strip()

        if not section:
            errors.append(
                f"Chunk {index}: empty section."
            )

        # Detect malformed sections such as:
        # 0.1
        # 0.2
        # 1
        # etc.
        if section.startswith("0."):
            errors.append(
                f"Chunk {index}: suspicious section '{section}'."
            )

        # Numbered sections should follow expected format
        if section != "general":
            if not NUMBERED_SECTION_RE.match(section):
                errors.append(
                    f"Chunk {index}: invalid numbered section "
                    f"'{section}'."
                )

        # ----------------------------------------------------
        # Section header validation
        # ----------------------------------------------------

        if section != "general":
            section_header = chunk.get("section_header")

            if not section_header:
                errors.append(
                    f"Chunk {index}: numbered section "
                    f"'{section}' has no section_header."
                )

        # ----------------------------------------------------
        # Noise validation
        # ----------------------------------------------------

        if "Synthetic BIS Navigator test document" in text:
            errors.append(
                f"Chunk {index}: synthetic page/header noise "
                f"still present."
            )

        if PAGE_RE.search(text):
            errors.append(
                f"Chunk {index}: page-number noise still present."
            )

        # ----------------------------------------------------
        # Page number validation
        # ----------------------------------------------------

        page_number = chunk.get("page_number")

        if not isinstance(page_number, int):
            errors.append(
                f"Chunk {index}: page_number must be an integer."
            )
        elif page_number <= 0:
            errors.append(
                f"Chunk {index}: page_number must be positive."
            )

        # ----------------------------------------------------
        # Metadata consistency
        # ----------------------------------------------------

        for field in [
            "document_id",
            "standard_id",
            "document_title",
            "document_type",
            "version",
            "authority_level",
            "source_url",
        ]:
            expected = metadata[field]
            actual = chunk.get(field)

            if actual != expected:
                errors.append(
                    f"Chunk {index}: metadata mismatch for "
                    f"'{field}'. Expected '{expected}', "
                    f"got '{actual}'."
                )

    # --------------------------------------------------------
    # Chunk ID uniqueness
    # --------------------------------------------------------

    chunk_ids = [
        chunk.get("chunk_id")
        for chunk in chunks
    ]

    duplicate_ids = {
        chunk_id
        for chunk_id in chunk_ids
        if chunk_ids.count(chunk_id) > 1
    }

    if duplicate_ids:
        errors.append(
            f"Duplicate chunk IDs found: "
            f"{sorted(duplicate_ids)}"
        )

    return errors


# ============================================================
# PROCESS ONE DOCUMENT
# ============================================================

def process_document(metadata: dict) -> dict:
    """
    Run:

        PDF
        ↓
        extraction
        ↓
        cleaning
        ↓
        chunking
        ↓
        metadata enrichment
        ↓
        validation
        ↓
        JSON output
    """

    pdf_path = RAW_DIR / metadata["file"]

    print("\n" + "=" * 70)
    print(f"Processing: {pdf_path.name}")
    print("=" * 70)

    # --------------------------------------------------------
    # Check input file
    # --------------------------------------------------------

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    # --------------------------------------------------------
    # 1. Extract
    # --------------------------------------------------------

    pages = extract_text_from_pdf(str(pdf_path))

    print(f"Pages extracted: {len(pages)}")

    # --------------------------------------------------------
    # 2. Clean
    # --------------------------------------------------------

    cleaned_pages = []

    for page in pages:
        cleaned_text = clean_text(page["text"])

        cleaned_pages.append({
            "page_number": page["page_number"],
            "text": cleaned_text,
        })

    # --------------------------------------------------------
    # 3. Chunk
    # --------------------------------------------------------

    all_chunks = []

    for page in cleaned_pages:

        page_chunks = chunk_text(page["text"])

        for chunk in page_chunks:

            chunk["page_number"] = page["page_number"]

            all_chunks.append(chunk)

    # --------------------------------------------------------
    # 4. Add document metadata
    # --------------------------------------------------------

    enriched_chunks = []

    for chunk in all_chunks:

        enriched_chunk = {
            **chunk,

            "document_id": metadata["document_id"],
            "standard_id": metadata["standard_id"],
            "document_title": metadata["document_title"],
            "document_type": metadata["document_type"],
            "version": metadata["version"],
            "authority_level": metadata["authority_level"],
            "source_url": metadata["source_url"],
        }

        enriched_chunks.append(enriched_chunk)

    # --------------------------------------------------------
    # 5. Globally renumber chunk IDs
    # --------------------------------------------------------

    for index, chunk in enumerate(enriched_chunks, start=1):

        chunk["chunk_id"] = (
            f"{metadata['standard_id']}_chunk_{index}"
        )

    # --------------------------------------------------------
    # 6. Validate
    # --------------------------------------------------------

    validation_errors = validate_chunks(
        enriched_chunks,
        metadata
    )

    # --------------------------------------------------------
    # 7. Calculate statistics
    # --------------------------------------------------------

    numbered_chunks = [
        chunk
        for chunk in enriched_chunks
        if chunk["section"] != "general"
    ]

    general_chunks = [
        chunk
        for chunk in enriched_chunks
        if chunk["section"] == "general"
    ]

    unique_sections = sorted(
        {
            chunk["section"]
            for chunk in enriched_chunks
        }
    )

    statistics = {
        "pages": len(pages),
        "chunks": len(enriched_chunks),
        "unique_sections": len(unique_sections),
        "numbered_sections": len(numbered_chunks),
        "general_chunks": len(general_chunks),
        "validation_errors": len(validation_errors),
    }

    # --------------------------------------------------------
    # 8. Final JSON structure
    # --------------------------------------------------------

    output = {
        "document": {
            "document_id": metadata["document_id"],
            "standard_id": metadata["standard_id"],
            "title": metadata["document_title"],
            "document_type": metadata["document_type"],
            "version": metadata["version"],
            "authority_level": metadata["authority_level"],
            "source_url": metadata["source_url"],
        },

        "statistics": statistics,

        "validation_errors": validation_errors,

        "chunks": enriched_chunks,
    }

    # --------------------------------------------------------
    # 9. Save JSON
    # --------------------------------------------------------

    output_filename = (
        pdf_path.stem + "_chunks.json"
    )

    output_path = PROCESSED_DIR / output_filename

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )

    # --------------------------------------------------------
    # 10. Print results
    # --------------------------------------------------------

    print("\nStatistics:")
    print(f"  Pages:             {statistics['pages']}")
    print(f"  Total chunks:      {statistics['chunks']}")
    print(f"  Unique sections:   {statistics['unique_sections']}")
    print(f"  Numbered chunks:   {statistics['numbered_sections']}")
    print(f"  General chunks:    {statistics['general_chunks']}")
    print(f"  Validation errors: {statistics['validation_errors']}")

    if validation_errors:

        print("\nVALIDATION ERRORS:")

        for error in validation_errors:
            print(f"  - {error}")

    else:

        print("\n✓ Validation passed.")

    print(f"\nSaved to:")
    print(f"  {output_path}")

    return output


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 70)
    print("BIS NAVIGATOR — LARGE DATASET INGESTION PIPELINE")
    print("=" * 70)

    successful_documents = 0
    failed_documents = 0

    total_pages = 0
    total_chunks = 0
    total_numbered_chunks = 0
    total_general_chunks = 0
    total_validation_errors = 0

    # --------------------------------------------------------
    # Process every document
    # --------------------------------------------------------

    for metadata in DOCUMENTS:

        try:

            result = process_document(metadata)

            successful_documents += 1

            stats = result["statistics"]

            total_pages += stats["pages"]
            total_chunks += stats["chunks"]
            total_numbered_chunks += stats["numbered_sections"]
            total_general_chunks += stats["general_chunks"]
            total_validation_errors += stats["validation_errors"]

        except Exception as error:

            failed_documents += 1

            print("\n" + "!" * 70)
            print(
                f"FAILED: {metadata['file']}"
            )
            print(f"Reason: {error}")
            print("!" * 70)

    # --------------------------------------------------------
    # Corpus summary
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("CORPUS SUMMARY")
    print("=" * 70)

    print(
        f"Documents successful: {successful_documents}"
    )

    print(
        f"Documents failed:    {failed_documents}"
    )

    print(
        f"Total pages:         {total_pages}"
    )

    print(
        f"Total chunks:        {total_chunks}"
    )

    print(
        f"Numbered chunks:     {total_numbered_chunks}"
    )

    print(
        f"General chunks:      {total_general_chunks}"
    )

    print(
        f"Validation errors:   {total_validation_errors}"
    )

    # --------------------------------------------------------
    # Final status
    # --------------------------------------------------------

    if (
        failed_documents == 0
        and total_validation_errors == 0
    ):

        print("\n✓ LARGE DATASET PIPELINE PASSED")
        print(
            "Extraction → Cleaning → Chunking → "
            "Metadata → Validation"
        )

    else:

        print("\n✗ LARGE DATASET PIPELINE HAS ERRORS")

    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()