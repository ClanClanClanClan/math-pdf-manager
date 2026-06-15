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

class TestAudit9Fixes:
    """Round-9 audit fixes: contested->review, deepest status dir,
    stale-suggestion clearing, explicit-standard not overridden."""

    def test_contested_match_is_suggested_not_dropped(self):
        # A title hitting two topics' strong keywords ties -> low
        # confidence, but it must still surface as a review suggestion
        # (audit-9 F), not silently go to standard.
        from processing.publication_topic_router import resolve_topic
        d = resolve_topic("Stackelberg games and BSDEs",
                          "Stackelberg leader follower BSDE backward stochastic")
        assert not d.auto
        assert d.needs_review
        assert d.suggested_code in ("07a", "07d")

    def test_explicit_standard_not_auto_overridden(self, lib):
        # User explicitly chose standard (topic=None, auto_topic=False)
        # for a paper whose text screams BSDE -> must stay standard.
        from processing.ingest import ingest_paper
        src = lib / "_in" / "drop.pdf"
        src.parent.mkdir()
        _write_minimal_pdf(src, title="Reflected BSDEs and backward stochastic",
                           author="Smith, J.")
        result = ingest_paper(
            src, library_root=lib, status="published", dry_run=False,
            canonical_override="Smith, J. - Reflected BSDEs",
            topic=None, auto_topic=False,
        )
        assert result["success"]
        # Lands in the standard tree, NOT 07a.
        assert "07a" not in Path(result["destination"]).relative_to(lib).parts[0]
        assert "auto_topic" not in result

    def test_reingest_clears_stale_suggestion(self, tmp_path):
        # A paper that first got a medium-confidence suggestion, then
        # re-ingests with a confident classification, must not keep the
        # stale suggestion (audit-9 D).
        from processing.identity import PaperIdentity, enable_sidecar_mirror, sidecar_path
        for d in ["07a - BSDEs", "01 - Published papers"]:
            (tmp_path / d).mkdir(parents=True, exist_ok=True)
        enable_sidecar_mirror(tmp_path)
        # Place a paper in 07a with a stale suggestion still set.
        sub = tmp_path / "07a - BSDEs" / "01 - Published papers" / "S"
        sub.mkdir(parents=True)
        pdf = sub / "Smith, J. - Reflected BSDEs.pdf"
        from synth_library import _write_minimal_pdf as _w
        _w(pdf, title="Reflected BSDEs", author="Smith, J.")
        ident = PaperIdentity()
        ident.topic_suggestion = "07b"   # stale
        ident.topic_confidence = 0.5
        ident.save(pdf)
        # Re-ingest in place (idempotent) with a confident topic.
        from processing.ingest import ingest_paper
        ingest_paper(pdf, library_root=tmp_path, status="published",
                     dry_run=False, topic="07a",
                     canonical_override="Smith, J. - Reflected BSDEs")
        reloaded = PaperIdentity.load(pdf)
        assert reloaded.topic_suggestion == ""

    def test_accept_preserves_working_year_subdir(self, tmp_path):
        # accept_topic_suggestion must keep the alpha AND year subdirs
        # (audit-9 C: deepest status dir + correct tail).
        from processing.identity import PaperIdentity, enable_sidecar_mirror
        from processing.publication_topic_router import accept_topic_suggestion
        for d in ["07a - BSDEs", "03 - Working papers"]:
            (tmp_path / d).mkdir(parents=True, exist_ok=True)
        enable_sidecar_mirror(tmp_path)
        sub = tmp_path / "03 - Working papers" / "S" / "2020"
        sub.mkdir(parents=True)
        pdf = sub / "Smith, J. - X.pdf"
        pdf.write_bytes(b"%PDF")
        ident = PaperIdentity(); ident.topic_suggestion = "07a"; ident.save(pdf)
        ok, msg = accept_topic_suggestion(pdf, tmp_path)
        assert ok, msg
        moved = (tmp_path / "07a - BSDEs" / "03 - Working papers" / "S" / "2020"
                 / "Smith, J. - X.pdf")
        assert moved.exists(), msg


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
