"""A co-occurrence keyword means "these words are near each other".

32 of the topic patterns are of the form `\\bA\\b.*\\bB\\b`. They read as
phrases and were written for titles, but they are matched against up to
4,000 characters of body text, where they assert almost nothing.

Measured over the real inbox before the bound: of the 213 papers filed
automatically, the winning match spanned a median of 2,083 characters
and at most 3,901. A paper mentioning "network" on page one and
"optimal control" on page two was filed as 07e on that evidence — which
is how a neural-network HJB paper landed there and had to be pulled back
out by hand.
"""
from __future__ import annotations

import pytest

from processing.publication_topic_router import resolve_topic
from processing.topic_classifier import _MAX_WILDCARD_GAP, classify_by_keywords


def spread(a: str, b: str, gap: int) -> str:
    """Two anchors separated by `gap` characters of plausible filler."""
    filler = "and we then consider the general setting in some detail. "
    pad = (filler * (gap // len(filler) + 1))[:gap]
    return f"{a} {pad} {b}"


class TestTheGapIsBounded:

    def test_anchors_a_page_apart_do_not_match(self):
        """The real failure, reproduced: a neural-network paper that also
        mentions Hamilton-Jacobi somewhere later."""
        text = spread("We study neural network approximations",
                      "the Hamilton-Jacobi-Bellman equation", 1800)
        d = resolve_topic(text)
        assert d.topic_code != "07e", (
            "a paper matched across 1,800 characters of body text")

    def test_anchors_in_one_phrase_still_match(self):
        """The bound must not break the patterns' actual purpose."""
        d = resolve_topic("A principal-agent model with moral hazard")
        assert d.topic_code == "07b"
        assert d.confidence >= 0.75

    @pytest.mark.parametrize("gap,should_match", [
        (10, True),
        (_MAX_WILDCARD_GAP - 20, True),
        (_MAX_WILDCARD_GAP + 200, False),
        (2000, False),
    ])
    def test_the_boundary_is_where_it_says_it_is(self, gap, should_match):
        text = spread("optimal control", "on networks", gap)
        hit = any(r["topic_code"] == "07e"
                  for r in classify_by_keywords(text, ""))
        assert hit is should_match, f"gap={gap}"


class TestWhatTheBoundMustNotBreak:

    def test_a_hyper_specific_single_keyword_still_auto_files(self):
        """The reason the threshold was NOT raised instead. A primary
        like "BSDE" essentially never appears off-topic, so one hit is
        good evidence; blanket-requiring two would have cost 102 papers
        their automatic filing to fix a problem they did not cause."""
        for title in ("Reflected BSDEs and obstacle problems",
                      "Stackelberg games in continuous time"):
            d = resolve_topic(title)
            assert d.topic_code is not None, title
            assert d.auto, title

    def test_patterns_without_a_wildcard_are_untouched(self):
        d = resolve_topic("On g-expectation and its applications")
        assert d.topic_code == "07a"

    def test_matching_is_still_case_insensitive(self):
        """The bound is applied inside a cached compile; losing the
        IGNORECASE flag there would be invisible in the common case."""
        assert resolve_topic("REFLECTED BSDES").topic_code == "07a"
        assert resolve_topic("reflected bsdes").topic_code == "07a"

    def test_a_generic_word_pair_no_longer_carries_a_topic_alone(self):
        """Nothing in the tree should be able to claim a topic on two
        common words found anywhere in four pages."""
        text = spread("we consider a control problem", "posed on graphs", 3000)
        assert resolve_topic(text).topic_code is None


class TestSecondaryPatternsAreBoundedToo:
    """A secondary keyword is worth 1.0, so a spurious one cannot invent
    a topic on its own — but it can push an uncontested single primary
    from 3.0 to 4.0, which is exactly the step from "75% confident" to
    "100% confident" in the cockpit.

    `\\bPardoux\\b.*\\bPeng\\b` is the case: two names that co-occur in one
    citation are strong evidence, and two names appearing on different
    pages of a bibliography are not.
    """

    def test_a_citation_in_one_phrase_raises_confidence(self):
        d = resolve_topic(
            "Reflected BSDEs. See Pardoux and Peng for the foundational result.")
        assert d.topic_code == "07a"
        assert d.confidence == 1.0

    def test_the_same_two_names_pages_apart_do_not(self):
        text = spread("Reflected BSDEs. See Pardoux for the original.",
                      "Peng later extended this.", 2000)
        d = resolve_topic(text)
        assert d.topic_code == "07a", "the primary hit must still stand"
        assert d.confidence == 0.75, (
            "a secondary matched across 2,000 characters inflated the "
            "confidence the cockpit shows the owner")
