"""
POST /api/chat - the one endpoint the frontend's chat UI needs.

Converts the rich internal result (ProductMatchResult + P1Output) into
the external ChatResponse contract (backend/models.py). Also wires in:
  - conversation memory (session_store.py) - resolves follow-up queries
    against the last matched product in this session
  - exact-match query caching (query_cache.py)
  - list/aggregate query detection (list_query.py) - short-circuits
    straight to a structured KB filter, skipping RAG entirely for
    "list all mandatory standards" style questions
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter

from .models import (
    ChatRequest,
    ChatResponse,
    StandardOut,
    ClarificationOptionOut,
    EvidenceOut,
)
from .dependencies import get_product_pipeline, get_session_store, get_query_cache
from .config import P1_API_BASE_URL
from .list_query import detect_list_intent, build_list_answer
from .routers_catalog import list_standards as get_catalog_standards
from integration.orchestrator import run_full_pipeline_with_context  # noqa: E402

router = APIRouter()


def _standards_out(applicable_standards) -> list[StandardOut]:
    return [
        StandardOut(
            standard_id=s.standard_id,
            is_number=s.is_number,
            title=s.title,
            status=s.status,
            relationship_type=s.relationship_type,
            is_mandatory=s.is_mandatory,
            source_url=s.source_url,
            confidence=s.confidence,
            last_verified=s.last_verified,
        )
        for s in applicable_standards
    ]


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    query_cache = get_query_cache()
    session_store = get_session_store()

    normalized_for_cache = request.query.strip().lower()

    # --- List/aggregate query short-circuit (no cache, no P1 call - the
    #     catalog data itself is the answer, and it's already fast) ---
    list_intent = detect_list_intent(request.query)
    if list_intent.is_list_query:
        catalog = [s.model_dump() for s in get_catalog_standards()]
        list_result = build_list_answer(list_intent, catalog)
        return ChatResponse(
            status="matched",
            answer=list_result["answer"],
            standards=[
                StandardOut(**{k: v for k, v in s.items() if k in StandardOut.model_fields})
                for s in list_result["standards"]
            ],
            confidence_score=list_result["confidence_score"],
            confidence_label=list_result["confidence_label"],
            evidence_sufficient=list_result["evidence_sufficient"],
        )

    # --- Exact-match cache ---
    cached = query_cache.get_or_none(normalized_for_cache)
    if cached is not None:
        cached_response = ChatResponse(**cached)
        cached_response.from_cache = True
        return cached_response

    # --- Conversation memory: resolve follow-ups against the last
    #     matched product in this session, if the query alone isn't enough ---
    context_hint = session_store.get_context_hint(request.session_id)

    product_pipeline = get_product_pipeline()
    result = run_full_pipeline_with_context(
        request.query,
        product_pipeline,
        p1_base_url=P1_API_BASE_URL,
        context_hint=context_hint,
    )
    p2_result = result["p2_result"]
    p1_output = result["p1_output"]

    if p2_result.matched_product:
        session_store.update(request.session_id, p2_result.matched_product.canonical_name)

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

    response = ChatResponse(
        status=p2_result.status,
        answer=p1_output.answer,
        matched_product_name=p2_result.matched_product.canonical_name if p2_result.matched_product else None,
        standards=_standards_out(p2_result.applicable_standards),
        confidence_score=p1_output.confidence_score,
        confidence_label=p1_output.confidence_label,
        evidence_sufficient=p1_output.evidence_sufficient,
        evidence=evidence,
        sources=p1_output.sources,
        needs_clarification=p1_output.clarification_needed,
        clarification_question=p1_output.clarification_question,
        clarification_options=clarification_options,
        detected_language=p2_result.detected_language,
    )

    # Only cache confident, complete answers - and only when the answer
    # didn't depend on this session's conversation memory. A query cache
    # keyed on literal query text is unsafe to reuse across sessions when
    # the result depended on context_hint (e.g. "what tests are needed"
    # resolves differently, or not at all, depending on what was asked
    # earlier in THAT session) - caching it here would leak one user's
    # conversation context into a different user's unrelated session.
    # This was a real bug caught by test_chat_conversation_memory_resolves_followup.
    if p2_result.status == "matched" and context_hint is None:
        query_cache.set(normalized_for_cache, response.model_dump())

    return response
