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

    def test_an_unambiguous_paper_scores_exactly_the_threshold(self):
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
