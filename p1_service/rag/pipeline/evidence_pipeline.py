
from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from fastembed import TextEmbedding
# 
# from sentence_transformers import SentenceTransformer


# ============================================================
# Project path setup
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAG_DIR = PROJECT_ROOT / "rag"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))


# ============================================================
# Existing P1 components
#
# FIX (found during P2/frontend integration testing): these were
# previously bare imports ("from retrieval.retriever import ..."),
# which relied on RAG_DIR being separately added to sys.path. That
# meant this file's modules (e.g. answer.gemini_generator) and the
# REST of the codebase's modules (e.g. rag.answer.gemini_generator,
# used in rag/service/p1_service.py and rag/knowledge/*.py) were two
# DIFFERENT module objects in sys.modules, despite being the same
# file. Patching/mocking one (e.g. in a test) silently didn't affect
# the other, which is a real and confusing latent bug for anyone
# writing tests against this pipeline. Normalized to the same
# "rag."-prefixed absolute imports used everywhere else in this
# codebase so there's only ever one module identity.
# ============================================================

from rag.retrieval.retriever import EvidenceRetriever
from rag.retrieval.reranker import EvidenceReranker
from rag.evidence.selector import EvidenceSelector
from rag.evidence.sufficiency import EvidenceSufficiencyChecker
from rag.answer.gemini_generator import GeminiAnswerGenerator
from rag.citations.builder import CitationBuilder
from rag.confidence.scorer import ConfidenceScorer


# ============================================================
# P4 components
# ============================================================

from rag.knowledge.adapter import P4KnowledgeAdapter
from rag.knowledge.evidence_builder import P4EvidenceBuilder


class EvidencePipeline:
    """
    P1 End-to-End Evidence Pipeline with P4 Knowledge Integration
    and Gemini-based grounded answer generation.

    Flow:

        Query
          ↓
        Query Embedding
          ↓
        ┌─────────────────────────────┐
        │                             │
        ▼                             ▼
    P1 Chroma                  P4 Structured Knowledge
    P1 Retrieval               P4 Evidence Builder
        │                             │
        └──────────────┬──────────────┘
                       ▼
                Merged Evidence
                       ↓
                    Reranking
                       ↓
          Query-aware Evidence Selection
                       ↓
                Evidence Sufficiency
                       ↓
                Confidence Scoring
                       ↓
              Gemini Answer Generation
                       ↓
                Citation Building
                       ↓
              Final Evidence Package

    Important architecture rule:

    Gemini does NOT perform retrieval.

    Gemini receives only evidence that has already passed:
        1. P1/P4 retrieval
        2. reranking
        3. evidence selection
        4. evidence sufficiency checks

    Therefore:

        Retrieval   = finding evidence
        Reranking   = prioritizing evidence
        Selection   = choosing evidence for the answer
        Sufficiency = deciding whether evidence is reliable enough
        Gemini      = explaining the selected evidence

    P4 integration is activated when standard_ids
    are supplied.

    For multi-standard queries, selection is coverage-aware.

    For completeness/list-style questions, the pipeline uses
    query-aware evidence selection.

    For test-completeness queries, authoritative P4 TEST
    records are preserved in full. Reranking determines their
    order, but the normal semantic-score threshold is not used
    to discard an authoritative P4 test record.
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

        # self.model = SentenceTransformer(model_name)
        self.model = TextEmbedding(model_name=f"sentence-transformers/{model_name}")

        print("Embedding model loaded.")

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

        self.answer_generator = GeminiAnswerGenerator(
            minimum_evidence_score=0.30
        )

        self.citation_builder = CitationBuilder()

        self.retrieval_top_k = retrieval_top_k
        self.rerank_top_k = rerank_top_k

        self.p4_adapter = P4KnowledgeAdapter()

        self.p4_evidence_builder = P4EvidenceBuilder(
            self.p4_adapter
        )

    # ========================================================
    # Query embedding
    # ========================================================

    def _embed_query(self, query: str) -> list[float]:
        # embedding = self.model.encode(
        #     query,
        #     normalize_embeddings=True,
        # )
        embedding = next(self.model.embed([query]))
        return embedding.tolist()
        
    # ========================================================
    # Similarity
    # ========================================================

    def _calculate_similarity(
        self,
        query_embedding: list[float],
        text: str,
    ) -> float:
        if not text or not text.strip():
            return 0.0

        # evidence_embedding = self.model.encode(
        #     text,
        #     normalize_embeddings=True,
        # )
        evidence_embedding = next(self.model.embed([text]))

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
    # General completeness detection
    # ========================================================

    def _is_completeness_query(
        self,
        query: str,
    ) -> bool:
        if not query:
            return False

        normalized_query = " ".join(
            query.lower().strip().split()
        )

        completeness_terms = (
            "what tests are required",
            "what tests are needed",
            "which tests are required",
            "which tests are needed",
            "list all tests",
            "list the tests",
            "all required tests",
            "all tests",
            "required tests",
            "tests required",
            "what requirements are required",
            "what are the requirements",
            "which requirements are required",
            "list all requirements",
            "list the requirements",
            "all requirements",
            "required requirements",
            "what documents are required",
            "which documents are required",
            "list all documents",
            "list the documents",
            "all required documents",
            "what certification steps",
            "what are the certification steps",
            "list all certification steps",
            "all certification steps",
        )

        return any(
            phrase in normalized_query
            for phrase in completeness_terms
        )

    # ========================================================
    # Test completeness detection
    # ========================================================

    def _is_test_completeness_query(
        self,
        query: str,
    ) -> bool:
        if not query:
            return False

        normalized_query = " ".join(
            query.lower().strip().split()
        )

        test_terms = (
            "test",
            "tests",
            "testing",
        )

        contains_test_term = any(
            term in normalized_query
            for term in test_terms
        )

        if not contains_test_term:
            return False

        completeness_test_terms = (
            "what tests are required",
            "what tests are needed",
            "which tests are required",
            "which tests are needed",
            "list all tests",
            "list the tests",
            "all required tests",
            "all tests",
            "required tests",
            "tests required",
            "required testing",
            "tests needed",
            "what testing is required",
            "what testing is needed",
            "which testing is required",
            "which testing is needed",
        )

        return any(
            phrase in normalized_query
            for phrase in completeness_test_terms
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

            if hasattr(record, "model_dump"):
                item = record.model_dump()

            elif hasattr(record, "dict"):
                item = record.dict()

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
    # Identify P4 test evidence
    # ========================================================

    @staticmethod
    def _is_p4_test_evidence(
        candidate: dict[str, Any],
    ) -> bool:

        if not isinstance(candidate, dict):
            return False

        chunk_id = str(
            candidate.get("chunk_id", "")
        ).strip().upper()

        return chunk_id.startswith("P4-TEST-")

    # ========================================================
    # Evidence selection with standard coverage
    # ========================================================

    def _select_with_standard_coverage(
        self,
        candidates: list[dict[str, Any]],
        standard_ids: list[str] | None,
        max_evidence: int | None = None,
        test_completeness_query: bool = False,
    ) -> list[dict[str, Any]]:

        if not candidates:
            return []

        evidence_limit = (
            max_evidence
            if max_evidence is not None
            else self.rerank_top_k
        )

        # ----------------------------------------------------
        # No standard filtering required
        # ----------------------------------------------------

        if not standard_ids:

            if evidence_limit == self.rerank_top_k:
                return self.selector.select(
                    candidates=candidates
                )

            selected = []

            for candidate in candidates:

                score = float(
                    candidate.get(
                        "rerank_score",
                        0.0,
                    )
                )

                if score < self.selector.minimum_score:
                    continue

                selected.append(candidate)

                if len(selected) >= evidence_limit:
                    break

            return selected

        # ----------------------------------------------------
        # Expected standards
        # ----------------------------------------------------

        expected_standards = list(
            dict.fromkeys(standard_ids)
        )

        # ----------------------------------------------------
        # SPECIAL CASE:
        # Test-completeness query
        #
        # For authoritative P4 TEST records:
        #
        #   reranking = ordering
        #   P4 completeness = preservation
        #
        # We intentionally DO NOT discard a P4 test simply
        # because its rerank score is below 0.30.
        # ----------------------------------------------------

        if test_completeness_query:

            p4_test_candidates = [
                candidate
                for candidate in candidates
                if self._is_p4_test_evidence(candidate)
            ]

            if p4_test_candidates:

                # Preserve every authoritative P4 test record.
                #
                # They have already been selected from the
                # standard-specific P4 knowledge base.
                #
                # Their rerank score is still useful for ordering,
                # but not for deleting an authoritative requirement.

                selected = list(
                    p4_test_candidates
                )

                selected.sort(
                    key=lambda item: (
                        float(
                            item.get(
                                "rerank_score",
                                item.get(
                                    "similarity_score",
                                    0.0,
                                ),
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

                # Make sure every requested standard that has
                # P4 test records remains represented.
                #
                # Since all P4 test records are preserved, this
                # naturally maintains standard coverage.

                return selected

        # ----------------------------------------------------
        # Normal score-based filtering
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

        # ----------------------------------------------------
        # Standard coverage
        # ----------------------------------------------------

        selected: list[dict[str, Any]] = []

        selected_chunk_ids: set[str] = set()

        for standard_id in expected_standards:

            best_candidate = None

            for candidate in valid_candidates:

                chunk_id = candidate.get(
                    "chunk_id"
                )

                if chunk_id in selected_chunk_ids:
                    continue

                if candidate.get(
                    "standard_id"
                ) != standard_id:
                    continue

                best_candidate = candidate

                break

            if best_candidate is None:
                continue

            selected.append(best_candidate)

            selected_chunk_ids.add(
                best_candidate.get("chunk_id")
            )

            if len(selected) >= evidence_limit:
                break

        # ----------------------------------------------------
        # Fill remaining evidence slots
        # ----------------------------------------------------

        if len(selected) < evidence_limit:

            for candidate in valid_candidates:

                chunk_id = candidate.get(
                    "chunk_id"
                )

                if chunk_id in selected_chunk_ids:
                    continue

                selected.append(candidate)

                selected_chunk_ids.add(chunk_id)

                if len(selected) >= evidence_limit:
                    break

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
        language: str = "en",
    ) -> dict:

        if not query or not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        # ----------------------------------------------------
        # Query embedding
        # ----------------------------------------------------

        query_embedding = self._embed_query(query)

        # ----------------------------------------------------
        # P1 retrieval
        # ----------------------------------------------------

        retrieved_candidates = self.retriever.retrieve(
            query_embedding=query_embedding,
            top_k=self.retrieval_top_k,
            standard_ids=standard_ids,
        )

        # ----------------------------------------------------
        # P4 retrieval
        # ----------------------------------------------------

        p4_candidates: list[dict[str, Any]] = []

        if standard_ids:

            p4_candidates = self._prepare_p4_evidence(
                query=query,
                query_embedding=query_embedding,
                standard_ids=standard_ids,
            )

        # ----------------------------------------------------
        # Merge P1 + P4
        # ----------------------------------------------------

        combined_candidates = self._merge_evidence(
            p1_evidence=retrieved_candidates,
            p4_evidence=p4_candidates,
        )

        # ----------------------------------------------------
        # Query classification
        # ----------------------------------------------------

        completeness_query = (
            self._is_completeness_query(query)
        )

        test_completeness_query = (
            self._is_test_completeness_query(query)
        )

        # ----------------------------------------------------
        # Evidence budget
        # ----------------------------------------------------

        if test_completeness_query and standard_ids:

            test_p4_count = sum(
                1
                for item in p4_candidates
                if self._is_p4_test_evidence(item)
            )

            evidence_budget = max(
                self.rerank_top_k,
                test_p4_count,
            )

        elif completeness_query and standard_ids:

            evidence_budget = max(
                self.rerank_top_k,
                len(p4_candidates),
            )

        else:

            evidence_budget = self.rerank_top_k

        # ----------------------------------------------------
        # Reranking candidates
        # ----------------------------------------------------

        if test_completeness_query and standard_ids:

            p4_test_candidates = [
                item
                for item in p4_candidates
                if self._is_p4_test_evidence(item)
            ]

            if p4_test_candidates:

                test_chunk_ids = {
                    item.get("chunk_id")
                    for item in p4_test_candidates
                }

                p4_chunk_ids = {
                    item.get("chunk_id")
                    for item in p4_candidates
                }

                reranking_candidates = [
                    item
                    for item in combined_candidates
                    if (
                        item.get("chunk_id")
                        not in p4_chunk_ids
                        or item.get("chunk_id")
                        in test_chunk_ids
                    )
                ]

            else:

                reranking_candidates = (
                    combined_candidates
                )

            coverage_rerank_top_k = max(
                evidence_budget,
                len(reranking_candidates),
            )

        elif completeness_query and standard_ids:

            coverage_rerank_top_k = max(
                evidence_budget,
                len(combined_candidates),
            )

            reranking_candidates = (
                combined_candidates
            )

        elif standard_ids and len(standard_ids) > 1:

            coverage_rerank_top_k = max(
                self.rerank_top_k,
                len(standard_ids) * 5,
            )

            reranking_candidates = (
                combined_candidates
            )

        else:

            coverage_rerank_top_k = (
                self.rerank_top_k
            )

            reranking_candidates = (
                combined_candidates
            )

        # ----------------------------------------------------
        # Reranking
        # ----------------------------------------------------

        reranked_candidates = self.reranker.rerank(
            query=query,
            candidates=reranking_candidates,
            top_k=coverage_rerank_top_k,
            standard_ids=standard_ids,
        )

        # ----------------------------------------------------
        # Evidence selection
        # ----------------------------------------------------

        selected_evidence = (
            self._select_with_standard_coverage(
                candidates=reranked_candidates,
                standard_ids=standard_ids,
                max_evidence=evidence_budget,
                test_completeness_query=(
                    test_completeness_query
                ),
            )
        )

        # ----------------------------------------------------
        # Evidence sufficiency
        # ----------------------------------------------------

        sufficiency = (
            self.sufficiency_checker.check(
                evidence=selected_evidence,
                standard_ids=standard_ids,
            )
        )

        evidence_sufficient = (
            sufficiency[
                "evidence_sufficient"
            ]
        )

        # ----------------------------------------------------
        # Confidence
        # ----------------------------------------------------

        confidence = (
            self.confidence_scorer.score(
                evidence=selected_evidence,
                evidence_sufficient=(
                    evidence_sufficient
                ),
                sufficiency_confidence=(
                    sufficiency[
                        "confidence_score"
                    ]
                ),
            )
        )

        # ----------------------------------------------------
        # Gemini answer generation
        # ----------------------------------------------------

        if not evidence_sufficient and not standard_ids:
            answer_result = self.answer_generator.generate_general_fallback(
                query=query,
                language=language,
            )
        else:
            answer_result = self.answer_generator.generate(
                query=query,
                evidence=selected_evidence,
                evidence_sufficient=evidence_sufficient,
                language=language,
            )

        # ----------------------------------------------------
        # Citations
        # ----------------------------------------------------

        citations = (
            self.citation_builder.build(
                selected_evidence
            )
        )

        # ----------------------------------------------------
        # Final response
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

            "p4_test_evidence_count": sum(
                1
                for item in p4_candidates
                if self._is_p4_test_evidence(item)
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

            "answer": answer_result[
                "answer"
            ],

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

            "language": language,

            "completeness_query": (
                completeness_query
            ),

            "test_completeness_query": (
                test_completeness_query
            ),

            "evidence_budget": (
                evidence_budget
            ),
        }


# ============================================================
# Standalone testing
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print(
        "P1 + P4 + Gemini — End-to-End Evidence Pipeline"
    )
    print("=" * 70)

    pipeline = EvidencePipeline()

    # ========================================================
    # TEST 1
    # ========================================================

    print("\n" + "=" * 70)
    print(
        "TEST 1 — P4 + Gemini: Domestic Pressure Cooker"
    )
    print("=" * 70)

    query = (
        "What tests are required for a "
        "domestic pressure cooker?"
    )

    result = pipeline.run(
        query=query,
        standard_ids=["STD-001"],
        language="en",
    )

    print("\nQuery:")
    print(query)

    print("\nLanguage:")
    print(result["language"])

    print("\nCompleteness query:")
    print(result["completeness_query"])

    print("\nTest completeness query:")
    print(result["test_completeness_query"])

    print("\nEvidence budget:")
    print(result["evidence_budget"])

    print("\nP1 retrieved evidence:")
    print(result["retrieved_count"])

    print("\nP4 structured evidence:")
    print(result["p4_evidence_count"])

    print("\nP4 test evidence:")
    print(result["p4_test_evidence_count"])

    print("\nCombined candidates:")
    print(result["combined_evidence_count"])

    print("\nReranked candidates:")
    print(result["reranked_count"])

    print("\nSelected evidence:")
    print(result["selected_count"])

    print("\nSelected evidence IDs:")

    for item in result["evidence"]:

        print(
            f"{item.get('chunk_id')} | "
            f"{item.get('document_title')}"
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

    print("\nEvidence used:")
    print("-" * 70)

    for item in result["evidence_used"]:

        print(
            f"{item.get('chunk_id')} | "
            f"Standard "
            f"{item.get('standard_id')} | "
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
    # TEST 2
    # ========================================================

    print("\n" + "=" * 70)
    print(
        "TEST 2 — P4 + Gemini: "
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
        language="en",
    )

    print("\nQuery:")
    print(query)

    print("\nLanguage:")
    print(result["language"])

    print("\nCompleteness query:")
    print(result["completeness_query"])

    print("\nTest completeness query:")
    print(result["test_completeness_query"])

    print("\nEvidence budget:")
    print(result["evidence_budget"])

    print("\nP1 retrieved evidence:")
    print(result["retrieved_count"])

    print("\nP4 structured evidence:")
    print(result["p4_evidence_count"])

    print("\nP4 test evidence:")
    print(result["p4_test_evidence_count"])

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
            f"Standard="
            f"{item.get('standard_id')} | "
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
    # TEST 3
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
        language="en",
    )

    print("\nQuery:")
    print(query)

    print("\nLanguage:")
    print(result["language"])

    print("\nCompleteness query:")
    print(result["completeness_query"])

    print("\nTest completeness query:")
    print(result["test_completeness_query"])

    print("\nEvidence budget:")
    print(result["evidence_budget"])

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
    # TEST 4
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
        language="en",
    )

    print("\nQuery:")
    print(query)

    print("\nLanguage:")
    print(result["language"])

    print("\nCompleteness query:")
    print(result["completeness_query"])

    print("\nTest completeness query:")
    print(result["test_completeness_query"])

    print("\nEvidence budget:")
    print(result["evidence_budget"])

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

    print("\n" + "=" * 70)
    print(
        "P1 + P4 + Gemini end-to-end pipeline test completed."
    )
    print("=" * 70)
