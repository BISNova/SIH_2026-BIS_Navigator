from confidence.scorer import ConfidenceScorer


def test_high_confidence():
    scorer = ConfidenceScorer()

    evidence = [
        {"chunk_id": "chunk_1", "rerank_score": 0.90},
        {"chunk_id": "chunk_2", "rerank_score": 0.85},
    ]

    result = scorer.score(
        evidence=evidence,
        evidence_sufficient=True,
        sufficiency_confidence=0.85,
    )

    assert result["confidence_label"] == "high"
    assert result["confidence_score"] >= 0.75


def test_medium_confidence():
    scorer = ConfidenceScorer()

    evidence = [
        {"chunk_id": "chunk_1", "rerank_score": 0.65},
        {"chunk_id": "chunk_2", "rerank_score": 0.60},
    ]

    result = scorer.score(
        evidence=evidence,
        evidence_sufficient=True,
        sufficiency_confidence=0.60,
    )

    assert result["confidence_label"] == "medium"
    assert 0.50 <= result["confidence_score"] < 0.75


def test_insufficient_evidence_returns_low():
    scorer = ConfidenceScorer()

    result = scorer.score(
        evidence=[],
        evidence_sufficient=False,
        sufficiency_confidence=0.0,
    )

    assert result["confidence_score"] == 0.0
    assert result["confidence_label"] == "low"


def test_missing_scores_returns_low():
    scorer = ConfidenceScorer()

    evidence = [
        {
            "chunk_id": "chunk_1",
            "text": "Some evidence",
        }
    ]

    result = scorer.score(
        evidence=evidence,
        evidence_sufficient=True,
        sufficiency_confidence=0.80,
    )

    assert result["confidence_score"] == 0.0
    assert result["confidence_label"] == "low"


def test_similarity_score_can_be_used():
    scorer = ConfidenceScorer()

    evidence = [
        {
            "chunk_id": "chunk_1",
            "similarity_score": 0.80,
        },
        {
            "chunk_id": "chunk_2",
            "similarity_score": 0.75,
        },
    ]

    result = scorer.score(
        evidence=evidence,
        evidence_sufficient=True,
        sufficiency_confidence=0.75,
    )

    assert result["confidence_score"] > 0.50
    assert result["confidence_label"] == "high"


def test_invalid_score_is_ignored():
    scorer = ConfidenceScorer()

    evidence = [
        {
            "chunk_id": "chunk_1",
            "rerank_score": "invalid",
        },
        {
            "chunk_id": "chunk_2",
            "rerank_score": 0.70,
        },
    ]

    result = scorer.score(
        evidence=evidence,
        evidence_sufficient=True,
        sufficiency_confidence=0.70,
    )

    assert result["confidence_score"] > 0.50


def test_score_is_bounded():
    scorer = ConfidenceScorer()

    evidence = [
        {
            "chunk_id": "chunk_1",
            "rerank_score": 1.50,
        },
        {
            "chunk_id": "chunk_2",
            "rerank_score": -0.50,
        },
    ]

    result = scorer.score(
        evidence=evidence,
        evidence_sufficient=True,
        sufficiency_confidence=1.50,
    )

    assert 0.0 <= result["confidence_score"] <= 1.0