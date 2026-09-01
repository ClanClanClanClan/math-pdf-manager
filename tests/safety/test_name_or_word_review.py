"""Words that are both a mathematician and an ordinary word get asked about.

THE OWNER'S REQUIREMENT, verbatim: "for words that can be both, this is
usually flagged so that I can check myself. Also, this should be learning, as
new words will be added with times (maybe first appear as a noun, and later
shows up as a mathematician and conversely)".

So there are three obligations:

  1. A word whose evidence is genuinely mixed is HELD BACK and queued, not
     guessed. An unanswered question must not act as a yes.
  2. The owner's answer beats the evidence and survives a re-mine.
  3. When the library's usage later crosses to the other side of the rule,
     the word comes BACK for another look — carrying what it was decided
     against, so the change is visible.

MEASURED over the 25,043 in-scope titles: of 11,779 mined surnames, 10,925
never appear in a title, 731 appear only capitalised, 84 only in lower case,
and 39 appear BOTH ways. 17 of those land in the review band. Holding them
back costs 47 of 1,033 recoveries — mostly "May" (42) and "Bell" (4) — which
the owner buys back by answering 17 questions.
"""
import json

import pytest

import processing.author_vocabulary as av


@pytest.fixture(autouse=True)
def _clear_caches():
    av._CACHE = av._EVIDENCE = av._DECISIONS = None
    yield
    av._CACHE = av._EVIDENCE = av._DECISIONS = None


@pytest.fixture
def vocab(tmp_path):
    """A vocabulary file with one clear name, one clear word, one ambiguous."""
    p = tmp_path / "vocab.json"
    p.write_text(json.dumps({
        "names": ["bourbaki", "law", "green", "may"],
        "evidence": {
            "bourbaki": [64, 0],     # only ever capitalised  -> NAME
            "law": [0, 240],         # only ever lower        -> COMMON
            "green": [6, 10],        # mixed, neither wins    -> REVIEW
            "may": [42, 10],         # 4.2x, under DOMINANCE  -> REVIEW
        },
    }), encoding="utf-8")
    return p


# ------------------------------------------------------------- the verdicts

@pytest.mark.parametrize("up,low,expected", [
    (64, 0, av.NAME),        # nothing argues against it
    (0, 240, av.COMMON),     # the library only ever writes it as a word
    (0, 0, av.NAME),         # never used in a title; nothing can go wrong
    (154, 4, av.NAME),       # Stackelberg — 38x
    (90, 3, av.NAME),        # Black — 30x
    (6, 10, av.REVIEW),      # Green — genuinely mixed
    (42, 10, av.REVIEW),     # May — 4.2x, under the 6x bar
    (5, 6, av.REVIEW),       # back
    (4, 27, av.COMMON),      # root — 6.75x the other way
])
def test_the_evidence_decides_or_defers(up, low, expected):
    assert av.verdict(up, low) == expected


def test_dominance_is_symmetric():
    """Whatever bar a name must clear, a common word clears the same one."""
    n = av.DOMINANCE
    assert av.verdict(n, 1) == av.NAME
    assert av.verdict(1, n) == av.COMMON
    assert av.verdict(n - 1, 1) == av.REVIEW
    assert av.verdict(1, n - 1) == av.REVIEW


# ----------------------------------------------------- holding back, not guessing

def test_a_review_word_is_not_used_as_a_name(vocab, tmp_path):
    """THE POINT. An unanswered question must not act as a yes."""
    names = av.surnames(vocab, tmp_path / "none.json")
    assert "bourbaki" in names
    assert "law" not in names
    assert "green" not in names, "mixed evidence must not silently count as a name"
    assert "may" not in names


def test_a_review_word_is_queued_with_its_evidence(vocab, tmp_path):
    q = av.review_queue(vocab, tmp_path / "none.json")
    words = {r["word"] for r in q}
    assert words == {"green", "may"}, words
    green = next(r for r in q if r["word"] == "green")
    assert (green["capitalised"], green["lower"]) == (6, 10)
    assert green["suggestion"] == av.REVIEW
    assert green["decided"] is None


def test_the_clearly_decided_words_are_not_queued(vocab, tmp_path):
    q = av.review_queue(vocab, tmp_path / "none.json")
    assert not {"bourbaki", "law"} & {r["word"] for r in q}


def test_the_closest_call_is_asked_first(vocab, tmp_path):
    """A 1:1 split is where a human adds something; 40:1 is not."""
    q = av.review_queue(vocab, tmp_path / "none.json")
    assert q[0]["word"] == "green", [r["word"] for r in q]


# ------------------------------------------------------------ the owner's call

def test_a_decision_beats_the_evidence(vocab, tmp_path):
    d = tmp_path / "decisions.json"
    av.save_decision("green", av.NAME, d, evidence=(6, 10))
    av._CACHE = av._EVIDENCE = av._DECISIONS = None
    assert "green" in av.surnames(vocab, d)

    av.save_decision("bourbaki", av.COMMON, d, evidence=(64, 0))
    av._CACHE = av._EVIDENCE = av._DECISIONS = None
    assert "bourbaki" not in av.surnames(vocab, d), (
        "the owner overrules the evidence in BOTH directions"
    )


def test_a_decided_word_leaves_the_queue(vocab, tmp_path):
    d = tmp_path / "decisions.json"
    av.save_decision("green", av.COMMON, d, evidence=(6, 10))
    av._CACHE = av._EVIDENCE = av._DECISIONS = None
    assert "green" not in {r["word"] for r in av.review_queue(vocab, d)}


def test_decisions_survive_a_rewrite_of_the_vocabulary(vocab, tmp_path):
    """A re-mine must never erase an answer — they are separate files."""
    d = tmp_path / "decisions.json"
    av.save_decision("green", av.NAME, d, evidence=(6, 10))
    av.write(["bourbaki", "green", "newname"],
             {"green": (7, 9), "bourbaki": (70, 0)}, vocab)
    av._CACHE = av._EVIDENCE = av._DECISIONS = None
    assert "green" in av.surnames(vocab, d)


def test_a_nonsense_decision_is_refused():
    with pytest.raises(ValueError):
        av.save_decision("green", "maybe")


# --------------------------------------------------------------- the learning

def test_a_word_comes_back_when_the_usage_crosses_over(vocab, tmp_path):
    """"first appear as a noun, and later shows up as a mathematician".

    Decided COMMON on 2 capitals against 30. Later that person publishes and
    the counts read 60 against 30 — no longer a common word by the rule, so
    the word is queued again rather than sitting on a stale answer.

    Note the suggestion is REVIEW, not NAME: 60:30 is 2x, under the 6x bar.
    The evidence has stopped saying "common" without yet saying "name", and
    reporting that honestly is the point.
    """
    d = tmp_path / "decisions.json"
    av.save_decision("green", av.COMMON, d, evidence=(2, 30))
    av.write(["green"], {"green": (60, 30)}, vocab)     # the world moved
    av._CACHE = av._EVIDENCE = av._DECISIONS = None

    q = av.review_queue(vocab, d)
    row = next((r for r in q if r["word"] == "green"), None)
    assert row is not None, "a decision taken on old evidence must be revisited"
    assert row["changed_since_you_decided"] is True
    assert row["decided"] == av.COMMON
    assert row["suggestion"] == av.REVIEW


def test_a_word_that_crosses_all_the_way_to_a_name(vocab, tmp_path):
    """The full journey: common word -> unambiguous mathematician."""
    d = tmp_path / "decisions.json"
    av.save_decision("green", av.COMMON, d, evidence=(2, 30))
    av.write(["green"], {"green": (300, 30)}, vocab)    # 10x, clears the bar
    av._CACHE = av._EVIDENCE = av._DECISIONS = None
    row = next(r for r in av.review_queue(vocab, d) if r["word"] == "green")
    assert row["changed_since_you_decided"] is True
    assert row["suggestion"] == av.NAME


def test_and_conversely(vocab, tmp_path):
    """The owner asked for both directions, so both are tested."""
    d = tmp_path / "decisions.json"
    av.save_decision("green", av.NAME, d, evidence=(30, 2))
    av.write(["green"], {"green": (30, 300)}, vocab)
    av._CACHE = av._EVIDENCE = av._DECISIONS = None
    row = next(r for r in av.review_queue(vocab, d) if r["word"] == "green")
    assert row["changed_since_you_decided"] is True
    assert row["suggestion"] == av.COMMON


def test_a_small_drift_does_not_reopen_a_settled_word(vocab, tmp_path):
    """Otherwise the queue never empties and the owner stops reading it."""
    d = tmp_path / "decisions.json"
    av.save_decision("green", av.NAME, d, evidence=(60, 2))
    av.write(["green"], {"green": (64, 3)}, vocab)      # same verdict, more data
    av._CACHE = av._EVIDENCE = av._DECISIONS = None
    assert "green" not in {r["word"] for r in av.review_queue(vocab, d)}


def test_a_reopened_word_is_asked_before_the_undecided_ones(vocab, tmp_path):
    d = tmp_path / "decisions.json"
    av.save_decision("may", av.COMMON, d, evidence=(1, 40))
    av.write(["green", "may"], {"green": (6, 10), "may": (80, 10)}, vocab)
    av._CACHE = av._EVIDENCE = av._DECISIONS = None
    q = av.review_queue(vocab, d)
    assert q[0]["word"] == "may" and q[0]["changed_since_you_decided"]


def test_a_decision_records_what_it_was_decided_against(tmp_path):
    """Without it there is nothing to compare later usage to."""
    d = tmp_path / "decisions.json"
    av.save_decision("green", av.NAME, d, evidence=(6, 10))
    raw = json.loads(d.read_text())
    assert raw["decisions"]["green"]["decided_against"] == [6, 10]


def test_a_decision_with_no_evidence_never_reopens(tmp_path, vocab):
    """An answer given without recorded evidence is trusted indefinitely.

    It is the honest behaviour: with nothing to compare against, "has this
    changed?" is UNKNOWN, and reopening on UNKNOWN would nag for ever.
    """
    d = tmp_path / "decisions.json"
    av.save_decision("green", av.NAME, d)
    av.write(["green"], {"green": (1, 999)}, vocab)
    av._CACHE = av._EVIDENCE = av._DECISIONS = None
    assert "green" not in {r["word"] for r in av.review_queue(vocab, d)}


# ------------------------------------------------------------ degrading safely

def test_everything_degrades_when_the_files_are_missing(tmp_path):
    missing = tmp_path / "nope.json"
    assert av.surnames(missing, missing) == set()
    assert av.review_queue(missing, missing) == []
    assert av.load_decisions(missing) == {}


def test_a_corrupt_decisions_file_does_not_take_the_page_down(tmp_path, vocab):
    d = tmp_path / "decisions.json"
    d.write_text("{ this is not json", encoding="utf-8")
    assert av.load_decisions(d) == {}
    assert "bourbaki" in av.surnames(vocab, d)


def test_a_decision_for_an_unmined_word_is_still_honoured(vocab, tmp_path):
    """The owner may know a name the author blocks have never seen."""
    d = tmp_path / "decisions.json"
    av.save_decision("gronwall", av.NAME, d, evidence=None)
    av._CACHE = av._EVIDENCE = av._DECISIONS = None
    assert "gronwall" in av.surnames(vocab, d)
