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
