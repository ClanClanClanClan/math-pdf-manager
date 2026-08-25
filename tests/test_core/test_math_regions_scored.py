"""Score find_math_regions against the hand-labelled corpus.

WHY A SCORE AND NOT A PASS/FAIL. Every other test of this module asserts
one title's spans. That catches a regression on a case someone thought
of, and says nothing about the 25,049 it was never pointed at. Three
successive implementations passed their own unit tests while one called
"é" mathematics 4,331 times and another claimed 49.6% of an average
title. Unit tests were not the missing instrument -- a population was.

So this pins the two numbers that describe behaviour over a population,
with a floor rather than an equality: an improvement should not have to
edit the test, but a regression must fail it.

THE CORPUS is 345 library titles hand-decided by stratified sample,
201 spans over 1,042 characters. Re-deriving it costs a day of
labelling, which is why it is a committed fixture and not a scratch
file. tests/fixtures/math_regions_ground_truth.json carries the
sampling frame and the two conventions that make the labels
reproducible.

MEASURED at the time of writing (core/math_regions.py at 20f039c):
precision 0.681, recall 0.872, exactly right on 272 of 345. The
floors below sit just under those. They are LOW -- a candidate scoring
1.000/0.996 exists and is documented in docs/math-regions-measured.md;
it is unlanded because it changes no proposed title on this library
and breaks 13 tests. If it lands, raise these floors.
"""
import json
import pathlib

import pytest

from core.math_regions import find_math_regions

_FIXTURE = (pathlib.Path(__file__).resolve().parents[1]
            / "fixtures" / "math_regions_ground_truth.json")


@pytest.fixture(scope="module")
def corpus():
    rows = json.loads(_FIXTURE.read_text())["labelled"]
    assert len(rows) == 345, "the corpus changed size; re-read it before trusting a score"
    return rows


def _chars(spans):
    out = set()
    for s, e in spans:
        out |= set(range(s, e))
    return out


@pytest.fixture(scope="module")
def scored(corpus):
    tp = fp = fn = 0
    exact = 0
    misses, falses = [], []
    for r in corpus:
        gold = _chars(r["math_spans"])
        got = _chars(find_math_regions(r["title"]))
        tp += len(gold & got)
        fp += len(got - gold)
        fn += len(gold - got)
        if gold == got:
            exact += 1
        elif got - gold:
            falses.append(r["title"])
        else:
            misses.append(r["title"])
    return {
        "precision": tp / (tp + fp) if tp + fp else 1.0,
        "recall": tp / (tp + fn) if tp + fn else 1.0,
        "exact": exact,
        "falses": falses,
        "misses": misses,
    }


def test_precision_does_not_regress(scored):
    assert scored["precision"] >= 0.67, (
        f"precision fell to {scored['precision']:.4f}; it was 0.681. "
        f"Over-claiming means the caser is told prose is mathematics and "
        f"leaves it alone -- titles silently stop being normalised."
    )


def test_recall_does_not_regress(scored):
    assert scored["recall"] >= 0.86, (
        f"recall fell to {scored['recall']:.4f}; it was 0.872. "
        f"Under-claiming means the caser RECASES REAL MATHEMATICS: "
        f"'L^2' becomes 'l^2', 'AR(1)' becomes 'Ar(1)'."
    )


def test_exactly_right_on_most_titles(scored):
    assert scored["exact"] >= 270, (
        f"exact-match titles fell to {scored['exact']}; it was 272."
    )


def test_no_span_is_three_or_more_ordinary_english_words(corpus):
    """The pathology that killed the predecessor.

    math_utils grew a region from any operator -- and "-" is one --
    through letters, digits AND spaces to the end of the sentence. One
    span claimed 186 of 189 characters of an English sentence; 3,921
    spans were three or more ordinary English words.

    "Ordinary English word" is decided by the system dictionary, NOT by
    "three or more letters". The first version of this test used the
    letter-count heuristic and flagged
    "Lexp(mu*sqrt(2log(1+L)))-integrable" -- reading `exp`, `sqrt` and
    `log` as English prose. They are function names, and that span is
    entirely mathematics. A test that cannot tell a function name from
    a word is not measuring the pathology it names.
    """
    import re
    words_file = pathlib.Path("/usr/share/dict/words")
    if not words_file.exists():
        pytest.skip("no system dictionary to judge English with")
    english = {w.strip().lower() for w in words_file.read_text().splitlines()
               if len(w.strip()) >= 3}
    # Function names are lexically English-shaped but are mathematics.
    english -= {"exp", "log", "sin", "cos", "tan", "max", "min", "sup",
                "inf", "lim", "det", "dim", "arg", "ker", "mod", "gcd",
                "lcm", "abs", "sgn", "erf", "var", "cov"}
    offenders = []
    for r in corpus:
        for s, e in find_math_regions(r["title"]):
            span = r["title"][s:e]
            hits = [w for w in re.findall(r"[A-Za-z]{3,}", span)
                    if w.lower() in english]
            if len(hits) >= 3:
                offenders.append((r["title"], span, hits))
    assert not offenders, offenders[:5]


def test_the_average_claim_stays_near_the_true_coverage(corpus):
    """True labelled coverage is 4.57% of a title.

    Any implementation whose average claim is far above that is
    over-reaching by construction, whatever its per-case tests say.
    math_utils averaged 49.6%.
    """
    total = claimed = 0
    for r in corpus:
        total += len(r["title"])
        claimed += sum(e - s for s, e in find_math_regions(r["title"]))
    share = claimed / total
    assert share <= 0.12, f"claims {share:.1%} of an average title; truth is 4.6%"


def test_the_fixture_still_describes_itself(corpus):
    """A fixture that loses its conventions cannot be re-labelled later."""
    doc = json.loads(_FIXTURE.read_text())
    assert "_readme" in doc and "acronym" in doc["_readme"].lower()
