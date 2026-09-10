from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from sentence_transformers import SentenceTransformer


# ============================================================
# Project path setup
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# ============================================================
# Existing P1 components
# ============================================================

from retrieval.retriever import EvidenceRetriever
from retrieval.reranker import EvidenceReranker
from evidence.selector import EvidenceSelector
from evidence.sufficiency import EvidenceSufficiencyChecker
from answer.generator import GroundedAnswerGenerator
from citations.builder import CitationBuilder
from confidence.scorer import ConfidenceScorer


# ============================================================
# P4 components
# ============================================================

from rag.knowledge.adapter import P4KnowledgeAdapter
from rag.knowledge.evidence_builder import P4EvidenceBuilder


class EvidencePipeline:
    """
    P1 End-to-End Evidence Pipeline with P4 Knowledge Integration.

    Flow:

        Query
          ↓
        Query Embedding
          ↓
        ┌─────────────────────────────┐
        │                             │
        ▼                             ▼
    P1 Chroma                  P4 Structured Knowledge
    Retrieval                  Evidence Builder
        │                             │
        └──────────────┬──────────────┘
                       ▼
                Merged Evidence
                       ↓
                    Reranking
                       ↓
          Coverage-aware Selection
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

    P4 integration is activated when standard_ids
    are supplied.

    For multi-standard queries, selection is coverage-aware:
    at least one relevant evidence item is selected from each
    expected standard whenever suitable evidence is available.
    """

    # ========================================================
    # Initialization
    # ========================================================

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        retrieval_top_k: int = 10,
        rerank_top_k: int = 5,
    ):
        print("Loading embedding model...")

        self.model = SentenceTransformer(model_name)

        print("Embedding model loaded.")

        # ----------------------------------------------------
        # Existing P1 components
        # ----------------------------------------------------

        self.retriever = EvidenceRetriever()

        self.reranker = EvidenceReranker()

        self.selector = EvidenceSelector(
            minimum_score=0.30,
            max_evidence=rerank_top_k,
        )

        self.sufficiency_checker = EvidenceSufficiencyChecker(
            minimum_score=0.30,
            strong_score=0.50,
            minimum_evidence=1,
        )

        self.confidence_scorer = ConfidenceScorer()

        self.answer_generator = GroundedAnswerGenerator(
            minimum_evidence_score=0.30
        )

        self.citation_builder = CitationBuilder()

        self.retrieval_top_k = retrieval_top_k
        self.rerank_top_k = rerank_top_k

        # ----------------------------------------------------
        # P4 components
        # ----------------------------------------------------

        self.p4_adapter = P4KnowledgeAdapter()

        self.p4_evidence_builder = P4EvidenceBuilder(
            self.p4_adapter
        )

    # ========================================================
    # Query embedding
    # ========================================================

    def _embed_query(
        self,
        query: str,
    ) -> list[float]:
        """
        Generate a normalized embedding for the query.
        """

        embedding = self.model.encode(
            query,
            normalize_embeddings=True,
        )

        return embedding.tolist()

    # ========================================================
    # Similarity calculation
    # ========================================================

    def _calculate_similarity(
        self,
        query_embedding: list[float],
        text: str,
    ) -> float:
        """
        Calculate cosine similarity between the query embedding
        and an evidence text embedding.

        Both vectors are normalized, so their dot product is
        equivalent to cosine similarity.
        """

        if not text or not text.strip():
            return 0.0

        evidence_embedding = self.model.encode(
            text,
            normalize_embeddings=True,
        )

        similarity = float(
            sum(
                q * e
                for q, e in zip(
                    query_embedding,
                    evidence_embedding.tolist(),
                )
            )
        )

        return max(
            0.0,
            min(similarity, 1.0),
        )

    # ========================================================
    # Prepare P4 evidence
    # ========================================================

    def _prepare_p4_evidence(
        self,
        query: str,
        query_embedding: list[float],
        standard_ids: list[str],
    ) -> list[dict[str, Any]]:
        """
        Build structured P4 evidence for the supplied standards.

        Each P4 EvidenceRecord is converted into a dictionary and
        assigned a semantic similarity score so that it can enter
        the existing P1 reranking pipeline.
        """

        if not standard_ids:
            return []

        p4_records: list[Any] = []

        for standard_id in standard_ids:

            records = (
                self.p4_evidence_builder.build_for_standard(
                    standard_id
                )
            )

            if records:
                p4_records.extend(records)

        prepared: list[dict[str, Any]] = []

        for record in p4_records:

            # Pydantic v2
            if hasattr(record, "model_dump"):
                item = record.model_dump()

            # Pydantic v1 compatibility
            elif hasattr(record, "dict"):
                item = record.dict()

            # Already a dictionary
            elif isinstance(record, dict):
                item = dict(record)

            else:
                continue

            text = item.get("text")

            if not text or not str(text).strip():
                continue

            similarity_score = self._calculate_similarity(
                query_embedding=query_embedding,
                text=str(text),
            )

            item["similarity_score"] = similarity_score

            # Initial rerank value.
            # The actual reranker will overwrite this.
            item.setdefault(
                "rerank_score",
                similarity_score,
            )

            prepared.append(item)

        return prepared

    # ========================================================
    # Merge P1 + P4 evidence
    # ========================================================

    def _merge_evidence(
        self,
        p1_evidence: list[dict[str, Any]],
        p4_evidence: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Merge P1 retrieved evidence and P4 structured evidence.

        Duplicate chunk IDs are removed while preserving order.
        """

        merged: list[dict[str, Any]] = []

        seen_chunk_ids: set[str] = set()

        for item in p1_evidence + p4_evidence:

            if not isinstance(item, dict):
                continue

            chunk_id = item.get("chunk_id")

            if not chunk_id:
                continue

            if chunk_id in seen_chunk_ids:
                continue

            seen_chunk_ids.add(chunk_id)

            merged.append(item)

        return merged

    # ========================================================
    # Coverage-aware evidence selection
    # ========================================================

    def _select_with_standard_coverage(
        self,
        candidates: list[dict[str, Any]],
        standard_ids: list[str] | None,
    ) -> list[dict[str, Any]]:
        """
        Select final evidence while preserving coverage of
        applicable standards.

        Normal P1 behavior:
            candidates → selector → top evidence

        Multi-standard P4 behavior:
            1. Prefer at least one relevant candidate from every
               expected standard.
            2. Fill remaining evidence slots with highest-scoring
               candidates overall.
            3. Never exceed self.rerank_top_k.

        This method does not weaken the sufficiency checker.
        It simply gives the sufficiency checker a better evidence
        set to evaluate.
        """

        if not candidates:
            return []

        # ----------------------------------------------------
        # General P1 query
        # ----------------------------------------------------

        if not standard_ids:
            return self.selector.select(
                candidates=candidates
            )

        expected_standards = list(
            dict.fromkeys(standard_ids)
        )

        # ----------------------------------------------------
        # First filter by the existing selector threshold.
        #
        # We do this ourselves instead of immediately calling
        # selector.select(), because we need to preserve enough
        # candidates to achieve standard coverage.
        # ----------------------------------------------------

        valid_candidates = []

        for candidate in candidates:

            score = float(
                candidate.get(
                    "rerank_score",
                    0.0,
                )
            )

            if score < self.selector.minimum_score:
                continue

            valid_candidates.append(candidate)

        if not valid_candidates:
            return []

        # ----------------------------------------------------
        # Candidates are already sorted by the reranker.
        #
        # We still sort here to make this method safe if it is
        # called independently.
        # ----------------------------------------------------

        valid_candidates.sort(
            key=lambda item: (
                float(
                    item.get(
                        "rerank_score",
                        0.0,
                    )
                ),
                float(
                    item.get(
                        "similarity_score",
                        0.0,
                    )
                ),
            ),
            reverse=True,
        )

        selected: list[dict[str, Any]] = []

        selected_chunk_ids: set[str] = set()

        # ----------------------------------------------------
        # STEP 1
        #
        # Select the strongest candidate for every expected
        # standard.
        # ----------------------------------------------------

        for standard_id in expected_standards:

            best_candidate = None

            for candidate in valid_candidates:

                if candidate.get("chunk_id") in selected_chunk_ids:
                    continue

                if candidate.get("standard_id") != standard_id:
                    continue

                best_candidate = candidate
                break

            if best_candidate is None:
                continue

            selected.append(best_candidate)

            selected_chunk_ids.add(
                best_candidate.get("chunk_id")
            )

            if len(selected) >= self.rerank_top_k:
                break

        # ----------------------------------------------------
        # STEP 2
        #
        # Fill remaining slots with strongest candidates.
        # ----------------------------------------------------

        if len(selected) < self.rerank_top_k:

            for candidate in valid_candidates:

                chunk_id = candidate.get("chunk_id")

                if chunk_id in selected_chunk_ids:
                    continue

                selected.append(candidate)

                selected_chunk_ids.add(chunk_id)

                if len(selected) >= self.rerank_top_k:
                    break

        # ----------------------------------------------------
        # Final ordering by rerank score.
        #
        # Coverage is guaranteed, but the final evidence is
        # still presented in relevance order.
        # ----------------------------------------------------

        selected.sort(
            key=lambda item: (
                float(
                    item.get(
                        "rerank_score",
                        0.0,
                    )
                ),
                float(
                    item.get(
                        "similarity_score",
                        0.0,
                    )
                ),
            ),
            reverse=True,
        )

        return selected

    # ========================================================
    # Main pipeline
    # ========================================================

    def run(
        self,
        query: str,
        standard_ids: list[str] | None = None,
    ) -> dict:
        """
        Run the complete P1 + P4 evidence pipeline.
        """

        if not query or not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        # ----------------------------------------------------
        # 1. Query embedding
        # ----------------------------------------------------

        query_embedding = self._embed_query(query)

        # ----------------------------------------------------
        # 2. Existing P1 retrieval
        # ----------------------------------------------------

        retrieved_candidates = self.retriever.retrieve(
            query_embedding=query_embedding,
            top_k=self.retrieval_top_k,
            standard_ids=standard_ids,
        )

        # ----------------------------------------------------
        # 3. P4 structured evidence
        # ----------------------------------------------------

        p4_candidates: list[dict[str, Any]] = []

        if standard_ids:

            p4_candidates = self._prepare_p4_evidence(
                query=query,
                query_embedding=query_embedding,
                standard_ids=standard_ids,
            )

        # ----------------------------------------------------
        # 4. Merge P1 + P4
        # ----------------------------------------------------

        combined_candidates = self._merge_evidence(
            p1_evidence=retrieved_candidates,
            p4_evidence=p4_candidates,
        )

        # ----------------------------------------------------
        # 5. Reranking
        #
        # IMPORTANT:
        # For multi-standard P4 queries, use a larger reranking
        # pool so evidence from lower-ranked applicable standards
        # is not discarded before coverage-aware selection.
        # ----------------------------------------------------

        if standard_ids and len(standard_ids) > 1:

            coverage_rerank_top_k = max(
                self.rerank_top_k,
                len(standard_ids) * 5,
            )

        else:

            coverage_rerank_top_k = self.rerank_top_k

        reranked_candidates = self.reranker.rerank(
            query=query,
            candidates=combined_candidates,
            top_k=coverage_rerank_top_k,
            standard_ids=standard_ids,
        )

        # ----------------------------------------------------
        # 6. Coverage-aware selection
        # ----------------------------------------------------

        selected_evidence = (
            self._select_with_standard_coverage(
                candidates=reranked_candidates,
                standard_ids=standard_ids,
            )
        )

        # ----------------------------------------------------
        # 7. Evidence sufficiency
        # ----------------------------------------------------

        sufficiency = self.sufficiency_checker.check(
            evidence=selected_evidence,
            standard_ids=standard_ids,
        )

        evidence_sufficient = (
            sufficiency["evidence_sufficient"]
        )

        # ----------------------------------------------------
        # 8. Confidence scoring
        # ----------------------------------------------------

        confidence = self.confidence_scorer.score(
            evidence=selected_evidence,
            evidence_sufficient=evidence_sufficient,
            sufficiency_confidence=(
                sufficiency["confidence_score"]
            ),
        )

        # ----------------------------------------------------
        # 9. Grounded answer generation
        # ----------------------------------------------------

        answer_result = self.answer_generator.generate(
            query=query,
            evidence=selected_evidence,
            evidence_sufficient=evidence_sufficient,
        )

        # ----------------------------------------------------
        # 10. Citation building
        # ----------------------------------------------------

        citations = self.citation_builder.build(
            selected_evidence
        )

        # ----------------------------------------------------
        # 11. Final result
        # ----------------------------------------------------

        return {
            "query": query,
            "standard_ids": standard_ids,

            "retrieved_count": len(
                retrieved_candidates
            ),

            "p4_evidence_count": len(
                p4_candidates
            ),

            "combined_evidence_count": len(
                combined_candidates
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

            "confidence_score": confidence[
                "confidence_score"
            ],

            "confidence_label": confidence[
                "confidence_label"
            ],

            "confidence_reason": confidence[
                "reason"
            ],

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


# ============================================================
# Standalone End-to-End Tests
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print(
        "P1 + P4 — End-to-End Evidence Pipeline"
    )
    print("=" * 70)

    pipeline = EvidencePipeline()

    # ========================================================
    # TEST 1 — Pressure Cooker
    # ========================================================

    print("\n" + "=" * 70)
    print(
        "TEST 1 — P4 Integration: Domestic Pressure Cooker"
    )
    print("=" * 70)

    query = (
        "What tests are required for a "
        "domestic pressure cooker?"
    )

    result = pipeline.run(
        query=query,
        standard_ids=["STD-001"],
    )

    print("\nQuery:")
    print(query)

    print("\nP1 retrieved evidence:")
    print(result["retrieved_count"])

    print("\nP4 structured evidence:")
    print(result["p4_evidence_count"])

    print("\nCombined candidates:")
    print(result["combined_evidence_count"])

    print("\nReranked candidates:")
    print(result["reranked_count"])

    print("\nSelected evidence:")
    print(result["selected_count"])

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

    print("\nEvidence used:")
    print("-" * 70)

    for item in result["evidence_used"]:

        print(
            f"{item.get('chunk_id')} | "
            f"Standard {item.get('standard_id')} | "
            f"Score "
            f"{item.get('rerank_score', 0):.4f}"
        )

    print("\nCitations:")
    print("-" * 70)

    for citation in result["citations"]:

        print(
            f"{citation.get('standard_id')} | "
            f"{citation.get('document_title')} | "
            f"Source: "
            f"{citation.get('source_url')}"
        )

    # ========================================================
    # TEST 2 — Storage Electric Water Heater
    # ========================================================

    print("\n" + "=" * 70)
    print(
        "TEST 2 — P4 Integration: "
        "Storage Electric Water Heater"
    )
    print("=" * 70)

    query = (
        "What tests are required for a "
        "storage electric water heater?"
    )

    result = pipeline.run(
        query=query,
        standard_ids=[
            "STD-002",
            "STD-003",
            "STD-004",
        ],
    )

    print("\nQuery:")
    print(query)

    print("\nP1 retrieved evidence:")
    print(result["retrieved_count"])

    print("\nP4 structured evidence:")
    print(result["p4_evidence_count"])

    print("\nCombined candidates:")
    print(result["combined_evidence_count"])

    print("\nReranked candidates:")
    print(result["reranked_count"])

    print("\nSelected evidence:")
    print(result["selected_count"])

    print("\nSelected evidence details:")
    for item in result["evidence"]:

        print(
            f"{item.get('chunk_id')} | "
            f"Standard={item.get('standard_id')} | "
            f"Similarity="
            f"{item.get('similarity_score', 0):.4f} | "
            f"Keyword="
            f"{item.get('keyword_score', 0):.4f} | "
            f"Section="
            f"{item.get('section_score', 0):.4f} | "
            f"Rerank="
            f"{item.get('rerank_score', 0):.4f}"
        )

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

    print("\nMatched standards:")
    print(result["matched_standard_count"])

    print("\nSufficiency reason:")
    print(result["sufficiency_reason"])

    print("\nCitations:")
    print("-" * 70)

    for citation in result["citations"]:

        print(
            f"{citation.get('standard_id')} | "
            f"{citation.get('document_title')} | "
            f"Source: "
            f"{citation.get('source_url')}"
        )

    # ========================================================
    # TEST 3 — General P1 question
    # ========================================================

    print("\n" + "=" * 70)
    print(
        "TEST 3 — General P1 question"
    )
    print("=" * 70)

    query = (
        "What documents are required "
        "for certification?"
    )

    result = pipeline.run(
        query=query,
        standard_ids=None,
    )

    print("\nQuery:")
    print(query)

    print("\nP1 retrieved evidence:")
    print(result["retrieved_count"])

    print("\nP4 structured evidence:")
    print(result["p4_evidence_count"])

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

    # ========================================================
    # TEST 4 — Unknown / unrelated question
    # ========================================================

    print("\n" + "=" * 70)
    print(
        "TEST 4 — Unknown / unrelated question"
    )
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

    print("\nCitations:")

    if result["citations"]:

        for citation in result["citations"]:
            print(citation)

    else:

        print("No citations generated.")

    # ========================================================
    # Completion
    # ========================================================

    print("\n" + "=" * 70)
    print(
        "P1 + P4 end-to-end pipeline test completed."
    )
    print("=" * 70)