from __future__ import annotations

from typing import Any


class GroundedAnswerGenerator:
    """
    P1 Grounded Answer Generator - V1

    This is a deterministic answer generator.

    IMPORTANT:
    The generator is allowed to use ONLY the evidence supplied to it.
    It must not access ChromaDB, the retriever, PDFs, or any other
    knowledge source directly.

    This V1 is intentionally simple. It establishes the grounding
    boundary before introducing an LLM-based generator.
    """

    def __init__(
        self,
        minimum_evidence_score: float = 0.30,
    ):
        self.minimum_evidence_score = minimum_evidence_score

    def generate(
        self,
        query: str,
        evidence: list[dict[str, Any]],
        evidence_sufficient: bool,
    ) -> dict[str, Any]:
        """
        Generate a grounded answer using only selected evidence.

        Parameters
        ----------
        query:
            User's question.

        evidence:
            Evidence selected by the P1 evidence selector.

        evidence_sufficient:
            Result from the P1 sufficiency checker.

        Returns
        -------
        dict
            Contains answer, evidence_used and grounded status.
        """

        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        # --------------------------------------------------
        # 1. Never answer if evidence is insufficient
        # --------------------------------------------------

        if not evidence_sufficient:
            return {
                "answer": (
                    "I don't have enough reliable evidence "
                    "to answer this question."
                ),
                "evidence_used": [],
                "grounded": False,
            }

        # --------------------------------------------------
        # 2. Validate evidence
        # --------------------------------------------------

        valid_evidence = []

        for item in evidence:

            if not isinstance(item, dict):
                continue

            text = item.get("text")

            if not text or not str(text).strip():
                continue

            score = item.get("rerank_score")

            # Some pipeline outputs may use similarity_score
            # instead of rerank_score.
            if score is None:
                score = item.get("similarity_score")

            if score is not None:
                try:
                    score = float(score)
                except (TypeError, ValueError):
                    continue

                if score < self.minimum_evidence_score:
                    continue

            valid_evidence.append(item)

        # --------------------------------------------------
        # 3. Final grounding guard
        # --------------------------------------------------

        if not valid_evidence:
            return {
                "answer": (
                    "I don't have enough reliable evidence "
                    "to answer this question."
                ),
                "evidence_used": [],
                "grounded": False,
            }

        # --------------------------------------------------
        # 4. Build deterministic grounded answer
        # --------------------------------------------------

        answer_parts = []

        answer_parts.append(
            "Based on the available evidence:"
        )

        for item in valid_evidence:

            text = str(item["text"]).strip()

            section = item.get("section")

            if section:
                prefix = f"{section} "

                if text.startswith(prefix):
                    text = text[len(prefix):].strip()

                answer_parts.append(
                    f"Clause {section}: {text}"
                )
            else:
                answer_parts.append(text)

        answer = "\n\n".join(answer_parts)

        # --------------------------------------------------
        # 5. Return answer + exact evidence used
        # --------------------------------------------------

        return {
            "answer": answer,
            "evidence_used": valid_evidence,
            "grounded": True,
        }


if __name__ == "__main__":

    print("=" * 70)
    print("P1 — Grounded Answer Generator V1")
    print("=" * 70)

    generator = GroundedAnswerGenerator()

    test_evidence = [
        {
            "chunk_id": "SYN-STD-101_chunk_7",
            "section": "7.1",
            "text": (
                "The manufacturer shall conduct inspection "
                "of the finished product."
            ),
            "rerank_score": 0.74,
        },
        {
            "chunk_id": "SYN-STD-101_chunk_8",
            "section": "7.2",
            "text": (
                "Inspection shall be performed according "
                "to the prescribed inspection procedure."
            ),
            "rerank_score": 0.69,
        },
    ]

    result = generator.generate(
        query="What are the inspection requirements?",
        evidence=test_evidence,
        evidence_sufficient=False,
    )

    print("\nAnswer:")
    print(result["answer"])

    print("\nEvidence used:")
    for item in result["evidence_used"]:
        print(
            f"- {item['chunk_id']} "
            f"(score={item.get('rerank_score')})"
        )

    print("\nGrounded:")
    print(result["grounded"])

    print("\n" + "=" * 70)