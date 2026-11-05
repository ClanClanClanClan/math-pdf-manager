"""An answer replayed from the saved Crossref answers is not a new check.

Step-back audit, finding G4-2 (verified 3 of 3). The publication checker
keeps every Crossref answer in ``.publication_check_cache.json`` with no
date and no expiry, and hands a saved answer back as if it had just
asked. The state machine then counted each replayed "no match" as a fresh
miss: three presses of "Run checks" in one afternoon latched a paper
``permanently_unpublished`` on what was ONE answer from June, and 1,038
Unpublished records carry that latch today.

Now the checker says when an answer came from the saved ones
(``last_from_cache``), the scan carries it (``from_cache``), and the
state machine records it only when it is news: a hit at or above the
threshold that the record does not hold yet. Everything else is listed as
``replayed`` and the record is left exactly as it was.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as hst, HealthCheck

from processing.identity import PaperIdentity, sidecar_path
from processing.publication_state import update_publication_state
from tests.ui.test_cockpit_renders_content import cockpit, home, lib  # noqa: F401 -- fixtures


# ------------------------------------------------------------ the checker

def _offline_checker(monkeypatch, cache_path, entries):
    """A checker whose saved answers are ``entries`` and which may not ask."""
    from processing import publication_checker as pc
    cache_path.write_text(json.dumps(
        {"_version": pc.CrossrefChecker.CACHE_VERSION, "entries": entries}))
    c = pc.CrossrefChecker(cache_path=cache_path)
    monkeypatch.setattr(pc.time, "sleep", lambda *_: None)

    def _no_network(*a, **k):
        raise AssertionError("a saved answer was re-asked over the network")

    monkeypatch.setattr(c.session, "get", _no_network)
    return c


def _key(title):
    from processing.publication_checker import CrossrefChecker
    return CrossrefChecker(cache_path=None)._cache_key(title)


HIT = {"doi": "10.1007/s00440-020-01000-0", "journal": "Probab. Theory",
       "confidence": 0.97, "author_count": 1, "year": 2020,
       "matched_title": "A long enough title for parsing"}


@pytest.mark.parametrize("saved", [None, HIT])
def test_the_checker_says_the_answer_was_saved(tmp_path, monkeypatch, saved):
    title = "A long enough title for parsing"
    c = _offline_checker(monkeypatch, tmp_path / "c.json", {_key(title): saved})
    assert c.check_title(title, ["Author"]) == saved
    assert c.last_from_cache is True
    assert c.last_lookup_failed is False


def test_a_fresh_answer_is_not_marked_saved(tmp_path, monkeypatch):
    """The flag resets: a stale True would hide every real check after a
    replayed one."""
    from processing import publication_checker as pc
    title = "A long enough title for parsing"
    c = _offline_checker(monkeypatch, tmp_path / "c.json", {_key(title): None})
    c.check_title(title, ["Author"])
    assert c.last_from_cache

    class _Resp:
        status_code = 200
        headers = {}

        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"items": []}}

    monkeypatch.setattr(c.session, "get", lambda *a, **k: _Resp())
    c.check_title("Another title that was never asked", ["Other"])
    assert c.last_from_cache is False


@pytest.mark.parametrize("where", ["loaded from the file", "already in memory"])
def test_a_saved_repository_match_turned_into_no_match_is_still_saved(tmp_path, monkeypatch, where):
    """A saved arXiv/SSRN hit becomes "no match" -- on load, or on the way
    out when it reached the cache another way. Either way that "no match"
    is the June answer, not a new one."""
    title = "A long enough title for parsing"
    repo = dict(HIT, doi="10.48550/arxiv.2001.00001", journal="arXiv")
    c = _offline_checker(monkeypatch, tmp_path / "c.json", {_key(title): repo})
    if where == "already in memory":
        c._cache[_key(title)] = repo
    assert c.check_title(title, ["Author"]) is None
    assert c.last_from_cache is True


def test_a_saved_hit_without_author_count_is_asked_again_and_is_fresh(tmp_path, monkeypatch):
    """The other branch of the cache: an entry too old to trust is dropped
    and re-asked, so the answer that comes back IS new."""
    from processing import publication_checker as pc
    title = "A long enough title for parsing"
    path = tmp_path / "c.json"
    path.write_text(json.dumps({_key(title): {"doi": "10.1/x", "confidence": 0.99}}))
    c = pc.CrossrefChecker(cache_path=path)
    assert _key(title) not in c._cache  # dropped on load
    monkeypatch.setattr(pc.time, "sleep", lambda *_: None)

    class _Resp:
        status_code = 200
        headers = {}

        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"items": []}}

    monkeypatch.setattr(c.session, "get", lambda *a, **k: _Resp())
    c.check_title(title, ["Author"])
    assert c.last_from_cache is False


def test_the_weekly_check_hands_the_replayed_papers_on(tmp_path, monkeypatch):
    """check_publications is what the Monday sweep and "Run checks" both
    call; the list must survive it to reach the report and the page."""
    import maintenance.weekly_report as W
    from processing import publication_checker as pc
    lib = tmp_path / "lib"
    d = lib / "02 - Unpublished papers"
    d.mkdir(parents=True)
    pdf = _paper(d, "Author, A. - A long enough title for parsing.pdf")
    monkeypatch.setattr(pc, "scan_directory", lambda folder, **k: (
        [_saved(pdf)] if folder == d else []))
    out = W.check_publications(lib, verbose=False)
    assert out["replayed"] == [str(pdf)]
    assert PaperIdentity.load(pdf).recheck_count == 0


def test_the_scan_carries_it(tmp_path, monkeypatch):
    from processing import publication_checker as pc
    d = tmp_path / "02 - Unpublished papers"
    d.mkdir()
    (d / "Author, A. - A long enough title for parsing.pdf").write_bytes(b"%PDF-1.4")
    title, _ = pc.parse_paper_filename(next(d.iterdir()))
    c = _offline_checker(monkeypatch, tmp_path / "c.json", {_key(title): None})
    out = pc.scan_directory(d, checker=c)
    assert [e["from_cache"] for e in out] == [True]
    assert out[0]["published"] is False


# ------------------------------------------------------ the state machine

def _paper(tmp_path, name="p.pdf") -> Path:
    pdf = tmp_path / name
    pdf.write_bytes(b"%PDF-1.4 test")
    PaperIdentity().save(pdf)
    return pdf


def _saved(pdf, match=None):
    e = {"file": str(pdf), "published": bool(match), "from_cache": True}
    if match:
        e["match"] = match
    return e


def test_three_replayed_misses_never_latch(tmp_path):
    """THE CORRUPTION: three presses in one afternoon wrote a paper off."""
    pdf = _paper(tmp_path)
    before = sidecar_path(pdf).read_bytes()
    for _ in range(5):
        s = update_publication_state([_saved(pdf)])
        assert s.replayed == [str(pdf)] and not s.checked
    ident = PaperIdentity.load(pdf)
    assert not ident.permanently_unpublished
    assert ident.recheck_count == 0
    assert sidecar_path(pdf).read_bytes() == before, "the record was rewritten"


def test_fresh_misses_still_latch_so_the_guard_is_not_simply_off(tmp_path):
    pdf = _paper(tmp_path)
    for _ in range(3):
        update_publication_state([{"file": str(pdf), "published": False,
                                   "from_cache": False}])
    assert PaperIdentity.load(pdf).permanently_unpublished


def test_a_saved_borderline_match_is_not_counted_as_a_miss(tmp_path):
    """A saved 0.6 match is below the hit threshold. Recorded on every run it
    would have been a miss each time -- the same latch by another door."""
    pdf = _paper(tmp_path)
    weak = dict(HIT, confidence=0.6)
    for _ in range(4):
        s = update_publication_state([_saved(pdf, weak)])
        assert s.replayed == [str(pdf)]
    ident = PaperIdentity.load(pdf)
    assert ident.recheck_count == 0 and not ident.publication_checks


def test_a_saved_hit_the_record_lacks_is_recorded_once_then_replayed(tmp_path):
    """A hit nobody wrote down is news the first time, and only then."""
    pdf = _paper(tmp_path)
    s1 = update_publication_state([_saved(pdf, HIT)])
    assert s1.checked == [str(pdf)] and s1.hits and not s1.replayed
    ident = PaperIdentity.load(pdf)
    assert [c["source"] for c in ident.publication_checks] == ["crossref (saved answer)"]
    s2 = update_publication_state([_saved(pdf, HIT)])
    assert s2.replayed == [str(pdf)] and not s2.checked
    assert len(PaperIdentity.load(pdf).publication_checks) == 1


def test_a_saved_match_exactly_at_the_threshold_is_a_hit(tmp_path):
    """The state machine calls 0.75 a hit; the replay rule must agree, or a
    saved answer at the line is neither recorded nor counted."""
    pdf = _paper(tmp_path)
    s = update_publication_state([_saved(pdf, dict(HIT, confidence=0.75))])
    assert s.checked == [str(pdf)] and s.hits


def test_a_saved_hit_for_another_doi_is_still_news(tmp_path):
    pdf = _paper(tmp_path)
    update_publication_state([_saved(pdf, HIT)])
    other = dict(HIT, doi="10.1016/j.spa.2021.01.001")
    s = update_publication_state([_saved(pdf, other)])
    assert s.checked == [str(pdf)]


def test_the_doi_comparison_ignores_case_and_spaces(tmp_path):
    pdf = _paper(tmp_path)
    update_publication_state([_saved(pdf, HIT)])
    shouted = dict(HIT, doi="  " + HIT["doi"].upper() + " ")
    assert update_publication_state([_saved(pdf, shouted)]).replayed == [str(pdf)]


def test_a_recorded_miss_with_the_same_doi_field_is_not_a_hit(tmp_path):
    """Only HITS count as already recorded: a record holding a miss that
    happens to carry details must not swallow a real saved hit."""
    pdf = _paper(tmp_path)
    ident = PaperIdentity.load(pdf)
    ident.record_publication_check(hit=False, source="crossref", confidence=0.4,
                                   details={"doi": HIT["doi"]})
    ident.save(pdf)
    s = update_publication_state([_saved(pdf, HIT)])
    assert s.checked == [str(pdf)] and s.hits


def test_a_saved_answer_for_a_latched_paper_changes_nothing(tmp_path):
    pdf = _paper(tmp_path)
    ident = PaperIdentity.load(pdf)
    ident.permanently_unpublished = True
    ident.recheck_count = 3
    ident.save(pdf)
    before = sidecar_path(pdf).read_bytes()
    assert update_publication_state([_saved(pdf)]).replayed == [str(pdf)]
    assert sidecar_path(pdf).read_bytes() == before


def test_a_missing_from_cache_key_means_a_fresh_answer(tmp_path):
    """Results from callers that predate the flag are taken as fresh, as
    they always were -- so the old behaviour is kept where it was right."""
    pdf = _paper(tmp_path)
    update_publication_state([{"file": str(pdf), "published": False}])
    assert PaperIdentity.load(pdf).recheck_count == 1


@settings(max_examples=60, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(runs=hst.lists(
    hst.one_of(
        hst.none(),
        hst.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
    min_size=1, max_size=8))
def test_property_replayed_answers_never_advance_the_counter(tmp_path_factory, runs):
    """Whatever mix of saved misses and saved matches of any confidence,
    replayed over any number of runs: the counter never moves and the
    paper is never latched. At most one new hit is written per DOI."""
    tmp = tmp_path_factory.mktemp("replay")
    pdf = _paper(tmp)
    for conf in runs:
        match = None if conf is None else dict(HIT, confidence=conf)
        update_publication_state([_saved(pdf, match)])
    ident = PaperIdentity.load(pdf)
    assert ident.recheck_count == 0
    assert not ident.permanently_unpublished
    assert len(ident.publication_checks) <= 1
    assert all(c["hit"] for c in ident.publication_checks)


# ------------------------------------------------- what he is told about it

def test_the_weekly_report_says_which_papers_were_not_asked_again():
    from maintenance.weekly_report import run_problems
    out = run_problems({"publications": {"replayed": ["a.pdf", "b.pdf"]}})
    assert any("2 paper(s) were not asked again" in line for line in out), out


def test_the_maintenance_page_says_so_instead_of_a_clean_count(cockpit):
    """The page drew "Newly-published papers found: 0" over a run that had
    asked Crossref nothing new -- "I didn't look" as "it's fine"."""
    from tests.ui.test_cockpit_renders_content import rendered_text
    cockpit.st.session_state["maintenance_results"] = {
        "publications": {"unpublished": [], "working": [],
                         "replayed": ["/lib/02/a.pdf", "/lib/02/b.pdf", "/lib/03/c.pdf"]},
    }
    cockpit.render_maintenance()
    text = rendered_text(cockpit.st)
    assert "3 paper(s) were not asked again" in text
    assert "not a full answer" in text


def test_a_run_with_nothing_replayed_reads_as_before(cockpit):
    from tests.ui.test_cockpit_renders_content import rendered_text
    cockpit.st.session_state["maintenance_results"] = {
        "publications": {"unpublished": [{"file": "x.pdf"}], "working": []},
    }
    cockpit.render_maintenance()
    text = rendered_text(cockpit.st)
    assert "not asked again" not in text and "not a full answer" not in text
