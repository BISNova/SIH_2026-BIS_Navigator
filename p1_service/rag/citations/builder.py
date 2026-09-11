from __future__ import annotations

from typing import Any


class CitationBuilder:
    """
    P1 Citation Builder.

    Builds citation/provenance information from selected evidence.

    IMPORTANT:
    This class does not retrieve evidence and does not generate answers.

    It only converts evidence metadata into structured citations.

    Citation information must come directly from the evidence.
    No source information is invented.
    """

    def build(
        self,
        evidence: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Build citations from selected evidence.

        Parameters
        ----------
        evidence:
            Evidence selected by the P1 evidence selector.

        Returns
        -------
        list[dict]
            Structured citation records.
        """

        citations = []

        for item in evidence:

            if not isinstance(item, dict):
                continue

            chunk_id = item.get("chunk_id")

            if not chunk_id:
                continue

            citation = {
                "chunk_id": chunk_id,
                "standard_id": item.get("standard_id"),
                "document_id": item.get("document_id"),
                "document_title": item.get("document_title"),
                "document_type": item.get("document_type"),
                "section": item.get("section"),
                "section_header": item.get("section_header"),
                "page_number": item.get("page_number"),
                "source_url": item.get("source_url"),
                "version": item.get("version"),
                "authority_level": item.get("authority_level"),
            }

            citations.append(citation)

        return citations


if __name__ == "__main__":

    print("=" * 70)
    print("P1 — Citation Builder")
    print("=" * 70)

    builder = CitationBuilder()

    test_evidence = [
        {
            "chunk_id": "SYN-STD-101_chunk_25",
            "standard_id": "SYN-STD-101",
            "document_id": "SYN-BIS-STD-A",
            "document_title": "Synthetic BIS Standard A",
            "document_type": "INDIAN_STANDARD",
            "section": "7.1",
            "section_header": "Clause 7 · Inspection Requirements",
            "page_number": 2,
            "source_url": "https://example.com/synthetic-standard-a",
            "version": "2026",
            "authority_level": 1,
        },
        {
            "chunk_id": "SYN-STD-101_chunk_26",
            "standard_id": "SYN-STD-101",
            "document_id": "SYN-BIS-STD-A",
            "document_title": "Synthetic BIS Standard A",
            "document_type": "INDIAN_STANDARD",
            "section": "7.2",
            "section_header": "Clause 7 · Inspection Requirements",
            "page_number": 2,
            "source_url": "https://example.com/synthetic-standard-a",
            "version": "2026",
            "authority_level": 1,
        },
    ]

    citations = builder.build(test_evidence)

    print("\nCitations:")
    print("-" * 70)

    for citation in citations:
        for key, value in citation.items():
            print(f"{key}: {value}")

        print("-" * 70)

    print("=" * 70)
    print("Citation builder test completed.")
    print("=" * 70)