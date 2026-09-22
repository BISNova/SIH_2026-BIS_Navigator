from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.auth.dependencies import get_current_user
from backend.database import supabase


router = APIRouter()


class ChatHistoryCreate(BaseModel):
    session_id: UUID
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1)
    metadata: dict | None = None


class ChatHistoryResponse(BaseModel):
    id: UUID
    user_id: UUID
    session_id: UUID
    role: Literal["user", "assistant"]
    content: str
    metadata: dict | None = None
    created_at: datetime


class ChatSessionResponse(BaseModel):
    session_id: UUID
    created_at: datetime
    updated_at: datetime
    message_count: int


@router.post(
    "/chat/history",
    response_model=ChatHistoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_chat_history(
    request: ChatHistoryCreate,
    current_user=Depends(get_current_user),
):
    message = {
        "user_id": str(current_user["id"]),
        "session_id": str(request.session_id),
        "role": request.role,
        "content": request.content,
        "metadata": request.metadata,
    }

    try:
        result = (
            supabase
            .table("chat_messages")
            .insert(message)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to save chat message",
        ) from exc

    if not result.data:
        raise HTTPException(
            status_code=500,
            detail="Chat message was not saved",
        )

    return result.data[0]


@router.get(
    "/chat/history/{session_id}",
    response_model=list[ChatHistoryResponse],
)
def get_chat_history(
    session_id: UUID,
    current_user=Depends(get_current_user),
):
    try:
        result = (
            supabase
            .table("chat_messages")
            .select(
                "id,user_id,session_id,role,content,metadata,created_at"
            )
            .eq("user_id", str(current_user["id"]))
            .eq("session_id", str(session_id))
            .order("created_at", desc=False)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve chat history",
        ) from exc

    return result.data or []


@router.delete(
    "/chat/history/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_chat_history(
    session_id: UUID,
    current_user=Depends(get_current_user),
):
    """
    Delete all messages belonging to one chat session.

    Security:
        user_id is always taken from the authenticated JWT.
        A user can only delete their own chat session.
    """

    user_id = str(current_user["id"])

    try:
        (
            supabase
            .table("chat_messages")
            .delete()
            .eq("user_id", user_id)
            .eq("session_id", str(session_id))
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete chat history",
        ) from exc

    return None


@router.get(
    "/chat/sessions",
    response_model=list[ChatSessionResponse],
)
def get_chat_sessions(
    current_user=Depends(get_current_user),
):
    """
    Return all chat sessions belonging to the authenticated user.

    user_id is taken only from the JWT.
    The frontend cannot request another user's sessions.
    """

    user_id = str(current_user["id"])

    try:
        result = (
            supabase
            .table("chat_messages")
            .select("session_id,created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve chat sessions",
        ) from exc

    rows = result.data or []

    sessions = {}

    for row in rows:
        session_id = row["session_id"]
        created_at = row["created_at"]

        if session_id not in sessions:
            sessions[session_id] = {
                "session_id": session_id,
                "created_at": created_at,
                "updated_at": created_at,
                "message_count": 0,
            }

        sessions[session_id]["updated_at"] = created_at
        sessions[session_id]["message_count"] += 1

    return sorted(
        sessions.values(),
        key=lambda session: session["updated_at"],
        reverse=True,
    )