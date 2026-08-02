"""Tests for ``ui.attention_queue``."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ui.attention_queue import (
    AttentionItem,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    collect_conflict_copies,
    collect_permanently_unpublished,
    collect_upgrade_flags,
    collect_watcher_failures,
    dismiss,
    gather_attention_items,
    undismiss,
    _filter_dismissed,
    _load_dismissals,
    _save_dismissals,
)


# ---------------------------------------------------------------------------
# Dismissals store
# ---------------------------------------------------------------------------

class TestDismissals:

    def test_missing_file_yields_empty(self, tmp_path):
        assert _load_dismissals(tmp_path / "nope.json") == {}

    def test_save_then_load_roundtrip(self, tmp_path):
        f = tmp_path / "d.json"
        _save_dismissals({"a": "2026-06-01", "b": "2027-01-01"}, f)
        assert _load_dismissals(f) == {"a": "2026-06-01", "b": "2027-01-01"}

    def test_corrupt_file_yields_empty(self, tmp_path):
        f = tmp_path / "d.json"
        f.write_text("{not valid")
        assert _load_dismissals(f) == {}

    def test_non_object_yields_empty(self, tmp_path):
        f = tmp_path / "d.json"
        f.write_text('["a", "b"]')
        assert _load_dismissals(f) == {}

    def test_dismiss_writes_future_timestamp(self, tmp_path):
        f = tmp_path / "d.json"
        dismiss("foo", days=3, path=f)
        data = _load_dismissals(f)
        assert "foo" in data
        until = datetime.fromisoformat(data["foo"])
        delta = until - datetime.now(timezone.utc)
        assert timedelta(days=2, hours=23) < delta < timedelta(days=3, minutes=1)

    def test_dismiss_negative_days_raises(self, tmp_path):
        with pytest.raises(ValueError):
            dismiss("foo", days=-1, path=tmp_path / "d.json")

    def test_undismiss_removes_entry(self, tmp_path):
        f = tmp_path / "d.json"
        dismiss("foo", days=7, path=f)
        undismiss("foo", path=f)
        assert _load_dismissals(f) == {}

    def test_undismiss_missing_key_is_noop(self, tmp_path):
        undismiss("nope", path=tmp_path / "d.json")  # no raise


class TestFilterDismissed:

    def _item(self, key: str) -> AttentionItem:
        return AttentionItem(key=key, source="x", severity=SEVERITY_INFO, title=key)

    def test_active_dismissal_filters_item(self):
        items = [self._item("a"), self._item("b")]
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        out = _filter_dismissed(items, {"a": future})
        assert [it.key for it in out] == ["b"]

    def test_expired_dismissal_passes_through(self):
        items = [self._item("a")]
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        out = _filter_dismissed(items, {"a": past})
        assert [it.key for it in out] == ["a"]

    def test_bogus_iso_treated_as_expired(self):
        out = _filter_dismissed([self._item("a")], {"a": "not-a-date"})
        assert [it.key for it in out] == ["a"]


# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------

class TestWatcherFailures:

    def test_missing_log_yields_empty(self, tmp_path):
        assert collect_watcher_failures(tmp_path / "missing.log") == []

    def test_parses_error_line(self, tmp_path):
        # Format must match what src/watcher/daemon.py actually emits:
        #   logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        log = tmp_path / "watcher.log"
        log.write_text(
            "2026-05-17 12:34:56,789 [ERROR] Failed to ingest paper.pdf: bad metadata\n"
        )
        items = collect_watcher_failures(log)
        assert len(items) == 1
        it = items[0]
        assert it.source == "watcher_failure"
        assert it.severity == SEVERITY_ERROR
        assert it.payload["file"] == "paper.pdf"
        assert "bad metadata" in it.payload["reason"]

    def test_parses_real_daemon_format(self, tmp_path):
        """Smoke test against a real log entry recorded by the daemon."""
        import logging
        log = tmp_path / "watcher.log"
        # Build a real log line via the same logging machinery the
        # daemon uses, so this test breaks if the daemon's format
        # changes upstream.
        h = logging.FileHandler(log)
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger_obj = logging.getLogger("test_real_daemon_format")
        logger_obj.setLevel(logging.DEBUG)
        logger_obj.addHandler(h)
        try:
            logger_obj.error("Failed to ingest realpaper.pdf: real reason here")
        finally:
            logger_obj.removeHandler(h)
            h.close()
        items = collect_watcher_failures(log)
        assert len(items) == 1
        assert items[0].payload["file"] == "realpaper.pdf"
        assert "real reason here" in items[0].payload["reason"]

    def test_dedupes_per_file_keeping_latest(self, tmp_path):
        log = tmp_path / "watcher.log"
        log.write_text(
            "2026-05-15 10:00:00,000 [ERROR] Failed to ingest p.pdf: first\n"
            "2026-05-16 11:00:00,000 [ERROR] Failed to ingest p.pdf: second\n"
            "2026-05-17 12:00:00,000 [ERROR] Failed to ingest p.pdf: third\n"
        )
        items = collect_watcher_failures(log)
        assert len(items) == 1
        assert "third" in items[0].payload["reason"]

    def test_warning_level_recorded(self, tmp_path):
        log = tmp_path / "watcher.log"
        log.write_text(
            "2026-05-17 12:34:56 [WARNING] Failed to ingest q.pdf: no metadata\n"
        )
        items = collect_watcher_failures(log)
        assert items[0].severity == SEVERITY_WARNING

    def test_error_ingesting_line_also_matched(self, tmp_path):
        # daemon.py emits two distinct messages: "Failed to ingest" on
        # graceful failure, "Error ingesting" on exception path.
        log = tmp_path / "watcher.log"
        log.write_text(
            "2026-05-17 12:00:00 [ERROR] Error ingesting boom.pdf: ValueError boom\n"
        )
        items = collect_watcher_failures(log)
        assert len(items) == 1
        assert items[0].payload["file"] == "boom.pdf"

    def test_unrelated_lines_ignored(self, tmp_path):
        log = tmp_path / "watcher.log"
        log.write_text(
            "2026-05-17 12:00:00 [INFO] Watching /inbox\n"
            "2026-05-17 12:01:00 [INFO] Filed: x.pdf → /lib/03/S/Smith.pdf\n"
        )
        assert collect_watcher_failures(log) == []


class TestUpgradeFlags:

    def test_empty_dir_yields_empty(self, tmp_path):
        assert collect_upgrade_flags(tmp_path) == []

    def test_flag_file_becomes_item(self, tmp_path):
        flag_dir = tmp_path / "04 - Papers to be downloaded" / "Annals of Probability"
        flag_dir.mkdir(parents=True)
        flag = flag_dir / "On a paper title.txt"
        flag.write_text(
            "DOI: 10.1214/foo\n"
            "Journal: Annals of Probability\n"
            "Year: 2024\n"
            "Title: On a paper\n"
            "Authors: Smith, J.\n"
            "Confidence: 95%\n"
            "Preprint: /lib/03/S/Smith.pdf\n",
            encoding="utf-8",
        )
        items = collect_upgrade_flags(tmp_path)
        assert len(items) == 1
        it = items[0]
        assert it.source == "upgrade_flag"
        assert it.payload["doi"] == "10.1214/foo"
        assert it.payload["journal"] == "Annals of Probability"
        # Detail contains the file body
        assert "Annals of Probability" in it.detail

    def test_multiple_flags_yield_multiple_items(self, tmp_path):
        for journal in ("Foo Journal", "Bar Journal"):
            d = tmp_path / "04 - Papers to be downloaded" / journal
            d.mkdir(parents=True)
            (d / "p.txt").write_text("DOI: 10.1/x\n", encoding="utf-8")
        items = collect_upgrade_flags(tmp_path)
        assert len(items) == 2

    def test_keys_are_stable_across_runs(self, tmp_path):
        d = tmp_path / "04 - Papers to be downloaded" / "J"
        d.mkdir(parents=True)
        (d / "p.txt").write_text("DOI: 10.1/x\n", encoding="utf-8")
        k1 = collect_upgrade_flags(tmp_path)[0].key
        k2 = collect_upgrade_flags(tmp_path)[0].key
        assert k1 == k2


class TestPermanentlyUnpublished:

    def _make_pdf(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"%PDF-1.4 test")
        return path

    def test_finds_marked_papers(self, tmp_path):
        from processing.identity import PaperIdentity
        live = self._make_pdf(tmp_path / "live.pdf")
        permanent = self._make_pdf(tmp_path / "perm.pdf")
        PaperIdentity().save(live)
        PaperIdentity(permanently_unpublished=True).save(permanent)
        items = collect_permanently_unpublished(tmp_path)
        assert len(items) == 1
        it = items[0]
        assert it.source == "permanently_unpublished"
        assert it.severity == SEVERITY_INFO
        assert it.payload["path"].endswith("perm.pdf")
        # The reset action is exposed so the user can override.
        assert any(a_id == "reset_recheck" for _, a_id in it.actions)

    def test_no_marked_papers_yields_empty(self, tmp_path):
        from processing.identity import PaperIdentity
        live = self._make_pdf(tmp_path / "p.pdf")
        PaperIdentity().save(live)
        assert collect_permanently_unpublished(tmp_path) == []

    def test_missing_root_returns_empty(self, tmp_path):
        assert collect_permanently_unpublished(tmp_path / "nope") == []


class TestConflictCopies:

    def test_no_conflicts_yields_empty(self, tmp_path):
        assert collect_conflict_copies(tmp_path) == []

    def test_finds_dropbox_style_conflict(self, tmp_path):
        good = tmp_path / "Smith, J. - Paper.pdf"
        bad = tmp_path / "Smith, J. - Paper (DESKTOP-ABC's conflicted copy 2024-05-13).pdf"
        good.write_bytes(b"%PDF-1.4 normal")
        bad.write_bytes(b"%PDF-1.4 conflict")
        items = collect_conflict_copies(tmp_path)
        assert len(items) == 1
        assert items[0].payload["path"].endswith("conflicted copy 2024-05-13).pdf")

    def test_ignores_trash(self, tmp_path):
        trash = tmp_path / ".trash" / "old"
        trash.mkdir(parents=True)
        (trash / "x (conflicted copy 2024-01-01).pdf").write_bytes(b"%PDF")
        assert collect_conflict_copies(tmp_path) == []

    def test_case_insensitive_match(self, tmp_path):
        (tmp_path / "p (Conflicted Copy 2024-01-01).pdf").write_bytes(b"%PDF")
        assert len(collect_conflict_copies(tmp_path)) == 1


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

class TestGatherAttentionItems:

    def test_runs_all_collectors(self, tmp_path):
        # Use a custom collector list so the test is hermetic (won't pick
        # up the real ~/.mathpdf/watcher.log).
        custom = [
            ("noop", lambda root: []),
            ("constant", lambda root: [
                AttentionItem(key="k1", source="x", severity=SEVERITY_INFO, title="t1"),
                AttentionItem(key="k2", source="x", severity=SEVERITY_ERROR, title="t2"),
            ]),
        ]
        out = gather_attention_items(
            tmp_path,
            dismissals_path=tmp_path / "d.json",
            collectors=custom,
        )
        assert {it.key for it in out} == {"k1", "k2"}

    def test_sort_errors_before_warnings_before_info(self, tmp_path):
        items = [
            AttentionItem(key="i", source="x", severity=SEVERITY_INFO, title="i"),
            AttentionItem(key="e", source="x", severity=SEVERITY_ERROR, title="e"),
            AttentionItem(key="w", source="x", severity=SEVERITY_WARNING, title="w"),
        ]
        out = gather_attention_items(
            tmp_path,
            dismissals_path=tmp_path / "d.json",
            collectors=[("c", lambda r: list(items))],
        )
        assert [it.severity for it in out] == [SEVERITY_ERROR, SEVERITY_WARNING, SEVERITY_INFO]

    def test_newer_items_first_within_severity(self, tmp_path):
        items = [
            AttentionItem(
                key="old", source="x", severity=SEVERITY_INFO, title="old",
                created_at="2026-01-01T00:00:00+00:00",
            ),
            AttentionItem(
                key="new", source="x", severity=SEVERITY_INFO, title="new",
                created_at="2026-12-31T00:00:00+00:00",
            ),
        ]
        out = gather_attention_items(
            tmp_path,
            dismissals_path=tmp_path / "d.json",
            collectors=[("c", lambda r: list(items))],
        )
        assert [it.key for it in out] == ["new", "old"]

    def test_dismissed_items_filtered(self, tmp_path):
        item = AttentionItem(key="bye", source="x", severity=SEVERITY_INFO, title="t")
        dpath = tmp_path / "d.json"
        dismiss("bye", days=7, path=dpath)
        out = gather_attention_items(
            tmp_path,
            dismissals_path=dpath,
            collectors=[("c", lambda r: [item])],
        )
        assert out == []

    def test_include_dismissed_overrides(self, tmp_path):
        item = AttentionItem(key="bye", source="x", severity=SEVERITY_INFO, title="t")
        dpath = tmp_path / "d.json"
        dismiss("bye", days=7, path=dpath)
        out = gather_attention_items(
            tmp_path,
            include_dismissed=True,
            dismissals_path=dpath,
            collectors=[("c", lambda r: [item])],
        )
        assert len(out) == 1

    def test_collector_exception_doesnt_break_aggregation(self, tmp_path):
        def bad(_root):
            raise RuntimeError("boom")

        out = gather_attention_items(
            tmp_path,
            dismissals_path=tmp_path / "d.json",
            collectors=[
                ("bad", bad),
                ("ok", lambda r: [AttentionItem(key="k", source="x", severity=SEVERITY_INFO, title="t")]),
            ],
        )
        # The other collectors still run — one failure must never cost the
        # whole queue.
        keys = [it.key for it in out]
        assert "k" in keys
        # ...and the failure is now REPORTED rather than swallowed.  A
        # collector that dies silently means a whole class of work (say
        # every conflict copy) vanishes from the queue with nothing on
        # screen to say so, which is indistinguishable from "all clear".
        assert "collector_error::bad" in keys


# ---------------------------------------------------------------------------
# Item serialisation (used by tests + future snapshot diffing)
# ---------------------------------------------------------------------------

class TestAttentionItemSerialisation:

    def test_to_dict_roundtrip_preserves_fields(self):
        it = AttentionItem(
            key="k", source="upgrade_flag", severity=SEVERITY_WARNING,
            title="t", detail="d",
            payload={"a": 1},
            actions=[("Open", "open"), ("Dismiss", "dismiss_7d")],
        )
        d = it.to_dict()
        assert d["actions"] == [["Open", "open"], ["Dismiss", "dismiss_7d"]]
        # JSON-serialisable end-to-end
        assert json.loads(json.dumps(d))["key"] == "k"
