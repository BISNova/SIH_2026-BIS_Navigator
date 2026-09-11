from __future__ import annotations

from typing import Any


class ConfidenceScorer:
    """
    P1 Confidence Scoring layer.

    Converts evidence quality and sufficiency information
    into a final P1 confidence score and confidence label.

    This layer does NOT:
    - retrieve evidence
    - generate answers
    - modify evidence
    - create citations

    It only evaluates the information already produced
    by the P1 evidence pipeline.
    """

    def __init__(
        self,
        high_threshold: float = 0.75,
        medium_threshold: float = 0.50,
    ):
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold

    def score(
        self,
        evidence: list[dict[str, Any]],
        evidence_sufficient: bool,
        sufficiency_confidence: float = 0.0,
    ) -> dict[str, Any]:
        """
        Calculate final P1 confidence.

        Parameters
        ----------
        evidence:
            Selected evidence from EvidenceSelector.

        evidence_sufficient:
            Result from EvidenceSufficiencyChecker.

        sufficiency_confidence:
            Confidence calculated by the sufficiency layer.

        Returns
        -------
        dict
            Contains confidence_score and confidence_label.
        """

        # --------------------------------------------------
        # 1. No sufficient evidence
        # --------------------------------------------------

        if not evidence_sufficient:
            return {
                "confidence_score": 0.0,
                "confidence_label": "low",
                "reason": (
                    "Evidence is not sufficient to support "
                    "a confident answer."
                ),
            }

        # --------------------------------------------------
        # 2. No evidence
        # --------------------------------------------------

        if not evidence:
            return {
                "confidence_score": 0.0,
                "confidence_label": "low",
                "reason": (
                    "No evidence is available for "
                    "confidence scoring."
                ),
            }

        # --------------------------------------------------
        # 3. Collect valid evidence scores
        # --------------------------------------------------

        scores = []

        for item in evidence:

            if not isinstance(item, dict):
                continue

            score = item.get("rerank_score")

            if score is None:
                score = item.get("similarity_score")

            if score is None:
                continue

            try:
                score = float(score)
            except (TypeError, ValueError):
                continue

            scores.append(
                max(0.0, min(score, 1.0))
            )

        if not scores:
            return {
                "confidence_score": 0.0,
                "confidence_label": "low",
                "reason": (
                    "Evidence does not contain valid "
                    "relevance scores."
                ),
            }

        # --------------------------------------------------
        # 4. Calculate evidence quality
        # --------------------------------------------------

        average_evidence_score = (
            sum(scores) / len(scores)
        )

        # --------------------------------------------------
        # 5. Combine with sufficiency confidence
        # --------------------------------------------------

        try:
            sufficiency_confidence = float(
                sufficiency_confidence
            )
        except (TypeError, ValueError):
            sufficiency_confidence = 0.0

        sufficiency_confidence = max(
            0.0,
            min(sufficiency_confidence, 1.0)
        )

        confidence_score = (
            0.70 * average_evidence_score
            + 0.30 * sufficiency_confidence
        )

        confidence_score = max(
            0.0,
            min(confidence_score, 1.0)
        )

        confidence_score = round(
            confidence_score,
            4
        )

        # --------------------------------------------------
        # 6. Assign confidence label
        # --------------------------------------------------

        if confidence_score >= self.high_threshold:

            confidence_label = "high"

        elif confidence_score >= self.medium_threshold:

            confidence_label = "medium"

        else:

            confidence_label = "low"

        # --------------------------------------------------
        # 7. Explanation
        # --------------------------------------------------

        reason = (
            "Confidence is based on the quality of the "
            "selected evidence and the evidence sufficiency "
            "assessment."
        )

        return {
            "confidence_score": confidence_score,
            "confidence_label": confidence_label,
            "reason": reason,
        }


if __name__ == "__main__":

    print("=" * 70)
    print("P1 — Confidence Scorer")
    print("=" * 70)

    scorer = ConfidenceScorer()

    # ==================================================
    # TEST 1 — High confidence
    # ==================================================

    strong_evidence = [
        {
            "chunk_id": "chunk_1",
            "rerank_score": 0.90,
        },
        {
            "chunk_id": "chunk_2",
            "rerank_score": 0.85,
        },
    ]

    result = scorer.score(
        evidence=strong_evidence,
        evidence_sufficient=True,
        sufficiency_confidence=0.85,
    )

    print("\nTEST 1 — Strong evidence")
    print("-" * 70)

    for key, value in result.items():
        print(f"{key}: {value}")

    # ==================================================
    # TEST 2 — Medium confidence
    # ==================================================

    medium_evidence = [
        {
            "chunk_id": "chunk_3",
            "rerank_score": 0.65,
        },
        {
            "chunk_id": "chunk_4",
            "rerank_score": 0.60,
        },
    ]

    result = scorer.score(
        evidence=medium_evidence,
        evidence_sufficient=True,
        sufficiency_confidence=0.60,
    )

    print("\nTEST 2 — Medium evidence")
    print("-" * 70)

    for key, value in result.items():
        print(f"{key}: {value}")

    # ==================================================
    # TEST 3 — Insufficient evidence
    # ==================================================

    result = scorer.score(
        evidence=[],
        evidence_sufficient=False,
        sufficiency_confidence=0.0,
    )

    print("\nTEST 3 — Insufficient evidence")
    print("-" * 70)

    for key, value in result.items():
        print(f"{key}: {value}")

    print("\n" + "=" * 70)
    print("Confidence scorer test completed.")
    print("=" * 70)