import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.kb_updater.staging import ChangeStagingQueue


def test_stage_change_appears_in_pending():
    with tempfile.TemporaryDirectory() as tmp:
        queue = ChangeStagingQueue(path=Path(tmp) / "staging.json")
        queue.stage_change("DOC-001", "https://example.com", old_hash=None, new_hash="abc123")
        pending = queue.pending()
        assert len(pending) == 1
        assert pending[0]["document_id"] == "DOC-001"
        assert pending[0]["status"] == "pending"


def test_restaging_same_document_replaces_pending_entry_not_duplicates():
    with tempfile.TemporaryDirectory() as tmp:
        queue = ChangeStagingQueue(path=Path(tmp) / "staging.json")
        queue.stage_change("DOC-001", "https://example.com", old_hash=None, new_hash="hash-v1")
        queue.stage_change("DOC-001", "https://example.com", old_hash="hash-v1", new_hash="hash-v2")
        pending = queue.pending()
        assert len(pending) == 1
        assert pending[0]["new_content_hash"] == "hash-v2"


def test_approve_removes_from_pending():
    with tempfile.TemporaryDirectory() as tmp:
        queue = ChangeStagingQueue(path=Path(tmp) / "staging.json")
        queue.stage_change("DOC-001", "https://example.com", old_hash=None, new_hash="abc123")
        found = queue.review("DOC-001", approve=True, note="Verified against BIS gazette")
        assert found is True
        assert queue.pending() == []


def test_reject_removes_from_pending():
    with tempfile.TemporaryDirectory() as tmp:
        queue = ChangeStagingQueue(path=Path(tmp) / "staging.json")
        queue.stage_change("DOC-001", "https://example.com", old_hash=None, new_hash="abc123")
        queue.review("DOC-001", approve=False, note="False positive - nav menu changed")
        assert queue.pending() == []


def test_review_unknown_document_returns_false():
    with tempfile.TemporaryDirectory() as tmp:
        queue = ChangeStagingQueue(path=Path(tmp) / "staging.json")
        found = queue.review("DOC-999", approve=True)
        assert found is False


def test_multiple_documents_stay_independent():
    with tempfile.TemporaryDirectory() as tmp:
        queue = ChangeStagingQueue(path=Path(tmp) / "staging.json")
        queue.stage_change("DOC-001", "https://example.com/1", old_hash=None, new_hash="h1")
        queue.stage_change("DOC-002", "https://example.com/2", old_hash=None, new_hash="h2")
        queue.review("DOC-001", approve=True)
        pending = queue.pending()
        assert len(pending) == 1
        assert pending[0]["document_id"] == "DOC-002"
