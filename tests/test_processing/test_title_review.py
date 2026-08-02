"""The title bucket is ~1,000 proposals; this splits it into decisions."""
from __future__ import annotations

import pytest

from processing.title_review import (
    COSMETIC, FIRSTWORD, CASE, REWRITE,
    classify_proposal, split_titles, word_decisions, proposals_for_words,
)


def _p(old_title, new_title, key=None):
    return {"old": key or old_title, "old_name": f"Doe, J. - {old_title}.pdf",
            "name": f"Doe, J. - {new_title}.pdf", "kind": "title"}


class TestClassify:
    @pytest.mark.parametrize("old,new,expected", [
        # Only the first word gained a capital — that IS sentence case.
        ("sciences mathématiques, 1966", "Sciences mathématiques, 1966", FIRSTWORD),
        ("mathématique, 1991", "Mathématique, 1991", FIRSTWORD),
        # Mid-title case is a real decision.
        ("Trading signals In VIX futures", "Trading signals in VIX futures", CASE),
        ("A study of Integrals", "A study of integrals", CASE),
        # No letter changed at all.
        ("An integral over (0,π)", "An integral over (0, π)", COSMETIC),
        (" Leading space", "Leading space", COSMETIC),
        # The words themselves differ.
        ("Propagation of chaos", "Jourdain, B. - Propagation of chaos", REWRITE),
    ])
    def test_groups(self, old, new, expected):
        assert classify_proposal(f"Doe, J. - {old}.pdf",
                                 f"Doe, J. - {new}.pdf") == expected

    def test_first_word_lowering_is_not_the_safe_group(self):
        # Only lower -> UPPER on the first word is mechanical.  The reverse
        # is a genuine decision and must stay in the review.
        assert classify_proposal("Doe, J. - Sciences x.pdf",
                                 "Doe, J. - sciences x.pdf") == CASE


class TestWordDecisions:
    def test_one_ruling_covers_every_file_with_that_word(self):
        rows = [_p("A study of Integrals", "A study of integrals", "f1"),
                _p("On Integrals again", "On integrals again", "f2")]
        d = word_decisions(rows)
        assert d[("Integrals", "integrals")]["count"] == 2
        assert set(d[("Integrals", "integrals")]["files"]) == {"f1", "f2"}

    def test_a_file_needs_all_its_changes_approved(self):
        # Two different words change in the same title: approving one must
        # NOT rename the file half-way.
        rows = [_p("Trading In Integrals", "Trading in integrals", "f1")]
        partial = {("In", "in")}
        assert proposals_for_words(rows, partial) == []
        full = {("In", "in"), ("Integrals", "integrals")}
        assert len(proposals_for_words(rows, full)) == 1

    def test_unapproved_words_rename_nothing(self):
        rows = [_p("A study of Integrals", "A study of integrals", "f1")]
        assert proposals_for_words(rows, set()) == []


def test_split_covers_every_proposal():
    rows = [_p("sciences x", "Sciences x"), _p("a (0,π) b", "a (0, π) b"),
            _p("Trading In x", "Trading in x")]
    g = split_titles(rows)
    assert sum(len(v) for v in g.values()) == len(rows)
