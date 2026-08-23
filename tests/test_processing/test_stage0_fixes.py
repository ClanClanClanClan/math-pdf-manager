"""Five defects that each looked like a typo and each cost a capability.

Every one was found by measurement rather than by reading, and every one
had been in the tree long enough to shape the library.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _escape_pdf  # noqa: E402


def write_pdf(path: Path, *, title="", author="", created="") -> Path:
    """A minimal PDF whose Info dict can carry a /CreationDate.

    The shared harness builder has no date field, and the date is the
    whole point here.
    """
    parts = []
    if title:
        parts.append(f"/Title ({_escape_pdf(title)})")
    if author:
        parts.append(f"/Author ({_escape_pdf(author)})")
    if created:
        parts.append(f"/CreationDate ({created})")
    info = " ".join(parts)
    body = (
        "%PDF-1.4\n"
        "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        "3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << >> "
        "/MediaBox [0 0 612 792] >>\nendobj\n"
        f"4 0 obj\n<< {info} >>\nendobj\n"
        "trailer\n<< /Root 1 0 R /Info 4 0 R >>\n%%EOF\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body.encode("latin-1", "replace"))
    return path


class TestTheYearCanBeRead:
    """A PDF creation date is "D:20250807120000Z" — the year is followed
    by a DIGIT, so the old pattern's trailing \\b could never match.

    Measured before the fix: of 519 sampled inbox PDFs, 121 carried a
    creationDate, every one D:-prefixed, and the pattern matched 0.
    Two capabilities were silently off as a result — the year
    subdirectory under `03 - Working papers`, which 4,053 of the 4,059
    existing working papers have, and the owner's 02-vs-03 age policy,
    which is gated on this field.
    """

    @pytest.mark.parametrize("created,expected", [
        ("D:20250807120000Z", 2025),          # the real, universal shape
        ("D:20250807120000+02'00'", 2025),    # with a UTC offset
        ("D:19991231235959Z", 1999),
        ("2021-04-07T10:00:00Z", 2021),       # some producers write ISO
        ("D:20030101000000", 2003),           # no timezone at all
    ])
    def test_a_real_creation_date_yields_its_year(self, tmp_path, created,
                                                  expected):
        from processing.ingest import extract_metadata_from_pdf
        pdf = write_pdf(tmp_path / "p.pdf", title="A paper", created=created)
        assert extract_metadata_from_pdf(pdf).get("year") == expected

    def test_a_trailing_word_boundary_would_break_every_one_of_them(self):
        """The regression guard. Re-adding \\b passes any test that only
        uses a bare "2025", so the guard has to use the real format."""
        for date in ("D:20250807120000Z", "D:19991231235959Z"):
            assert re.search(r"\b(19\d{2}|20\d{2})", date), date
            assert not re.search(r"\b(19\d{2}|20\d{2})\b", date), (
                f"{date} matches WITH a trailing boundary — the guard has "
                "stopped guarding")

    def test_an_absent_date_yields_no_year(self, tmp_path):
        from processing.ingest import extract_metadata_from_pdf
        pdf = write_pdf(tmp_path / "p.pdf", title="A paper")
        assert extract_metadata_from_pdf(pdf).get("year") is None

    @pytest.mark.parametrize("created", ["D:20990101000000Z",
                                         "D:20510101000000Z"])
    def test_a_future_year_is_still_rejected(self, tmp_path, created):
        """Loosening the pattern must not loosen the range check.

        The dates have to be FUTURE ones. My first version used 1850 and
        2999, which the pattern never matches in the first place — so
        deleting the range check entirely left the test green. A
        malformed date really does produce years like these: a wrong
        system clock stamps 2099 and the paper files under a directory
        that sorts after everything.
        """
        from processing.ingest import extract_metadata_from_pdf
        pdf = write_pdf(tmp_path / "p.pdf", title="A paper", created=created)
        year = extract_metadata_from_pdf(pdf).get("year")
        assert year is None or 1900 <= year <= datetime.now().year


class TestTheAutoFileThresholdGatesOnlyTheSilentPath:
    """An audit recommended raising this constant 0.75 -> 0.80 on the
    strength of a precision measurement. The measurement was taken
    through pipeline_preview, which never reads this constant.

    These tests pin the two facts that make the recommendation
    inapplicable HERE, so nobody re-applies it from the report alone.
    """

    def test_an_unambiguous_paper_sits_exactly_ON_the_threshold(self):
        """_confidence is strength x dominance with a full-strength score
        of 4.0, and a clear paper classified on a title scores 3.0 —
        uncontested but not full strength, i.e. exactly 0.75. Raising the
        bar above it does not trade recall for precision on this path;
        it stops auto-filing altogether."""
        from processing.publication_topic_router import (
            AUTO_CONFIDENCE, resolve_topic)
        for title in ("Reflected BSDEs and optimal stopping",
                      "Team-optimal closed-loop Stackelberg strategies"):
            d = resolve_topic(title)
            assert d.topic_code is not None, title
            assert d.confidence == 0.75, (title, d.confidence)
            assert d.confidence >= AUTO_CONFIDENCE, (
                "an unambiguous paper no longer auto-files — this "
                "constant has been raised above the score such papers "
                "actually reach")

    def test_the_cockpit_preview_does_not_read_this_constant(self):
        """The load-bearing fact. If pipeline_preview ever starts reading
        it, the two populations are coupled and the audit's number
        becomes relevant again — so this should fail loudly then."""
        src = (Path(__file__).resolve().parents[2] / "src" / "processing" /
               "pipeline_preview.py").read_text(encoding="utf-8")
        assert "AUTO_CONFIDENCE" not in src

    def test_a_paper_below_it_is_suggested_rather_than_filed(self):
        from processing.publication_topic_router import (
            AUTO_CONFIDENCE, REVIEW_CONFIDENCE)
        assert REVIEW_CONFIDENCE < AUTO_CONFIDENCE, (
            "the review band must be non-empty, or every paper is either "
            "auto-filed or ignored and nothing ever reaches the owner")


class TestAProgressCallbackCannotDiscardAScan:
    """The handler whose comment says "progress reporting must never
    abort a scan" raised NameError, because the module never defined a
    logger. The cockpit is the only caller that passes a callback, and
    the scan it discards takes about ten minutes.
    """

    def test_the_module_has_the_logger_its_handler_uses(self):
        import processing.pipeline_preview as pp
        assert hasattr(pp, "logger")

    def test_a_raising_callback_does_not_abort(self, tmp_path):
        import processing.pipeline_preview as pp
        for i in range(3):
            p = tmp_path / "01 - Published papers" / "S" / f"Smith, J. - Paper {i}.pdf"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"%PDF-1.4\n%%EOF\n")

        def hostile(*_a, **_k):
            raise RuntimeError("the UI went away")

        summary, _proposals = pp.preview_topic_filing(
            tmp_path, progress=hostile)
        assert summary.scanned == 3, (
            "a raising progress callback threw the whole scan away")


class TestARefusedPaperLeavesNothingBehind:
    """The gate used to run AFTER the copy.

    bulk_sort called ingest_paper (which copies), then checked the name,
    then returned ok=False without undoing anything. A scratch run
    reported "filed 6, failed 9" with fifteen PDFs on disk and fifteen
    sidecars asserting the rejects had been ingested properly. On the
    real inbox that is 197 junk-named PDFs written into the library under
    a message saying they were left behind.

    The existing test for this mocked ingest_paper away and asserted only
    that ok was False and the source still existed. It never asserted
    that a destination was NOT created, which is the only thing that
    actually matters.
    """

    @pytest.fixture
    def offline(self, monkeypatch):
        """No test may reach the network.

        Discovered the hard way: a fixture PDF named after a real arXiv
        id made this suite call arxiv.org, so the result depended on
        someone else's uptime and on a paper's metadata never changing.
        """
        import urllib.request

        def refuse(*a, **k):
            raise AssertionError("a test tried to open a network connection")
        monkeypatch.setattr(urllib.request, "urlopen", refuse)
        return refuse

    @pytest.fixture
    def lib(self, tmp_path):
        for d in ("01 - Published papers", "03 - Working papers",
                  "12 - To be sorted"):
            (tmp_path / d).mkdir(parents=True, exist_ok=True)
        return tmp_path

    def _pdfs_in_library(self, lib):
        return {p for p in lib.rglob("*.pdf")
                if "12 - To be sorted" not in p.parts}

    def test_a_junk_named_arrival_writes_no_file(self, lib, offline):
        """The name must carry NO resolvable identifier.

        My first version used "2105.10623v1.pdf" — a real arXiv id — and
        the test failed because the pipeline resolved it against the live
        arXiv API and produced the correct paper. Two lessons: the gate
        was right, and the suite was reaching the network. Hence the
        `offline` fixture below.
        """
        from processing.ingest import ingest_paper
        src = write_pdf(lib / "12 - To be sorted" / "scan0001.pdf")
        before = self._pdfs_in_library(lib)

        result = ingest_paper(src, library_root=lib, status="working",
                              dry_run=False)

        assert result["success"] is False
        assert result["identification_state"] == "unidentified"
        assert self._pdfs_in_library(lib) == before, (
            "a refused paper was still copied into the library")
        assert not list(lib.rglob("*.meta.json")), (
            "a sidecar was written asserting the reject had been ingested")
        assert src.exists(), "and the original must still be where it was"
        assert not result["destination"], (
            "a refused paper reported a destination it was never written "
            "to — the cockpit renders that field, so this is the "
            "shows-one-thing-does-another failure in miniature")
        assert not result["actions"], (
            "and it reported actions it did not take")

    def test_a_title_that_fell_back_to_the_stem_writes_no_file(self, lib, offline):
        """The /Author field in this corpus contains "Administrator",
        "Windows User", "Springer" and — from Preview re-saves — the
        owner's own name on papers he did not write. An author without a
        title is not an identification."""
        from processing.ingest import ingest_paper
        src = write_pdf(lib / "12 - To be sorted" / "sdarticle.pdf",
                        author="Windows User")
        before = self._pdfs_in_library(lib)
        result = ingest_paper(src, library_root=lib, status="working",
                              dry_run=False)
        assert result["success"] is False
        assert self._pdfs_in_library(lib) == before

    def test_the_watcher_path_inherits_the_same_gate(self, lib, offline):
        """The watcher calls ingest_paper directly and had no gate, while
        shipping with delete_source: true — so a junk-named paper was
        filed as a success, a notification fired, and the original was
        moved out of the inbox. The watcher only retires the source when
        result["success"] is true, so this assertion is what protects
        the original."""
        from processing.ingest import ingest_paper
        src = write_pdf(lib / "12 - To be sorted" / "main.pdf")
        result = ingest_paper(src, library_root=lib, status="working",
                              dry_run=False, dedup_check=True,
                              variant_check=True)
        assert result["success"] is False

    def test_a_real_extraction_still_files(self, lib):
        from processing.ingest import ingest_paper
        src = write_pdf(lib / "12 - To be sorted" / "whatever.pdf",
                        title="On the rate of escape of random walks",
                        author="Bass, R.")
        result = ingest_paper(src, library_root=lib, status="published",
                              dry_run=False)
        assert result["success"] is True, result.get("error")
        assert result["identification_state"] == "identified"
        assert self._pdfs_in_library(lib), "a good paper was not filed"

    def test_an_arrival_already_in_house_form_is_accepted(self, lib):
        """Its title equals its stem for the good reason that someone
        already named it properly. 22 of the inbox's papers are like
        this and they must not be treated as failures."""
        from processing.ingest import ingest_paper
        src = write_pdf(lib / "12 - To be sorted" /
                        "Yor, M. - Some aspects of Brownian motion.pdf")
        result = ingest_paper(src, library_root=lib, status="published",
                              dry_run=False)
        assert result["success"] is True, result.get("error")

    def test_the_owner_naming_it_himself_is_an_identification(self, lib, offline):
        """A hand-typed name IS the identification, so the gate must not
        veto it — otherwise the one reliable source of truth in the
        system is the one thing that cannot get a paper filed."""
        from processing.ingest import ingest_paper
        src = write_pdf(lib / "12 - To be sorted" / "scan0001.pdf")
        result = ingest_paper(
            src, library_root=lib, status="working", dry_run=False,
            canonical_override="Kabanov, Yu. M. - On a maximum principle.pdf")
        assert result["success"] is True, result.get("error")

    def test_force_is_available_for_an_explicit_override(self, lib, offline):
        from processing.ingest import ingest_paper
        src = write_pdf(lib / "12 - To be sorted" / "scan0001.pdf")
        assert ingest_paper(src, library_root=lib, status="working",
                            dry_run=False, force=True)["success"] is True

    def test_the_verdict_is_reported_even_when_it_passes(self, lib):
        """Three states, never two. A caller must be able to tell "checked
        and fine" from "not checked"."""
        from processing.ingest import ingest_paper
        src = write_pdf(lib / "12 - To be sorted" / "whatever.pdf",
                        title="On the rate of escape of random walks",
                        author="Bass, R.")
        result = ingest_paper(src, library_root=lib, status="published",
                              dry_run=True)
        assert result["identification_state"] in (
            "identified", "needs_review", "unidentified")


class TestATitleWithoutAnAuthorIsNotAnIdentification:
    """Found by running the gate against 40 real inbox papers rather than
    by reading it.

    Three came through: "LLM Embedding for Regression Priors", "Systems
    of Singularly Perturbed Forward-Backward Stochastic Differential
    Equations and Control Problems", and "Scannable Document" — a
    scanner's default title. Each has a title, so `title_from_metadata`
    is true; each differs from its source stem, so the
    nothing-was-extracted rule misses it; and each has no author, so it
    files under Z/ where the library already keeps 201 such arrivals
    that nobody has gone back to.
    """

    @pytest.mark.parametrize("canonical", [
        "Scannable Document.pdf",
        "LLM Embedding for Regression Priors.pdf",
        "Systems of Singularly Perturbed Forward-Backward SDEs.pdf",
    ])
    def test_an_authorless_name_is_held_for_review(self, canonical):
        from processing.ingest import identification_state, NEEDS_REVIEW
        state, why = identification_state(canonical, "whatever-the-source-was",
                                          title_from_metadata=True)
        assert state == NEEDS_REVIEW, canonical
        assert "no author" in why

    def test_a_name_with_an_author_still_passes(self):
        from processing.ingest import identification_state, IDENTIFIED
        state, _ = identification_state(
            "Bass, R. - On the rate of escape of random walks.pdf",
            "sdarticle", title_from_metadata=True)
        assert state == IDENTIFIED

    def test_the_batch_row_carries_the_verdict(self, tmp_path):
        """Without this the cockpit can only say ok/not-ok, and cannot
        tell the owner whether a paper was checked and passed or never
        checked at all."""
        import inspect
        from processing import bulk_sort as bs
        src = inspect.getsource(bs.sort_one)
        assert 'result["identification_state"]' in src
