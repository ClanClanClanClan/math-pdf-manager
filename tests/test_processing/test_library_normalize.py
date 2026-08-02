"""Retroactive library-wide filename normalization (synthetic library)."""
from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402

from processing.library_normalize import (
    AUTHOR,
    BOTH,
    TITLE,
    apply_renames,
    propose_renames,
    scan,
)


@pytest.fixture
def lib(tmp_path):
    from processing.identity import enable_sidecar_mirror
    for d in ["01 - Published papers", "02 - Unpublished papers",
              "03 - Working papers"]:
        (tmp_path / d).mkdir(parents=True)
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _paper(lib, rel):
    """Create a filed PDF (with sidecar) named exactly ``rel``."""
    from processing.identity import PaperIdentity
    p = lib / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_pdf(p, title="t", author="A")
    PaperIdentity().save(p, recompute_hash=False)
    return p


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------
class TestPropose:

    def test_author_initial_spacing(self, lib):
        _paper(lib, "01 - Published papers/D/Dalang, R.C. - Stochastic heat.pdf")
        props, _ = propose_renames(lib)
        assert len(props) == 1
        p = props[0]
        assert p["kind"] == AUTHOR
        assert p["name"] == "Dalang, R. C. - Stochastic heat.pdf"

    def test_title_casing_from_vocab(self, lib):
        # Seed the vocabulary: "widgets" is an ordinary common word.
        from processing.title_vocab import decide
        decide(lib, "widgets", "common")
        _paper(lib, "01 - Published papers/S/Smith, J. - On Widgets today.pdf")
        props, _ = propose_renames(lib)
        assert len(props) == 1
        p = props[0]
        assert p["kind"] == TITLE
        assert "widgets" in p["name"]        # lowercased
        assert "Widgets" not in p["name"]

    def test_both_sides_change(self, lib):
        from processing.title_vocab import decide
        decide(lib, "widgets", "common")
        _paper(lib, "01 - Published papers/D/Dalang, R.C. - On Widgets now.pdf")
        props, _ = propose_renames(lib)
        assert props[0]["kind"] == BOTH

    def test_already_canonical_yields_nothing(self, lib):
        _paper(lib, "01 - Published papers/D/Dalang, R. C. - Stochastic heat.pdf")
        props, _ = propose_renames(lib)
        assert props == []

    def test_nfc_only_change_is_skipped(self, lib):
        # A composed vs decomposed "é" is invisible and FS-treacherous: the
        # sweep must never propose a rename whose only diff is NFD↔NFC.
        nfd = unicodedata.normalize("NFD", "Émery, M. - Résumé note.pdf")
        _paper(lib, f"03 - Working papers/E/{nfd}")
        props, _ = propose_renames(lib)
        for p in props:
            assert unicodedata.normalize("NFC", p["old_name"]) != \
                   unicodedata.normalize("NFC", p["name"])

    def test_limit_caps_the_walk(self, lib):
        for i in range(5):
            _paper(lib, f"01 - Published papers/D/Dalang, R.C. - Paper {i}.pdf")
        props, _ = propose_renames(lib, limit=2)
        assert len(props) <= 2

    def test_pending_words_surfaced(self, lib):
        # An unknown capitalized word is queued, not renamed away.
        _paper(lib, "01 - Published papers/S/Smith, J. - On Frobnication methods.pdf")
        _, pending = propose_renames(lib)
        assert any(w.lower() == "frobnication" for w in pending)


# --------------------------------------------------------------------------
# scan() summary
# --------------------------------------------------------------------------
class TestScan:

    def test_scan_is_read_only(self, lib):
        p = _paper(lib, "01 - Published papers/D/Dalang, R.C. - Heat.pdf")
        before = {q.name for q in (lib / "01 - Published papers/D").iterdir()}
        scan(lib)
        after = {q.name for q in (lib / "01 - Published papers/D").iterdir()}
        assert before == after
        assert p.exists()

    def test_scan_counts_by_kind(self, lib):
        _paper(lib, "01 - Published papers/D/Dalang, R.C. - Heat.pdf")
        _paper(lib, "01 - Published papers/K/Karatzas, I. - Clean title.pdf")
        s = scan(lib)
        assert s["total"] == 1
        assert s["by_kind"][AUTHOR] == 1


# --------------------------------------------------------------------------
# Apply — reversible, collision-safe, sidecar-carrying
# --------------------------------------------------------------------------
class TestApply:

    def test_dry_run_changes_nothing(self, lib):
        _paper(lib, "01 - Published papers/D/Dalang, R.C. - Heat.pdf")
        props, _ = propose_renames(lib)
        res = apply_renames(lib, props, dry_run=True)
        assert res["dry_run"] and res["would_rename"] == 1
        assert (lib / "01 - Published papers/D/Dalang, R.C. - Heat.pdf").exists()

    def test_apply_renames_and_carries_sidecar(self, lib):
        from processing.identity import PaperIdentity
        p = _paper(lib, "01 - Published papers/D/Dalang, R.C. - Heat.pdf")
        props, _ = propose_renames(lib)
        res = apply_renames(lib, props, dry_run=False)
        assert res["renamed"] == 1 and res["tx_id"]
        new = lib / "01 - Published papers/D/Dalang, R. C. - Heat.pdf"
        assert new.exists() and not p.exists()
        # Sidecar followed the rename (identity still loadable, not new).
        assert not PaperIdentity.load(new).is_new()

    def test_apply_is_reversible(self, lib):
        from processing.undo_log import UndoLog
        old = "01 - Published papers/D/Dalang, R.C. - Heat.pdf"
        _paper(lib, old)
        props, _ = propose_renames(lib)
        res = apply_renames(lib, props, dry_run=False)
        UndoLog(log_dir=lib / ".operation_log").undo_transaction(res["tx_id"])
        assert (lib / old).exists()
        assert not (lib / "01 - Published papers/D/Dalang, R. C. - Heat.pdf").exists()

    def test_collision_is_skipped_not_forced(self, lib):
        # Two files that canonicalise to the SAME name: keep the one already
        # there, skip (report) the other — never clobber.
        _paper(lib, "01 - Published papers/D/Dalang, R. C. - Heat.pdf")   # canonical
        _paper(lib, "01 - Published papers/D/Dalang, R.C. - Heat.pdf")    # -> same
        props, _ = propose_renames(lib)
        res = apply_renames(lib, props, dry_run=False)
        assert res["renamed"] == 0
        assert res["skipped"] and res["skipped"][0]["reason"] == "target exists"
        # Both original files still present (nothing destroyed).
        assert (lib / "01 - Published papers/D/Dalang, R. C. - Heat.pdf").exists()
        assert (lib / "01 - Published papers/D/Dalang, R.C. - Heat.pdf").exists()

    def test_apply_queues_pending_words(self, lib):
        from processing.title_vocab import load_vocab
        _paper(lib, "01 - Published papers/D/Dalang, R.C. - Heat.pdf")
        props, pending = propose_renames(lib)
        apply_renames(lib, props, dry_run=False, pending_words=pending)
        vocab = load_vocab(lib)
        # Any surfaced pending word is now queued for review.
        if pending:
            assert set(pending) & set(vocab["pending"])

    def test_apply_empty_selection_no_tx(self, lib):
        res = apply_renames(lib, [], dry_run=False)
        assert res["renamed"] == 0 and res["tx_id"] is None


class TestApplyRenameRobustness:
    """A real 6,186-file batch aborted partway on an over-long name.

    ``Path.exists()`` RAISES ``ENAMETOOLONG`` rather than returning False,
    so spacing the initials of a 13-author paper past the 255-byte limit
    killed the loop.  The transaction's ``finally`` still committed what
    had been done (nothing was left half-renamed), but the remaining
    files were never attempted.
    """

    def test_over_long_target_is_skipped_not_fatal(self, tmp_path):
        from processing.library_normalize import apply_renames
        src = tmp_path / "Doe, J.A. - Short.pdf"
        src.write_bytes(b"%PDF-1.4\n")
        long_name = "Doe, J. A. - " + ("x" * 300) + ".pdf"
        out = apply_renames(
            tmp_path,
            [{"old": src.name, "new": long_name, "name": long_name,
              "old_name": src.name, "kind": "author"}],
            dry_run=False,
        )
        assert out["renamed"] == 0
        assert out["skipped"] and out["skipped"][0]["reason"] == "name too long"
        assert src.exists()                      # untouched, not lost

    def test_batch_continues_past_an_unusable_entry(self, tmp_path):
        # The whole point: one bad row must not cost the other renames.
        from processing.library_normalize import apply_renames
        good = tmp_path / "Roe, R.B. - Fine.pdf"
        good.write_bytes(b"%PDF-1.4\n")
        bad = tmp_path / "Doe, J.A. - Bad.pdf"
        bad.write_bytes(b"%PDF-1.4\n")
        out = apply_renames(
            tmp_path,
            [
                {"old": bad.name, "new": "Doe, J. A. - " + "x" * 300 + ".pdf",
                 "name": "x", "old_name": bad.name, "kind": "author"},
                {"old": good.name, "new": "Roe, R. B. - Fine.pdf",
                 "name": "Roe, R. B. - Fine.pdf", "old_name": good.name,
                 "kind": "author"},
            ],
            dry_run=False,
        )
        assert out["renamed"] == 1
        assert (tmp_path / "Roe, R. B. - Fine.pdf").exists()


class TestCaseOnlyRename:
    """macOS/APFS is case-insensitive, so a rename that only changes
    capitalisation has a "destination that already exists" — and it is the
    SOURCE.  Comparing paths as strings called every such rename a clobber:
    771 first-word capitalisations were refused in one batch, all reported
    as "target exists".  The guard exists to stop one paper overwriting
    ANOTHER, so it must ask the filesystem, not the string.
    """

    def test_case_only_rename_is_performed(self, tmp_path):
        from processing.undo_log import UndoLog, logged_rename
        src = tmp_path / "space-time calculus.pdf"
        src.write_bytes(b"%PDF-1.4\n")
        log = UndoLog(log_dir=tmp_path / ".log")
        log.begin_transaction("case-only")
        logged_rename(src, tmp_path / "Space-time calculus.pdf", undo_log=log)
        log.commit()
        assert [p.name for p in tmp_path.glob("*.pdf")] == \
            ["Space-time calculus.pdf"]

    def test_a_real_clobber_is_still_refused(self, tmp_path):
        from processing.undo_log import logged_rename
        a = tmp_path / "one.pdf"
        a.write_bytes(b"A")
        b = tmp_path / "two.pdf"
        b.write_bytes(b"B")
        with pytest.raises(FileExistsError):
            logged_rename(a, b)
        assert b.read_bytes() == b"B"        # untouched

    def test_apply_renames_performs_a_case_only_change(self, tmp_path):
        from processing.library_normalize import apply_renames
        src = tmp_path / "Doe, J. - space-time methods.pdf"
        src.write_bytes(b"%PDF-1.4\n")
        out = apply_renames(
            tmp_path,
            [{"old": src.name, "new": "Doe, J. - Space-time methods.pdf",
              "name": "Doe, J. - Space-time methods.pdf",
              "old_name": src.name, "kind": "title"}],
            dry_run=False,
        )
        assert out["renamed"] == 1, out["skipped"]
        assert (tmp_path / "Doe, J. - Space-time methods.pdf").exists()
