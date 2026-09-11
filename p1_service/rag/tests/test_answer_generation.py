from answer.generator import GroundedAnswerGenerator


def test_generates_answer_with_sufficient_evidence():
    """
    The generator should produce a grounded answer when
    sufficient evidence is available.
    """

    generator = GroundedAnswerGenerator()

    evidence = [
        {
            "chunk_id": "SYN-STD-101_chunk_25",
            "section": "7.1",
            "text": (
                "7.1 Each production batch shall be subject "
                "to the applicable inspection activities."
            ),
            "rerank_score": 0.7477,
        },
        {
            "chunk_id": "SYN-STD-101_chunk_26",
            "section": "7.2",
            "text": (
                "7.2 Inspection shall verify product identity, "
                "dimensions and visible workmanship."
            ),
            "rerank_score": 0.7410,
        },
    ]

    result = generator.generate(
        query="What are the inspection requirements?",
        evidence=evidence,
        evidence_sufficient=True,
    )

    assert result["grounded"] is True
    assert result["evidence_used"] == evidence

    assert "7.1" in result["answer"]
    assert "7.2" in result["answer"]

    assert (
        "Each production batch shall be subject "
        "to the applicable inspection activities."
        in result["answer"]
    )


def test_refuses_when_evidence_is_insufficient():
    """
    The generator must not produce a factual answer when
    the sufficiency checker says evidence is insufficient.
    """

    generator = GroundedAnswerGenerator()

    evidence = [
        {
            "chunk_id": "SYN-STD-101_chunk_25",
            "section": "7.1",
            "text": (
                "7.1 Each production batch shall be subject "
                "to the applicable inspection activities."
            ),
            "rerank_score": 0.7477,
        }
    ]

    result = generator.generate(
        query="What are the inspection requirements?",
        evidence=evidence,
        evidence_sufficient=False,
    )

    assert result["grounded"] is False
    assert result["evidence_used"] == []

    assert (
        result["answer"]
        == "I don't have enough reliable evidence to answer this question."
    )


def test_refuses_when_evidence_is_empty():
    """
    Empty evidence must never result in an answer.
    """

    generator = GroundedAnswerGenerator()

    result = generator.generate(
        query="What are the inspection requirements?",
        evidence=[],
        evidence_sufficient=True,
    )

    assert result["grounded"] is False
    assert result["evidence_used"] == []

    assert (
        result["answer"]
        == "I don't have enough reliable evidence to answer this question."
    )


def test_rejects_weak_evidence():
    """
    Evidence below the generator's minimum score should not
    be used for answer generation.
    """

    generator = GroundedAnswerGenerator(
        minimum_evidence_score=0.30
    )

    weak_evidence = [
        {
            "chunk_id": "weak_chunk",
            "section": "5.5",
            "text": (
                "5.5 Product characteristics shall remain "
                "within the permitted tolerance."
            ),
            "rerank_score": 0.20,
        }
    ]

    result = generator.generate(
        query="What are the inspection requirements?",
        evidence=weak_evidence,
        evidence_sufficient=True,
    )

    assert result["grounded"] is False
    assert result["evidence_used"] == []

    assert (
        result["answer"]
        == "I don't have enough reliable evidence to answer this question."
    )


def test_only_selected_evidence_is_used():
    """
    The generator must use only the evidence explicitly
    supplied to it.
    """

    generator = GroundedAnswerGenerator()

    selected_evidence = [
        {
            "chunk_id": "selected_1",
            "section": "7.1",
            "text": (
                "7.1 Each production batch shall be inspected."
            ),
            "rerank_score": 0.74,
        }
    ]

    result = generator.generate(
        query="What are the inspection requirements?",
        evidence=selected_evidence,
        evidence_sufficient=True,
    )

    assert result["grounded"] is True

    assert result["evidence_used"] == selected_evidence

    assert "Each production batch shall be inspected." in result["answer"]

    # Something that was never supplied as evidence must not appear.
    assert "certification fee" not in result["answer"]
    assert "hallmarking" not in result["answer"]


def test_skips_invalid_evidence():
    """
    Invalid evidence entries should be ignored.
    Valid evidence should still be used.
    """

    generator = GroundedAnswerGenerator()

    evidence = [
        {
            "chunk_id": "invalid_1",
            "section": "6.1",
            "text": "",
            "rerank_score": 0.80,
        },
        {
            "chunk_id": "valid_1",
            "section": "7.1",
            "text": (
                "7.1 Each production batch shall be inspected."
            ),
            "rerank_score": 0.74,
        },
    ]

    result = generator.generate(
        query="What are the inspection requirements?",
        evidence=evidence,
        evidence_sufficient=True,
    )

    assert result["grounded"] is True

    assert len(result["evidence_used"]) == 1
    assert result["evidence_used"][0]["chunk_id"] == "valid_1"

    assert "Each production batch shall be inspected." in result["answer"]


def test_rejects_empty_query():
    """
    Empty queries should raise an error.
    """

    generator = GroundedAnswerGenerator()

    try:
        generator.generate(
            query="",
            evidence=[],
            evidence_sufficient=False,
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert str(exc) == "Query cannot be empty."