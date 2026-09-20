from typing import Literal
from uuid import UUID

from backend.database import supabase


def save_chat_message(
    user_id: str,
    session_id: UUID,
    role: Literal["user", "assistant"],
    content: str,
    metadata: dict | None = None,
):
    """
    Save one chat message for the authenticated user.

    user_id must come from the validated JWT in the API layer.
    It must never be supplied by the frontend.
    """

    message = {
        "user_id": str(user_id),
        "session_id": str(session_id),
        "role": role,
        "content": content,
        "metadata": metadata,
    }

    result = (
        supabase
        .table("chat_messages")
        .insert(message)
        .execute()
    )

    if not result.data:
        raise RuntimeError("Chat message was not saved")

    return result.data[0]