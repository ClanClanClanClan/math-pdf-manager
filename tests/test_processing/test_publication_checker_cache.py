"""Tests for the publication_checker cache schema (audit-5 #6).

A v1 cache entry (legacy) lacks ``match.author_count``.  Loading a v1
cache must drop those entries so they get re-queried -- otherwise
``auto_apply_safe_transitions`` falls back to ``author_count=1`` and
risks auto-upgrading multi-author papers.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from processing.publication_checker import CrossrefChecker


def test_v2_cache_round_trip(tmp_path):
    cache = tmp_path / "cache.json"
    c1 = CrossrefChecker(cache_path=cache)
    c1._cache = {
        "abc": {"match": {"doi": "10.1/x", "author_count": 2, "confidence": 0.9}},
    }
    c1._save_cache()
    raw = json.loads(cache.read_text())
    assert raw["_version"] == CrossrefChecker.CACHE_VERSION
    assert "abc" in raw["entries"]

    c2 = CrossrefChecker(cache_path=cache)
    assert "abc" in c2._cache
    assert c2._cache["abc"]["match"]["author_count"] == 2


def test_v1_cache_entries_dropped_when_author_count_missing(tmp_path):
    """Legacy entries land in a flat dict without _version.  Any
    entry missing ``match.author_count`` is dropped on load so the
    safe-upgrade selector doesn't fall back to its default of 1."""
    cache = tmp_path / "cache.json"
    cache.write_text(json.dumps({
        "legacy_hit": {"match": {"doi": "10.1/legacy", "confidence": 0.99}},
        "modern_hit": {"match": {"doi": "10.1/modern",
                                 "author_count": 1, "confidence": 0.99}},
        "miss": {"match": None},
    }))
    c = CrossrefChecker(cache_path=cache)
    # legacy_hit dropped (no author_count); modern_hit kept; miss kept (no match)
    assert "legacy_hit" not in c._cache
    assert "modern_hit" in c._cache
    assert "miss" in c._cache


def test_corrupt_cache_resets_to_empty(tmp_path):
    cache = tmp_path / "cache.json"
    cache.write_text("not valid json")
    c = CrossrefChecker(cache_path=cache)
    assert c._cache == {}


def test_missing_cache_starts_empty(tmp_path):
    c = CrossrefChecker(cache_path=tmp_path / "no.json")
    assert c._cache == {}


# ---------------------------------------------------------------------------
# Audit-7 #2/#4: 429/503 must NOT poison the cache.
# ---------------------------------------------------------------------------

class TestRetriableErrorsDoNotPoisonCache:

    def _mk_resp(self, status_code, headers=None, json_body=None):
        from unittest.mock import MagicMock
        r = MagicMock()
        r.status_code = status_code
        r.headers = headers or {}
        r.json.return_value = json_body or {}
        r.raise_for_status.side_effect = (
            None if 200 <= status_code < 400 else Exception(f"http {status_code}")
        )
        return r

    def test_429_does_not_cache(self, tmp_path, monkeypatch):
        c = CrossrefChecker(cache_path=tmp_path / "c.json")
        # Skip the 1s rate-limit pause in tests
        monkeypatch.setattr(c, "_rate_limit", lambda: None)
        # First call returns 429 with a tiny Retry-After
        from unittest.mock import patch
        with patch.object(c.session, "get",
                          return_value=self._mk_resp(429, {"Retry-After": "0"})):
            out = c.check_title("Some Title", [])
        assert out is None
        # The cache must NOT contain a poisoned None for this title
        cache_key = c._cache_key("Some Title")
        assert cache_key not in c._cache

    def test_500_does_not_cache(self, tmp_path, monkeypatch):
        c = CrossrefChecker(cache_path=tmp_path / "c.json")
        monkeypatch.setattr(c, "_rate_limit", lambda: None)
        from unittest.mock import patch
        with patch.object(c.session, "get",
                          return_value=self._mk_resp(503, {"Retry-After": "0"})):
            c.check_title("Another Title", [])
        assert c._cache_key("Another Title") not in c._cache

    def test_200_empty_result_does_cache(self, tmp_path, monkeypatch):
        """A real "no match" from a healthy Crossref should cache so we
        don't re-query forever."""
        c = CrossrefChecker(cache_path=tmp_path / "c.json")
        monkeypatch.setattr(c, "_rate_limit", lambda: None)
        from unittest.mock import patch
        with patch.object(c.session, "get",
                          return_value=self._mk_resp(200, json_body={"message": {"items": []}})):
            out = c.check_title("Genuine Miss", [])
        assert out is None
        # Real miss is cached
        assert c._cache_key("Genuine Miss") in c._cache
