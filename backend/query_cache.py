"""
Exact-match query-result cache - answers the judges' first piece of
feedback ("no caching system... query-result cache: exact-match
queries return instantly").

DEMO-GRADE, NOT PRODUCTION-SCALE: in-memory dict, same caveats as
session_store.py (resets on restart, not shared across workers). The
real production upgrade is Redis - swap `_cache: dict` for a Redis
client with the same get/set interface, nothing else in the codebase
needs to change, since callers only ever use .get_or_none() / .set().

NOT built in this pass (documented here, not silently skipped):
  - Semantic cache (embed the query, match near-duplicate phrasings
    like "IS standard for pressure cooker" vs "which BIS standard
    applies to pressure cookers") - needs an embedding model, which is
    the same network-dependent piece already used by P1's service, not
    P2's. Natural next step: expose it as a P1-side cache since P1
    already has the embedding model loaded.
  - Cache invalidation tied to content_hash - the KB's content_hash
    field is still unpopulated (see pipeline.py's _last_verified()
    docstring for the same finding). The mechanism here (cache key
    includes a `kb_version` stamp) is ready for this: bump kb_version
    whenever the KB reloads, and every cached entry from the old
    version stops being served automatically, without deleting anything
    - see invalidate_all().
"""

import time
import hashlib
from dataclasses import dataclass
from threading import Lock
from typing import Any, Optional

CACHE_TTL_SECONDS = 60 * 60  # 1 hour
MAX_ENTRIES = 2000


@dataclass
class CacheEntry:
    value: Any
    cached_at: float
    kb_version: int


class QueryResultCache:
    def __init__(self):
        self._cache: dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._kb_version = 1
        self.hits = 0
        self.misses = 0

    @staticmethod
    def _key(normalized_query: str) -> str:
        # hashed so cache keys have a bounded, predictable size regardless
        # of query length
        return hashlib.sha256(normalized_query.strip().lower().encode("utf-8")).hexdigest()

    def get_or_none(self, normalized_query: str) -> Optional[Any]:
        key = self._key(normalized_query)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self.misses += 1
                return None
            if entry.kb_version != self._kb_version:
                del self._cache[key]
                self.misses += 1
                return None
            if time.time() - entry.cached_at > CACHE_TTL_SECONDS:
                del self._cache[key]
                self.misses += 1
                return None
            self.hits += 1
            return entry.value

    def set(self, normalized_query: str, value: Any):
        key = self._key(normalized_query)
        with self._lock:
            if len(self._cache) >= MAX_ENTRIES and key not in self._cache:
                oldest_key = min(self._cache, key=lambda k: self._cache[k].cached_at)
                del self._cache[oldest_key]
            self._cache[key] = CacheEntry(value=value, cached_at=time.time(), kb_version=self._kb_version)

    def invalidate_all(self):
        """Call after knowledge_base/ is updated - bumping the version
        makes every existing entry miss on next lookup, without needing
        to enumerate/delete which specific standards/products changed."""
        with self._lock:
            self._kb_version += 1

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 3) if total else 0.0,
            "entries": len(self._cache),
        }
