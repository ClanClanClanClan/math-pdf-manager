r"""The wildcard bound has to be enforced, not hoped for.

The first version of this was ``pattern.replace(".*", ".{0,120}")``. It
worked, and it was safe only because no pattern in the table happened to
use a different spelling. A future ``.+`` or ``[\s\S]*`` would have
restored the four-page roaming with nothing failing anywhere — the same
"safe by accident" shape as every other defect found in this project.
"""
from __future__ import annotations

import pytest

from processing.topic_classifier import (
    _MAX_WILDCARD_GAP,
    TOPICS,
    bound_wildcards,
)


class TestEveryRoamingFormIsBounded:

    @pytest.mark.parametrize("pattern,expected", [
        (r"\ba\b.*\bb\b", r"\ba\b.{0,120}\bb\b"),
        (r"\ba\b.+\bb\b", r"\ba\b.{1,120}\bb\b"),
        (r"\ba\b.*?\bb\b", r"\ba\b.{0,120}?\bb\b"),
        (r"\ba\b.+?\bb\b", r"\ba\b.{1,120}?\bb\b"),
    ])
    def test_it_bounds_the_form(self, pattern, expected):
        assert bound_wildcards(pattern) == expected

    @pytest.mark.parametrize("pattern", [
        r"\ba\b[\s\S]*\bb\b",       # crosses newlines as well
        r"\ba\b[\S\s]+\bb\b",
        r"\ba\b.{5,}\bb\b",         # open-ended upper bound
    ])
    def test_it_REFUSES_what_it_cannot_bound(self, pattern):
        """Silently passing these through is the failure mode. A pattern
        the bounder does not understand must stop the import, not sail
        past it."""
        with pytest.raises(ValueError, match="unbounded"):
            bound_wildcards(pattern)

    def test_it_refuses_a_gap_wider_than_the_limit(self):
        with pytest.raises(ValueError, match="9999"):
            bound_wildcards(r"\ba\b.{0,9999}\bb\b")

    def test_a_word_only_wildcard_is_not_a_span_risk(self):
        r"""``\w*`` cannot leave a word, so it cannot carry a match across
        a phrase and must not be rejected — over-refusing would push
        someone to disable the check."""
        assert bound_wildcards(r"\bnon.commutativ\w*\b") == \
            r"\bnon.commutativ\w*\b".replace(".", ".", 1)

    def test_a_pattern_with_no_wildcard_is_returned_unchanged(self):
        assert bound_wildcards(r"\bg.expectation\b") == r"\bg.expectation\b"


class TestTheLiveTableObeysIt:
    """A property test over the real keyword table, so a new pattern with
    an unbounded wildcard fails here rather than quietly re-filing a
    hundred papers into 07e."""

    @pytest.mark.parametrize("code", sorted(TOPICS))
    def test_every_pattern_in_this_topic_comes_back_bounded(self, code):
        """"bound_wildcards did not raise" is not a postcondition — assert
        that what comes back genuinely has no roaming wildcard left."""
        from processing.topic_classifier import _UNBOUNDED_SPAN
        seen = 0
        for kind in ("primary", "secondary"):
            for pattern in TOPICS[code][kind]:
                bounded = bound_wildcards(pattern)
                assert not _UNBOUNDED_SPAN.search(bounded), (code, pattern)
                seen += 1
        assert seen, f"{code} has no patterns at all — the table is empty"

    def test_no_pattern_can_span_more_than_the_limit(self):
        import re
        span = re.compile(r"(?:\.|\[\\s\\S\]|\[\\S\\s\])\{\d*,(\d+)\}")
        for code, topic in TOPICS.items():
            for kind in ("primary", "secondary"):
                for pattern in topic[kind]:
                    for gap in span.findall(bound_wildcards(pattern)):
                        assert int(gap) <= _MAX_WILDCARD_GAP, (code, pattern)
