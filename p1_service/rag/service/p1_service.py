from rag.schemas.p1_input import P1Input
from rag.schemas.p1_output import P1Output
from rag.schemas.evidence import EvidenceRecord

from rag.pipeline.evidence_pipeline import EvidencePipeline


class P1Service:
    """
    Service layer for P1.

    Responsibilities:
    - Accept P1Input from P2
    - Handle clarification requests
    - Handle unmatched/not-found requests
    - Run the existing P1 RAG pipeline
    - Convert the pipeline result into P1Output
    """

    def __init__(self):
        self.pipeline = EvidencePipeline()

    def run(self, p1_input: P1Input) -> P1Output:
        """
        Process a P1Input and return a P1Output.
        """

        # --------------------------------------------------
        # 1. Handle clarification
        # --------------------------------------------------

        if p1_input.needs_clarification:
            return P1Output(
                answer=(
                    "I need some clarification before "
                    "I can answer this question."
                ),
                evidence=[],
                sources=[],
                confidence_score=p1_input.confidence_score,
                confidence_label=p1_input.confidence_label,
                evidence_sufficient=False,
                clarification_needed=True,
                clarification_question=(
                    p1_input.clarification_question
                ),
            )

        # --------------------------------------------------
        # 2. Handle P2 not-found status
        # --------------------------------------------------

        # if p1_input.status == "not_found":
        #     return P1Output(
        #         answer=(
        #             "I could not identify an applicable "
        #             "BIS standard for this query."
        #         ),
        #         evidence=[],
        #         sources=[],
        #         confidence_score=0.0,
        #         confidence_label="low",
        #         evidence_sufficient=False,
        #         clarification_needed=False,
        #         clarification_question=None,
        #     )

        # --------------------------------------------------
        # 3. Determine the query used for retrieval
        # --------------------------------------------------

        query = (
            p1_input.normalized_query
            or p1_input.query
        )

        if not query or not query.strip():
            raise ValueError(
                "P1 query cannot be empty."
            )

        # --------------------------------------------------
        # 3b. Every distinct English translation P2's translators
        #     produced for this query (Google Translate's and
        #     MyMemory's phrasings of the same source text often
        #     differ). Passed through so EvidencePipeline can search
        #     with all of them and keep whichever finds the best
        #     evidence - see EvidencePipeline.run().
        # --------------------------------------------------

        query_variants = list(
            getattr(p1_input, "normalized_query_variants", []) or []
        )

        # --------------------------------------------------
        # 4. Get applicable standard IDs
        # --------------------------------------------------

        standard_ids = p1_input.get_standard_ids()

        # If no standards are supplied, allow the
        # existing pipeline to perform general retrieval.
        if not standard_ids:
            standard_ids = None

        # --------------------------------------------------
        # 5. Run the complete P1 RAG pipeline
        # --------------------------------------------------

        result = self.pipeline.run(
            query=query,
            standard_ids=standard_ids,
            language=p1_input.language,
            query_variants=query_variants,
        )

        # --------------------------------------------------
        # 6. Convert selected evidence into EvidenceRecord
        # --------------------------------------------------

        evidence = []

        for item in result.get("evidence", []):
            evidence.append(
                EvidenceRecord(
                    chunk_id=item["chunk_id"],
                    standard_id=item["standard_id"],
                    document_id=item["document_id"],
                    document_title=item["document_title"],
                    document_type=item.get(
                        "document_type"
                    ),
                    section=item.get("section"),
                    section_header=item.get(
                        "section_header"
                    ),
                    page_number=item.get(
                        "page_number"
                    ),
                    text=item["text"],
                    source_url=item.get(
                        "source_url"
                    ),
                    version=item.get("version"),
                    authority_level=item.get(
                        "authority_level"
                    ),
                )
            )

        # --------------------------------------------------
        # 7. Extract source URLs
        # --------------------------------------------------

        sources = []

        for citation in result.get("citations", []):
            source_url = citation.get("source_url")

            if source_url and source_url not in sources:
                sources.append(source_url)

        # --------------------------------------------------
        # 8. Return final P1Output
        # --------------------------------------------------

        return P1Output(
            answer=result.get(
                "answer",
                "I don't have enough reliable evidence "
                "to answer this question.",
            ),
            evidence=evidence,
            sources=sources,
            confidence_score=result.get(
                "confidence_score",
                0.0,
            ),
            confidence_label=result.get(
                "confidence_label",
                "low",
            ),
            evidence_sufficient=result.get(
                "evidence_sufficient",
                False,
            ),
            clarification_needed=False,
            clarification_question=None,
        )