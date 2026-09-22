"""
Persists a logged-in user's checked-off checklist items. Needs the
checklist_progress table in Supabase - see the SQL sent alongside this
file, run it the same way the chat_messages table SQL went in.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .database import supabase
from .auth.dependencies import get_current_user

router = APIRouter()


class ChecklistProgressIn(BaseModel):
    product_id: str
    completed_step_ids: list[str]


@router.post("/checklist/progress")
def save_progress(
    payload: ChecklistProgressIn,
    current_user=Depends(get_current_user),
):
    supabase.table("checklist_progress").upsert(
        {
            "user_id": current_user["id"],
            "product_id": payload.product_id,
            "completed_step_ids": payload.completed_step_ids,
        },
        on_conflict="user_id,product_id",
    ).execute()
    return {"status": "saved"}


@router.get("/checklist/progress")
def get_progress(
    product_id: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    query = supabase.table("checklist_progress").select("*").eq("user_id", current_user["id"])
    if product_id:
        query = query.eq("product_id", product_id)
    result = query.execute()

    if product_id:
        return result.data[0] if result.data else {"product_id": product_id, "completed_step_ids": []}
    return result.data
