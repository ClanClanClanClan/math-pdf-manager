"""Routing fixes surfaced by the live trial (the 3-paper upgrade that
renamed papers the user had curated).

Covers:
  * filename preservation on upgrade (canonical_override authoritative
    for both name AND alpha-subdir)
  * collision = skip, never silent overwrite
  * ETH credential resolution from env + secure store
  * undo-log default location is the library, not the Scripts repo
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402


# ---------------------------------------------------------------------------
# Filename + alpha-subdir preservation via canonical_override
# ---------------------------------------------------------------------------

@pytest.fixture
def lib(tmp_path):
    for d in ["01 - Published papers", "02 - Unpublished papers",
              "03 - Working papers"]:
        (tmp_path / d).mkdir(parents=True)
    return tmp_path


class TestCanonicalOverridePreservesRouting:

    def test_override_name_kept_verbatim(self, lib):
        from processing.ingest import ingest_paper
        src = lib / "_in" / "drop.pdf"
        src.parent.mkdir()
        # Published metadata says a DIFFERENT author initial than the
        # curated name -- the override must win.
        _write_minimal_pdf(src, title="Recursive equilibrium", author="Cao, Dan")
        result = ingest_paper(
            src, library_root=lib, status="published", dry_run=False,
            canonical_override="Cao, C. - Recursive equilibrium in Krusell and Smith (1998)",
        )
        assert result["success"]
        dest = Path(result["destination"])
        # Name preserved exactly (the user's "C.", not metadata's "Dan")
        assert dest.name == "Cao, C. - Recursive equilibrium in Krusell and Smith (1998).pdf"

    def test_override_drives_alpha_subdir(self, lib):
        """A curated name with a nobiliary particle must file under the
        letter implied by the NAME, not by the published metadata."""
        from processing.ingest import ingest_paper
        src = lib / "_in" / "drop.pdf"
        src.parent.mkdir()
        _write_minimal_pdf(src, title="Some title", author="Karoui, Nicole")
        result = ingest_paper(
            src, library_root=lib, status="published", dry_run=False,
            canonical_override="el Karoui, N. - Some title",
        )
        assert result["success"]
        dest = Path(result["destination"])
        # "el Karoui" strips the particle -> files under K
        assert "/01 - Published papers/K/" in str(dest)


# ---------------------------------------------------------------------------
# Collision = skip, never clobber
# ---------------------------------------------------------------------------

class TestCollisionDoesNotClobber:

    def test_existing_destination_is_not_overwritten(self, lib):
        from processing.ingest import ingest_paper
        # File the first paper.
        src1 = lib / "_in" / "a.pdf"
        src1.parent.mkdir()
        _write_minimal_pdf(src1, title="Title", author="Smith, J.")
        r1 = ingest_paper(
            src1, library_root=lib, status="published", dry_run=False,
            canonical_override="Smith, J. - Title",
        )
        assert r1["success"]
        dest = Path(r1["destination"])
        original_bytes = dest.read_bytes()

        # File a DIFFERENT paper that resolves to the same canonical name.
        src2 = lib / "_in" / "b.pdf"
        _write_minimal_pdf(src2, title="Different content here", author="Smith, J.")
        r2 = ingest_paper(
            src2, library_root=lib, status="published", dry_run=False,
            canonical_override="Smith, J. - Title",
        )
        # Second ingest must NOT succeed-overwrite; the existing file is intact.
        assert dest.read_bytes() == original_bytes
        assert any("already exists" in a for a in r2.get("actions", [])) or not r2["success"]

    def test_identical_reingest_is_idempotent(self, lib):
        """Re-ingesting the SAME paper (identical bytes) to the same
        destination is a no-op, not a refused collision."""
        from processing.ingest import ingest_paper
        import shutil
        src = lib / "_in" / "a.pdf"
        src.parent.mkdir()
        _write_minimal_pdf(src, title="Idem", author="Smith, J.")
        r1 = ingest_paper(
            src, library_root=lib, status="published", dry_run=False,
            canonical_override="Smith, J. - Idem",
        )
        dest = Path(r1["destination"])
        # Copy the filed file back to a fresh inbox and re-ingest it.
        again = lib / "_in2" / "a.pdf"
        again.parent.mkdir()
        shutil.copy2(dest, again)
        r2 = ingest_paper(
            again, library_root=lib, status="published", dry_run=False,
            canonical_override="Smith, J. - Idem",
        )
        # Idempotent: no ERROR, destination unchanged.
        assert not any("ERROR" in a for a in r2.get("actions", []))
        assert any("identical content" in a for a in r2.get("actions", []))


# ---------------------------------------------------------------------------
# ETH credential resolution
# ---------------------------------------------------------------------------

class TestEthCredentialResolution:

    def test_explicit_args_win(self, monkeypatch):
        from downloader.eth_institutional import _resolve_eth_credentials
        u, p = _resolve_eth_credentials("alice", "secret")
        assert (u, p) == ("alice", "secret")

    def test_eth_env_vars(self, monkeypatch):
        from downloader.eth_institutional import _resolve_eth_credentials
        monkeypatch.setenv("ETH_USERNAME", "bob")
        monkeypatch.setenv("ETH_PASSWORD", "pw")
        monkeypatch.delenv("INSTITUTIONAL_USERNAME", raising=False)
        assert _resolve_eth_credentials() == ("bob", "pw")

    def test_institutional_env_fallback(self, monkeypatch):
        from downloader.eth_institutional import _resolve_eth_credentials
        monkeypatch.delenv("ETH_USERNAME", raising=False)
        monkeypatch.delenv("ETH_PASSWORD", raising=False)
        monkeypatch.setenv("INSTITUTIONAL_USERNAME", "carol")
        monkeypatch.setenv("INSTITUTIONAL_PASSWORD", "pw2")
        assert _resolve_eth_credentials() == ("carol", "pw2")

    def test_empty_when_nothing_configured(self, monkeypatch):
        from downloader import eth_institutional
        for v in ("ETH_USERNAME", "ETH_PASSWORD",
                  "INSTITUTIONAL_USERNAME", "INSTITUTIONAL_PASSWORD"):
            monkeypatch.delenv(v, raising=False)
        # Force the secure store to yield nothing
        monkeypatch.setattr(
            eth_institutional, "_resolve_eth_credentials",
            eth_institutional._resolve_eth_credentials,
        )
        # Patch the secure lookup to return None
        import sys as _sys
        import types as _types
        fake = _types.ModuleType("core.config.secure_config")
        fake.get_secure_credential = lambda k: None
        monkeypatch.setitem(_sys.modules, "core.config.secure_config", fake)
        u, p = eth_institutional._resolve_eth_credentials()
        assert u == "" and p == ""


# ---------------------------------------------------------------------------
# Undo-log location
# ---------------------------------------------------------------------------

class TestUndoLogLocation:

    def test_default_log_dir_under_library(self, monkeypatch, tmp_path):
        # Point the library root at tmp_path and confirm the default
        # log dir resolves under it (not the Scripts repo).
        import core.config_paths as cp
        monkeypatch.setattr(cp, "get_library_root", lambda: tmp_path)
        import importlib
        import processing.undo_log as ul
        importlib.reload(ul)
        try:
            assert ul._default_log_dir() == tmp_path / ".operation_log"
        finally:
            importlib.reload(ul)  # restore module-level LOG_DIR
