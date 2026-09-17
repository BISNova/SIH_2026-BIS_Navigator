"""
Conversation memory - in-memory, keyed by session_id.

DEMO-GRADE, NOT PRODUCTION-SCALE: this is a plain Python dict living in
the backend process's memory. It resets on restart and doesn't share
state across multiple backend processes/workers. For real production
use with multiple workers, this needs to move to Redis (same upgrade
path as the query cache in query_cache.py, and the same thing the
judges' feedback asked for under "layered caching") - the interface
below is deliberately small so that swap is a drop-in replacement, not
a redesign.

What it remembers: only the last matched product's name per session -
enough to resolve a follow-up like "what tests does it need" right
after "I manufacture pressure cookers", without needing full
conversation transcripts. Deliberately minimal - more context stored
means more chances for a follow-up to get resolved against the WRONG
prior turn.
"""

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional

SESSION_TTL_SECONDS = 60 * 30  # 30 minutes of inactivity - then forgotten
MAX_SESSIONS = 5000  # simple cap so a demo/small deployment can't leak memory forever


@dataclass
class SessionContext:
    last_matched_product_name: Optional[str] = None
    last_updated_at: float = field(default_factory=time.time)


class ConversationSessionStore:
    def __init__(self):
        self._sessions: dict[str, SessionContext] = {}
        self._lock = Lock()

    def get_context_hint(self, session_id: Optional[str]) -> Optional[str]:
        if not session_id:
            return None
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if time.time() - session.last_updated_at > SESSION_TTL_SECONDS:
                del self._sessions[session_id]
                return None
            return session.last_matched_product_name

    def update(self, session_id: Optional[str], matched_product_name: Optional[str]):
        if not session_id or not matched_product_name:
            return
        with self._lock:
            if len(self._sessions) >= MAX_SESSIONS and session_id not in self._sessions:
                self._evict_oldest()
            self._sessions[session_id] = SessionContext(
                last_matched_product_name=matched_product_name,
                last_updated_at=time.time(),
            )

    def _evict_oldest(self):
        if not self._sessions:
            return
        oldest_id = min(self._sessions, key=lambda k: self._sessions[k].last_updated_at)
        del self._sessions[oldest_id]

    def clear(self, session_id: str):
        with self._lock:
            self._sessions.pop(session_id, None)
