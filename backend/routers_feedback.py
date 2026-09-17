"""
POST /api/feedback - 👍/👎 capture feeding a review queue.
GET /api/feedback/stats - quick up/down counts (useful for a demo).
"""

from fastapi import APIRouter

from .models import FeedbackRequest, FeedbackResponse
from .dependencies import get_feedback_store

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(request: FeedbackRequest):
    store = get_feedback_store()
    total = store.record(
        query=request.query,
        answer=request.answer,
        rating=request.rating,
        session_id=request.session_id,
        comment=request.comment,
    )
    return FeedbackResponse(status="recorded", total_feedback_count=total)


@router.get("/feedback/stats")
def feedback_stats():
    store = get_feedback_store()
    return store.stats()
