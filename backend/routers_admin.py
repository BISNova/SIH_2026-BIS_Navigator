"""
GET /api/admin/staged-changes - pending content changes detected by the
KB updater scraper, waiting for human review.

POST /api/admin/review - approve or reject one.

The scrape step itself (backend/kb_updater/scraper.py) needs real
internet access to bis.gov.in - see that file's docstring. These
endpoints don't - they only manage the review queue, so they're fully
demoable/testable regardless.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .dependencies import get_staging_queue
from .auth.dependencies import require_roles


router = APIRouter()


@router.get("/admin/staged-changes")
def list_staged_changes(
    current_user=Depends(require_roles("admin")),
):
    return get_staging_queue().pending()


class ReviewRequest(BaseModel):
    document_id: str
    approve: bool
    note: Optional[str] = None


@router.post("/admin/review")
def review_staged_change(
    request: ReviewRequest,
    current_user=Depends(require_roles("admin")),
):
    found = get_staging_queue().review(
        request.document_id,
        request.approve,
        request.note,
    )

    return (
        {
            "found": found,
            "status": "approved" if request.approve else "rejected",
        }
        if found
        else {
            "found": False,
        }
    )
