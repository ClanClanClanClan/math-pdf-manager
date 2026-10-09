"""A count on screen is the count of what it names -- and "could not read" is not 0.

Two cockpit-audit findings the owner asked to have checked before fixing.
Both reproduced on the real library, 2026-10-09:

Search. ``search_index`` stopped at 200 matches and the page built its
count AND both downloads from that list. "stochastic" matches 3,848
filenames; the page said 200, the CSV held 200, and a caption said "All
results are included in the CSV / BibTeX exports below". Same for
"optimal" (2,206), "control" (1,744), "brownian" (871), "bsde" (791).

Words awaiting a ruling. The Stats health strip read only the old title
vocabulary (0 pending) while the casing census -- the list the renamer
consults -- held 148 words back (124 held, 24 flagged). Settings said
"No uncertain title words. ✓" for the same empty list, and Home had no
row for it. Separately, every failed probe in the strip fell back to 0
or "not trained yet", the second of which invites a retrain over a
model that was merely unreadable.
"""
from __future__ import annotations

import csv
import io

import pytest

from tests.ui.test_cockpit_renders_content import (  # noqa: F401  (fixtures)
    _pdf, assert_metric, cockpit, home, lib, metrics, rendered_text,
)


# ------------------------------------------------------------------ search

def _download(st_stub, prefix: str):
    for name, args, kwargs in st_stub.calls:
        if name == "download_button" and str(args[0]).startswith(prefix):
            return args[0], args[1]
    raise AssertionError(f"no {prefix!r} download was offered")


def test_search_index_returns_every_match_by_default(tmp_path):
    from ui.search_page import build_index, search_index
    for i in range(230):
        _pdf(tmp_path / "01 - Published papers" / "S" / f"Smith, J. - Stochastic {i}.pdf")
    assert len(search_index(build_index(tmp_path), "stochastic")) == 230


@pytest.mark.parametrize("n", [1, 25, 26, 230])
def test_the_count_and_both_downloads_hold_every_match(cockpit, lib, n):
    for i in range(n):
        _pdf(lib / "01 - Published papers" / "S" / f"Smith, J. - Stochastic {i}.pdf")
    _pdf(lib / "01 - Published papers" / "E" / "Ekeland, I. - Convexity.pdf")
    cockpit.st.values["search_query"] = "stochastic"
    cockpit.render_search()
    text = rendered_text(cockpit.st)
    assert f"{n:,} result(s)" in text
    label, payload = _download(cockpit.st, "⬇ CSV")
    rows = list(csv.DictReader(io.StringIO(payload)))
    assert len(rows) == n, f"the CSV held {len(rows)} of {n} matches"
    assert f"{n:,} rows" in label, "the button must say how many rows it holds"
    _, bib = _download(cockpit.st, "⬇ BibTeX")
    assert bib.count("@") == n
    assert "Ekeland" not in payload


def test_a_long_list_says_the_downloads_hold_all_of_it_and_means_it(cockpit, lib):
    for i in range(230):
        _pdf(lib / "01 - Published papers" / "S" / f"Smith, J. - Stochastic {i}.pdf")
    cockpit.st.values["search_query"] = "stochastic"
    cockpit.render_search()
    text = rendered_text(cockpit.st)
    assert "first 200" not in text
    assert "hold all 230 results" in text
    # Only 25 names are LISTED -- the paging is the page's, not the search's.
    listed = [a[0] for n, a, k in cockpit.st.calls
              if n == "markdown" and a and str(a[0]).startswith("**Smith")]
    assert len(listed) == 25


# ------------------------------------------------- health: the real backlog

QUEUE = [{"word": w, "kind": k, "capitalised": 3, "lower": 2, "suggestion": "?",
          "decided": None, "held_back": k == "held", "is_author": False,
          "changed_since_you_decided": False}
         for w, k in [("copulas", "held"), ("vitesse", "held"), ("éléments", "flagged")]]


def test_health_counts_the_words_the_renamer_is_holding_back(tmp_path, monkeypatch):
    import processing.casing_vocabulary as cv
    from maintenance.health import collect_library_health
    monkeypatch.setattr(cv, "review_queue", lambda *a, **k: QUEUE)
    h = collect_library_health(tmp_path)
    assert (h["casing_review"], h["casing_held"]) == (3, 2)
    assert h["vocab_pending"] == 0, "the old list really is empty here"


def _boom(*a, **k):
    raise OSError("half-synced")


@pytest.mark.parametrize("probe,module,attr,keys", [
    ("casing", "processing.casing_vocabulary", "review_queue",
     ["casing_review", "casing_held"]),
    ("vocab", "processing.title_vocab", "load_vocab",
     ["vocab_pending", "vocab_ruled"]),
    ("corpus", "processing.title_corpus", "stats_path",
     ["corpus_stats_age_days"]),
])
def test_a_probe_that_fails_reports_unknown_not_zero(tmp_path, monkeypatch,
                                                     probe, module, attr, keys):
    import importlib
    from maintenance.health import collect_library_health
    monkeypatch.setattr(importlib.import_module(module), attr, _boom)
    h = collect_library_health(tmp_path)
    for key in keys:
        assert h[key] is None, f"{key} turned 'could not read' into {h[key]!r}"


def test_an_unreadable_model_is_unknown_and_a_missing_one_is_untrained(tmp_path, monkeypatch):
    from maintenance.health import collect_library_health
    from processing.title_model import model_path
    assert collect_library_health(tmp_path)["model_trained_on"] == 0   # missing
    mp = model_path(tmp_path)
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text("{half a fi")                                         # unreadable
    h = collect_library_health(tmp_path)
    assert h["model_trained_on"] is None and h["model_age_days"] is None


# ------------------------------------------------------- the Stats metric

@pytest.mark.parametrize("h,value", [
    ({"casing_review": 148, "casing_held": 124, "vocab_pending": 0, "vocab_ruled": 4}, 148),
    ({"casing_review": 0, "casing_held": 0, "vocab_pending": 5, "vocab_ruled": 0}, 5),
    ({"casing_review": 10, "casing_held": 1, "vocab_pending": 5, "vocab_ruled": 0}, 15),
    ({"casing_review": 0, "casing_held": 0, "vocab_pending": 0, "vocab_ruled": 0}, 0),
    ({"casing_review": None, "casing_held": None, "vocab_pending": 0, "vocab_ruled": 0}, "—"),
    ({"casing_review": 3, "casing_held": 3, "vocab_pending": None, "vocab_ruled": None}, "—"),
    ({"vocab_pending": 0, "vocab_ruled": 0}, "—"),          # a snapshot that never measured it
])
def test_the_metric_never_turns_unknown_into_a_number(cockpit, h, value):
    got, help_text = cockpit._words_awaiting_ruling(h)
    assert got == value
    if value == "—":
        assert "could not be read" in help_text
    elif h.get("casing_review"):
        assert "Spelling" in help_text, "send him where the buttons are"


def _health(**over):
    base = {"sidecar_coverage": 1.0, "sidecars": 1, "pdfs": 1,
            "vocab_pending": 0, "vocab_ruled": 4, "casing_review": 148,
            "casing_held": 124, "undo_transactions": 1, "last_tx_age_days": 1,
            "trash_pdfs": 0, "model_trained_on": 900, "model_accuracy": 0.9,
            "model_age_days": 3, "corpus_stats_age_days": 2}
    base.update(over)
    fn = lambda *a, **k: base          # noqa: E731
    fn.clear = lambda: None
    return fn


def test_stats_shows_the_148_and_points_at_spelling(cockpit, lib, monkeypatch):
    monkeypatch.setattr(cockpit, "_library_health_cached", _health())
    cockpit.render_stats()
    assert_metric(cockpit.st, "Words awaiting your ruling", 148)
    helps = [k.get("help", "") for n, a, k in cockpit.st.calls
             if n == "metric" and a and a[0] == "Words awaiting your ruling"]
    assert "124 are held back" in helps[0] and "Spelling" in helps[0]
    assert "Settings → Title vocabulary" not in helps[0], (
        "that list is empty -- it is not where the 148 are")


def test_stats_never_says_untrained_for_an_unreadable_model(cockpit, lib, monkeypatch):
    monkeypatch.setattr(cockpit, "_library_health_cached",
                        _health(model_trained_on=None, model_accuracy=None,
                                model_age_days=None, corpus_stats_age_days=None))
    cockpit.render_stats()
    text = rendered_text(cockpit.st)
    assert "not trained yet" not in text
    assert "could not be read" in text and "NOT the same as untrained" in text


# ------------------------------------------------- Settings and Home

def test_settings_does_not_tick_an_empty_list_while_the_other_waits(cockpit, lib, monkeypatch):
    import processing.casing_vocabulary as cv
    monkeypatch.setattr(cv, "review_queue", lambda *a, **k: QUEUE)
    cockpit._render_title_vocabulary(lib)
    text = rendered_text(cockpit.st)
    assert "No uncertain title words" not in text
    assert "3 word(s)" in text and "Spelling" in text


def test_settings_says_unknown_when_the_other_list_cannot_be_read(cockpit, lib, monkeypatch):
    import processing.casing_vocabulary as cv
    monkeypatch.setattr(cv, "review_queue", _boom)
    cockpit._render_title_vocabulary(lib)
    text = rendered_text(cockpit.st)
    assert "No uncertain title words" not in text and "could not be read" in text


def test_settings_still_ticks_when_both_lists_are_empty(cockpit, lib, monkeypatch):
    import processing.casing_vocabulary as cv
    monkeypatch.setattr(cv, "review_queue", lambda *a, **k: [])
    cockpit._render_title_vocabulary(lib)
    assert "No uncertain title words" in rendered_text(cockpit.st)


def test_home_gets_one_row_for_the_whole_backlog(tmp_path, monkeypatch):
    import processing.casing_vocabulary as cv
    from ui.attention_queue import SEVERITY_WARNING, collect_casing_rulings
    monkeypatch.setattr(cv, "review_queue", lambda *a, **k: QUEUE)
    items = collect_casing_rulings(tmp_path)
    assert len(items) == 1
    it = items[0]
    assert "3 word(s)" in it.title and it.severity == SEVERITY_WARNING
    assert "2 held back" in it.detail and "1 worth a look" in it.detail
    monkeypatch.setattr(cv, "review_queue", lambda *a, **k: [])
    assert collect_casing_rulings(tmp_path) == []


def test_a_home_row_that_cannot_be_built_is_shown_as_such(tmp_path, monkeypatch):
    import processing.casing_vocabulary as cv
    from ui.attention_queue import collect_casing_rulings, gather_attention_items
    monkeypatch.setattr(cv, "review_queue", _boom)
    items = gather_attention_items(
        tmp_path, collectors=[("casing_rulings", collect_casing_rulings)],
        dismissals_path=tmp_path / "d.json")
    assert [it.source for it in items] == ["collector_error"]


def test_the_collector_is_registered():
    from ui.attention_queue import COLLECTORS, collect_casing_rulings
    assert ("casing_rulings", collect_casing_rulings) in COLLECTORS


def test_a_long_title_cut_at_a_space_still_renders_bold(cockpit, lib):
    """Seen live on the real library: a name cut at 95 characters right
    after a space printed its markdown asterisks literally."""
    name = "Matoussi, A., Possamaï, D., Zhou, C. - Robust utility maximization in nondominated models with random endowment.pdf"
    assert name[:95].endswith(" "), "precondition: the live case"
    _pdf(lib / "01 - Published papers" / "M" / name)
    cockpit.st.values["search_query"] = "matoussi"
    cockpit.render_search()
    shown = [a[0] for n, a, k in cockpit.st.calls
             if n == "markdown" and a and str(a[0]).startswith("**Matoussi")]
    assert shown and not shown[0].endswith(" **") and shown[0].endswith("…**"), shown
