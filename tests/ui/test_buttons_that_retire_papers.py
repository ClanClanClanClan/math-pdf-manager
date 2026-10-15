"""Cockpit buttons that RETIRE papers to the trash, pressed for real.

Conflicts, Duplicates, same-paper variants and the download notes: each
moves a file into ``<library>/.trash/``.  Each test presses the button on
a synthetic library, checks where every file went, and presses ↶ Undo on
the Activity page to check the library comes back exactly.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from processing.duplicate_scan import find_exact_duplicates
from processing.identity import PaperIdentity
from processing.preprint_variants import VariantPair
from tests.ui.press_harness import (ck, presses, put, snapshot,  # noqa: F401
                                    transactions, undo_from_activity)

PAPER = "01 - Published papers/S/Smith, J. - A paper.pdf"
COPY = "01 - Published papers/S/Smith, J. - A paper (Dylan's conflicted copy 2026-01-02).pdf"


def _new_txs(lib, before):
    seen = {t["id"] for t in before}
    return [t for t in transactions(lib) if t["id"] not in seen]


def _record(pdf: Path, doi: str) -> None:
    ident = PaperIdentity.load(pdf)
    ident.doi = doi
    ident.save(pdf)


def _files(lib) -> set[str]:
    return set(snapshot(lib))


# --------------------------------------------------------------------------
# Conflicts, one at a time
# --------------------------------------------------------------------------

def _conflict_pair(lib, *, same: bool):
    canonical = put(lib, PAPER, b"%PDF-1.4\n% original\n%%EOF\n")
    copy = put(lib, COPY, b"%PDF-1.4\n% original\n%%EOF\n" if same
               else b"%PDF-1.4\n% the copy, edited on the other Mac\n%%EOF\n")
    _record(canonical, "10.1000/a")
    return canonical, copy


@presses("render_conflicts[kc_{}]")
def test_keep_canonical_retires_the_copy(ck):
    lib = ck.lib
    canonical, copy = _conflict_pair(lib, same=True)
    before, txs = snapshot(lib), transactions(lib)
    ck.st.press(f"kc_{copy}")

    assert ck.run("render_conflicts") == "rerun"

    assert canonical.exists() and not copy.exists()
    assert (lib / ".trash/conflict_copies" / copy.name).exists()
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


@presses("render_conflicts[kf_{}]")
def test_keep_conflict_puts_the_copy_in_the_originals_place(ck):
    lib = ck.lib
    canonical, copy = _conflict_pair(lib, same=False)
    copy_bytes = copy.read_bytes()
    before, txs = snapshot(lib), transactions(lib)
    ck.st.press(f"kf_{copy}")

    assert ck.run("render_conflicts") == "rerun"

    assert canonical.read_bytes() == copy_bytes, "the copy did not take the name"
    assert not copy.exists()
    retired = lib / ".trash/conflict_copies" / f"{canonical.stem}.old.pdf"
    assert retired.read_bytes() == b"%PDF-1.4\n% original\n%%EOF\n", (
        "the original was not kept in the trash")
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


@presses("render_conflicts[kb_{}]")
def test_keep_both_renames_the_copy_beside_the_original(ck):
    lib = ck.lib
    canonical, copy = _conflict_pair(lib, same=False)
    before, txs = snapshot(lib), transactions(lib)
    ck.st.press(f"kb_{copy}")

    assert ck.run("render_conflicts") == "rerun"

    v2 = canonical.with_name("Smith, J. - A paper-v2.pdf")
    assert canonical.exists() and v2.exists() and not copy.exists()
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


def test_a_conflict_that_vanished_is_reported_not_faked(ck):
    """The copy went (synced away) between the scan and the press."""
    lib = ck.lib
    canonical, copy = _conflict_pair(lib, same=True)
    rows = ck.module._conflicts_cached(str(lib))
    copy.unlink()
    ck.module._conflicts_cached = lambda _s: rows   # the page's stale list
    before, txs = snapshot(lib), transactions(lib)
    ck.st.press(f"kc_{copy}")

    assert ck.run("render_conflicts") == "done", "a failed resolve reran"

    assert snapshot(lib) == before
    errors = [a[0] for n, a, _ in ck.st.calls if n == "error"]
    assert any("conflict gone" in e for e in errors), errors
    assert _new_txs(lib, txs) == [], "an empty transaction was recorded"


# --------------------------------------------------------------------------
# Conflicts, in bulk
# --------------------------------------------------------------------------

def _two_conflicts(lib):
    a, a_copy = _conflict_pair(lib, same=True)              # suggested: keep canonical
    b_copy = put(lib, "03 - Working papers/T/Tan, X. - Lone (conflicted copy "
                      "2026-01-03).pdf")                    # suggested: keep conflict
    return a, a_copy, b_copy


@pytest.mark.parametrize("button, action", [
    ("conf_bulk_suggested", "suggested"),
    ("conf_bulk_kc", "keep_canonical"),
    ("conf_bulk_kf", "keep_conflict"),
])
def test_bulk_conflict_buttons_resolve_every_selected_copy(ck, button, action):
    lib = ck.lib
    a, a_copy, b_copy = _two_conflicts(lib)
    before, txs = snapshot(lib), transactions(lib)
    ck.st.session_state["conflicts_selected"] = {str(a_copy), str(b_copy)}
    ck.st.press(button)

    assert ck.run("render_conflicts") == "rerun"

    assert not a_copy.exists() and not b_copy.exists()
    lone = lib / "03 - Working papers/T/Tan, X. - Lone.pdf"
    if action == "keep_canonical":
        # the copy with no original also goes to the trash: nothing is lost
        assert a.exists() and not lone.exists()
        assert (lib / ".trash/conflict_copies" / b_copy.name).exists()
    else:
        assert lone.exists(), "the lone copy was not promoted to the name"
    tx, = _new_txs(lib, txs)
    assert tx["description"] == f"bulk conflict {action} (2)"
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


# The decorator checks each claimed site; the parametrised test above
# presses all three, so each also gets a dedicated claim here.
@presses("render_conflicts[conf_bulk_suggested]")
def test_apply_suggested_follows_each_conflicts_own_suggestion(ck):
    lib = ck.lib
    a, a_copy, b_copy = _two_conflicts(lib)
    before, txs = snapshot(lib), transactions(lib)
    ck.st.session_state["conflicts_selected"] = {str(a_copy), str(b_copy)}
    ck.st.press("conf_bulk_suggested")

    ck.run("render_conflicts")

    # identical copy -> the copy is retired; lone copy -> it takes the name
    assert a.read_bytes() == b"%PDF-1.4\n% original\n%%EOF\n"
    assert (lib / ".trash/conflict_copies" / a_copy.name).exists()
    assert (lib / "03 - Working papers/T/Tan, X. - Lone.pdf").exists()
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


@presses("render_conflicts[conf_bulk_kc]")
def test_keep_canonical_in_bulk_retires_every_copy(ck):
    lib = ck.lib
    a, a_copy, b_copy = _two_conflicts(lib)
    ck.st.session_state["conflicts_selected"] = {str(a_copy), str(b_copy)}
    before, txs = snapshot(lib), transactions(lib)
    ck.st.press("conf_bulk_kc")

    ck.run("render_conflicts")

    trashed = {p.name for p in (lib / ".trash/conflict_copies").iterdir()}
    assert trashed == {a_copy.name, b_copy.name}
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


@presses("render_conflicts[conf_bulk_kf]")
def test_keep_conflict_in_bulk_promotes_every_copy(ck):
    lib = ck.lib
    a, a_copy, b_copy = _two_conflicts(lib)
    ck.st.session_state["conflicts_selected"] = {str(a_copy), str(b_copy)}
    before, txs = snapshot(lib), transactions(lib)
    ck.st.press("conf_bulk_kf")

    ck.run("render_conflicts")

    assert (lib / "03 - Working papers/T/Tan, X. - Lone.pdf").exists()
    assert (lib / ".trash/conflict_copies" / f"{a.stem}.old.pdf").exists()
    assert not a_copy.exists()
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


def test_bulk_buttons_cannot_be_pressed_with_nothing_selected(ck):
    lib = ck.lib
    _two_conflicts(lib)
    before = snapshot(lib)
    ck.st.press("conf_bulk_suggested", "conf_bulk_kc", "conf_bulk_kf")

    ck.run("render_conflicts")

    assert snapshot(lib) == before
    assert len(ck.st.unused_presses()) == 3


# --------------------------------------------------------------------------
# Duplicates
# --------------------------------------------------------------------------

@presses("render_duplicates[dup_apply_auto]")
def test_trash_redundant_copies_keeps_one_of_each(ck):
    lib = ck.lib
    body = b"%PDF-1.4\n% one paper, filed twice\n%%EOF\n"
    keep = put(lib, "01 - Published papers/S/Smith, J. - Twice.pdf", body)
    extra = put(lib, "12 - To be sorted/01 - Published papers/twice.pdf", body)
    _record(keep, "10.1000/twice")
    groups = find_exact_duplicates(lib)
    assert [g.auto_safe for g in groups] == [True]
    before, txs = snapshot(lib), transactions(lib)
    ck.st.session_state["dup_groups"] = [g.to_dict() for g in groups]
    ck.st.press("dup_apply_auto")

    assert ck.run("render_duplicates") == "rerun"

    assert keep.exists() and not extra.exists()
    assert ck.st.session_state["dup_groups"] == [], "the list was not refreshed"
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


@presses("render_duplicates[dup_rev_apply_{}]")
def test_trash_the_others_keeps_the_copy_he_chose(ck):
    lib = ck.lib
    body = b"%PDF-1.4\n% one paper in two homes\n%%EOF\n"
    pub = put(lib, "01 - Published papers/S/Smith, J. - Home.pdf", body)
    book = put(lib, "05 - Books and lecture notes/S/Smith, J. - Home.pdf", body)
    groups = find_exact_duplicates(lib)
    assert [g.auto_safe for g in groups] == [False]
    g = groups[0]
    before, txs = snapshot(lib), transactions(lib)
    ck.st.session_state["dup_groups"] = [g.to_dict() for g in groups]
    # He keeps the BOOK copy, whatever the scan proposed.
    ck.st.set(**{f"dup_rev_keep_{g.sha256[:12]}": str(book)})
    ck.st.press(f"dup_rev_apply_{g.sha256[:12]}")

    assert ck.run("render_duplicates") == "rerun"

    assert book.exists() and not pub.exists()
    assert ck.st.session_state["dup_groups"] == []
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


# --------------------------------------------------------------------------
# Same-paper variants
# --------------------------------------------------------------------------

@presses("_render_variant_section[var_retire_{}]")
def test_retire_the_other_keeps_the_chosen_variant(ck):
    lib = ck.lib
    pre_rel = "02 - Unpublished papers/S/Smith, J. - Stopping.pdf"
    pub_rel = "01 - Published papers/S/Smith, J. - Stopping.pdf"
    pre = put(lib, pre_rel, b"%PDF-1.4\n% arXiv v2\n%%EOF\n")
    pub = put(lib, pub_rel, b"%PDF-1.4\n% journal version\n%%EOF\n")
    _record(pre, "10.1000/stop")
    _record(pub, "10.1000/stop")
    pair = VariantPair(preprint=pre_rel, published=pub_rel, tier="doi",
                       evidence={"doi": "10.1000/stop"})
    before, txs = snapshot(lib), transactions(lib)
    ck.st.session_state["variant_pairs"] = [pair.to_dict()]
    ck.st.set(**{f"var_keep_which_{pair.key()}": pub_rel})
    ck.st.press(f"var_retire_{pair.key()}")

    assert ck.run("_render_variant_section", lib) == "rerun"

    assert pub.exists() and not pre.exists()
    assert (lib / ".trash/upgraded_preprints" / pre.name).exists()
    assert ck.st.session_state["variant_pairs"] == []
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


# --------------------------------------------------------------------------
# To Download: the notes in 04/
# --------------------------------------------------------------------------

def _flag(lib) -> Path:
    return put(lib, "04 - Papers to be downloaded/Ann. Probab/Stopping.txt",
               b"DOI: 10.1000/stop\nTitle: Stopping\n")


@presses("render_to_download[flag_done_{}]")
def test_mark_done_moves_the_note_to_the_trash(ck):
    lib = ck.lib
    flag = _flag(lib)
    body = flag.read_bytes()
    ck.st.press(f"flag_done_{flag}")

    assert ck.run("render_to_download") == "rerun"

    assert not flag.exists()
    assert (lib / ".trash/done_flags/Stopping.txt").read_bytes() == body


@presses("render_to_download[flag_dl_{}]")
def test_download_now_files_the_paper_and_clears_the_note(ck, monkeypatch):
    import ui.cockpit_actions as actions
    lib = ck.lib
    flag = _flag(lib)
    inbox = ck.lib.parent / "inbox"
    got = []

    def fake_download(doi, inbox_dir):
        got.append(doi)
        Path(inbox_dir).mkdir(parents=True, exist_ok=True)
        out = Path(inbox_dir) / "stopping.pdf"
        out.write_bytes(b"%PDF-1.4\n% downloaded\n%%EOF\n")
        return actions.DOIDownloadResult(ok=True, message="ok", pdf_path=str(out))

    monkeypatch.setattr(actions, "download_doi_to_inbox", fake_download)
    from watcher.config import WatcherConfig
    monkeypatch.setattr(WatcherConfig, "load",
                        classmethod(lambda cls, *a, **k: cls(inbox_dir=inbox)))
    before, txs = snapshot(lib), transactions(lib)
    ck.st.press(f"flag_dl_{flag}")

    assert ck.run("render_to_download") == "rerun"

    assert got == ["10.1000/stop"]
    assert (inbox / "stopping.pdf").exists()
    assert not flag.exists()
    assert (lib / ".trash/done_flags/Stopping.txt").exists()
    # The note comes back; the download stays in the inbox for the filer.
    tx, = _new_txs(lib, txs)
    done = [e for e in ck.st.session_state["activity_log"]
            if e["action"] == "download.flag_done"]
    assert [e["tx_id"] for e in done] == [tx["id"]], (
        "Activity cannot say which click this entry was")
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before
    assert (inbox / "stopping.pdf").exists()


@presses("render_to_download[flag_done_{}]")
def test_mark_done_can_be_undone_from_activity(ck):
    """It could not: the note went to the trash by a bare shutil.move,
    outside the undo log (strict xfail until 2026-10-15)."""
    lib = ck.lib
    flag = _flag(lib)
    before, txs = snapshot(lib), transactions(lib)
    ck.st.press(f"flag_done_{flag}")
    ck.run("render_to_download")
    assert not flag.exists()
    tx, = _new_txs(lib, txs)
    assert ck.st.session_state["activity_log"][0]["tx_id"] == tx["id"]
    assert tx["description"] == "Marked a download note done: Stopping.txt"
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before
    (kind, msg), = ck.flashes()
    assert kind == "success", msg
    assert next(t for t in transactions(lib) if t["id"] == tx["id"])["undone"]


def test_mark_done_when_the_library_is_busy_changes_nothing(ck):
    from processing.locking import LibraryLock
    lib = ck.lib
    flag = _flag(lib)
    before, txs = snapshot(lib), transactions(lib)
    other = LibraryLock(lib)
    assert other.acquire(blocking=False)
    try:
        ck.st.press(f"flag_done_{flag}")
        assert ck.run("render_to_download") == "rerun"
    finally:
        other.release()
    assert snapshot(lib) == before and _new_txs(lib, txs) == []
    (kind, msg), = ck.flashes()
    assert kind == "error" and "Mark done" in msg, msg


def test_mark_done_on_a_note_already_gone_records_nothing(ck):
    """Two tabs: the note was marked done in the other. Nothing to retire,
    so no empty entry with a live Undo button lands in Activity."""
    lib = ck.lib
    flag = lib / "04 - Papers to be downloaded/Ann. Probab/Stopping.txt"
    txs = transactions(lib)
    assert ck.module._mark_note_done(flag, lib, "Marked a download note done") == ""
    assert _new_txs(lib, txs) == []
