from rag.schemas.p1_input import P1Input, ApplicableStandard
from rag.schemas.evidence import EvidenceRecord
from rag.schemas.p1_output import P1Output

from rag.pipeline.evidence_pipeline import EvidencePipeline


def test_p1_input_to_pipeline_to_output():
    # --------------------------------------------------
    # 1. Create realistic P2 → P1 input
    # --------------------------------------------------

    p1_input = P1Input(
        query="What are the inspection requirements?",
        normalized_query="inspection requirements",
        status="matched",
        matched_product={
                "product_id": "SYN-PROD-001",
                "canonical_name": "Synthetic Product A",
                "attributes": {}
            },
        applicable_standards=[
            ApplicableStandard(
                standard_id="SYN-STD-101",
                standard_title="Synthetic Standard A",
                relevance="Primary applicable standard",
                mandatory=True,
            )
        ],
        confidence_score=0.95,
        confidence_label="high",
        needs_clarification=False,
    )

    # --------------------------------------------------
    # 2. Extract standard IDs using P1Input helper
    # --------------------------------------------------

    standard_ids = p1_input.get_standard_ids()

    assert standard_ids == ["SYN-STD-101"]

    # --------------------------------------------------
    # 3. Run actual evidence pipeline
    # --------------------------------------------------

    pipeline = EvidencePipeline()

    result = pipeline.run(
        query=p1_input.normalized_query or p1_input.query,
        standard_ids=standard_ids,
    )

    # --------------------------------------------------
    # 4. Basic pipeline validation
    # --------------------------------------------------

    assert result["query"] == "inspection requirements"

    assert result["standard_ids"] == [
        "SYN-STD-101"
    ]

    assert result["retrieved_count"] > 0

    assert result["reranked_count"] > 0

    # --------------------------------------------------
    # 5. Convert selected evidence into EvidenceRecord
    # --------------------------------------------------

    evidence_records = []

    for evidence in result["evidence"]:

        record = EvidenceRecord(
            chunk_id=evidence["chunk_id"],
            standard_id=evidence["standard_id"],
            document_id=evidence["document_id"],
            document_title=evidence["document_title"],
            document_type=evidence["document_type"],
            section=evidence["section"],
            section_header=evidence["section_header"],
            page_number=evidence["page_number"],
            text=evidence["text"],
            source_url=evidence["source_url"],
            version=evidence["version"],
            authority_level=evidence["authority_level"],
        )

        evidence_records.append(record)

    # --------------------------------------------------
    # 6. Validate EvidenceRecord boundary
    # --------------------------------------------------

    assert len(evidence_records) == result["selected_count"]

    for record in evidence_records:

        assert record.chunk_id
        assert record.standard_id
        assert record.document_id
        assert record.document_title
        assert record.text

        assert record.section is not None
        assert record.page_number is not None

        assert isinstance(
            record.page_number,
            int,
        )

        assert isinstance(
            record.authority_level,
            int,
        )

    # --------------------------------------------------
    # 7. Build final P1Output
    # --------------------------------------------------

    output = P1Output(
        answer=result["answer"],
        evidence=evidence_records,
        sources=[
            record.source_url
            for record in evidence_records
            if record.source_url
        ],
        confidence_score=result["confidence_score"],
        confidence_label=result["confidence_label"],
        evidence_sufficient=result["evidence_sufficient"],
        clarification_needed=False,
    )

    # --------------------------------------------------
    # 8. Validate final output
    # --------------------------------------------------

    assert output.answer

    assert output.answer == result["answer"]

    assert len(output.evidence) == result[
        "selected_count"
    ]

    assert output.evidence_sufficient == result[
        "evidence_sufficient"
    ]

    assert (
        output.confidence_score
        == result["confidence_score"]
    )

    assert (
        output.confidence_label
        == result["confidence_label"]
    )

    print("\n" + "=" * 70)
    print("P1 CONTRACT TEST PASSED")
    print("=" * 70)

    print(
        f"P1 standards:       {standard_ids}"
    )

    print(
        f"Retrieved:           {result['retrieved_count']}"
    )

    print(
        f"Reranked:            {result['reranked_count']}"
    )

    print(
        f"Evidence selected:   {result['selected_count']}"
    )

    print(
        f"Evidence sufficient: {result['evidence_sufficient']}"
    )

    print(
        f"Confidence:          "
        f"{result['confidence_score']:.4f}"
    )

    print(
        f"Confidence label:    "
        f"{result['confidence_label']}"
    )

    print("\nEvidenceRecord fields preserved:")

    for record in evidence_records:
        print(
            f"  {record.chunk_id} | "
            f"section={record.section} | "
            f"page={record.page_number} | "
            f"authority={record.authority_level}"
        )

    print("=" * 70)