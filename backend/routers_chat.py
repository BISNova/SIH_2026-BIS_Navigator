"""
POST /api/chat

Main chat endpoint used by the frontend.

Responsibilities:
    - Authenticate the request using the user's JWT.
    - Obtain user_id from the validated JWT.
    - Create a session_id when the frontend does not provide one.
    - Save the user's message automatically.
    - Resolve follow-up questions using session context.
    - Use exact-match query cache when appropriate.
    - Handle structured list/aggregate queries.
    - Run the normal P2 -> P1 pipeline.
    - Save the assistant response automatically.

Important:
    user_id is NEVER accepted from the frontend.
    It always comes from the authenticated JWT.
"""

import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

from fastapi import APIRouter, Depends, HTTPException

from .auth.dependencies import get_current_user
from .config import P1_API_BASE_URL
from .dependencies import (
    get_product_pipeline,
    get_query_cache,
    get_session_store,
)
from .list_query import (
    build_list_answer,
    detect_list_intent,
)
from .models import (
    ChatRequest,
    ChatResponse,
    ClarificationOptionOut,
    EvidenceOut,
    StandardOut,
)
from .routers_catalog import list_standards as get_catalog_standards
from .chat_history_service import save_chat_message

from integration.orchestrator import (
    run_full_pipeline_with_context,
)


router = APIRouter()


def _standards_out(applicable_standards):
    """
    Convert internal P2 standard objects into the public API model.
    """

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


def _get_session_id(request: ChatRequest):
    """
    Use the frontend-provided session ID when available.

    Otherwise create a new UUID for the conversation.
    """

    if request.session_id is not None:
        return request.session_id

    return uuid4()


def _save_message_or_raise(
    user_id: str,
    session_id,
    role: str,
    content: str,
    metadata: dict | None = None,
):
    """
    Persist one chat message.

    Any database failure is surfaced as HTTP 500 instead of silently
    returning a successful chat response while history was lost.
    """

    try:
        save_chat_message(
            user_id=str(user_id),
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to save chat history",
        ) from exc


@router.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
    current_user=Depends(get_current_user),
):
    """
    Main BISNova chat endpoint.

    Authentication:
        Bearer JWT is required.

    User isolation:
        user_id comes from current_user, which comes from the JWT.
    """

    query_cache = get_query_cache()
    session_store = get_session_store()

    session_id = _get_session_id(request)
    session_id_str = str(session_id)

    user_id = str(current_user["id"])

    # ---------------------------------------------------------------
    # 1. Save user's message
    # ---------------------------------------------------------------

    _save_message_or_raise(
        user_id=user_id,
        session_id=session_id,
        role="user",
        content=request.query,
        metadata={
            "source": "chat",
        },
    )

    # ---------------------------------------------------------------
    # 2. Normalize query for exact-match cache
    # ---------------------------------------------------------------

    normalized_for_cache = request.query.strip().lower()

    # ---------------------------------------------------------------
    # 3. Handle list / aggregate queries
    # ---------------------------------------------------------------

    list_intent = detect_list_intent(request.query)

    if list_intent.is_list_query:
        catalog = [
            standard.model_dump()
            for standard in get_catalog_standards()
        ]

        list_result = build_list_answer(
            list_intent,
            catalog,
        )

        response = ChatResponse(
            status="matched",
            answer=list_result["answer"],
            standards=[
                StandardOut(
                    **{
                        key: value
                        for key, value in standard.items()
                        if key in StandardOut.model_fields
                    }
                )
                for standard in list_result["standards"]
            ],
            confidence_score=list_result["confidence_score"],
            confidence_label=list_result["confidence_label"],
            evidence_sufficient=list_result["evidence_sufficient"],
        )

        # -----------------------------------------------------------
        # Save assistant response
        # -----------------------------------------------------------

        _save_message_or_raise(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            content=response.answer,
            metadata={
                "source": "chat",
                "from_cache": False,
                "status": response.status,
            },
        )

        return response

    # ---------------------------------------------------------------
    # 4. Get conversation context
    # ---------------------------------------------------------------

    context_hint = session_store.get_context_hint(
        session_id_str
    )

    # ---------------------------------------------------------------
    # 5. Exact-match cache
    #
    # Do not use cached answers when the session has a context hint,
    # because follow-up questions may depend on that context.
    # ---------------------------------------------------------------

    if context_hint is None:
        cached = query_cache.get_or_none(
            normalized_for_cache
        )

        if cached is not None:
            cached_response = ChatResponse(
                **cached
            )

            cached_response.from_cache = True

            _save_message_or_raise(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                content=cached_response.answer,
                metadata={
                    "source": "chat",
                    "from_cache": True,
                    "status": cached_response.status,
                },
            )

            return cached_response

    # ---------------------------------------------------------------
    # 6. Run normal P2 -> P1 pipeline
    # ---------------------------------------------------------------

    product_pipeline = get_product_pipeline()

    result = run_full_pipeline_with_context(
        request.query,
        product_pipeline,
        p1_base_url=P1_API_BASE_URL,
        context_hint=context_hint,
    )

    p2_result = result["p2_result"]
    p1_output = result["p1_output"]
    p1_success = result["p1_success"]

    # ---------------------------------------------------------------
    # 7. Update conversation context
    # ---------------------------------------------------------------

    if p2_result.matched_product:
        session_store.update(
            session_id_str,
            p2_result.matched_product.canonical_name,
        )

    # ---------------------------------------------------------------
    # 8. Convert clarification options
    # ---------------------------------------------------------------

    clarification_options = [
        ClarificationOptionOut(
            label=option.label,
            query=f"{request.query} {option.label}",
        )
        for option in p2_result.clarification_options
    ]

    # ---------------------------------------------------------------
    # 9. Convert evidence
    # ---------------------------------------------------------------

    evidence = [
        EvidenceOut(
            chunk_id=item.chunk_id,
            standard_id=item.standard_id,
            text=item.text,
            section_header=item.section_header,
            source_url=item.source_url,
        )
        for item in p1_output.evidence
    ]

    # ---------------------------------------------------------------
    # 10. Build public response
    # ---------------------------------------------------------------

    response = ChatResponse(
        status=p2_result.status,
        answer=p1_output.answer,
        matched_product_name=(
            p2_result.matched_product.canonical_name
            if p2_result.matched_product
            else None
        ),
        standards=_standards_out(
            p2_result.applicable_standards
        ),
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

    # ---------------------------------------------------------------
    # 11. Cache successful standalone matched queries
    # ---------------------------------------------------------------

    if (
        p1_success
        and p2_result.status == "matched"
        and context_hint is None
    ):
        query_cache.set(
            normalized_for_cache,
            response.model_dump(),
        )

    # ---------------------------------------------------------------
    # 12. Save assistant response
    # ---------------------------------------------------------------

    _save_message_or_raise(
        user_id=user_id,
        session_id=session_id,
        role="assistant",
        content=response.answer,
        metadata={
            "source": "chat",
            "from_cache": response.from_cache,
            "status": response.status,
            "matched_product_name": (
                response.matched_product_name
            ),
            "confidence_score": (
                response.confidence_score
            ),
            "evidence_sufficient": (
                response.evidence_sufficient
            ),
        },
    )

    return response