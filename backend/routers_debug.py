"""
GET /api/health - basic liveness/readiness check.
POST /api/debug/match-product - Product Intelligence ONLY, no RAG call.

The debug endpoint exists so the frontend/QA can test product matching
immediately, even before real embeddings are generated on a dev
machine (RAG needs the real model + internet; product matching does
not). Not meant for the actual chat UI - that should always use /chat.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from .models import HealthResponse, StandardOut
from .dependencies import get_product_pipeline
from .config import P1_API_BASE_URL

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health():
    pipeline = get_product_pipeline()

    from integration.p1_client import check_p1_health
    p1_reachable = check_p1_health(P1_API_BASE_URL)

    return HealthResponse(
        status="ok",
        products_loaded=len(pipeline.products_df),
        standards_loaded=len(pipeline.standards_df),
        p1_service_reachable=p1_reachable,
    )


class DebugMatchRequest(BaseModel):
    query: str


class DebugMatchResponse(BaseModel):
    status: str
    matched_product_name: Optional[str] = None
    confidence_score: float
    confidence_label: str
    standards: List[StandardOut] = []
    clarification_question: Optional[str] = None


@router.post("/debug/match-product", response_model=DebugMatchResponse)
def debug_match_product(request: DebugMatchRequest):
    pipeline = get_product_pipeline()
    result = pipeline.process(request.query)

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
        for s in result.applicable_standards
    ]

    return DebugMatchResponse(
        status=result.status,
        matched_product_name=result.matched_product.canonical_name if result.matched_product else None,
        confidence_score=result.confidence_score,
        confidence_label=result.confidence_label,
        standards=standards,
        clarification_question=result.clarification_question,
    )
