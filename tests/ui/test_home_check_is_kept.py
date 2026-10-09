"""The Home check is paid for once, kept, and never thrown away by a click.

Cockpit audit findings 12, 13, 14 and 15, all approved. The sweep behind
Home walks every PDF and loads every record: 22-27 s warm on the 29.5k
library (measured 2026-09-05), more cold.

13. It lived only in st.session_state, so every browser reload, second tab
    or server restart re-ran it -- and Home, the landing page, started it
    unconditionally on arrival.
12. Acting on ONE Home row threw the whole list away, and the rerun paid
    for a new sweep immediately.
15. Any change anywhere deleted the list (and two other scans with it).
14. Trashing one duplicate group re-ran the whole-library duplicate scan
    (~10 s per click, 55 groups pending) and never saved the result, so a
    reload brought the trashed group back.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.ui.test_cockpit_smoke import st_stub  # noqa: F401  (fixture)

COCKPIT = Path(__file__).resolve().parents[2] / "src" / "ui" / "cockpit.py"


@pytest.fixture
def C(st_stub, monkeypatch, tmp_path):
    import ui.cockpit as cockpit
    import ui.attention_queue as aq
    from ui.attention_queue import AttentionItem
    calls = {"scans": 0, "conflicts": 0, "search": 0}

    def _gather(lib, include_dismissed=False, progress=None, **kw):
        calls["scans"] += 1
        return [AttentionItem(key=f"k{i}", source="conflict_copy",
                              severity="warning", title=f"item {i}",
                              actions=[("Move conflict copy to trash", "delete_conflict")])
                for i in range(3)]

    monkeypatch.setattr(aq, "gather_attention_items", _gather)
    monkeypatch.setattr(aq, "_load_dismissals", lambda *a, **k: {})
    monkeypatch.setattr(cockpit._conflicts_cached, "clear",
                        lambda: calls.__setitem__("conflicts", calls["conflicts"] + 1))
    monkeypatch.setattr(cockpit._search_index_cached, "clear",
                        lambda: calls.__setitem__("search", calls["search"] + 1))
    cockpit._calls = calls
    cockpit._lib = str(tmp_path / "lib")
    return cockpit


def _keys(items):
    return [it.key for it in items]


def _new_session(C):
    C.st.session_state.pop("_attn_cache", None)


# ----------------------------------------------------- 13. reload, arrival

def test_a_reload_shows_the_saved_check_without_scanning(C):
    C._gather_attention_cached(C._lib, scan=True)
    assert C._calls["scans"] == 1
    _new_session(C)                                   # a browser reload
    items = C._gather_attention_cached(C._lib, scan=False)
    assert _keys(items) == ["k0", "k1", "k2"]
    assert C._calls["scans"] == 1, "the reload paid for a second sweep"


def test_nothing_saved_and_not_asked_means_no_scan(C):
    assert C._gather_attention_cached(C._lib, scan=False) is None
    assert C._calls["scans"] == 0


def test_a_saved_check_belongs_to_its_library_only(C, tmp_path):
    C._gather_attention_cached(C._lib, scan=True)
    _new_session(C)
    assert C._gather_attention_cached(str(tmp_path / "other"), scan=False) is None


# ------------------------------------------------- 12. one row, one removal

@pytest.mark.parametrize("moved", [True, False])
def test_acting_on_a_row_drops_that_row_only(C, moved):
    C._gather_attention_cached(C._lib, scan=True)
    C._attention_resolved("k1", files_moved=moved)
    assert _keys(C._gather_attention_cached(C._lib, scan=False)) == ["k0", "k2"]
    assert C._calls["scans"] == 1, "a row action re-ran the sweep"
    assert C._calls["conflicts"] == C._calls["search"] == (1 if moved else 0), (
        "only an action that moved files may drop the conflict list and index")
    _new_session(C)
    assert _keys(C._gather_attention_cached(C._lib, scan=False)) == ["k0", "k2"], (
        "the removal must be saved too, or a reload resurrects the row")


def test_home_row_actions_use_the_row_removal_not_the_global_clear():
    tree = ast.parse(COCKPIT.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "render_attention")
    src = ast.unparse(fn)
    assert "_attention_count_cached.clear()" not in src
    assert src.count("_attention_resolved(it.key") == 7


# -------------------------------------------- 15. outdated, not deleted

def test_a_change_elsewhere_marks_the_list_outdated_and_keeps_it(C):
    C._gather_attention_cached(C._lib, scan=True)
    C._clear_scan_caches()
    assert _keys(C._gather_attention_cached(C._lib, scan=False)) == ["k0", "k1", "k2"]
    assert C._attention_meta(C._lib)["outdated"] is True
    assert C._calls["scans"] == 1
    _new_session(C)
    assert C._attention_meta(C._lib)["outdated"] is True, "the mark must survive a reload"


def test_rescan_forgets_memory_and_disk(C):
    C._gather_attention_cached(C._lib, scan=True)
    C._gather_attention_cached.clear()
    assert C._gather_attention_cached(C._lib, scan=False) is None
    _new_session(C)
    assert C._gather_attention_cached(C._lib, scan=False) is None


def test_a_fresh_check_clears_the_outdated_mark(C):
    C._gather_attention_cached(C._lib, scan=True)
    C._clear_scan_caches()
    C._gather_attention_cached.clear()
    C._gather_attention_cached(C._lib, scan=True)
    assert C._attention_meta(C._lib)["outdated"] is False


# --------------------------------------------- dismissals need no rescan

def test_dismissing_filters_the_kept_list_without_a_sweep(C, monkeypatch):
    import ui.attention_queue as aq
    C._gather_attention_cached(C._lib, scan=True)
    monkeypatch.setattr(aq, "_load_dismissals",
                        lambda *a, **k: {"k0": "2999-01-01T00:00:00+00:00"})
    assert _keys(C._gather_attention_cached(C._lib, False, scan=False)) == ["k1", "k2"]
    assert _keys(C._gather_attention_cached(C._lib, True, scan=False)) == ["k0", "k1", "k2"]
    assert C._calls["scans"] == 1


# --------------------------------------------------- 14. duplicates

def test_resolving_one_duplicate_group_removes_exactly_that_group(C):
    groups = [{"sha256": "aa", "paths": ["1", "2"]},
              {"sha256": "bb", "paths": ["3", "4"]}]
    assert C._without_dup_group(groups, "aa") == [{"sha256": "bb", "paths": ["3", "4"]}]


def test_the_per_group_handler_neither_rescans_nor_forgets_to_save():
    src = COCKPIT.read_text(encoding="utf-8")
    i = src.index('"Trash the others",')
    block = src[i:src.index("def _page_chrome", i)]
    assert "find_exact_duplicates" not in block, "it still re-runs the whole-library scan"
    assert '_save_scan("duplicates"' in block, "the result is not saved for a reload"
