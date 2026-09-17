import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.query_cache import QueryResultCache
import backend.query_cache as query_cache_module


def test_miss_on_empty_cache():
    cache = QueryResultCache()
    assert cache.get_or_none("domestic pressure cooker") is None
    assert cache.misses == 1


def test_hit_after_set():
    cache = QueryResultCache()
    cache.set("domestic pressure cooker", {"answer": "IS 2347 applies"})
    result = cache.get_or_none("domestic pressure cooker")
    assert result == {"answer": "IS 2347 applies"}
    assert cache.hits == 1


def test_case_and_whitespace_insensitive_key():
    cache = QueryResultCache()
    cache.set("  Domestic Pressure Cooker  ", {"answer": "x"})
    assert cache.get_or_none("domestic pressure cooker") == {"answer": "x"}


def test_invalidate_all_clears_effective_cache_without_deleting():
    cache = QueryResultCache()
    cache.set("domestic pressure cooker", {"answer": "old"})
    cache.invalidate_all()
    assert cache.get_or_none("domestic pressure cooker") is None


def test_ttl_expiry(monkeypatch):
    cache = QueryResultCache()
    cache.set("domestic pressure cooker", {"answer": "x"})

    import time
    future = time.time() + query_cache_module.CACHE_TTL_SECONDS + 1
    monkeypatch.setattr(query_cache_module.time, "time", lambda: future)

    assert cache.get_or_none("domestic pressure cooker") is None


def test_stats_reports_hit_rate():
    cache = QueryResultCache()
    cache.set("q1", {"a": 1})
    cache.get_or_none("q1")  # hit
    cache.get_or_none("q2")  # miss
    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 0.5
