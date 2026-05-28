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
    """The cache stores match dicts directly (not wrapped under
    'match').  Round-trip must preserve a non-repository entry that
    carries ``author_count``."""
    cache = tmp_path / "cache.json"
    c1 = CrossrefChecker(cache_path=cache)
    c1._cache = {
        "abc": {
            "doi": "10.1007/s10000-024-0042-z",  # real Springer DOI, not a repo
            "journal": "Annals of Probability",
            "author_count": 2,
            "confidence": 0.9,
        },
    }
    c1._save_cache()
    raw = json.loads(cache.read_text())
    assert raw["_version"] == CrossrefChecker.CACHE_VERSION
    assert "abc" in raw["entries"]

    c2 = CrossrefChecker(cache_path=cache)
    assert "abc" in c2._cache
    assert c2._cache["abc"]["author_count"] == 2


def test_v1_cache_entries_dropped_when_author_count_missing(tmp_path):
    """Legacy v1 cache stores match dicts DIRECTLY at the cache key
    (not nested under a 'match' field).  An entry without
    ``author_count`` is dropped on load so the safe-upgrade selector
    doesn't fall back to its default of 1.  Live-trial finding: the
    audit-6 migration code assumed nested structure and silently
    kept all entries."""
    cache = tmp_path / "cache.json"
    cache.write_text(json.dumps({
        "legacy_hit": {"doi": "10.1007/legacy", "confidence": 0.99,
                       "journal": "Annals of Probability"},  # no author_count
        "modern_hit": {"doi": "10.1007/modern", "author_count": 1,
                       "confidence": 0.99,
                       "journal": "Annals of Probability"},
        "miss": None,
    }))
    c = CrossrefChecker(cache_path=cache)
    # legacy_hit dropped (no author_count); modern_hit kept; miss kept (None)
    assert "legacy_hit" not in c._cache
    assert "modern_hit" in c._cache
    assert "miss" in c._cache
    assert c._cache["miss"] is None


def test_v1_cache_repo_match_neutralised(tmp_path):
    """v1 cache with an SSRN match should become a NEGATIVE entry
    on load -- otherwise scan_directory keeps surfacing the
    pre-filter false-positives indefinitely."""
    cache = tmp_path / "cache.json"
    cache.write_text(json.dumps({
        "repo_hit": {"doi": "10.2139/ssrn.1234567",
                     "journal": "SSRN Electronic Journal",
                     "author_count": 1, "confidence": 0.8},
    }))
    c = CrossrefChecker(cache_path=cache)
    assert "repo_hit" in c._cache
    assert c._cache["repo_hit"] is None  # neutralised


def test_corrupt_cache_resets_to_empty(tmp_path):
    cache = tmp_path / "cache.json"
    cache.write_text("not valid json")
    c = CrossrefChecker(cache_path=cache)
    assert c._cache == {}


def test_missing_cache_starts_empty(tmp_path):
    c = CrossrefChecker(cache_path=tmp_path / "no.json")
    assert c._cache == {}


# ---------------------------------------------------------------------------
# Live-trial findings: stale entries in v2 caches were bypassing today's
# validation rules (repository filter, author_count gate).
# ---------------------------------------------------------------------------

class TestV2CacheRevalidation:

    def test_v2_repository_match_converted_to_negative_on_load(self, tmp_path):
        """A v2 cache that has an SSRN match (cached before the
        repository filter existed, or from a prior dev session)
        used to return that match as positive on lookup, then the
        state machine recorded it as a hit, then the Attention
        Queue surfaced it.  Now we convert known-repository matches
        to negative cache entries on load."""
        import json
        cache = tmp_path / "cache.json"
        cache.write_text(json.dumps({
            "_version": CrossrefChecker.CACHE_VERSION,
            "entries": {
                "abc": {
                    "doi": "10.2139/ssrn.1234567",
                    "journal": "SSRN Electronic Journal",
                    "author_count": 2,
                    "confidence": 0.8,
                },
            },
        }))
        c = CrossrefChecker(cache_path=cache)
        # The SSRN entry is now stored as a negative cache hit
        assert c._cache["abc"] is None

    def test_v2_entries_without_author_count_dropped(self, tmp_path):
        """Pre-Phase-3 cached entries lack ``author_count`` and would
        feed Phase 3's safe-upgrade gate a default of 1, risking a
        wrong auto-upgrade.  Drop them on load."""
        import json
        cache = tmp_path / "cache.json"
        cache.write_text(json.dumps({
            "_version": CrossrefChecker.CACHE_VERSION,
            "entries": {
                "old": {"doi": "10.1/x", "confidence": 0.95},  # no author_count
                "new": {"doi": "10.1/y", "confidence": 0.95, "author_count": 1},
            },
        }))
        c = CrossrefChecker(cache_path=cache)
        assert "old" not in c._cache
        assert "new" in c._cache

    def test_runtime_filter_on_cache_hit(self, tmp_path, monkeypatch):
        """Even if a stale repo entry sneaks past load-time filtering
        (defence in depth), ``check_title`` re-validates on every
        cache hit and returns None for repository matches."""
        import json
        cache = tmp_path / "cache.json"
        # Hand-craft a cache with the stale repo entry and bypass the
        # load-time filter by manually monkeypatching after construction.
        c = CrossrefChecker(cache_path=cache)
        c._cache["the-cache-key"] = {
            "doi": "10.2139/ssrn.7654321",
            "journal": "SSRN Electronic Journal",
            "author_count": 1,
            "confidence": 0.95,
        }
        # Bypass the cache_key derivation: directly call the lookup
        # via a known title that hashes to our key, OR just patch the
        # cache_key to return our chosen key.
        monkeypatch.setattr(c, "_cache_key", lambda title: "the-cache-key")
        # Also skip rate-limit + network -- if the runtime filter
        # works, we never reach them.
        monkeypatch.setattr(c, "_rate_limit", lambda: None)
        result = c.check_title("Stub title", [])
        assert result is None
        # And the cache entry is now neutralised
        assert c._cache["the-cache-key"] is None


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
