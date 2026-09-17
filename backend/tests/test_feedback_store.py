import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.feedback_store import FeedbackStore


def test_record_and_count():
    with tempfile.TemporaryDirectory() as tmp:
        store = FeedbackStore(path=Path(tmp) / "feedback.jsonl")
        count = store.record("domestic pressure cooker", "IS 2347 applies", "up", "session-1", None)
        assert count == 1
        count = store.record("gold jewellery", "IS 1417 applies", "down", "session-2", "wrong standard")
        assert count == 2


def test_stats_breaks_down_up_vs_down():
    with tempfile.TemporaryDirectory() as tmp:
        store = FeedbackStore(path=Path(tmp) / "feedback.jsonl")
        store.record("q1", "a1", "up", None, None)
        store.record("q2", "a2", "up", None, None)
        store.record("q3", "a3", "down", None, "unhelpful")
        stats = store.stats()
        assert stats == {"total": 3, "up": 2, "down": 1}


def test_empty_store_returns_zero_stats():
    with tempfile.TemporaryDirectory() as tmp:
        store = FeedbackStore(path=Path(tmp) / "feedback.jsonl")
        assert store.stats() == {"total": 0, "up": 0, "down": 0}
