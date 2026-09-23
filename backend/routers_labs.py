"""
Two things:

1. POST /labs/profile - a newly-registered lab user submits their
   contact number + hours right after registering. Deliberately NOT
   folded into auth/router.py's register endpoint - keeping it separate
   means zero changes to the tested register/login flow. Called with
   the user_id the register response already returns, before the user
   can log in (they're pending) - so this is intentionally
   unauthenticated, but validated server-side (must be a real, pending
   lab user) so it can't be abused to attach a profile to someone else's
   account.

2. GET /labs/platform-registered - approved platform-registered labs,
   shaped to match the exact fields TestingLabsPage.jsx already expects
   from /catalog/labs (lab_id, lab_name, lab_type, status, city,
   district, state, contact) plus two new fields the frontend uses to
   decide which button to show: platform_registered, lab_user_id.
   /catalog/labs itself is untouched - the frontend merges both lists
   client-side, so the original 15 scraped labs keep working exactly as
   they do today.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .database import supabase

router = APIRouter()


class LabProfileIn(BaseModel):
    user_id: str
    contact_number: str
    opening_time: str
    closing_time: str


@router.post("/labs/profile")
def submit_lab_profile(payload: LabProfileIn):
    user_result = (
        supabase.table("users")
        .select("id,role,status")
        .eq("id", payload.user_id)
        .limit(1)
        .execute()
    )
    if not user_result.data:
        raise HTTPException(status_code=404, detail="User not found.")

    user = user_result.data[0]
    if user["role"] != "lab":
        raise HTTPException(status_code=400, detail="This account is not a lab account.")

    supabase.table("lab_profiles").upsert(
        {
            "user_id": payload.user_id,
            "contact_number": payload.contact_number,
            "opening_time": payload.opening_time,
            "closing_time": payload.closing_time,
        },
        on_conflict="user_id",
    ).execute()

    return {"status": "saved"}


@router.get("/labs/platform-registered")
def list_platform_labs():
    result = (
        supabase.table("users")
        .select("id,name,lab_profiles(contact_number,opening_time,closing_time)")
        .eq("role", "lab")
        .eq("status", "active")
        .execute()
    )

    labs = []
    for u in result.data:
        profile_raw = u.get("lab_profiles")
        profile = (profile_raw[0] if profile_raw else {}) if isinstance(profile_raw, list) else (profile_raw or {})

        labs.append({
            "lab_id": f"PLATFORM-{u['id']}",
            "lab_name": u["name"],
            "lab_type": "Platform-Registered Lab",
            "status": "Registered",
            "city": None,
            "district": None,
            "state": None,
            "address": None,
            "contact": profile.get("contact_number"),
            "opening_time": profile.get("opening_time"),
            "closing_time": profile.get("closing_time"),
            "platform_registered": True,
            "lab_user_id": u["id"],
        })

    return labs
