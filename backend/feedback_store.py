"""
👍/👎 feedback capture, feeding a review queue rather than just a vanity
counter - per the judges' feedback: "feeding back into a review queue,
not just vanity metrics."

DEMO-GRADE: appends to a local JSONL file (backend/data/feedback.jsonl).
Good enough to actually inspect/review by hand or with a simple script
right now; the real production upgrade is a proper database table so a
review dashboard can query/filter it - the interface here
(record()/all()/stats()) is small enough that swap doesn't touch
calling code.
"""

import json
import time
from pathlib import Path
from threading import Lock
from typing import Optional

FEEDBACK_LOG_PATH = Path(__file__).resolve().parent / "data" / "feedback.jsonl"


class FeedbackStore:
    def __init__(self, path: Path = FEEDBACK_LOG_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def record(self, query: str, answer: str, rating: str, session_id: Optional[str], comment: Optional[str]) -> int:
        entry = {
            "timestamp": time.time(),
            "query": query,
            "answer": answer,
            "rating": rating,  # "up" | "down"
            "session_id": session_id,
            "comment": comment,
        }
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            return self._count()

    def _count(self) -> int:
        if not self.path.exists():
            return 0
        with open(self.path, encoding="utf-8") as f:
            return sum(1 for _ in f)

    def all(self) -> list:
        if not self.path.exists():
            return []
        with open(self.path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def stats(self) -> dict:
        entries = self.all()
        up = sum(1 for e in entries if e["rating"] == "up")
        down = sum(1 for e in entries if e["rating"] == "down")
        return {"total": len(entries), "up": up, "down": down}
