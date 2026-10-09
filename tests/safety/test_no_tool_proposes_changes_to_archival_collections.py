"""No tool proposes changes to the archival collections.

The owner's decision 3A, 2026-10-09: the archival collections (JEHPS and
the academy folders 05/00, 05/01, 05/02, 05/11) may keep their saved
records, but no tool may ever propose to move, rename, retire or re-file
anything in them. Non-negotiable 6: processing.library_scope is the
single answer.

Measured that day: the topic pipeline kept its own folder list and
treated 1,689 archival volumes as candidates for topic moves (all but
JEHPS); the Spelling page skipped only the inbox; and five more proposers
-- Home's topic suggestions, conflict copies (Conflicts page and Home),
same-paper variants, and the two publication-state lists -- walked every
folder. None had produced an archival proposal yet, only because no
archival record happened to carry a trigger. Each test below plants the
trigger, in every archival collection, next to an in-scope control that
MUST still be proposed -- so the test cannot pass by proposing nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from processing.library_scope import ARCHIVAL_COLLECTIONS, why_not_proposable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402

CONTROL = "01 - Published papers/S"


@pytest.fixture
def lib(tmp_path):
    from processing.identity import enable_sidecar_mirror
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _pdf(lib, folder, name, title="t"):
    p = lib / folder / name
    p.parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_pdf(p, title=title, author="Smith, J.")
    return p


def _record(pdf, **fields):
    from processing.identity import PaperIdentity
    ident = PaperIdentity.load(pdf)
    for k, v in fields.items():
        setattr(ident, k, v)
    ident.save(pdf, recompute_hash=True)


def _everywhere(lib, name, **fields):
    """One planted paper per archival collection, plus the control."""
    planted = {}
    for folder in list(ARCHIVAL_COLLECTIONS) + [CONTROL]:
        p = _pdf(lib, folder, name)
        if fields:
            _record(p, **fields)
        planted[folder] = p
    return planted


def _names(paths):
    return {str(Path(p)) for p in paths}


# ------------------------------------------------------- the single answer

@pytest.mark.parametrize("folder", ARCHIVAL_COLLECTIONS)
def test_every_archival_collection_is_not_proposable(lib, folder):
    assert why_not_proposable(lib, lib / folder / "x.pdf") is not None


@pytest.mark.parametrize("folder", [CONTROL, "12 - To be sorted",
                                    "04 - Papers to be downloaded/J",
                                    "05 - Books and lecture notes/05 - Astérisque"])
def test_ordinary_folders_and_staging_are_proposable(lib, folder):
    assert why_not_proposable(lib, lib / folder / "x.pdf") is None


def test_the_code_checkout_is_not_proposable(lib):
    assert why_not_proposable(lib, lib / "Scripts" / "x.pdf") is not None


# ------------------------------------------------------------ the proposers

def test_home_topic_suggestions(lib):
    from processing.publication_topic_router import list_topic_suggestions
    planted = _everywhere(lib, "Smith, J. - A paper.pdf",
                          topic_suggestion="07a", topic_confidence=0.6)
    got = _names(r["path"] for r in list_topic_suggestions(lib))
    assert got == {str(planted[CONTROL])}


def test_conflict_copies_on_the_conflicts_page_and_home(lib):
    from processing.conflict_resolver import scan_conflicts
    from ui.attention_queue import collect_conflict_copies
    name = "Smith, J. - A paper (Dylan's conflicted copy 2026-10-09).pdf"
    planted = _everywhere(lib, name)
    assert _names(c.conflict for c in scan_conflicts(lib)) == {str(planted[CONTROL])}
    keys = {it.key for it in collect_conflict_copies(lib)}
    assert len(keys) == 1 and CONTROL in next(iter(keys))


def test_permanently_unpublished_and_borderline_lists(lib):
    from processing.publication_state import (list_borderline_matches,
                                              list_permanently_unpublished)
    planted = _everywhere(lib, "Smith, J. - Never published.pdf",
                          permanently_unpublished=True)
    assert _names(list_permanently_unpublished(lib)) == {str(planted[CONTROL])}
    check = {"date": "2026-10-01", "hit": True, "confidence": 0.85,
             "details": {"doi": "10.1/x"}}
    planted = _everywhere(lib, "Smith, J. - Borderline.pdf",
                          publication_checks=[check])
    got = _names(r["path"] for r in list_borderline_matches(lib))
    assert str(planted[CONTROL]) in got
    assert not any(a in p for p in got for a in ARCHIVAL_COLLECTIONS)


def test_same_paper_variants_never_involve_an_archival_volume(lib):
    from processing.preprint_variants import _collect_records
    _everywhere(lib, "Smith, J. - A paper.pdf", doi="10.1/same")
    rels = {r["rel"] for r in _collect_records(lib)}
    assert rels == {f"{CONTROL}/Smith, J. - A paper.pdf"}


def test_the_topic_pipeline_counts_and_skips_them(lib):
    from processing.pipeline_preview import preview_topic_filing
    planted = _everywhere(lib, "Smith, J. - Reflected BSDEs and backward stochastic equations.pdf")
    summary, proposals = preview_topic_filing(lib, with_extras=False)
    paths = {p.path for p in proposals}
    assert str(planted[CONTROL]) in paths, "control: the pipeline still works"
    assert not any(a in p for p in paths for a in ARCHIVAL_COLLECTIONS)
    assert sum(summary.left_alone.values()) == len(ARCHIVAL_COLLECTIONS)
    assert summary.to_dict()["left_alone"] == summary.left_alone


@pytest.mark.parametrize("folder", ARCHIVAL_COLLECTIONS)
def test_an_explicit_archival_scope_gets_nothing_either(lib, folder):
    """With ``scope`` the pipeline skipped its own routability filter, so
    a caller handing in an archival folder got proposals for it."""
    from processing.pipeline_preview import preview_topic_filing
    _pdf(lib, folder, "Smith, J. - Reflected BSDEs and backward stochastic equations.pdf")
    summary, proposals = preview_topic_filing(lib, scope=lib / folder, with_extras=False)
    assert proposals == [] and sum(summary.left_alone.values()) == 1


def test_the_first_page_text_step_skips_them(lib, monkeypatch):
    import processing.classifier_text as ct
    from processing.identity import PaperIdentity
    planted = _everywhere(lib, "Smith, J. - A paper.pdf")
    monkeypatch.setattr(ct, "extract_classifier_text", lambda *a, **k: "first pages")
    stats = ct.backfill_classifier_text(lib)
    assert stats["left_alone"] == len(ARCHIVAL_COLLECTIONS)
    for folder, pdf in planted.items():
        has = bool(PaperIdentity.load(pdf).classifier_text)
        assert has is (folder == CONTROL), folder


def test_spelling_counts_them_but_offers_no_fix(lib, monkeypatch):
    from tests.ui.test_cockpit_smoke import _StreamlitModule
    fake = _StreamlitModule()
    monkeypatch.setitem(sys.modules, "streamlit", fake)
    monkeypatch.setenv("MATH_LIBRARY", str(lib))
    monkeypatch.setenv("HOME", str(lib / "home"))
    monkeypatch.delitem(sys.modules, "ui.cockpit", raising=False)
    import ui.cockpit as C
    import maintenance.typos as T
    monkeypatch.setattr(T, "self_check", lambda *a, **k: None)
    planted = _everywhere(lib, "Smith, J. - A diﬀerential equation.pdf")   # ligature
    seen = []
    real = T.build_corpus_stats
    monkeypatch.setattr(T, "build_corpus_stats",
                        lambda names, **k: real(list(seen.extend(names) or seen), **k))
    data = C._spelling_scan(lib)
    # Their titles still count as evidence of how words are spelt -- so
    # the verdicts on every other title are exactly what they were.
    assert len(seen) == len(planted), "archival titles must stay in the statistics"
    assert {b["rel"] for b in data["broken"]} == {f"{CONTROL}/Smith, J. - A diﬀerential equation.pdf"}
    assert data["left_alone"] == len(ARCHIVAL_COLLECTIONS)
    assert data["scanned"] == 1
