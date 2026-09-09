from __future__ import annotations


class EvidenceSufficiencyChecker:
    """
    P1 Evidence Sufficiency layer.

    Determines whether the selected evidence is strong enough
    to safely support an answer.

    This layer does NOT generate an answer.

    It checks:
    1. Whether evidence exists
    2. Whether evidence scores are strong enough
    3. Whether enough evidence is available
    4. Whether the evidence comes from the expected standards
    """

    def __init__(
        self,
        minimum_score: float = 0.30,
        strong_score: float = 0.50,
        minimum_evidence: int = 1,
    ):
        self.minimum_score = minimum_score
        self.strong_score = strong_score
        self.minimum_evidence = minimum_evidence

    def check(
        self,
        evidence: list[dict],
        standard_ids: list[str] | None = None,
    ) -> dict:
        """
        Check whether selected evidence is sufficient.

        Parameters
        ----------
        evidence:
            Evidence selected by EvidenceSelector.

        standard_ids:
            Standards expected to provide evidence.
            None means this is a general question.

        Returns
        -------
        dict
            Sufficiency result.
        """

        # --------------------------------------------------
        # 1. No evidence
        # --------------------------------------------------

        if not evidence:
            return {
                "evidence_sufficient": False,
                "confidence_score": 0.0,
                "reason": "No evidence was retrieved.",
                "evidence_count": 0,
                "strong_evidence_count": 0,
                "matched_standard_count": 0,
            }

        # --------------------------------------------------
        # 2. Filter evidence by minimum score
        # --------------------------------------------------

        valid_evidence = []

        for item in evidence:

            score = float(
                item.get("rerank_score", 0.0)
            )

            if score >= self.minimum_score:
                valid_evidence.append(item)

        if not valid_evidence:
            return {
                "evidence_sufficient": False,
                "confidence_score": 0.0,
                "reason": (
                    "Retrieved evidence is below "
                    "the minimum relevance threshold."
                ),
                "evidence_count": len(evidence),
                "strong_evidence_count": 0,
                "matched_standard_count": 0,
            }

        # --------------------------------------------------
        # 3. Count strong evidence
        # --------------------------------------------------

        strong_evidence = [
            item
            for item in valid_evidence
            if float(
                item.get("rerank_score", 0.0)
            ) >= self.strong_score
        ]

        strong_evidence_count = len(strong_evidence)

        # --------------------------------------------------
        # 4. Check standard coverage
        # --------------------------------------------------

        matched_standard_ids = set()

        if standard_ids:

            expected_standards = set(standard_ids)

            for item in valid_evidence:

                standard_id = item.get("standard_id")

                if standard_id in expected_standards:
                    matched_standard_ids.add(
                        standard_id
                    )

        else:
            # General question — no specific standards expected.
            matched_standard_ids = set()

        # --------------------------------------------------
        # 5. Determine sufficiency
        # --------------------------------------------------

        enough_evidence = (
            len(valid_evidence)
            >= self.minimum_evidence
        )

        has_strong_evidence = (
            strong_evidence_count > 0
        )

        if standard_ids:

            standards_covered = (
                len(matched_standard_ids)
                == len(set(standard_ids))
            )

            evidence_sufficient = (
                enough_evidence
                and has_strong_evidence
                and standards_covered
            )

        else:

            evidence_sufficient = (
                enough_evidence
                and has_strong_evidence
            )

        # --------------------------------------------------
        # 6. Calculate confidence
        # --------------------------------------------------

        scores = [
            float(
                item.get("rerank_score", 0.0)
            )
            for item in valid_evidence
        ]

        average_score = sum(scores) / len(scores)

        confidence_score = min(
            max(average_score, 0.0),
            1.0
        )

        # If expected standards are missing,
        # reduce confidence.

        if standard_ids:

            coverage_ratio = (
                len(matched_standard_ids)
                / len(set(standard_ids))
            )

            confidence_score *= coverage_ratio

        # --------------------------------------------------
        # 7. Generate explanation
        # --------------------------------------------------

        if evidence_sufficient:

            reason = (
                "Sufficient relevant evidence is available "
                "to support an answer."
            )

        elif standard_ids and (
            len(matched_standard_ids)
            < len(set(standard_ids))
        ):

            reason = (
                "Evidence was found, but not all "
                "expected standards are covered."
            )

        elif not has_strong_evidence:

            reason = (
                "Evidence was retrieved, but none "
                "is sufficiently strong."
            )

        else:

            reason = (
                "Some relevant evidence was found, "
                "but it is not sufficient for a confident answer."
            )

        return {
            "evidence_sufficient": evidence_sufficient,
            "confidence_score": round(
                confidence_score,
                4
            ),
            "reason": reason,
            "evidence_count": len(valid_evidence),
            "strong_evidence_count": strong_evidence_count,
            "matched_standard_count": len(
                matched_standard_ids
            ),
        }


if __name__ == "__main__":

    print("=" * 60)
    print("P1 — Evidence Sufficiency Checker")
    print("=" * 60)

    # --------------------------------------------------
    # TEST 1 — Strong evidence
    # --------------------------------------------------

    strong_evidence = [
        {
            "chunk_id": "chunk_1",
            "text": (
                "Inspection requirements shall "
                "be verified."
            ),
            "rerank_score": 0.74,
            "standard_id": "SYN-STD-101",
        },
        {
            "chunk_id": "chunk_2",
            "text": (
                "Inspection shall be performed "
                "at specified intervals."
            ),
            "rerank_score": 0.65,
            "standard_id": "SYN-STD-101",
        },
    ]

    checker = EvidenceSufficiencyChecker()

    result = checker.check(
        evidence=strong_evidence,
        standard_ids=["SYN-STD-101"],
    )

    print("\nTEST 1 — Strong evidence")
    print("-" * 60)

    for key, value in result.items():
        print(f"{key}: {value}")

    # --------------------------------------------------
    # TEST 2 — Weak evidence
    # --------------------------------------------------

    weak_evidence = [
        {
            "chunk_id": "chunk_3",
            "text": "Some unrelated information.",
            "rerank_score": 0.24,
            "standard_id": "SYN-STD-101",
        }
    ]

    result = checker.check(
        evidence=weak_evidence,
        standard_ids=["SYN-STD-101"],
    )

    print("\nTEST 2 — Weak evidence")
    print("-" * 60)

    for key, value in result.items():
        print(f"{key}: {value}")

    # --------------------------------------------------
    # TEST 3 — No evidence
    # --------------------------------------------------

    result = checker.check(
        evidence=[],
        standard_ids=["SYN-STD-101"],
    )

    print("\nTEST 3 — No evidence")
    print("-" * 60)

    for key, value in result.items():
        print(f"{key}: {value}")

    # --------------------------------------------------
    # TEST 4 — Multiple standards
    # --------------------------------------------------

    multi_standard_evidence = [
        {
            "chunk_id": "chunk_4",
            "text": "Requirement from Standard A.",
            "rerank_score": 0.70,
            "standard_id": "SYN-STD-101",
        },
        {
            "chunk_id": "chunk_5",
            "text": "Requirement from Standard B.",
            "rerank_score": 0.68,
            "standard_id": "SYN-STD-202",
        },
    ]

    result = checker.check(
        evidence=multi_standard_evidence,
        standard_ids=[
            "SYN-STD-101",
            "SYN-STD-202",
        ],
    )

    print("\nTEST 4 — Multiple standards")
    print("-" * 60)

    for key, value in result.items():
        print(f"{key}: {value}")

    print("\n" + "=" * 60)
    print("Evidence sufficiency tests completed.")
    print("=" * 60)