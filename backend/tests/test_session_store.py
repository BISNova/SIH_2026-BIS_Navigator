import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.session_store import ConversationSessionStore
import backend.session_store as session_store_module


def test_no_context_for_unknown_session():
    store = ConversationSessionStore()
    assert store.get_context_hint("unknown-session") is None


def test_context_remembered_across_turns():
    store = ConversationSessionStore()
    store.update("session-1", "Domestic Pressure Cooker")
    assert store.get_context_hint("session-1") == "Domestic Pressure Cooker"


def test_different_sessions_do_not_share_context():
    store = ConversationSessionStore()
    store.update("session-1", "Domestic Pressure Cooker")
    store.update("session-2", "Gold Jewellery")
    assert store.get_context_hint("session-1") == "Domestic Pressure Cooker"
    assert store.get_context_hint("session-2") == "Gold Jewellery"


def test_context_expires_after_ttl(monkeypatch):
    store = ConversationSessionStore()
    store.update("session-1", "Domestic Pressure Cooker")

    # Simulate time passing beyond the TTL without actually sleeping
    import time
    future = time.time() + session_store_module.SESSION_TTL_SECONDS + 1
    monkeypatch.setattr(session_store_module.time, "time", lambda: future)

    assert store.get_context_hint("session-1") is None


def test_clear_removes_session():
    store = ConversationSessionStore()
    store.update("session-1", "Domestic Pressure Cooker")
    store.clear("session-1")
    assert store.get_context_hint("session-1") is None


def test_none_session_id_returns_none_safely():
    store = ConversationSessionStore()
    assert store.get_context_hint(None) is None
    store.update(None, "Something")  # must not raise
