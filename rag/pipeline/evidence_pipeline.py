from __future__ import annotations

from pathlib import Path
import sys

from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parents[1]

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


from retrieval.retriever import EvidenceRetriever
from retrieval.reranker import EvidenceReranker
from evidence.selector import EvidenceSelector
from evidence.sufficiency import EvidenceSufficiencyChecker
from answer.generator import GroundedAnswerGenerator
from citations.builder import CitationBuilder
from confidence.scorer import ConfidenceScorer


class EvidencePipeline:
    """
    P1 End-to-End Evidence Pipeline.

    Flow:

        Query
          ↓
        Embedding
          ↓
        Semantic Retrieval
          ↓
        Reranking
          ↓
        Evidence Selection
          ↓
        Evidence Sufficiency
          ↓
        Confidence Scoring
          ↓
        Grounded Answer Generation
          ↓
        Citation Building
          ↓
        Final Evidence Package
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        retrieval_top_k: int = 10,
        rerank_top_k: int = 5,
    ):
        print("Loading embedding model...")

        self.model = SentenceTransformer(model_name)

        print("Embedding model loaded.")

        self.retriever = EvidenceRetriever()

        self.reranker = EvidenceReranker()

        self.selector = EvidenceSelector(
            minimum_score=0.30,
            max_evidence=rerank_top_k,
        )

        self.sufficiency_checker = (
            EvidenceSufficiencyChecker(
                minimum_score=0.30,
                strong_score=0.50,
                minimum_evidence=1,
            )
        )

        self.confidence_scorer = ConfidenceScorer()

        self.answer_generator = GroundedAnswerGenerator(
            minimum_evidence_score=0.30
        )

        self.citation_builder = CitationBuilder()

        self.retrieval_top_k = retrieval_top_k
        self.rerank_top_k = rerank_top_k

    def _embed_query(self, query: str) -> list[float]:
        """
        Convert user query into a normalized embedding.
        """

        embedding = self.model.encode(
            query,
            normalize_embeddings=True,
        )

        return embedding.tolist()

    def run(
        self,
        query: str,
        standard_ids: list[str] | None = None,
    ) -> dict:
        """
        Run the complete P1 evidence, confidence,
        answer, and citation pipeline.
        """

        if not query or not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        # --------------------------------------------------
        # 1. Query embedding
        # --------------------------------------------------

        query_embedding = self._embed_query(
            query
        )

        # --------------------------------------------------
        # 2. Semantic retrieval
        # --------------------------------------------------

        retrieved_candidates = self.retriever.retrieve(
            query_embedding=query_embedding,
            top_k=self.retrieval_top_k,
            standard_ids=standard_ids,
        )

        # --------------------------------------------------
        # 3. Reranking
        # --------------------------------------------------

        reranked_candidates = self.reranker.rerank(
            query=query,
            candidates=retrieved_candidates,
            top_k=self.rerank_top_k,
            standard_ids=standard_ids,
        )

        # --------------------------------------------------
        # 4. Evidence selection
        # --------------------------------------------------

        selected_evidence = self.selector.select(
            candidates=reranked_candidates
        )

        # --------------------------------------------------
        # 5. Evidence sufficiency
        # --------------------------------------------------

        sufficiency = (
            self.sufficiency_checker.check(
                evidence=selected_evidence,
                standard_ids=standard_ids,
            )
        )

        evidence_sufficient = (
            sufficiency["evidence_sufficient"]
        )

        # --------------------------------------------------
        # 6. Final P1 confidence scoring
        # --------------------------------------------------

        confidence = self.confidence_scorer.score(
            evidence=selected_evidence,
            evidence_sufficient=evidence_sufficient,
            sufficiency_confidence=(
                sufficiency["confidence_score"]
            ),
        )

        # --------------------------------------------------
        # 7. Grounded answer generation
        # --------------------------------------------------

        answer_result = self.answer_generator.generate(
            query=query,
            evidence=selected_evidence,
            evidence_sufficient=evidence_sufficient,
        )

        # --------------------------------------------------
        # 8. Citation building
        # --------------------------------------------------

        citations = self.citation_builder.build(
            selected_evidence
        )

        # --------------------------------------------------
        # 9. Final P1 package
        # --------------------------------------------------

        return {
            "query": query,

            "standard_ids": standard_ids,

            "retrieved_count": len(
                retrieved_candidates
            ),

            "reranked_count": len(
                reranked_candidates
            ),

            "selected_count": len(
                selected_evidence
            ),

            "evidence": selected_evidence,

            "answer": answer_result["answer"],

            "evidence_used": answer_result[
                "evidence_used"
            ],

            "citations": citations,

            "grounded": answer_result[
                "grounded"
            ],

            "evidence_sufficient": (
                evidence_sufficient
            ),

            # Final P1 confidence
            "confidence_score": (
                confidence[
                    "confidence_score"
                ]
            ),

            "confidence_label": (
                confidence[
                    "confidence_label"
                ]
            ),

            "confidence_reason": (
                confidence[
                    "reason"
                ]
            ),

            # Sufficiency information
            "sufficiency_confidence": (
                sufficiency[
                    "confidence_score"
                ]
            ),

            "sufficiency_reason": (
                sufficiency[
                    "reason"
                ]
            ),

            "strong_evidence_count": (
                sufficiency[
                    "strong_evidence_count"
                ]
            ),

            "matched_standard_count": (
                sufficiency[
                    "matched_standard_count"
                ]
            ),
        }


if __name__ == "__main__":

    print("=" * 70)
    print(
        "P1 — End-to-End Evidence + Confidence + "
        "Answer + Citation Pipeline"
    )
    print("=" * 70)

    pipeline = EvidencePipeline()

    print("\nChromaDB evidence count:")
    print(pipeline.retriever.count())

    # ==================================================
    # TEST 1 — Standard-specific question
    # ==================================================

    print("\n" + "=" * 70)
    print("TEST 1 — Standard-specific question")
    print("=" * 70)

    query = "What are the inspection requirements?"

    result = pipeline.run(
        query=query,
        standard_ids=["SYN-STD-101"],
    )

    print("\nQuery:")
    print(query)

    print("\nAnswer:")
    print("-" * 70)
    print(result["answer"])

    print("\nGrounded:")
    print(result["grounded"])

    print("\nEvidence sufficient:")
    print(result["evidence_sufficient"])

    print("\nFinal P1 Confidence:")
    print(
        f"{result['confidence_score']:.4f}"
    )

    print("\nConfidence label:")
    print(result["confidence_label"])

    print("\nConfidence reason:")
    print(result["confidence_reason"])

    print("\nSufficiency confidence:")
    print(
        f"{result['sufficiency_confidence']:.4f}"
    )

    print("\nEvidence used:")
    print("-" * 70)

    for item in result["evidence_used"]:
        print(
            f"{item.get('chunk_id')} | "
            f"Section {item.get('section')} | "
            f"Score {item.get('rerank_score', 0):.4f}"
        )

    print("\nCitations:")
    print("-" * 70)

    for citation in result["citations"]:

        print(
            f"{citation.get('standard_id')} | "
            f"{citation.get('document_title')} | "
            f"Clause {citation.get('section')} | "
            f"Page {citation.get('page_number')}"
        )

        print(
            f"Source: "
            f"{citation.get('source_url')}"
        )

    # ==================================================
    # TEST 2 — General question
    # ==================================================

    print("\n" + "=" * 70)
    print("TEST 2 — General question")
    print("=" * 70)

    query = "What documents are required for certification?"

    result = pipeline.run(
        query=query,
        standard_ids=None,
    )

    print("\nQuery:")
    print(query)

    print("\nAnswer:")
    print("-" * 70)
    print(result["answer"])

    print("\nGrounded:")
    print(result["grounded"])

    print("\nEvidence sufficient:")
    print(result["evidence_sufficient"])

    print("\nFinal P1 Confidence:")
    print(
        f"{result['confidence_score']:.4f}"
    )

    print("\nConfidence label:")
    print(result["confidence_label"])

    print("\nConfidence reason:")
    print(result["confidence_reason"])

    print("\nSufficiency confidence:")
    print(
        f"{result['sufficiency_confidence']:.4f}"
    )

    print("\nCitations:")
    print("-" * 70)

    for citation in result["citations"]:

        print(
            f"{citation.get('standard_id')} | "
            f"{citation.get('document_title')} | "
            f"Clause {citation.get('section')} | "
            f"Page {citation.get('page_number')}"
        )

    # ==================================================
    # TEST 3 — Unknown / unrelated question
    # ==================================================

    print("\n" + "=" * 70)
    print("TEST 3 — Unknown / unrelated question")
    print("=" * 70)

    query = (
        "What is the procedure for something "
        "completely unrelated?"
    )

    result = pipeline.run(
        query=query,
        standard_ids=None,
    )

    print("\nQuery:")
    print(query)

    print("\nAnswer:")
    print("-" * 70)
    print(result["answer"])

    print("\nGrounded:")
    print(result["grounded"])

    print("\nEvidence sufficient:")
    print(result["evidence_sufficient"])

    print("\nFinal P1 Confidence:")
    print(
        f"{result['confidence_score']:.4f}"
    )

    print("\nConfidence label:")
    print(result["confidence_label"])

    print("\nConfidence reason:")
    print(result["confidence_reason"])

    print("\nSufficiency confidence:")
    print(
        f"{result['sufficiency_confidence']:.4f}"
    )

    print("\nCitations:")
    print("-" * 70)

    if result["citations"]:
        for citation in result["citations"]:
            print(citation)
    else:
        print("No citations generated.")

    print("\n" + "=" * 70)
    print("End-to-end P1 pipeline test completed.")
    print("=" * 70)