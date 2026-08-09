"""The ingest namer may repair characters; it may not edit the title.

A filename records what a paper is CALLED.  Rewriting the author's words
is not normalisation, and the failure was not hypothetical: the ingest
path (arxivbot/models/cmo.py) returns check_filename's corrected_filename
wholesale, so a number-spelling fixer filed "AR(1) processes" as
"AR(one) processes" and would have rewritten 193 existing titles.

It was not even self-consistent — it only handled a single digit, giving
"Lectures 5 and 6" -> "Lectures five and 6" — and it disagreed with
move_normalizer, which keeps the original title, so the same paper had
two canonical names depending on which path last touched it.
"""
from __future__ import annotations

import pytest

from validators.filename_checker.core import _digits_of, check_filename


def _ingest(name: str) -> str:
    """Exactly what cmo.py does at ingest."""
    res = check_filename(name, auto_fix_authors=True, auto_fix_nfc=True,
                         sentence_case=False)
    return res.corrected_filename or name


class TestTheTitleSurvivesIngest:

    @pytest.mark.parametrize("name", [
        # Mathematics the fixer's heuristic did not recognise.
        "Smith, J. - AR(1) processes and GL(3) representations.pdf",
        "Smith, J. - A study of SU(2) gauge theory.pdf",
        "Smith, J. - GARCH(1,1) volatility models.pdf",
        "Smith, J. - L^2 estimates for 4 classes of operators.pdf",
        # Ordinary prose numbers are the author's words too.
        "Smith, J. - Lectures 5 and 6 on income distribution.pdf",
        "Smith, J. - The magic of 8 and 24.pdf",
        "Smith, J. - Lecture 2 - key facts on wealth distribution.pdf",
        "Smith, J. - How to beat the 1:e-strategy of best choice.pdf",
    ])
    def test_ingest_does_not_rewrite_the_title(self, name):
        assert _ingest(name) == name

    def test_the_author_block_is_still_fixed(self):
        """Removing the title fixer must not disable the author fixer."""
        assert _ingest("Smith,J. - GARCH(1,1) volatility models.pdf") == \
            "Smith, J. - GARCH(1,1) volatility models.pdf"


class TestTheDigitPostcondition:
    """The backstop, so this class of bug cannot return.

    find_math_regions() returns [] even for "SU(2)", so mathematics is
    protected by nothing but a context heuristic.  This is the actual
    guarantee: a character-level repair cannot change which digits the
    title contains, and a fixer that tries has its output discarded and
    is named in the result messages.
    """

    def test_digits_are_the_witness(self):
        assert _digits_of("AR(1) and GL(3)") == "13"
        assert _digits_of("AR(one) and GL(three)") == ""
        assert _digits_of("Lectures 5 and 6") == "56"

    def test_a_digit_mangling_fixer_is_discarded_and_named(self, monkeypatch):
        from validators.filename_checker import core

        def evil(text, regions, exc, spans):
            return text.replace("1", "one")
        evil.__name__ = "evil_fixer"

        # The fixer list is built inside check_filename from the module
        # globals, so patching the name is enough to inject it.
        monkeypatch.setattr(core, "fix_ellipsis", evil)
        res = check_filename("Smith,J. - AR(1) processes.pdf",
                             auto_fix_authors=True, auto_fix_nfc=True,
                             sentence_case=False)
        out = res.corrected_filename or ""
        assert "AR(1)" in out, "the mangled output must not be shipped"
        assert "AR(one)" not in out
        # …and the culprit is named rather than silently dropped.
        said = " ".join(str(m) for m in getattr(res, "messages", []))
        assert "evil_fixer" in said, said[:300]
