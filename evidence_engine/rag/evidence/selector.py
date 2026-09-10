from __future__ import annotations


class EvidenceSelector:
    """
    P1 Evidence Selection layer.

    Takes reranked candidates and selects evidence that is
    sufficiently relevant for answering the user's question.

    This layer does NOT generate an answer.
    It only decides which retrieved chunks should be passed
    to the next stage.
    """

    def __init__(
        self,
        minimum_score: float = 0.30,
        max_evidence: int = 5,
    ):
        self.minimum_score = minimum_score
        self.max_evidence = max_evidence

    def select(
        self,
        candidates: list[dict],
    ) -> list[dict]:
        """
        Select useful evidence from reranked candidates.

        Candidates are expected to contain:
        - chunk_id
        - text
        - rerank_score
        - similarity_score
        """

        if not candidates:
            return []

        selected = []

        for candidate in candidates:

            rerank_score = float(
                candidate.get("rerank_score", 0.0)
            )

            if rerank_score < self.minimum_score:
                continue

            selected.append(candidate)

            if len(selected) >= self.max_evidence:
                break

        return selected


if __name__ == "__main__":

    print("=" * 60)
    print("P1 — Evidence Selector")
    print("=" * 60)

    candidates = [
        {
            "chunk_id": "chunk_1",
            "text": "Inspection requirements shall be verified.",
            "similarity_score": 0.64,
            "rerank_score": 0.74,
        },
        {
            "chunk_id": "chunk_2",
            "text": "Testing shall follow the specified procedure.",
            "similarity_score": 0.60,
            "rerank_score": 0.65,
        },
        {
            "chunk_id": "chunk_3",
            "text": "Materials shall meet specified requirements.",
            "similarity_score": 0.40,
            "rerank_score": 0.25,
        },
    ]

    selector = EvidenceSelector(
        minimum_score=0.30,
        max_evidence=5,
    )

    selected = selector.select(candidates)

    print(f"\nInput candidates: {len(candidates)}")
    print(f"Selected evidence: {len(selected)}")

    print("\nSelected:")
    print("-" * 60)

    for rank, result in enumerate(
        selected,
        start=1
    ):
        print(f"\nRank {rank}")
        print(f"Chunk: {result['chunk_id']}")
        print(f"Score: {result['rerank_score']:.4f}")
        print(f"Evidence: {result['text']}")

    print("\n" + "=" * 60)
    print("Evidence selector test completed.")
    print("=" * 60)