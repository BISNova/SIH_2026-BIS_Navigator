"""
Staging -> review -> publish flow for detected content changes -
per the judges' feedback: "so scraped changes don't go live unverified
(important for a compliance tool - wrong info here has real
consequences)."

A detected change NEVER modifies knowledge_base/ directly. It's
recorded here as a pending entry; a human calls approve() or reject()
explicitly. This file only manages the review queue - actually writing
an approved change into knowledge_base/structured/*.json is a
deliberate manual step for now (see learning.md), not automated, since
that's the exact "wrong info here has real consequences" risk the
feedback called out.

DEMO-GRADE: JSON file storage, like feedback_store.py. Same upgrade
path (a real database) applies here for production scale.
"""

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from threading import Lock
from typing import Optional

STAGING_PATH = Path(__file__).resolve().parent.parent / "data" / "kb_change_staging.json"


@dataclass
class StagedChange:
    document_id: str
    source_url: str
    old_content_hash: Optional[str]
    new_content_hash: str
    detected_at: float
    status: str = "pending"  # "pending" | "approved" | "rejected"
    reviewed_at: Optional[float] = None
    reviewer_note: Optional[str] = None


class ChangeStagingQueue:
    def __init__(self, path: Path = STAGING_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def _read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def _write_all(self, entries: list[dict]):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)

    def stage_change(self, document_id: str, source_url: str, old_hash: Optional[str], new_hash: str) -> StagedChange:
        change = StagedChange(
            document_id=document_id,
            source_url=source_url,
            old_content_hash=old_hash,
            new_content_hash=new_hash,
            detected_at=time.time(),
        )
        with self._lock:
            entries = self._read_all()
            # Don't duplicate a pending entry for the same document -
            # update it in place instead.
            entries = [e for e in entries if not (e["document_id"] == document_id and e["status"] == "pending")]
            entries.append(asdict(change))
            self._write_all(entries)
        return change

    def pending(self) -> list[dict]:
        return [e for e in self._read_all() if e["status"] == "pending"]

    def review(self, document_id: str, approve: bool, note: Optional[str] = None) -> bool:
        """Returns True if a pending entry was found and updated."""
        with self._lock:
            entries = self._read_all()
            found = False
            for e in entries:
                if e["document_id"] == document_id and e["status"] == "pending":
                    e["status"] = "approved" if approve else "rejected"
                    e["reviewed_at"] = time.time()
                    e["reviewer_note"] = note
                    found = True
            if found:
                self._write_all(entries)
            return found
