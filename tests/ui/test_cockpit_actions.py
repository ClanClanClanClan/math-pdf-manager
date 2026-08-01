"""Tests for ``src/ui/cockpit_actions.py`` -- the Phase 5 helper module.

These cover the helpers without spawning real processes or hitting the
network:
* download_doi_to_inbox -- input validation, downloader patched out
* watcher_status / start_watcher / stop_watcher -- launchctl mocked
* run_publication_check -- subprocess.run mocked, stdout parsed
* list_download_flags / mark_flag_done -- real filesystem under tmp_path
* load/save_cockpit_config + WatcherConfig.save round-trip
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ui.cockpit_actions import (
    DOIDownloadResult,
    MaintenanceRunResult,
    WATCHER_LABEL,
    download_doi_to_inbox,
    list_download_flags,
    load_cockpit_config,
    mark_flag_done,
    run_publication_check,
    save_cockpit_config,
    start_watcher,
    stop_watcher,
    watcher_status,
)


# ---------------------------------------------------------------------------
# DOI download
# ---------------------------------------------------------------------------

class TestDownloadDOIToInbox:

    def test_empty_doi_rejected(self, tmp_path):
        result = download_doi_to_inbox("", tmp_path)
        assert not result.ok
        assert "empty" in result.message

    def test_whitespace_doi_rejected(self, tmp_path):
        assert not download_doi_to_inbox("   ", tmp_path).ok

    def test_non_doi_string_rejected(self, tmp_path):
        # No slash -> not a DOI
        result = download_doi_to_inbox("notadoi", tmp_path)
        assert not result.ok
        assert "not a DOI" in result.message

    def test_url_prefix_stripped(self, tmp_path):
        """DOIs pasted from the address bar should still work."""
        with patch("downloader.doi_downloader.DOIDownloader") as Downloader:
            instance = Downloader.return_value
            instance.download.return_value = tmp_path / "fake.pdf"
            (tmp_path / "fake.pdf").write_bytes(b"%PDF")
            result = download_doi_to_inbox("https://doi.org/10.1/x", tmp_path)
        assert result.ok
        # The downloader saw the stripped DOI, not the URL
        call_doi = Downloader.return_value.download.call_args[0][0]
        assert call_doi == "10.1/x"

    def test_dx_doi_org_prefix_stripped(self, tmp_path):
        with patch("downloader.doi_downloader.DOIDownloader") as Downloader:
            Downloader.return_value.download.return_value = tmp_path / "f.pdf"
            (tmp_path / "f.pdf").write_bytes(b"%PDF")
            download_doi_to_inbox("http://dx.doi.org/10.1/y", tmp_path)
            assert Downloader.return_value.download.call_args[0][0] == "10.1/y"

    def test_downloader_returns_none_reported_as_failure(self, tmp_path):
        with patch("downloader.doi_downloader.DOIDownloader") as Downloader:
            Downloader.return_value.download.return_value = None
            result = download_doi_to_inbox("10.1/x", tmp_path)
        assert not result.ok
        assert "failed" in result.message.lower()

    def test_downloader_exception_caught(self, tmp_path):
        with patch("downloader.doi_downloader.DOIDownloader") as Downloader:
            Downloader.return_value.download.side_effect = RuntimeError("boom")
            result = download_doi_to_inbox("10.1/x", tmp_path)
        assert not result.ok
        assert "boom" in result.message

    def test_success_reports_pdf_path(self, tmp_path):
        fake = tmp_path / "fake.pdf"
        fake.write_bytes(b"%PDF")
        with patch("downloader.doi_downloader.DOIDownloader") as Downloader:
            Downloader.return_value.download.return_value = fake
            result = download_doi_to_inbox("10.1/x", tmp_path)
        assert result.ok
        assert result.pdf_path == str(fake)


# ---------------------------------------------------------------------------
# Watcher control (launchctl mocked)
# ---------------------------------------------------------------------------

def _mock_subprocess(stdout: str = "", stderr: str = "", returncode: int = 0):
    """Build a CompletedProcess-shaped mock."""
    m = MagicMock(spec=subprocess.CompletedProcess)
    m.stdout = stdout
    m.stderr = stderr
    m.returncode = returncode
    return m


class TestWatcherStatus:

    def test_print_parses_running_state(self):
        raw = "state = running\npid = 4242\n"
        with patch("ui.cockpit_actions._launchctl",
                   return_value=_mock_subprocess(stdout=raw, returncode=0)):
            out = watcher_status()
        assert out["running"] is True
        assert out["pid"] == 4242

    def test_print_failure_falls_back_to_list(self):
        list_out = f"4242\t0\t{WATCHER_LABEL}\n"
        # First call (print) fails, second call (list) succeeds.
        side = [
            _mock_subprocess(returncode=1, stderr="no such service"),
            _mock_subprocess(stdout=list_out, returncode=0),
        ]
        with patch("ui.cockpit_actions._launchctl", side_effect=side):
            out = watcher_status()
        assert out["running"] is True
        assert out["pid"] == 4242

    def test_not_loaded_reports_false(self):
        side = [
            _mock_subprocess(returncode=1),
            _mock_subprocess(stdout="", returncode=0),
        ]
        with patch("ui.cockpit_actions._launchctl", side_effect=side):
            out = watcher_status()
        assert out["running"] is False
        assert out["pid"] is None


class TestStartStopWatcher:

    def test_start_missing_plist_installs_it_first(self, tmp_path, monkeypatch):
        """A missing service is now SET UP, not reported back at him.

        It used to answer "plist not installed" — true, but the remedy was
        ``deploy/launchd/install.sh``, a shell script the cockpit user
        cannot run.  So automatic filing could never be switched on from
        the UI at all.  start_watcher now installs the agent into the
        user's own ~/Library/LaunchAgents and proceeds.
        """
        monkeypatch.setenv("HOME", str(tmp_path))
        ok, msg = start_watcher()
        # launchctl cannot really bootstrap under a synthetic HOME, so the
        # call still fails — but it must fail AFTER installing, and say
        # something other than "go run a script".
        assert not ok
        assert "not installed" not in msg
        plist = tmp_path / "Library" / "LaunchAgents" / f"{WATCHER_LABEL}.plist"
        assert plist.exists(), "the service should have been installed"

    def test_start_success(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        plist = tmp_path / "Library" / "LaunchAgents" / f"{WATCHER_LABEL}.plist"
        plist.parent.mkdir(parents=True)
        plist.write_text("<plist/>")
        with patch("ui.cockpit_actions._launchctl",
                   return_value=_mock_subprocess(returncode=0)):
            ok, msg = start_watcher()
        assert ok

    def test_start_already_loaded_is_success(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        plist = tmp_path / "Library" / "LaunchAgents" / f"{WATCHER_LABEL}.plist"
        plist.parent.mkdir(parents=True)
        plist.write_text("<plist/>")
        with patch("ui.cockpit_actions._launchctl",
                   return_value=_mock_subprocess(
                       returncode=1, stderr="service already loaded")):
            ok, msg = start_watcher()
        assert ok
        assert "already" in msg

    def test_stop_success(self):
        with patch("ui.cockpit_actions._launchctl",
                   return_value=_mock_subprocess(returncode=0)):
            ok, msg = stop_watcher()
        assert ok

    def test_stop_not_running_is_success(self):
        with patch("ui.cockpit_actions._launchctl",
                   return_value=_mock_subprocess(
                       returncode=1, stderr="could not find service")):
            ok, msg = stop_watcher()
        assert ok
        assert "not running" in msg


# ---------------------------------------------------------------------------
# Maintenance launcher
# ---------------------------------------------------------------------------

class TestRunPublicationCheck:

    def test_parses_report_path_from_stdout(self, tmp_path):
        report = tmp_path / "report.html"
        report.write_text("html")
        json_report = report.with_suffix(".json")
        json_report.write_text('{"foo": "bar"}')
        stdout = (
            "Running maintenance on /lib...\n"
            f"Report: {report}\n"
            "Summary: 0 published, 0 aging, 0 duplicates\n"
        )
        with patch("subprocess.run",
                   return_value=_mock_subprocess(stdout=stdout, returncode=0)):
            out = run_publication_check(tmp_path)
        assert out.ok
        assert out.report_path == str(report)
        assert out.summary == {"foo": "bar"}

    def test_nonzero_exit_reports_failure(self, tmp_path):
        with patch("subprocess.run",
                   return_value=_mock_subprocess(stderr="boom", returncode=2)):
            out = run_publication_check(tmp_path)
        assert not out.ok
        assert "boom" in out.message or "exit 2" in out.message

    def test_timeout_reported(self, tmp_path):
        with patch("subprocess.run",
                   side_effect=subprocess.TimeoutExpired("python", 5)):
            out = run_publication_check(tmp_path, timeout=5)
        assert not out.ok
        assert "timed out" in out.message

    def test_auto_apply_flag_passed(self, tmp_path):
        with patch("subprocess.run",
                   return_value=_mock_subprocess(returncode=0)) as run:
            run_publication_check(tmp_path, auto_apply_safe=True)
        cmd = run.call_args[0][0]
        assert "--auto-apply-safe" in cmd


# ---------------------------------------------------------------------------
# Download-flag browser
# ---------------------------------------------------------------------------

class TestListDownloadFlags:

    def test_empty_when_folder_missing(self, tmp_path):
        assert list_download_flags(tmp_path) == []

    def test_parses_doi_and_url(self, tmp_path):
        d = tmp_path / "04 - Papers to be downloaded" / "Annals of Probability"
        d.mkdir(parents=True)
        flag = d / "On the convergence of SGD.txt"
        flag.write_text(
            "DOI: 10.1214/foo\n"
            "URL: https://doi.org/10.1214/foo\n"
            "Title: On the convergence of SGD\n",
            encoding="utf-8",
        )
        items = list_download_flags(tmp_path)
        assert len(items) == 1
        it = items[0]
        assert it["doi"] == "10.1214/foo"
        assert it["url"] == "https://doi.org/10.1214/foo"
        assert it["journal"] == "Annals of Probability"


class TestMarkFlagDone:

    def test_moves_to_trash(self, tmp_path):
        flag = tmp_path / "04 - Papers to be downloaded" / "J" / "p.txt"
        flag.parent.mkdir(parents=True)
        flag.write_text("body")
        assert mark_flag_done(flag, tmp_path) is True
        assert not flag.exists()
        trashed = tmp_path / ".trash" / "done_flags" / "p.txt"
        assert trashed.exists()

    def test_collision_disambiguated(self, tmp_path):
        flag1 = tmp_path / "f.txt"
        flag1.write_text("one")
        mark_flag_done(flag1, tmp_path)
        flag2 = tmp_path / "f.txt"
        flag2.write_text("two")
        mark_flag_done(flag2, tmp_path)
        names = sorted(p.name for p in (tmp_path / ".trash" / "done_flags").iterdir())
        assert names == ["f (1).txt", "f.txt"]

    def test_missing_returns_false(self, tmp_path):
        assert mark_flag_done(tmp_path / "nope.txt", tmp_path) is False


# ---------------------------------------------------------------------------
# Config editor + WatcherConfig.save round trip
# ---------------------------------------------------------------------------

class TestConfigEditor:

    def test_load_returns_known_keys(self, monkeypatch):
        monkeypatch.delenv("UNPAYWALL_EMAIL", raising=False)
        out = load_cockpit_config()
        assert "library_root" in out
        assert "inbox_dir" in out
        assert out.get("unpaywall_email") == ""

    def test_unpaywall_email_from_env(self, monkeypatch):
        monkeypatch.setenv("UNPAYWALL_EMAIL", "user@example.com")
        out = load_cockpit_config()
        assert out["unpaywall_email"] == "user@example.com"

    def test_save_round_trip(self, tmp_path, monkeypatch):
        # Point watcher config at a temp YAML so we don't touch ~
        from watcher.config import WatcherConfig
        target = tmp_path / "watcher.yaml"
        # Make load() use a fresh blank config (no candidate exists yet)
        cfg = WatcherConfig()
        cfg.inbox_dir = tmp_path / "inbox"
        cfg.library_root = tmp_path / "lib"
        cfg.default_status = "unpublished"
        cfg.notifications = False
        path = cfg.save(target)
        assert path == target
        # And load it back
        reloaded = WatcherConfig.load(target)
        assert reloaded.default_status == "unpublished"
        assert reloaded.notifications is False
        assert str(reloaded.inbox_dir) == str(tmp_path / "inbox")

    def test_save_atomic_via_tmp(self, tmp_path):
        from watcher.config import WatcherConfig
        target = tmp_path / "watcher.yaml"
        cfg = WatcherConfig()
        cfg.save(target)
        # No leftover .tmp file
        leftovers = list(tmp_path.glob("*.tmp"))
        assert leftovers == []

    def test_save_cockpit_config_propagates_to_yaml(self, tmp_path, monkeypatch):
        from watcher.config import WatcherConfig
        # Force WatcherConfig.load() to start from defaults by pointing
        # the candidate list at a non-existent path.
        import watcher.config as wc
        monkeypatch.setattr(wc, "_CONFIG_PATHS", [tmp_path / "watcher.yaml"])
        # The new library_root must exist on disk before save so the
        # audit-5 validation gate doesn't reject it.
        newlib = tmp_path / "newlib"
        newlib.mkdir()
        ok, msg = save_cockpit_config({
            "library_root": str(newlib),
            "default_status": "published",
        })
        assert ok, msg
        reloaded = WatcherConfig.load(tmp_path / "watcher.yaml")
        assert reloaded.default_status == "published"
        assert reloaded.library_root == newlib

    def test_save_rejects_nonexistent_library_root(self, tmp_path, monkeypatch):
        """Audit-5 #8: a typo in the library_root field used to silently
        write garbage that broke every subsequent operation.  The
        validation gate now bounces the form before the save."""
        import watcher.config as wc
        monkeypatch.setattr(wc, "_CONFIG_PATHS", [tmp_path / "watcher.yaml"])
        ok, msg = save_cockpit_config({
            "library_root": "/this/path/does/not/exist",
        })
        assert not ok
        assert "does not exist" in msg

    def test_save_rejects_library_root_that_is_a_file(self, tmp_path, monkeypatch):
        import watcher.config as wc
        monkeypatch.setattr(wc, "_CONFIG_PATHS", [tmp_path / "watcher.yaml"])
        f = tmp_path / "not_a_dir.txt"
        f.write_text("oops")
        ok, msg = save_cockpit_config({"library_root": str(f)})
        assert not ok
        assert "not a directory" in msg

    def test_default_year_dynamic_preserved_round_trip(self, tmp_path):
        """Audit-6 #6: a YAML that says ``default_year: current`` must
        re-save as ``current``, not get silently frozen to the year
        the save happened in."""
        import yaml
        from watcher.config import WatcherConfig
        target = tmp_path / "watcher.yaml"
        target.write_text(yaml.safe_dump({"default_year": "current"}))
        cfg = WatcherConfig.load(target)
        assert cfg._default_year_is_dynamic is True
        cfg.save(target)
        re = yaml.safe_load(target.read_text())
        assert re["default_year"] == "current"

    def test_default_year_dynamic_survives_replace(self, tmp_path):
        """Audit-7 #7: ``dataclasses.replace`` must carry the dynamic
        flag.  Earlier code stored it as an instance attribute that
        replace() dropped, silently freezing the year on the new
        config's first save."""
        import dataclasses
        import yaml
        from watcher.config import WatcherConfig
        target = tmp_path / "watcher.yaml"
        target.write_text(yaml.safe_dump({"default_year": "current"}))
        cfg = WatcherConfig.load(target)
        assert cfg._default_year_is_dynamic is True
        # Replace clones the dataclass; the flag must come along
        cfg2 = dataclasses.replace(cfg, default_status="published")
        assert cfg2._default_year_is_dynamic is True

    def test_default_year_explicit_year_preserved_round_trip(self, tmp_path):
        """The inverse: an explicit year (``2023``) must NOT collapse
        to ``current`` even if it equals the current year on save."""
        import yaml
        from watcher.config import WatcherConfig
        from datetime import datetime
        target = tmp_path / "watcher.yaml"
        # Use this year explicitly (the worst case for the old logic).
        this_year = datetime.now().year
        target.write_text(yaml.safe_dump({"default_year": this_year}))
        cfg = WatcherConfig.load(target)
        assert cfg._default_year_is_dynamic is False
        cfg.save(target)
        re = yaml.safe_load(target.read_text())
        assert re["default_year"] == this_year

    def test_save_with_validation_off_for_migrations(self, tmp_path, monkeypatch):
        import watcher.config as wc
        monkeypatch.setattr(wc, "_CONFIG_PATHS", [tmp_path / "watcher.yaml"])
        ok, _ = save_cockpit_config(
            {"library_root": str(tmp_path / "not_yet")},
            require_existing_paths=False,
        )
        assert ok
