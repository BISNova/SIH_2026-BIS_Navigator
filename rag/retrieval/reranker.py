from __future__ import annotations

import re


class EvidenceReranker:
    """
    P1 Evidence Reranker V2.

    Reranks candidates returned by semantic retrieval.

    Signals used:

    1. Semantic similarity
    2. Keyword relevance
    3. Section/header relevance

    Authority is intentionally NOT part of the score yet because
    the current synthetic dataset gives all documents the same
    authority level.

    Standard filtering is handled by the retriever when P2 provides
    applicable standard IDs.
    """

    def __init__(
        self,
        semantic_weight: float = 0.70,
        keyword_weight: float = 0.10,
        section_weight: float = 0.20,
    ):
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
        self.section_weight = section_weight

        total_weight = (
            semantic_weight
            + keyword_weight
            + section_weight
        )

        if abs(total_weight - 1.0) > 1e-6:
            raise ValueError(
                "Reranker weights must sum to 1.0. "
                f"Got {total_weight:.4f}"
            )

    # =========================================================
    # Text normalization
    # =========================================================

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison.
        """

        if not text:
            return ""

        text = text.lower()

        text = re.sub(
            r"[^a-z0-9\s]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    # =========================================================
    # Tokenization
    # =========================================================

    def _tokenize(self, text: str) -> list[str]:
        """
        Convert text into normalized tokens.
        """

        normalized = self._normalize_text(text)

        if not normalized:
            return []

        return normalized.split()

    # =========================================================
    # Stop words
    # =========================================================

    def _remove_stopwords(
        self,
        tokens: list[str]
    ) -> list[str]:
        """
        Remove common question words that do not carry much
        relevance information.
        """

        stopwords = {
            "what",
            "are",
            "is",
            "the",
            "a",
            "an",
            "for",
            "of",
            "to",
            "in",
            "on",
            "and",
            "or",
            "how",
            "which",
            "does",
            "do",
            "required",
            "requirements",
        }

        return [
            token
            for token in tokens
            if token not in stopwords
        ]

    # =========================================================
    # Simple word normalization
    # =========================================================

    def _normalize_word(
        self,
        word: str
    ) -> str:
        """
        Lightweight normalization for common singular/plural
        forms.

        This is deliberately simple. We do not want to introduce
        another NLP dependency just for reranking.
        """

        if len(word) > 4 and word.endswith("ies"):
            return word[:-3] + "y"

        if len(word) > 4 and word.endswith("es"):
            return word[:-2]

        if len(word) > 3 and word.endswith("s"):
            return word[:-1]

        return word

    # =========================================================
    # Keyword relevance
    # =========================================================

    def _keyword_overlap(
        self,
        query: str,
        candidate_text: str
    ) -> float:
        """
        Calculate query-term coverage in the candidate.

        Returns a value between 0 and 1.
        """

        query_tokens = self._remove_stopwords(
            self._tokenize(query)
        )

        candidate_tokens = {
            self._normalize_word(token)
            for token in self._tokenize(candidate_text)
        }

        if not query_tokens:
            return 0.0

        normalized_query_tokens = {
            self._normalize_word(token)
            for token in query_tokens
        }

        overlap = (
            normalized_query_tokens
            .intersection(candidate_tokens)
        )

        return (
            len(overlap)
            / len(normalized_query_tokens)
        )

    # =========================================================
    # Phrase relevance
    # =========================================================

    def _phrase_match(
        self,
        query: str,
        section_header: str | None
    ) -> float:
        """
        Detect whether the important words in the query appear
        together in the section heading.

        Example:

        Query:
            "What are the inspection requirements?"

        Header:
            "Clause 7 · Inspection Requirements"

        This should receive a strong score.
        """

        if not section_header:
            return 0.0

        query_tokens = self._remove_stopwords(
            self._tokenize(query)
        )

        if not query_tokens:
            return 0.0

        header = self._normalize_text(
            section_header
        )

        normalized_query = [
            self._normalize_word(token)
            for token in query_tokens
        ]

        # Exact phrase after normalization
        query_phrase = " ".join(
            normalized_query
        )

        normalized_header_tokens = [
            self._normalize_word(token)
            for token in self._tokenize(header)
        ]

        normalized_header = " ".join(
            normalized_header_tokens
        )

        if query_phrase in normalized_header:
            return 1.0

        # Otherwise calculate partial coverage.
        header_tokens = set(
            normalized_header_tokens
        )

        overlap = (
            set(normalized_query)
            .intersection(header_tokens)
        )

        return (
            len(overlap)
            / len(set(normalized_query))
        )

    # =========================================================
    # Section relevance
    # =========================================================

    def _section_relevance(
        self,
        query: str,
        section_header: str | None
    ) -> float:
        """
        Combine keyword overlap and phrase matching in the
        section header.
        """

        if not section_header:
            return 0.0

        keyword_score = self._keyword_overlap(
            query,
            section_header
        )

        phrase_score = self._phrase_match(
            query,
            section_header
        )

        # Phrase match is stronger than individual word overlap.
        return (
            0.30 * keyword_score
            + 0.70 * phrase_score
        )

    # =========================================================
    # Final score
    # =========================================================

    def _calculate_score(
        self,
        query: str,
        candidate: dict
    ) -> dict:
        """
        Calculate the final reranking score.
        """

        semantic_score = float(
            candidate.get(
                "similarity_score",
                0.0
            )
        )

        keyword_score = self._keyword_overlap(
            query,
            candidate.get("text", "")
        )

        section_score = self._section_relevance(
            query,
            candidate.get("section_header")
        )

        rerank_score = (
            self.semantic_weight
            * semantic_score
            +
            self.keyword_weight
            * keyword_score
            +
            self.section_weight
            * section_score
        )

        result = dict(candidate)

        result["keyword_score"] = keyword_score
        result["section_score"] = section_score
        result["rerank_score"] = rerank_score

        return result

    # =========================================================
    # Main reranking function
    # =========================================================

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = 5,
        standard_ids: list[str] | None = None,
    ) -> list[dict]:
        """
        Rerank retrieved evidence candidates.

        Parameters
        ----------
        query:
            Original user query.

        candidates:
            Candidates returned by EvidenceRetriever.

        top_k:
            Number of candidates to return after reranking.

        standard_ids:
            Standards identified by P2.

        Returns
        -------
        list[dict]
            Reranked candidates.
        """

        if not candidates:
            return []

        scored_candidates = []

        for candidate in candidates:

            result = self._calculate_score(
                query=query,
                candidate=candidate
            )

            # Keep standard-match information for later
            # integration with P2/P4.
            if standard_ids:

                result["standard_match"] = (
                    result.get("standard_id")
                    in standard_ids
                )

            else:

                result["standard_match"] = None

            scored_candidates.append(result)

        # -----------------------------------------------------
        # Sort by final reranking score
        # -----------------------------------------------------

        scored_candidates.sort(
            key=lambda item: (
                item["rerank_score"],
                item.get("similarity_score", 0.0),
            ),
            reverse=True
        )

        return scored_candidates[:top_k]


# =============================================================
# Standalone test
# =============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("P1 — Evidence Reranker V2")
    print("=" * 60)

    query = "What are the inspection requirements?"

    candidates = [
        {
            "chunk_id": "chunk_1",
            "text": (
                "7.1 Inspection requirements shall be "
                "verified by the manufacturer."
            ),
            "similarity_score": 0.64,
            "standard_id": "SYN-STD-101",
            "document_id": "SYN-BIS-STD-A",
            "section": "7.1",
            "section_header": (
                "Clause 7 · Inspection Requirements"
            ),
            "document_title": "Synthetic Standard A",
            "document_type": "standard",
            "version": "1.0",
            "authority_level": 1,
            "source_url": "https://example.com",
            "page_number": 2,
        },
        {
            "chunk_id": "chunk_2",
            "text": (
                "6.1 Testing shall be performed according "
                "to the specified procedure."
            ),
            "similarity_score": 0.63,
            "standard_id": "SYN-STD-101",
            "document_id": "SYN-BIS-STD-A",
            "section": "6.1",
            "section_header": (
                "Clause 6 · Testing Requirements"
            ),
            "document_title": "Synthetic Standard A",
            "document_type": "standard",
            "version": "1.0",
            "authority_level": 1,
            "source_url": "https://example.com",
            "page_number": 2,
        },
        {
            "chunk_id": "chunk_3",
            "text": (
                "5.1 Materials used in manufacturing shall "
                "meet the specified requirements."
            ),
            "similarity_score": 0.57,
            "standard_id": "SYN-STD-101",
            "document_id": "SYN-BIS-STD-A",
            "section": "5.1",
            "section_header": "Clause 5 · Materials",
            "document_title": "Synthetic Standard A",
            "document_type": "standard",
            "version": "1.0",
            "authority_level": 1,
            "source_url": "https://example.com",
            "page_number": 1,
        },
    ]

    reranker = EvidenceReranker()

    results = reranker.rerank(
        query=query,
        candidates=candidates,
        top_k=3,
    )

    print("\nQuery:")
    print(query)

    print("\nReranked Results:")
    print("-" * 60)

    for rank, result in enumerate(
        results,
        start=1
    ):

        print(f"\nRank {rank}")

        print(
            f"Chunk:          "
            f"{result['chunk_id']}"
        )

        print(
            f"Section:        "
            f"{result['section']}"
        )

        print(
            f"Semantic:       "
            f"{result['similarity_score']:.4f}"
        )

        print(
            f"Keyword:        "
            f"{result['keyword_score']:.4f}"
        )

        print(
            f"Section score:  "
            f"{result['section_score']:.4f}"
        )

        print(
            f"Final score:    "
            f"{result['rerank_score']:.4f}"
        )

        print(
            f"Evidence:       "
            f"{result['text']}"
        )

    print("\n" + "=" * 60)
    print("Reranker V2 test completed.")
    print("=" * 60)