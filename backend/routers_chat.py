"""
POST /api/chat - the one endpoint the frontend's chat UI needs.

Converts the rich internal result (ProductMatchResult + P1Output) into
the external ChatResponse contract (backend/models.py). This is where
"our internal shape" and "what the frontend gets" are deliberately kept
separate - internals can keep evolving without breaking the API.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Depends

from .models import (
    ChatRequest,
    ChatResponse,
    StandardOut,
    ClarificationOptionOut,
    EvidenceOut,
)
from .dependencies import get_product_pipeline
from .config import P1_API_BASE_URL
from integration.orchestrator import run_full_pipeline_with_context  # noqa: E402

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    product_pipeline = get_product_pipeline()

    result = run_full_pipeline_with_context(request.query, product_pipeline, p1_base_url=P1_API_BASE_URL)
    p2_result = result["p2_result"]
    p1_output = result["p1_output"]

    standards = [
        StandardOut(
            standard_id=s.standard_id,
            is_number=s.is_number,
            title=s.title,
            status=s.status,
            relationship_type=s.relationship_type,
            is_mandatory=s.is_mandatory,
            source_url=s.source_url,
            confidence=s.confidence,
        )
        for s in p2_result.applicable_standards
    ]

    # Clarification options come back as ready-to-send follow-up queries -
    # the frontend can wire these straight into its existing action-chip
    # click handler with no new UI component needed (see chip.query pattern
    # already used for other suggested follow-ups in the frontend).
    clarification_options = [
        ClarificationOptionOut(
            label=opt.label,
            query=f"{request.query} {opt.label}",
        )
        for opt in p2_result.clarification_options
    ]

    evidence = [
        EvidenceOut(
            chunk_id=e.chunk_id,
            standard_id=e.standard_id,
            text=e.text,
            section_header=e.section_header,
            source_url=e.source_url,
        )
        for e in p1_output.evidence
    ]

    return ChatResponse(
        status=p2_result.status,
        answer=p1_output.answer,
        matched_product_name=p2_result.matched_product.canonical_name if p2_result.matched_product else None,
        standards=standards,
        confidence_score=p1_output.confidence_score,
        confidence_label=p1_output.confidence_label,
        evidence_sufficient=p1_output.evidence_sufficient,
        evidence=evidence,
        sources=p1_output.sources,
        needs_clarification=p1_output.clarification_needed,
        clarification_question=p1_output.clarification_question,
        clarification_options=clarification_options,
    )
