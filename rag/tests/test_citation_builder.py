from citations.builder import CitationBuilder


def test_builds_citation_from_evidence():
    builder = CitationBuilder()

    evidence = [
        {
            "chunk_id": "chunk_1",
            "standard_id": "SYN-STD-101",
            "document_id": "SYN-BIS-STD-A",
            "document_title": "Synthetic BIS Standard A",
            "document_type": "INDIAN_STANDARD",
            "section": "7.1",
            "section_header": "Clause 7 · Inspection Requirements",
            "page_number": 2,
            "source_url": "https://example.com/standard-a",
            "version": "2026",
            "authority_level": 1,
        }
    ]

    result = builder.build(evidence)

    assert len(result) == 1

    citation = result[0]

    assert citation["chunk_id"] == "chunk_1"
    assert citation["standard_id"] == "SYN-STD-101"
    assert citation["document_id"] == "SYN-BIS-STD-A"
    assert citation["document_title"] == "Synthetic BIS Standard A"
    assert citation["document_type"] == "INDIAN_STANDARD"
    assert citation["section"] == "7.1"
    assert citation["section_header"] == (
        "Clause 7 · Inspection Requirements"
    )
    assert citation["page_number"] == 2
    assert citation["source_url"] == (
        "https://example.com/standard-a"
    )
    assert citation["version"] == "2026"
    assert citation["authority_level"] == 1


def test_builds_multiple_citations():
    builder = CitationBuilder()

    evidence = [
        {
            "chunk_id": "chunk_1",
            "standard_id": "SYN-STD-101",
            "document_id": "DOC-A",
            "document_title": "Standard A",
            "section": "7.1",
            "page_number": 2,
        },
        {
            "chunk_id": "chunk_2",
            "standard_id": "SYN-STD-101",
            "document_id": "DOC-A",
            "document_title": "Standard A",
            "section": "7.2",
            "page_number": 2,
        },
    ]

    result = builder.build(evidence)

    assert len(result) == 2
    assert result[0]["chunk_id"] == "chunk_1"
    assert result[1]["chunk_id"] == "chunk_2"


def test_skips_evidence_without_chunk_id():
    builder = CitationBuilder()

    evidence = [
        {
            "standard_id": "SYN-STD-101",
            "section": "7.1",
            "page_number": 2,
        }
    ]

    result = builder.build(evidence)

    assert result == []


def test_skips_invalid_evidence():
    builder = CitationBuilder()

    evidence = [
        None,
        "invalid",
        {
            "chunk_id": "valid_chunk",
            "standard_id": "SYN-STD-101",
            "section": "7.1",
        },
    ]

    result = builder.build(evidence)

    assert len(result) == 1
    assert result[0]["chunk_id"] == "valid_chunk"


def test_empty_evidence_returns_empty_citations():
    builder = CitationBuilder()

    result = builder.build([])

    assert result == []


def test_missing_optional_metadata_is_preserved_as_none():
    builder = CitationBuilder()

    evidence = [
        {
            "chunk_id": "chunk_1",
            "standard_id": "SYN-STD-101",
            "document_id": "DOC-A",
            "section": "7.1",
        }
    ]

    result = builder.build(evidence)

    assert len(result) == 1

    citation = result[0]

    assert citation["chunk_id"] == "chunk_1"
    assert citation["standard_id"] == "SYN-STD-101"
    assert citation["document_id"] == "DOC-A"
    assert citation["section"] == "7.1"

    assert citation["document_title"] is None
    assert citation["page_number"] is None
    assert citation["source_url"] is None