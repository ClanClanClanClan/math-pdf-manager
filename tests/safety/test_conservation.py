"""Conservation laws: what must be TRUE afterwards, whatever the code did.

Every other test here checks a path — that a helper behaves when called.
That is how the watcher's hard-delete survived: `_retire_source()` had
four tests proving it retires correctly, and nothing proved the daemon
CALLS it. Re-arming `path.unlink()` at the call site left the full suite,
the pre-commit gate and the golden corpus all green.

A conservation law does not care which function ran. It drives the real
entry point with the SHIPPED config and asserts an invariant over the
bytes on disk. You cannot satisfy it by keeping a helper correct.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _find_bytes(root: Path, digest: str) -> list:
    return [p for p in root.rglob("*.pdf")
            if p.is_file() and _sha(p) == digest]


@pytest.fixture()
def lib(tmp_path):
    from processing.identity import enable_sidecar_mirror
    root = tmp_path / "lib"
    for d in ("01 - Published papers", "03 - Working papers", "12 - To be sorted"):
        (root / d).mkdir(parents=True)
    enable_sidecar_mirror(root)
    return root


class TestAnIngestedOriginalIsNeverDestroyed:
    """THE law. If the inbox copy is gone, its bytes are in the trash.

    Note what this deliberately does NOT say: "the bytes exist somewhere".
    That weaker form PASSES under the hard-delete mutant, because ingest
    has already copied the paper into the library — so the bytes survive
    while the owner's original is destroyed and unrecoverable. The
    trash-locality is the whole point.
    """

    def test_the_original_is_recoverable_after_a_watcher_ingest(self, lib, tmp_path):
        from watcher.config import WatcherConfig
        from watcher.daemon import PDFHandler

        inbox = tmp_path / "inbox"
        inbox.mkdir()
        src = inbox / "arrival.pdf"
        _write_minimal_pdf(src, title="A paper", author="Smith, J.")
        digest = _sha(src)

        cfg = WatcherConfig(inbox_dir=inbox, library_root=lib,
                            log_dir=tmp_path / "logs",
                            delete_source=True, settle_seconds=0.0)
        handler = PDFHandler(cfg)
        handler._ingest(src)

        if src.exists():
            return                      # nothing was consumed; law vacuous
        trashed = _find_bytes(lib / ".trash", digest)
        assert trashed, (
            "the inbox original disappeared and no copy of its bytes is in "
            ".trash — the owner's only copy of this paper is now whatever "
            "the pipeline decided to write, with no way back")

    def test_the_law_is_not_vacuously_satisfied(self, lib, tmp_path):
        """Guard against the law passing because nothing ever runs."""
        from watcher.config import WatcherConfig
        from watcher.daemon import PDFHandler
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        src = inbox / "arrival.pdf"
        _write_minimal_pdf(src, title="A paper", author="Smith, J.")
        cfg = WatcherConfig(inbox_dir=inbox, library_root=lib,
                            log_dir=tmp_path / "logs",
                            delete_source=True, settle_seconds=0.0)
        PDFHandler(cfg)._ingest(src)
        filed = list(lib.rglob("*.pdf"))
        assert filed, "the ingest did nothing at all, so the law proved nothing"


class TestTheShippedConfigIsWhatShips:
    """delete_source is False in the dataclass default and true in
    config/watcher.yaml. Every test that builds a WatcherConfig by hand
    tests a configuration the owner does not run."""

    def test_the_real_config_file_is_what_the_daemon_loads(self):
        import yaml
        cfg = Path(__file__).resolve().parents[2] / "config" / "watcher.yaml"
        raw = yaml.safe_load(cfg.read_text())
        assert raw.get("delete_source") is True, (
            "if this has changed, the conservation law above must be "
            "re-read: it exists because the shipped config consumes the "
            "owner's original")
