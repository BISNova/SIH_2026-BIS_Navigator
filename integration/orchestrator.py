"""
The complete request lifecycle, matching the orchestration logic the
master plan always specified: run Product Intelligence first; if it's
not confident, short-circuit with a clarification/not-found response
and never call the (expensive) RAG engine; only call RAG once a product
is confidently matched.

evidence_pipeline is passed in (dependency injection) rather than
constructed here, so:
  - production code does: EvidencePipeline() (her real class, needs
    real internet access for the embedding model)
  - sandbox tests do: EvidencePipeline() constructed under the mock
    SentenceTransformer patch (see tests/test_full_integration.py)

Nothing in this file needs to know or care which one it got.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_EVIDENCE_ENGINE_RAG = _PROJECT_ROOT / "evidence_engine" / "rag"
for p in (_PROJECT_ROOT, _EVIDENCE_ENGINE_RAG):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from schemas.p1_output import P1Output  # noqa: E402
from schemas.evidence import EvidenceRecord  # noqa: E402

from product_intelligence.src.pipeline import ProductIntelligencePipeline  # noqa: E402
from .adapter import adapt_to_p1_input  # noqa: E402

EVIDENCE_RECORD_FIELDS = [
    "chunk_id", "standard_id", "document_id", "document_title",
    "document_type", "section", "section_header", "page_number",
    "text", "source_url", "version", "authority_level",
]


def _confidence_label(score: float) -> str:
    """Matches her own test_contracts.py bucketing exactly - this is
    evidence/answer confidence, a DIFFERENT number from Product
    Intelligence's product-match confidence_label."""
    if score >= 0.70:
        return "high"
    if score >= 0.50:
        return "medium"
    return "low"


def run_full_pipeline(query: str, product_pipeline: ProductIntelligencePipeline, evidence_pipeline) -> P1Output:
    p2_result = product_pipeline.process(query)
    p1_input = adapt_to_p1_input(p2_result)

    if p1_input.needs_clarification:
        return P1Output(
            answer="",
            evidence=[],
            sources=[],
            confidence_score=p1_input.confidence_score,
            confidence_label=p1_input.confidence_label,
            evidence_sufficient=False,
            clarification_needed=True,
            clarification_question=p1_input.clarification_question,
        )

    if p1_input.status == "not_found":
        return P1Output(
            answer="We don't have this product in our curated knowledge base yet.",
            evidence=[],
            sources=[],
            confidence_score=0.0,
            confidence_label="low",
            evidence_sufficient=False,
            clarification_needed=False,
        )

    # status == "matched" - safe to call the (real) RAG engine now
    standard_ids = p1_input.get_standard_ids()
    raw = evidence_pipeline.run(
        query=p1_input.normalized_query or p1_input.query,
        standard_ids=standard_ids,
    )

    evidence_records = [
        EvidenceRecord(**{field: ev[field] for field in EVIDENCE_RECORD_FIELDS})
        for ev in raw["evidence"]
    ]

    # dedup while preserving order
    sources = list(dict.fromkeys(
        r.source_url for r in evidence_records if r.source_url
    ))

    return P1Output(
        answer=raw["answer"],
        evidence=evidence_records,
        sources=sources,
        confidence_score=raw["confidence_score"],
        confidence_label=_confidence_label(raw["confidence_score"]),
        evidence_sufficient=raw["evidence_sufficient"],
        clarification_needed=False,
    )
