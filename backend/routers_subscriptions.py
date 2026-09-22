"""
Lets an MSME user subscribe to a product's standard(s) for future
change notifications.

SCOPE NOTE (important - read before demoing this): this saves the
subscription intent only. Actually detecting when a standard changes
and emailing users about it is a separate system - a scheduled job
watching for KB changes, plus an email-sending service (Resend/
SendGrid/SES), neither of which exist in this project. Not built here,
and not realistically buildable before a deadline this close. If a
judge asks "does this send real emails," the honest answer is "not
yet - subscriptions are saved and ready, the notification job is next
on the roadmap." Don't claim it's live.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .database import supabase
from .auth.dependencies import require_roles

router = APIRouter()


class SubscriptionIn(BaseModel):
    product_id: str
    standard_ids: list[str]


@router.post("/subscriptions")
def create_subscription(
    payload: SubscriptionIn,
    current_user=Depends(require_roles("msme")),
):
    supabase.table("standard_subscriptions").upsert(
        {
            "user_id": current_user["id"],
            "product_id": payload.product_id,
            "standard_ids": payload.standard_ids,
            "email": current_user["email"],
        },
        on_conflict="user_id,product_id",
    ).execute()
    return {"status": "subscribed"}


@router.get("/subscriptions")
def list_subscriptions(current_user=Depends(require_roles("msme"))):
    result = (
        supabase.table("standard_subscriptions")
        .select("*")
        .eq("user_id", current_user["id"])
        .execute()
    )
    return result.data


@router.delete("/subscriptions/{product_id}")
def delete_subscription(
    product_id: str,
    current_user=Depends(require_roles("msme")),
):
    supabase.table("standard_subscriptions").delete().eq(
        "user_id", current_user["id"]
    ).eq("product_id", product_id).execute()
    return {"status": "unsubscribed"}
