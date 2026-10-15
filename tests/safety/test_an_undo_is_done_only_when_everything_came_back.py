"""An undo is DONE only when every change came back -- one rule, three readers.

Found 2026-10-15 by pressing ↶ Undo on an upgrade in a test.  Each undo
result row carries ``ok``.  The cockpit counted ``ok``; the undo log
decided "fully undone" with a second rule -- the row's TEXT starting with
SKIP or CANNOT.  "REFUSED: the original is gone" (undoing the copy that
filed a downloaded PDF) is ``ok: False`` and starts with neither, so the
page said "Undone in part ... so you can retry" while the log marked the
transaction undone and Activity showed ALREADY UNDONE, with no retry.

And the preview of that same undo promised "WOULD DELETE COPY": the dry
run asked only whether the copy was there, not whether the live run would
refuse it.  Both now ask :func:`copy_undo_blocker` / :func:`restore_blocker`.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from processing.undo_log import UndoLog, copy_undo_blocker


@pytest.fixture
def log(tmp_path):
    return UndoLog(log_dir=tmp_path / "log")


def _stored(log, tx) -> dict:
    return json.loads((log.log_dir / f"{tx}.json").read_text())


def _copy(log, tmp_path, name, *, original_survives=True):
    src = tmp_path / "src" / name
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(b"%PDF " + name.encode())
    dst = tmp_path / "lib" / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    log.record_copy(src, dst)
    if not original_survives:
        src.unlink()
    return src, dst


def _move(log, tmp_path, name):
    a = tmp_path / "a" / name
    a.parent.mkdir(parents=True, exist_ok=True)
    a.write_bytes(b"%PDF " + name.encode())
    b = tmp_path / "b" / name
    b.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(a), str(b))
    log.record_move(a, b)
    return a, b


# --------------------------------------------------------------------------
# pathologies
# --------------------------------------------------------------------------

def test_a_refused_copy_leaves_the_transaction_retryable(log, tmp_path, monkeypatch):
    """The upgrade shape: the filed PDF's original (the download) is gone."""
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path / "lib"))
    tx = log.begin_transaction("Cockpit upgrade: x")
    _src, dst = _copy(log, tmp_path, "published.pdf", original_survives=False)
    a, _b = _move(log, tmp_path, "preprint.pdf")
    log.commit()

    rows = log.undo_transaction(tx)

    assert [r["ok"] for r in rows] == [True, False]
    assert a.exists() and dst.exists(), "the only version was touched"
    stored = _stored(log, tx)
    assert stored["undone"] is False, "a refused copy was counted as undone"
    assert stored["partial_undo"]["reversed"] == 1
    assert stored["partial_undo"]["not_reversed"][0].startswith("REFUSED")


def test_a_failed_record_restore_leaves_the_transaction_retryable(
        log, tmp_path, monkeypatch):
    pdf = tmp_path / "p.pdf"
    pdf.write_bytes(b"%PDF")
    from processing.identity import PaperIdentity
    ident = PaperIdentity.load(pdf)
    ident.doi = "10.1/x"
    ident.save(pdf)
    tx = log.begin_transaction("edit")
    log.record_sidecar_edit(pdf, {"doi": ["10.1/x", "10.1/y"]})
    log.commit()

    def broken(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr("processing.identity.patch_record", broken)
    rows = log.undo_transaction(tx)

    assert [r["ok"] for r in rows] == [False]
    assert rows[0]["action"].startswith("FAILED")
    assert _stored(log, tx)["undone"] is False


def test_the_preview_of_a_refused_copy_says_it_will_be_refused(log, tmp_path):
    tx = log.begin_transaction("x")
    _copy(log, tmp_path, "published.pdf", original_survives=False)
    log.commit()

    dry = log.undo_transaction(tx, dry_run=True)
    live = log.undo_transaction(tx)

    assert [r["ok"] for r in dry] == [r["ok"] for r in live] == [False]
    assert dry[0]["action"] == live[0]["action"]


def test_the_blocker_reads_the_disk_not_the_log(tmp_path):
    src, dst = tmp_path / "s.pdf", tmp_path / "d.pdf"
    assert copy_undo_blocker(dst, src).startswith("SKIP")      # neither
    dst.write_bytes(b"x")
    assert copy_undo_blocker(dst, src).startswith("REFUSED")   # orphan copy
    src.write_bytes(b"x")
    assert copy_undo_blocker(dst, src) == ""                   # undoable
    dst.unlink()
    assert copy_undo_blocker(dst, src).startswith("SKIP")      # copy gone


# --------------------------------------------------------------------------
# the property
# --------------------------------------------------------------------------

#: What can have happened to one logged operation by the time of the undo.
KINDS = ("move", "move_gone", "move_occupied",
         "copy", "copy_orphan", "copy_gone")


def _build(log, root: Path, kinds: list[str]) -> str:
    tx = log.begin_transaction("mixed")
    for i, kind in enumerate(kinds):
        name = f"{i}-{kind}.pdf"
        if kind.startswith("move"):
            a, b = _move(log, root, name)
            if kind == "move_gone":
                b.unlink()
            elif kind == "move_occupied":
                a.write_bytes(b"someone else")
        else:
            src, dst = _copy(log, root, name,
                             original_survives=kind != "copy_orphan")
            if kind == "copy_gone":
                dst.unlink()
    log.commit()
    return tx


@settings(max_examples=60, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(kinds=st.lists(st.sampled_from(KINDS), min_size=1, max_size=6))
def test_done_means_every_row_came_back_and_the_preview_agrees(
        tmp_path_factory, monkeypatch, kinds):
    root = tmp_path_factory.mktemp("undo")
    monkeypatch.setenv("MATH_LIBRARY", str(root / "lib"))
    log = UndoLog(log_dir=root / "log")
    tx = _build(log, root, kinds)

    dry = log.undo_transaction(tx, dry_run=True)
    live = log.undo_transaction(tx)
    stored = _stored(log, tx)

    assert [r["ok"] for r in dry] == [r["ok"] for r in live], (
        "the preview disagreed with the undo")
    oks = [r["ok"] for r in live]
    assert stored["undone"] is all(oks)
    if not all(oks):
        assert stored["partial_undo"]["reversed"] == sum(oks)
        assert stored["partial_undo"]["not_reversed"] == [
            r["action"] for r in live if not r["ok"]]
    expected_ok = [k in ("move", "copy") for k in reversed(kinds)]
    assert oks == expected_ok
    # Nothing is ever deleted: every logged file is somewhere on disk or
    # retired to the trash.
    for i, kind in enumerate(kinds):
        if kind in ("move_gone", "copy_gone"):
            continue
        name = f"{i}-{kind}.pdf"
        assert list(root.rglob(name)), f"{name} vanished"


def test_the_old_text_rule_is_blind_to_a_refusal(log, tmp_path, monkeypatch):
    """Why the property needed ``ok``: the row text of a refused copy is
    invisible to the SKIP/CANNOT rule the log used to apply."""
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path / "lib"))
    tx = _build(log, tmp_path, ["copy_orphan"])
    rows = log.undo_transaction(tx)
    old_rule_failed = [r for r in rows
                       if str(r["action"]).startswith(("SKIP", "CANNOT"))]
    assert old_rule_failed == [], "control: the old rule misses REFUSED"
    assert _stored(log, tx)["undone"] is False
