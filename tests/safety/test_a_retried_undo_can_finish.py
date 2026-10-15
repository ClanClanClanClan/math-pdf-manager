"""A partly undone transaction, retried, finishes -- and never reverses twice.

Measured 2026-10-15 on a synthetic library: two logged moves, one source
blocked, Undo, the block cleared, Undo again -> both files home, and the
transaction still "PARTLY UNDONE". The retry attempted every operation
again; the one that had already come back now said "SKIP: file gone"
(``ok: False``), so "done" was out of reach for good. The comment in
``undo_log`` said a partial undo "remembers which operations already came
back". It did not.

Re-attempting was also unsafe, not just stuck: a reversal done twice moves
back a file that was deliberately filed again since, or writes the old
value of a record field over one the owner set since.

Now ``reversed_ops`` holds the index of every operation that came back; a
retry (and its preview) attempts only the rest, and the transaction is done
when every operation has come back on some press. And the Activity page
can see a partial undo at all: ``list_transactions`` dropped
``partial_undo``, so the row never said PARTLY UNDONE.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from processing.identity import PaperIdentity
from processing.undo_log import UndoLog, logged_move


@pytest.fixture
def log(tmp_path, monkeypatch):
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path / "lib"))
    return UndoLog(log_dir=tmp_path / "log")


def _stored(log, tx) -> dict:
    return json.loads((log.log_dir / f"{tx}.json").read_text())


def _write(p: Path, body: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body.encode())
    return p


def _two_moves(log, tmp_path):
    a = _write(tmp_path / "a.pdf", "AAA")
    c = _write(tmp_path / "c.pdf", "CCC")
    tx = log.begin_transaction("batch")
    logged_move(a, tmp_path / "m" / "a.pdf", undo_log=log)
    logged_move(c, tmp_path / "m" / "c.pdf", undo_log=log)
    log.commit()
    return tx, a, c


# --------------------------------------------------------------------------
# pathologies
# --------------------------------------------------------------------------

def test_the_measured_case_finishes_on_the_retry(log, tmp_path):
    tx, a, c = _two_moves(log, tmp_path)
    blocker = _write(a, "BLOCKER")

    first = log.undo_transaction(tx)
    assert [(r["op"], r["ok"]) for r in first] == [(1, True), (0, False)]
    stored = _stored(log, tx)
    assert stored["undone"] is False
    assert stored["reversed_ops"] == [1]

    blocker.unlink()
    second = log.undo_transaction(tx)

    assert [(r["op"], r["ok"]) for r in second] == [(0, True)], (
        "the retry attempted an operation that had already come back")
    assert a.read_bytes() == b"AAA" and c.read_bytes() == b"CCC"
    stored = _stored(log, tx)
    assert stored["undone"] is True, "every file is home, yet not done"
    assert "partial_undo" not in stored and "reversed_ops" not in stored
    with pytest.raises(ValueError, match="already been undone"):
        log.undo_transaction(tx)


def test_a_retry_leaves_alone_a_file_filed_again_since(log, tmp_path):
    """The double undo: after the first press brought ``a`` home, the owner
    filed it again under the same name. Retrying must not take it back."""
    tx, a, c = _two_moves(log, tmp_path)
    squatter = _write(c, "SOMEONE ELSE")
    log.undo_transaction(tx)                     # a home, c refused
    assert a.read_bytes() == b"AAA"
    shutil.move(str(a), str(tmp_path / "m" / "a.pdf"))   # filed again
    squatter.unlink()

    rows = log.undo_transaction(tx)

    assert [r["op"] for r in rows] == [1]
    assert (tmp_path / "m" / "a.pdf").read_bytes() == b"AAA", (
        "a reversal was done twice: the re-filed paper was moved back")
    assert not a.exists()
    assert c.read_bytes() == b"CCC"
    assert _stored(log, tx)["undone"] is True


def test_a_retry_does_not_restore_a_record_field_twice(log, tmp_path):
    """The first press put the DOI back; the owner then corrected it. A
    second restore would write the old value over his correction."""
    paper = _write(tmp_path / "p.pdf", "%PDF p")
    ident = PaperIdentity.load(paper)
    ident.doi = "10.1/old"
    ident.save(paper)
    other = _write(tmp_path / "o.pdf", "OOO")

    tx = log.begin_transaction("edit + move")
    logged_move(other, tmp_path / "m" / "o.pdf", undo_log=log)
    ident.doi = "10.1/new"
    ident.save(paper, undo_log=log)
    log.commit()
    squatter = _write(other, "SOMEONE ELSE")

    log.undo_transaction(tx)
    assert PaperIdentity.load(paper).doi == "10.1/old"
    ident = PaperIdentity.load(paper)
    ident.doi = "10.1/corrected"
    ident.save(paper)
    squatter.unlink()

    rows = log.undo_transaction(tx)

    assert [r["op"] for r in rows] == [0]
    assert PaperIdentity.load(paper).doi == "10.1/corrected"
    assert _stored(log, tx)["undone"] is True


def test_the_preview_of_a_retry_shows_only_what_is_left(log, tmp_path):
    tx, a, c = _two_moves(log, tmp_path)
    blocker = _write(a, "BLOCKER")
    log.undo_transaction(tx)
    blocker.unlink()

    dry = log.undo_transaction(tx, dry_run=True)
    live = log.undo_transaction(tx)

    assert [(r["op"], r["ok"]) for r in dry] == [(0, True)]
    assert [(r["op"], r["ok"]) for r in dry] == [(r["op"], r["ok"]) for r in live]
    assert dry[0]["action"].startswith("WOULD MOVE BACK")


def test_the_counts_add_up_over_every_press(log, tmp_path):
    papers = [_write(tmp_path / f"{n}.pdf", n) for n in "abc"]
    tx = log.begin_transaction("three")
    for p in papers:
        logged_move(p, tmp_path / "m" / p.name, undo_log=log)
    log.commit()
    blockers = [_write(papers[0], "X"), _write(papers[1], "Y")]

    log.undo_transaction(tx)
    assert _stored(log, tx)["partial_undo"]["reversed"] == 1
    blockers[0].unlink()
    log.undo_transaction(tx)
    partial = _stored(log, tx)["partial_undo"]
    assert partial["reversed"] == 2, "the second press forgot the first"
    assert len(partial["not_reversed"]) == 1
    assert partial["reversed"] + len(partial["not_reversed"]) == 3
    assert log.reversed_so_far(tx) == 2
    blockers[1].unlink()
    log.undo_transaction(tx)
    assert _stored(log, tx)["undone"] is True
    assert [p.read_bytes() for p in papers] == [b"a", b"b", b"c"]


def test_activity_sees_a_partial_undo(log, tmp_path):
    """``list_transactions`` is what the Activity page reads, and it copied
    ``undone`` alone: PARTLY UNDONE was never shown for a real entry."""
    tx, a, _c = _two_moves(log, tmp_path)
    blocker = _write(a, "BLOCKER")
    log.undo_transaction(tx)

    row, = log.list_transactions()
    assert row["undone"] is False
    assert row["partial_undo"]["reversed"] == 1
    assert row["partial_undo"]["not_reversed"][0].startswith("CANNOT UNDO")

    blocker.unlink()
    log.undo_transaction(tx)
    row, = log.list_transactions()
    assert row["undone"] is True and "partial_undo" not in row


def test_activity_sees_it_for_an_entry_missing_from_the_index(log, tmp_path):
    """The self-healing path (a record the index never got) as well."""
    tx, a, _c = _two_moves(log, tmp_path)
    _write(a, "BLOCKER")
    log.undo_transaction(tx)
    (log.log_dir / "index.jsonl").unlink()

    row, = log.list_transactions()
    assert row["id"] == tx and row["partial_undo"]["reversed"] == 1


def test_a_record_from_before_the_bookkeeping_is_retried_in_full(log, tmp_path):
    """A partial undo recorded before ``reversed_ops`` existed cannot say
    what came back; it is retried in full, as it always was. (The real log
    holds none, measured 2026-10-15.)"""
    tx, a, c = _two_moves(log, tmp_path)
    shutil.move(str(tmp_path / "m" / "c.pdf"), str(c))   # came back earlier
    stored = _stored(log, tx)
    stored["partial_undo"] = {"at": "x", "reversed": 1, "not_reversed": ["y"]}
    (log.log_dir / f"{tx}.json").write_text(json.dumps(stored))
    assert log.reversed_so_far(tx) == 0

    rows = log.undo_transaction(tx)

    assert [r["op"] for r in rows] == [1, 0]
    assert a.read_bytes() == b"AAA"


def test_a_kind_of_change_undo_does_not_know_is_refused_not_ignored(log, tmp_path):
    """It used to produce no row at all -- and so counted as come back."""
    tx = log.begin_transaction("future")
    log._append({"type": "teleport", "source": "/x", "destination": "/y"})
    log.commit()

    rows = log.undo_transaction(tx)

    assert [r["ok"] for r in rows] == [False]
    assert rows[0]["action"].startswith("CANNOT UNDO")
    assert _stored(log, tx)["undone"] is False


def test_an_empty_transaction_is_done_at_once(log):
    """0 of 0 came back is everything (the real log has such entries)."""
    tx = log.begin_transaction("Upgrade 1 papers to published")
    log.commit()
    assert log.undo_transaction(tx) == []
    assert _stored(log, tx)["undone"] is True


def test_a_preview_changes_no_bookkeeping(log, tmp_path):
    tx, a, _c = _two_moves(log, tmp_path)
    _write(a, "BLOCKER")
    log.undo_transaction(tx)
    before = (log.log_dir / f"{tx}.json").read_bytes()
    log.undo_transaction(tx, dry_run=True)
    assert (log.log_dir / f"{tx}.json").read_bytes() == before


# --------------------------------------------------------------------------
# the property
# --------------------------------------------------------------------------

#: What gets in the way of one operation's undo, and for how long:
#: none; blocked until press k (then cleared); blocked for good; its file
#: gone for good.
KINDS = ("move", "rename", "copy", "edit")


def _make(log, root: Path, i: int, kind: str):
    """Do one logged operation; return (block, unblock, home_ok)."""
    name = f"{i}-{kind}.pdf"
    body = f"%PDF {name}"
    if kind in ("move", "rename"):
        a = _write(root / "a" / name, body)
        b = root / "b" / name
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(a), str(b))
        (log.record_move if kind == "move" else log.record_rename)(a, b)

        def block():
            _write(a, "SQUATTER")

        def unblock():
            if a.exists() and a.read_bytes() == b"SQUATTER":
                a.unlink()

        def gone():
            b.unlink()

        return block, unblock, gone, lambda: a.read_bytes() == body.encode()
    if kind == "copy":
        src = _write(root / "s" / name, body)
        dst = root / "lib" / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        log.record_copy(src, dst)
        aside = root / "aside" / name

        def block():
            aside.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(aside))

        def unblock():
            if aside.exists():
                shutil.move(str(aside), str(src))

        def gone():
            dst.unlink()

        return block, unblock, gone, lambda: not dst.exists()
    paper = _write(root / "e" / name, body)
    ident = PaperIdentity.load(paper)
    ident.doi = f"10.1/{i}-old"
    ident.save(paper)
    ident.doi = f"10.1/{i}-new"
    ident.save(paper, undo_log=log)
    rec = paper.with_suffix(".meta.json")
    aside = root / "aside" / rec.name

    def block():
        aside.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(rec), str(aside))

    def unblock():
        if aside.exists():
            shutil.move(str(aside), str(rec))

    return block, unblock, block, (
        lambda: rec.exists() and PaperIdentity.load(paper).doi == f"10.1/{i}-old")


@settings(max_examples=80, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(plan=st.lists(st.tuples(st.sampled_from(KINDS),
                               st.sampled_from(("free", "until", "forever",
                                                "gone")),
                               st.integers(1, 3)),
                     min_size=1, max_size=6),
       presses=st.integers(1, 4))
def test_presses_reverse_each_change_once_and_finish_when_nothing_blocks(
        tmp_path_factory, monkeypatch, plan, presses):
    root = tmp_path_factory.mktemp("retry")
    monkeypatch.setenv("MATH_LIBRARY", str(root / "lib"))
    log = UndoLog(log_dir=root / "log")
    tx = log.begin_transaction("mixed")
    made = [_make(log, root, i, kind) for i, (kind, _, _) in enumerate(plan)]
    log.commit()
    for (block, _unblock, gone, _home), (_k, obstacle, _until) in zip(made, plan):
        if obstacle in ("until", "forever"):
            block()
        elif obstacle == "gone":
            gone()

    ever_ok: list[int] = []
    for press in range(1, presses + 1):
        dry = log.undo_transaction(tx, dry_run=True)
        live = log.undo_transaction(tx)
        assert [r["op"] for r in dry] == [r["op"] for r in live], (
            "the preview attempted different operations")
        # Of every kind of change -- restoring record fields too, which
        # always said it would -- the preview says what the press then does.
        assert [(r["op"], r["ok"]) for r in dry] == [
            (r["op"], r["ok"]) for r in live], "the preview disagreed"
        assert not set(r["op"] for r in live) & set(ever_ok), (
            "an operation that had come back was attempted again")
        ever_ok += [r["op"] for r in live if r["ok"]]
        stored = _stored(log, tx)
        assert stored["undone"] is (len(ever_ok) == len(plan))
        if not stored["undone"]:
            assert stored["partial_undo"]["reversed"] == len(ever_ok)
            assert stored["reversed_ops"] == sorted(ever_ok)
            assert log.list_transactions()[0]["partial_undo"] == stored["partial_undo"]
        else:
            break
        for (_b, unblock, _g, _h), (_k, obstacle, until) in zip(made, plan):
            if obstacle == "until" and until <= press:
                unblock()

    for i, ((_b, _u, _g, home), (_k, obstacle, _until)) in enumerate(zip(made, plan)):
        if i in ever_ok:
            assert home(), f"op {i} said it came back but did not"
    # Once only the permanent obstacles remain, one more press finishes
    # everything else -- and "done" means exactly "nothing permanent".
    for (_b, unblock, _g, _h), (_k, obstacle, _u) in zip(made, plan):
        if obstacle == "until":
            unblock()
    if not _stored(log, tx)["undone"]:
        live = log.undo_transaction(tx)
        ever_ok += [r["op"] for r in live if r["ok"]]
    stuck = {i for i, (_k, obstacle, _u) in enumerate(plan)
             if obstacle in ("forever", "gone")}
    assert set(range(len(plan))) - set(ever_ok) == stuck
    assert _stored(log, tx)["undone"] is (not stuck)
