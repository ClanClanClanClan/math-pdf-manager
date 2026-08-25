"""Score find_math_regions against the hand-labelled corpus.

WHY A SCORE AND NOT A PASS/FAIL. Every other test of this module asserts
one title's spans. That catches a regression on a case someone thought
of, and says nothing about the 25,049 it was never pointed at. Three
successive implementations passed their own unit tests while one called
"é" mathematics 4,331 times and another claimed 49.6% of an average
title. Unit tests were not the missing instrument -- a population was.

So this pins the numbers that describe behaviour over a population, with
floors rather than equalities: an improvement should not have to edit the
test, but a regression must fail it.

THE CORPUS is 345 library titles hand-decided by stratified sample,
201 spans over 1,042 characters, 166 titles positive and 179 negative.
Re-deriving it costs a day of labelling, which is why it is a committed
fixture and not a scratch file.
tests/fixtures/math_regions_ground_truth.json carries the sampling frame
and the two conventions that make the labels reproducible.

WHY THE FLOORS MOVED, 2026-08-25
---------------------------------
They were set just under the SCANNER's figures -- precision 0.67, recall
0.86, exact 270, share 0.12 -- and the scanner has been replaced by a
recursive-descent parser that measures:

              precision   recall   exact   claim share
    scanner       0.6809   0.8724     272        5.03%
    parser        1.0000   0.9962     343        3.91%
    gold labels        —        —     345        3.92%

The old floors PASS UNCHANGED at 1.000 / 0.996 / 343. That is the whole
problem: every one of those figures could fall the entire way back to the
scanner's and this file would stay green, so the measured gain -- 71 more
titles exactly right -- was protected by nothing at all. The floors below
sit just under the parser's real numbers instead.

They are floors, not equalities, and the slack is stated per test so that
a genuine trade (one false-positive character bought for five true ones)
does not require editing a test, while a regression does.

AND WHY THE AGGREGATE IS NOT ENOUGH
------------------------------------
Precision and recall over the pooled corpus average two populations that
fail in opposite directions, and the pooled number hides which one moved.
MEASURED: the scanner's precision problem is almost entirely on POSITIVE
titles -- it gets 178 of the 179 negatives clean, the same as the parser,
and 94 of the 166 positives exactly right against the parser's 164. A
detector could lose half the positives and still show a respectable
pooled precision. So the two strata are floored separately below, which
is where the 71-title gain actually lives.
"""
import json
import pathlib

import pytest

from core.math_regions import find_math_regions

_FIXTURE = (pathlib.Path(__file__).resolve().parents[1]
            / "fixtures" / "math_regions_ground_truth.json")

# ── the floors, in one place so that loosening one is a visible edit ─────
#
# Each is followed by the figure it was measured just under, on
# 2026-08-25, and by the scanner figure it must NOT tolerate.
FLOOR_PRECISION = 0.995     # measured 1.000000; scanner 0.680899
FLOOR_RECALL = 0.99         # measured 0.996161; scanner 0.872361
FLOOR_EXACT = 340           # measured 343 of 345; scanner 272
FLOOR_POSITIVES_EXACT = 163  # measured 164 of 166; scanner 94
FLOOR_NEGATIVES_CLEAN = 179  # measured 179 of 179; scanner 178
CEIL_CLAIM_SHARE = 0.045    # measured 0.039089; gold 0.039239; scanner 0.050273

#: What the implementation these floors replaced actually scored. Kept as
#: data so that ``test_the_floors_still_exclude_the_scanner`` can check the
#: floors against it instead of against a comment.
SCANNER = {"precision": 0.680899, "recall": 0.872361, "exact": 272,
           "positives_exact": 94, "negatives_clean": 178, "share": 0.050273}


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
    positives = positives_exact = 0
    negatives = negatives_clean = 0
    claimed = total = 0
    misses, falses = [], []
    for r in corpus:
        gold = _chars(r["math_spans"])
        got = _chars(find_math_regions(r["title"]))
        tp += len(gold & got)
        fp += len(got - gold)
        fn += len(gold - got)
        claimed += len(got)
        total += len(r["title"])
        if gold == got:
            exact += 1
        elif got - gold:
            falses.append(r["title"])
        else:
            misses.append(r["title"])
        if r["math_spans"]:
            positives += 1
            positives_exact += gold == got
        else:
            negatives += 1
            negatives_clean += not got
    assert positives == 166 and negatives == 179, (
        "the corpus strata changed size; the per-stratum floors below were "
        f"measured on 166 positive / 179 negative, this is {positives}/{negatives}"
    )
    return {
        "precision": tp / (tp + fp) if tp + fp else 1.0,
        "recall": tp / (tp + fn) if tp + fn else 1.0,
        "exact": exact,
        "positives_exact": positives_exact,
        "negatives_clean": negatives_clean,
        "share": claimed / total,
        "falses": falses,
        "misses": misses,
    }


def test_precision_does_not_regress(scored):
    """Over-claiming means the caser is told prose is mathematics and leaves
    it alone -- titles silently stop being normalised, with no error and no
    counter. The floor allows about five false-positive characters in the
    1,038 currently claimed, so a trade is possible without editing this."""
    assert scored["precision"] >= FLOOR_PRECISION, (
        f"precision fell to {scored['precision']:.4f}; it was 1.0000. "
        f"Titles that acquired a false span: {scored['falses'][:5]}"
    )


def test_recall_does_not_regress(scored):
    """Under-claiming means the caser RECASES REAL MATHEMATICS: 'L^2' becomes
    'l^2', 'AR(1)' becomes 'Ar(1)'. The floor allows about ten missed
    characters in the gold 1,042; four are missed today and both titles that
    lose them are pinned by name in the suite's TestDeclaredPrices."""
    assert scored["recall"] >= FLOOR_RECALL, (
        f"recall fell to {scored['recall']:.4f}; it was 0.9962. "
        f"Titles that lost gold characters: {scored['misses'][:5]}"
    )


def test_exactly_right_on_almost_every_title(scored):
    """The number a human would check. Character precision and recall can
    both look healthy while the spans are in the wrong PLACES; this cannot.
    Three titles of slack under the measured 343."""
    assert scored["exact"] >= FLOOR_EXACT, (
        f"exact-match titles fell to {scored['exact']}; it was 343 of 345. "
        f"The two it never gets are the colon-ratio and the bare Euler e."
    )


def test_the_positive_stratum_does_not_regress(scored):
    """Where the gain actually is.

    MEASURED: the scanner got 94 of the 166 titles that contain mathematics
    exactly right; this gets 164. That 70-title difference is the whole
    landing, and the pooled precision figure above does not isolate it --
    a detector could halve this number and still score well pooled, because
    179 of the 345 titles have no mathematics to get wrong.
    """
    assert scored["positives_exact"] >= FLOOR_POSITIVES_EXACT, (
        f"exactly-right POSITIVE titles fell to {scored['positives_exact']} "
        f"of 166; it was 164, and the scanner this replaced managed 94."
    )


def test_no_negative_title_acquires_a_span(scored):
    """The other stratum, and the only floor here that sits at its ceiling.

    A negative title is one the labeller decided contains NO mathematics, so
    every span on one is a false positive and the only direction available is
    down: there is no improvement for this floor to block. 179 of 179 are
    clean; the scanner managed 178, so 178 would be a floor that the
    implementation being replaced passes.
    """
    assert scored["negatives_clean"] >= FLOOR_NEGATIVES_CLEAN, (
        f"{179 - scored['negatives_clean']} of the 179 titles labelled "
        f"'no mathematics here' acquired a span. Those titles stop being "
        f"normalised entirely."
    )


def test_the_average_claim_stays_near_the_true_coverage(scored):
    """True labelled coverage is 3.92% of the corpus's 26,555 characters.

    Any implementation whose average claim is far above that is over-reaching
    by construction, whatever its per-case tests say. math_utils averaged
    49.6%; the scanner 5.03%; this claims 3.91%, marginally UNDER gold. The
    ceiling of 4.5% is tight enough to be worth having, where the previous
    12% was not -- 12% passes every implementation ever written here except
    math_utils.
    """
    assert scored["share"] <= CEIL_CLAIM_SHARE, (
        f"claims {scored['share']:.2%} of the corpus; gold is 3.92%"
    )


def test_the_floors_still_exclude_the_implementation_they_replaced(scored):
    """A ratchet is only a ratchet while nobody quietly winds it back.

    The failure this file exists to prevent happened once already: the floors
    were left at the scanner's figures after the parser landed, so the entire
    measured gain was unprotected and a regression all the way back would
    have gone green. This asserts the floors against the SCANNER's recorded
    scores rather than against a comment, so lowering one to make a red test
    pass fails here instead.

    It is a test of the test. If the corpus is ever re-labelled these
    constants are stale and this is the test that says so.
    """
    assert FLOOR_PRECISION > SCANNER["precision"]
    assert FLOOR_RECALL > SCANNER["recall"]
    assert FLOOR_EXACT > SCANNER["exact"]
    assert FLOOR_POSITIVES_EXACT > SCANNER["positives_exact"]
    assert FLOOR_NEGATIVES_CLEAN > SCANNER["negatives_clean"]
    assert CEIL_CLAIM_SHARE < SCANNER["share"]
    # …and every floor is genuinely BELOW what is measured today, or it is an
    # equality dressed as a floor and the next honest improvement fails it.
    assert FLOOR_PRECISION <= scored["precision"]
    assert FLOOR_RECALL <= scored["recall"]
    assert FLOOR_EXACT <= scored["exact"]
    assert FLOOR_POSITIVES_EXACT <= scored["positives_exact"]
    assert CEIL_CLAIM_SHARE >= scored["share"]


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


def test_the_fixture_still_describes_itself(corpus):
    """A fixture that loses its conventions cannot be re-labelled later, and
    the stratum sizes asserted in ``scored`` are quoted from this README."""
    doc = json.loads(_FIXTURE.read_text())
    assert "_readme" in doc and "acronym" in doc["_readme"].lower()
    assert "166 positive / 179 negative" in doc["_readme"], (
        "the README no longer states the stratum sizes the per-stratum "
        "floors in this file were measured on"
    )
