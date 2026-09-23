"""
Chat between a customer (general/msme) and a lab. Design principle from
the plan: Supabase is the source of truth, WebSocket is only a push
notification saying "go refetch" - so a dropped connection (Render free
tier sleeping, a flaky network) never loses a message, it just makes
delivery less instant until the frontend's polling fallback or a
reconnect catches up.

Browser WebSocket can't set custom headers, so the token travels as a
query param on the ws:// URL instead of an Authorization header - same
JWT, same decode_access_token() as every REST endpoint, just handed to
this endpoint differently because the transport is different.
"""

from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from jose import JWTError

from .database import supabase
from .auth.dependencies import get_current_user
from .auth.security import decode_access_token

router = APIRouter()


# ---------------------------------------------------------------------
# REST - source of truth
# ---------------------------------------------------------------------

class StartConversationIn(BaseModel):
    lab_user_id: str


@router.post("/lab-chat/conversations")
def start_conversation(
    payload: StartConversationIn,
    current_user=Depends(get_current_user),
):
    lab_check = (
        supabase.table("users")
        .select("id,role,status")
        .eq("id", payload.lab_user_id)
        .limit(1)
        .execute()
    )
    if not lab_check.data or lab_check.data[0]["role"] != "lab":
        raise HTTPException(status_code=404, detail="Lab not found.")

    existing = (
        supabase.table("lab_conversations")
        .select("id")
        .eq("customer_user_id", current_user["id"])
        .eq("lab_user_id", payload.lab_user_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        return {"conversation_id": existing.data[0]["id"]}

    created = (
        supabase.table("lab_conversations")
        .insert({
            "customer_user_id": current_user["id"],
            "lab_user_id": payload.lab_user_id,
        })
        .execute()
    )
    return {"conversation_id": created.data[0]["id"]}


@router.get("/lab-chat/conversations")
def list_conversations(current_user=Depends(get_current_user)):
    """
    Works for both sides of the same table - a lab user sees every
    conversation where they're the lab, a customer sees every
    conversation where they're the customer. Includes the OTHER
    party's name so the lab-side inbox can show "who is this" without
    a second round trip.
    """
    if current_user["role"] == "lab":
        result = (
            supabase.table("lab_conversations")
            .select("id,customer_user_id,created_at,users!lab_conversations_customer_user_id_fkey(name)")
            .eq("lab_user_id", current_user["id"])
            .order("created_at", desc=True)
            .execute()
        )
        return [
            {
                "conversation_id": c["id"],
                "other_party_name": (c.get("users") or {}).get("name", "Unknown"),
                "other_party_id": c["customer_user_id"],
            }
            for c in result.data
        ]
    else:
        result = (
            supabase.table("lab_conversations")
            .select("id,lab_user_id,created_at,users!lab_conversations_lab_user_id_fkey(name)")
            .eq("customer_user_id", current_user["id"])
            .order("created_at", desc=True)
            .execute()
        )
        return [
            {
                "conversation_id": c["id"],
                "other_party_name": (c.get("users") or {}).get("name", "Unknown"),
                "other_party_id": c["lab_user_id"],
            }
            for c in result.data
        ]


def _assert_participant(conversation_id: str, user_id: str):
    result = (
        supabase.table("lab_conversations")
        .select("id,customer_user_id,lab_user_id")
        .eq("id", conversation_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    convo = result.data[0]
    if user_id not in (convo["customer_user_id"], convo["lab_user_id"]):
        raise HTTPException(status_code=403, detail="Not a participant in this conversation.")
    return convo


@router.get("/lab-chat/conversations/{conversation_id}/messages")
def get_messages(conversation_id: str, current_user=Depends(get_current_user)):
    _assert_participant(conversation_id, current_user["id"])
    result = (
        supabase.table("lab_messages")
        .select("id,sender_user_id,content,created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )
    return result.data


class SendMessageIn(BaseModel):
    content: str


@router.post("/lab-chat/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    payload: SendMessageIn,
    current_user=Depends(get_current_user),
):
    convo = _assert_participant(conversation_id, current_user["id"])

    result = (
        supabase.table("lab_messages")
        .insert({
            "conversation_id": conversation_id,
            "sender_user_id": current_user["id"],
            "content": payload.content,
        })
        .execute()
    )
    message = result.data[0]

    other_party_id = (
        convo["lab_user_id"]
        if current_user["id"] == convo["customer_user_id"]
        else convo["customer_user_id"]
    )
    await connection_manager.push(other_party_id, {
        "type": "new_message",
        "conversation_id": conversation_id,
    })

    return message


# ---------------------------------------------------------------------
# WebSocket - push notification layer only, never the source of truth
# ---------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active[user_id] = websocket

    def disconnect(self, user_id: str):
        self.active.pop(user_id, None)

    async def push(self, user_id: str, payload: dict):
        ws = self.active.get(user_id)
        if ws is not None:
            try:
                await ws.send_json(payload)
            except Exception:
                # Connection is dead but hasn't been cleaned up yet -
                # the message is already safely in Supabase regardless,
                # so this is fine to silently drop.
                self.disconnect(user_id)


connection_manager = ConnectionManager()


@router.websocket("/lab-chat/ws")
async def lab_chat_ws(websocket: WebSocket, token: str):
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
    except JWTError:
        await websocket.close(code=4401)
        return

    if not user_id:
        await websocket.close(code=4401)
        return

    await connection_manager.connect(user_id, websocket)
    try:
        while True:
            # This connection is push-only from the server's side - the
            # client never needs to send anything over it (messages are
            # sent via the REST POST above, which is what actually
            # persists them). This just keeps the socket open and
            # detects disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(user_id)
