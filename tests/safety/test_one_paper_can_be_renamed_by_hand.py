"""One paper can be renamed or moved by hand -- and its record goes with it.

Cockpit audit finding 17 (approved). Every rename in the cockpit was one
the machine proposed; a filed paper could be renamed or moved only in
Finder, which leaves its saved record (DOI, first-page text) behind under
the old name -- an orphan, the class finding 21 is about. The editor on
the Search page judges the request (``processing.owner_rename``) and
moves through ``apply_renames``, the one rename path, so the lock, the
undo log and the APFS case / NFD / long-name handling are inherited, not
re-implemented.
"""
from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

import pytest

from processing.library_scope import ARCHIVAL_COLLECTIONS
from processing.owner_rename import MAX_NAME_BYTES, check_owner_rename, target_rel

PUB = "01 - Published papers/S"


@pytest.fixture
def lib(tmp_path):
    from processing.identity import enable_sidecar_mirror
    enable_sidecar_mirror(tmp_path)
    (tmp_path / PUB).mkdir(parents=True)
    (tmp_path / "02 - Unpublished papers" / "S").mkdir(parents=True)
    return tmp_path


def _paper(lib, rel, body=b"%PDF-1.4 x"):
    p = lib / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body)
    return p


OLD = f"{PUB}/Smith, J. - A note on contol.pdf"


def _check(lib, new_rel, old_rel=OLD):
    return check_owner_rename(lib, old_rel, new_rel)


# --------------------------------------------------------------- the judge

def test_an_ordinary_rename_is_allowed(lib):
    _paper(lib, OLD)
    assert _check(lib, f"{PUB}/Smith, J. - A note on control.pdf") == ([], [])


@pytest.mark.parametrize("stem,needle", [
    ("", "empty"),
    ("   ", "empty"),
    (" Smith, J. - X", "space"),
    ("Smith, J. - X ", "space"),
    (".Smith", "dot"),
    ("Smith\x07 - X", "control"),
])
def test_names_that_cannot_be_a_paper(lib, stem, needle):
    _paper(lib, OLD)
    problems, _ = _check(lib, f"{PUB}/{stem}.pdf")
    assert any(needle in p for p in problems), problems


def test_a_colon_is_a_warning_not_a_refusal(lib):
    _paper(lib, OLD)
    problems, warnings = _check(lib, f"{PUB}/Smith, J. - Astérisque: one.pdf")
    assert problems == [] and any("slash" in w for w in warnings)


def test_the_limit_is_bytes_not_letters(lib):
    _paper(lib, OLD)
    stem = "é" * ((MAX_NAME_BYTES - 4) // 2 + 1)          # under 255 letters
    problems, _ = _check(lib, f"{PUB}/{stem}.pdf")
    assert any("bytes" in p for p in problems), problems
    ok = "e" * (MAX_NAME_BYTES - 4)
    assert _check(lib, f"{PUB}/{ok}.pdf")[0] == []


@pytest.mark.parametrize("which", ["source", "destination"])
def test_the_archival_collections_are_left_alone(lib, which):
    arch = ARCHIVAL_COLLECTIONS[0]
    (lib / arch).mkdir(parents=True, exist_ok=True)
    if which == "source":
        old = _paper(lib, f"{arch}/Vol 1.pdf").relative_to(lib)
        problems, _ = check_owner_rename(lib, str(old), f"{arch}/Vol one.pdf")
    else:
        _paper(lib, OLD)
        problems, _ = _check(lib, f"{arch}/Smith, J. - A note on control.pdf")
    assert any("out of scope" in p and "archival" in p for p in problems), problems


def test_staging_is_allowed_by_hand(lib):
    _paper(lib, OLD)
    (lib / "12 - To be sorted").mkdir()
    assert _check(lib, "12 - To be sorted/Smith, J. - A note on control.pdf")[0] == []


def test_a_vanished_paper_and_a_missing_folder_and_no_change(lib):
    assert any("no longer" in p for p in _check(lib, f"{PUB}/X.pdf")[0])
    _paper(lib, OLD)
    assert any("does not exist" in p for p in _check(lib, "99 - Nowhere/X.pdf")[0])
    assert any("current name" in p for p in _check(lib, OLD)[0])


def test_another_file_in_the_way_is_refused(lib):
    _paper(lib, OLD)
    _paper(lib, f"{PUB}/Smith, J. - Taken.pdf", b"%PDF-1.4 another paper")
    assert any("Another file" in p for p in _check(lib, f"{PUB}/Smith, J. - Taken.pdf")[0])


@pytest.mark.skipif(sys.platform != "darwin", reason="APFS folds case")
def test_a_capitalisation_only_rename_is_not_a_collision(lib):
    _paper(lib, OLD)
    if not (lib / OLD.lower().replace("01 - published papers/s", PUB)).exists():
        pytest.skip("this volume is case-sensitive")
    assert _check(lib, f"{PUB}/Smith, J. - A Note on contol.pdf")[0] == []


def test_a_decomposed_name_is_the_same_name(lib):
    nfd = unicodedata.normalize("NFD", f"{PUB}/Lévy, P. - Processus.pdf")
    _paper(lib, nfd)
    nfc = unicodedata.normalize("NFC", f"{PUB}/Lévy, P. - Processus.pdf")
    assert any("current name" in p for p in check_owner_rename(lib, nfd, nfc)[0])


@pytest.mark.parametrize("stem,expected", [
    ("Smith, J. - X", f"{PUB}/Smith, J. - X.pdf"),
    ("Smith, J. - X.pdf", f"{PUB}/Smith, J. - X.pdf"),
    ("  Smith, J. - X  ", f"{PUB}/Smith, J. - X.pdf"),
    (unicodedata.normalize("NFD", "Lévy"), f"{PUB}/Lévy.pdf"),
])
def test_target_rel(stem, expected):
    assert target_rel(PUB, stem) == unicodedata.normalize("NFC", expected)


# --------------------------------------------------- the move, end to end

def test_a_move_carries_the_record_and_can_be_undone(lib):
    from processing.identity import PaperIdentity, find_sidecar
    from processing.library_normalize import apply_renames
    from processing.undo_log import UndoLog
    pdf = _paper(lib, "02 - Unpublished papers/S/Smith, J. - X.pdf")
    ident = PaperIdentity()
    ident.doi = "10.1/keep"
    ident.save(pdf, recompute_hash=True)
    new_rel = f"{PUB}/Smith, J. - X, published.pdf"
    assert check_owner_rename(lib, str(pdf.relative_to(lib)), new_rel)[0] == []
    res = apply_renames(lib, [{"old": str(pdf.relative_to(lib)), "new": new_rel}],
                        dry_run=False, description="Rename one paper: X → Y")
    moved = lib / new_rel
    assert res["renamed"] == 1 and moved.exists() and not pdf.exists()
    assert PaperIdentity.load(moved).doi == "10.1/keep", "the record went with it"
    log_file = lib / ".operation_log" / f"{res['tx_id']}.json"
    assert "Rename one paper" in log_file.read_text()
    UndoLog(log_dir=lib / ".operation_log").undo_transaction(res["tx_id"])
    assert pdf.exists() and find_sidecar(pdf) is not None


# ------------------------------------------------------------ the page

@pytest.fixture
def C(monkeypatch, lib):
    from tests.ui.test_cockpit_renders_content import _RecStreamlit
    stub = _RecStreamlit([], {})
    monkeypatch.setitem(sys.modules, "streamlit", stub)
    monkeypatch.setenv("MATH_LIBRARY", str(lib))
    monkeypatch.setenv("HOME", str(lib / "home"))
    monkeypatch.delitem(sys.modules, "ui.cockpit", raising=False)
    import ui.cockpit as cockpit
    return cockpit


def _index(lib):
    from ui.search_page import build_index
    return build_index(lib)


def test_every_search_result_offers_rename_or_move(C, lib):
    _paper(lib, OLD)
    C.st.values["search_query"] = "smith"
    C.render_search()
    labels = [a[0] for n, a, k in C.st.calls if n == "button" and a]
    assert "✏️ Rename or move" in labels


def test_the_editor_renames_through_the_one_rename_path(C, lib, monkeypatch):
    import processing.library_normalize as ln
    _paper(lib, OLD)
    calls = []
    real = ln.apply_renames
    monkeypatch.setattr(ln, "apply_renames",
                        lambda *a, **k: calls.append((a, k)) or real(*a, **k))
    C.st.values[f"edit_name::{OLD}"] = "Smith, J. - A note on control"
    C.st.values[f"edit_apply::{OLD}"] = True
    C.st.session_state["edit_paper"] = OLD
    cleared = []
    monkeypatch.setattr(C, "_clear_scan_caches", lambda: cleared.append(1))
    C._render_paper_editor(lib, OLD, _index(lib))
    (args, kw), = calls
    assert args[1] == [{"old": OLD, "new": f"{PUB}/Smith, J. - A note on control.pdf"}]
    assert kw["dry_run"] is False and kw["description"].startswith("Rename one paper")
    assert (lib / PUB / "Smith, J. - A note on control.pdf").exists()
    assert C.st.session_state["flash"][-1][0] == "success"
    assert "edit_paper" not in C.st.session_state and cleared == [1]


def test_a_refused_rename_says_why_and_keeps_the_editor(C, lib, monkeypatch):
    import processing.library_normalize as ln
    _paper(lib, OLD)
    monkeypatch.setattr(ln, "apply_renames", lambda *a, **k: {
        "renamed": 0, "skipped": [{"old": OLD, "reason": "library busy"}],
        "error": None})
    C.st.values[f"edit_name::{OLD}"] = "Smith, J. - A note on control"
    C.st.values[f"edit_apply::{OLD}"] = True
    C.st.session_state["edit_paper"] = OLD
    C._render_paper_editor(lib, OLD, _index(lib))
    kind, msg = C.st.session_state["flash"][-1][:2]
    assert kind == "error" and "library busy" in msg
    assert C.st.session_state["edit_paper"] == OLD


def test_a_blocked_rename_cannot_be_pressed_or_forced(C, lib, monkeypatch):
    import processing.library_normalize as ln
    _paper(lib, OLD)
    calls = []
    monkeypatch.setattr(ln, "apply_renames", lambda *a, **k: calls.append(a))
    C.st.values[f"edit_name::{OLD}"] = ""
    C.st.values[f"edit_apply::{OLD}"] = True        # a stale click, say
    C._render_paper_editor(lib, OLD, _index(lib))
    (kw,) = [k for n, a, k in C.st.calls if n == "button" and a and a[0] == "Rename"]
    assert kw["disabled"] is True
    assert calls == [], "the handler must re-check, not trust the greyed button"


def test_use_that_name_is_offered_and_parked_for_the_next_run(C, lib, monkeypatch):
    import processing.move_normalizer as mn
    _paper(lib, OLD)
    monkeypatch.setattr(mn, "normalize_full_name",
                        lambda name, root=None: ("Smith, J. - A Canonical name.pdf", True, []))
    C.st.values[f"edit_canon::{OLD}"] = True
    C._render_paper_editor(lib, OLD, _index(lib))
    assert C.st.session_state[f"edit_name_pending::{OLD}"] == "Smith, J. - A Canonical name"
    C.st.values.clear()
    C.st.calls.clear()
    C._render_paper_editor(lib, OLD, _index(lib))
    assert C.st.session_state[f"edit_name::{OLD}"] == "Smith, J. - A Canonical name"


def test_the_folder_list_never_offers_an_archival_collection(C, lib):
    arch = ARCHIVAL_COLLECTIONS[0]
    _paper(lib, f"{arch}/Vol 1.pdf")
    _paper(lib, OLD)
    folders = C._library_folders(_index(lib))
    assert PUB in folders and not any(f.startswith(arch) for f in folders)
