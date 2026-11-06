"""Undoing an upgrade takes the published copy off the shelf, safely.

The owner's ruling of 2026-11-06. An upgrade files the published PDF as a
COPY of a temporary download and moves the preprint to the trash. The app
deletes the download by design, so undo saw "a copy whose original is
gone" and refused: the preprint came back and the published copy stayed,
two versions on the shelf and a partial undo for ever.

That refusal is the rule that stands between the project and the paper it
lost (Abraham, Delmas, Weibel), so it was not loosened. An upgrade now
MARKS its copy (:meth:`UndoLog.mark_copy_from_download`) with what it
replaced and a fingerprint, and only such a copy is retired -- to the
trash, never deleted -- and only while it is what was filed and the
preprint is back. Otherwise it stays, and undo says why.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest
from hypothesis import given, strategies as hst

from processing.identity import enable_sidecar_mirror
from processing.undo_log import UndoLog, _sha256, copy_undo_blocker, logged_move


@pytest.fixture
def lib(tmp_path, monkeypatch):
    enable_sidecar_mirror(tmp_path)
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    return tmp_path


def _write(path: Path, body: bytes = b"%PDF-1.4 x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path


def _upgrade(lib, *, mark=True, move_preprint=True):
    """What upgrade_paper does to the disk and the log, without a network."""
    log = UndoLog(log_dir=lib / ".operation_log")
    tx = log.begin_transaction("Upgrade 1 paper")
    pre = _write(lib / "03 - Working papers/S/2020/Smith, J. - Games.pdf", b"%PDF-1.4 preprint")
    dl = _write(lib.parent / "dl" / "published.pdf", b"%PDF-1.4 published")
    pub = lib / "01 - Published papers/S/Smith, J. - Games.pdf"
    pub.parent.mkdir(parents=True, exist_ok=True)
    log.record_copy(dl, pub)
    pub.write_bytes(dl.read_bytes())
    if mark:
        assert log.mark_copy_from_download(pub, replaces=pre)
    if move_preprint:
        trash = lib / ".trash/upgraded_preprints" / pre.name
        trash.parent.mkdir(parents=True, exist_ok=True)
        logged_move(pre, trash, undo_log=log)
    log.commit()
    dl.unlink()
    return log, tx, pre, pub


def test_undo_takes_the_published_copy_off_and_brings_the_preprint_back(lib):
    log, tx, pre, pub = _upgrade(lib)
    dry = log.undo_transaction(tx, dry_run=True)
    assert all(r["ok"] for r in dry), dry
    assert any("WOULD RETIRE COPY" in r["action"] for r in dry)
    live = log.undo_transaction(tx)
    assert all(r["ok"] for r in live), live
    assert pre.read_bytes() == b"%PDF-1.4 preprint" and not pub.exists()
    assert (lib / ".trash/undone_copies" / pub.name).read_bytes() == b"%PDF-1.4 published"


def test_the_mark_survives_in_the_stored_entry(lib):
    log, tx, pre, pub = _upgrade(lib)
    ops = json.loads((log.log_dir / f"{tx}.json").read_text())["operations"]
    (copy,) = [o for o in ops if o["type"] == "copy"]
    assert copy["download"]["replaces"] == str(pre)
    assert len(copy["download"]["sha256"]) == 64


def test_a_preprint_kept_on_the_shelf_counts_as_back(lib):
    """The >20% larger preprint is never trashed; nothing has to return."""
    log, tx, pre, pub = _upgrade(lib, move_preprint=False)
    assert log.undo_transaction(tx)[0]["ok"] is True
    assert pre.exists() and not pub.exists()


def test_an_unmarked_copy_whose_original_is_gone_is_still_refused(lib):
    """THE RULE that cost a paper. Pin it: the pilot of June is unmarked,
    and so is any upgrade that crashed before its commit."""
    log, tx, pre, pub = _upgrade(lib, mark=False)
    rows = log.undo_transaction(tx)
    assert any(r["action"].startswith("REFUSED: the original is gone") for r in rows)
    assert pub.exists()


def test_a_published_copy_changed_since_stays(lib):
    log, tx, pre, pub = _upgrade(lib)
    pub.write_bytes(b"%PDF-1.4 annotated by hand")
    dry, live = log.undo_transaction(tx, dry_run=True), log.undo_transaction(tx)
    for rows in (dry, live):
        assert any(r["action"].startswith("KEPT: the published copy has changed")
                   for r in rows), rows
    assert pub.read_bytes() == b"%PDF-1.4 annotated by hand"
    assert pre.exists(), "the preprint still comes back"


def test_a_preprint_that_cannot_come_back_keeps_the_published_copy(lib):
    """A stranger at its place: the shelf must not lose its last version."""
    log, tx, pre, pub = _upgrade(lib)
    pre.write_bytes(b"%PDF-1.4 a different paper")
    dry, live = log.undo_transaction(tx, dry_run=True), log.undo_transaction(tx)
    for rows in (dry, live):
        assert any(r["action"].startswith("KEPT: the preprint it replaced")
                   for r in rows), rows
    assert pub.exists()
    assert pre.read_bytes() == b"%PDF-1.4 a different paper"


def test_a_retry_finishes_once_the_way_is_clear(lib):
    log, tx, pre, pub = _upgrade(lib)
    pre.write_bytes(b"%PDF-1.4 a different paper")
    log.undo_transaction(tx)
    pre.unlink()
    rows = log.undo_transaction(tx)
    assert all(r["ok"] for r in rows), rows
    assert pre.read_bytes() == b"%PDF-1.4 preprint" and not pub.exists()


def test_the_preview_says_what_the_press_does_when_the_preprint_is_gone_from_the_trash(lib):
    log, tx, pre, pub = _upgrade(lib)
    (lib / ".trash/upgraded_preprints" / pre.name).unlink()
    dry, live = log.undo_transaction(tx, dry_run=True), log.undo_transaction(tx)
    assert [r["ok"] for r in dry] == [r["ok"] for r in live], (dry, live)
    assert pub.exists(), "nothing of the paper may leave the shelf"


@pytest.mark.parametrize("blocked", [0, 1])
def test_a_transaction_with_two_upgrades_treats_each_on_its_own(lib, blocked):
    """A stranger at ONE preprint's place holds back that paper's copy, and
    only that one, whichever comes first in the batch."""
    log = UndoLog(log_dir=lib / ".operation_log")
    tx = log.begin_transaction("Upgrade 2 papers")
    pairs = []
    for n in ("A", "B"):
        pre = _write(lib / f"03 - Working papers/S/2020/{n}.pdf", b"%PDF " + n.encode())
        dl = _write(lib.parent / "dl" / f"{n}.pdf", b"%PDF published " + n.encode())
        pub = lib / f"01 - Published papers/S/{n}.pdf"
        pub.parent.mkdir(parents=True, exist_ok=True)
        log.record_copy(dl, pub)
        pub.write_bytes(dl.read_bytes())
        assert log.mark_copy_from_download(pub, replaces=pre)
        trash = lib / ".trash/upgraded_preprints" / pre.name
        trash.parent.mkdir(parents=True, exist_ok=True)
        logged_move(pre, trash, undo_log=log)
        dl.unlink()
        pairs.append((pre, pub))
    log.commit()
    pairs[blocked][0].write_bytes(b"%PDF a stranger")
    log.undo_transaction(tx)
    assert pairs[blocked][1].exists(), "its published copy stays"
    free_pre, free_pub = pairs[1 - blocked]
    assert not free_pub.exists() and free_pre.exists(), "the other is undone all the same"


def test_a_kept_preprint_moved_away_by_hand_keeps_the_published_copy(lib):
    """Nothing in this change moved it, so nothing brings it back."""
    log, tx, pre, pub = _upgrade(lib, move_preprint=False)
    pre.rename(pre.with_name("Elsewhere.pdf"))
    dry, live = log.undo_transaction(tx, dry_run=True), log.undo_transaction(tx)
    for rows in (dry, live):
        assert rows[0]["action"].startswith("KEPT: the preprint it replaced"), rows
    assert pub.exists()


def test_the_preview_of_a_retry_does_not_count_on_a_move_already_undone(lib):
    """The first press brought the preprint home and kept the changed copy.
    The copy is put right and the preprint moved away by hand: the retry
    will not bring it back again, and its preview must say so."""
    log, tx, pre, pub = _upgrade(lib)
    body = pub.read_bytes()
    pub.write_bytes(b"%PDF-1.4 annotated by hand")
    log.undo_transaction(tx)
    assert pre.exists()
    pub.write_bytes(body)
    pre.rename(pre.with_name("Elsewhere.pdf"))
    dry = log.undo_transaction(tx, dry_run=True)
    assert any(r["action"].startswith("KEPT: the preprint it replaced") for r in dry), dry
    assert pub.exists()


def test_marking_finds_the_latest_copy_to_that_place_or_says_no(lib):
    log = UndoLog(log_dir=lib / ".operation_log")
    log.begin_transaction("t")
    a = _write(lib / "a.pdf")
    log.record_copy(lib / "x.pdf", a)
    log.record_copy(lib / "y.pdf", a)
    assert log.mark_copy_from_download(a, replaces=lib / "p.pdf") is True
    first, second = log._current_tx["operations"]
    assert "download" not in first and second["download"]["sha256"] == _sha256(a)
    assert log.mark_copy_from_download(lib / "b.pdf", replaces=lib / "p.pdf") is False
    log.discard()


def test_marking_needs_an_open_transaction(lib):
    with pytest.raises(RuntimeError):
        UndoLog(log_dir=lib / ".operation_log").mark_copy_from_download(
            lib / "a.pdf", replaces=lib / "p.pdf")


@given(hst.booleans(), hst.booleans(), hst.booleans(), hst.booleans())
def test_property_the_blocker_decides_as_the_ruling_says(src_there, marked, same, back):
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        src, dst = Path(d) / "s.pdf", Path(d) / "d.pdf"
        dst.write_bytes(b"filed")
        if src_there:
            src.write_bytes(b"original")
        mark = {"sha256": _sha256(dst) if same else "0" * 64} if marked else None
        why = copy_undo_blocker(dst, src, mark, back)
        retire = src_there or (marked and same and back)
        assert (why == "") is retire


def test_a_copy_already_gone_is_skipped_whatever_the_mark(tmp_path):
    for mark, back in itertools.product((None, {"sha256": "x"}), (False, True)):
        assert copy_undo_blocker(tmp_path / "d", tmp_path / "s", mark, back).startswith("SKIP")
