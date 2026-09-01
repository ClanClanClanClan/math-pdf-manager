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

import processing.casing_vocabulary as av


@pytest.fixture(autouse=True)
def _clear_caches():
    av._CACHE = av._EVIDENCE = av._AUTHORS = av._DECISIONS = None
    yield
    av._CACHE = av._EVIDENCE = av._AUTHORS = av._DECISIONS = None


@pytest.fixture
def vocab(tmp_path):
    """A vocabulary file with one clear name, one clear word, one ambiguous."""
    p = tmp_path / "vocab.json"
    p.write_text(json.dumps({
        "authors": ["bourbaki", "law", "green", "may"],
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
    names = av.preserved(vocab, tmp_path / "none.json")
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
    av._CACHE = av._EVIDENCE = av._AUTHORS = av._DECISIONS = None
    assert "green" in av.preserved(vocab, d)

    av.save_decision("bourbaki", av.COMMON, d, evidence=(64, 0))
    av._CACHE = av._EVIDENCE = av._AUTHORS = av._DECISIONS = None
    assert "bourbaki" not in av.preserved(vocab, d), (
        "the owner overrules the evidence in BOTH directions"
    )


def test_a_decided_word_leaves_the_queue(vocab, tmp_path):
    d = tmp_path / "decisions.json"
    av.save_decision("green", av.COMMON, d, evidence=(6, 10))
    av._CACHE = av._EVIDENCE = av._AUTHORS = av._DECISIONS = None
    assert "green" not in {r["word"] for r in av.review_queue(vocab, d)}


def test_decisions_survive_a_rewrite_of_the_vocabulary(vocab, tmp_path):
    """A re-mine must never erase an answer — they are separate files."""
    d = tmp_path / "decisions.json"
    av.save_decision("green", av.NAME, d, evidence=(6, 10))
    av.write({"green": (7, 9), "bourbaki": (70, 0)},
             ["bourbaki", "green", "newname"], vocab)
    av._CACHE = av._EVIDENCE = av._AUTHORS = av._DECISIONS = None
    assert "green" in av.preserved(vocab, d)


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
    av.write({"green": (60, 30)}, [], vocab)     # the world moved
    av._CACHE = av._EVIDENCE = av._AUTHORS = av._DECISIONS = None

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
    av.write({"green": (300, 30)}, [], vocab)    # 10x, clears the bar
    av._CACHE = av._EVIDENCE = av._AUTHORS = av._DECISIONS = None
    row = next(r for r in av.review_queue(vocab, d) if r["word"] == "green")
    assert row["changed_since_you_decided"] is True
    assert row["suggestion"] == av.NAME


def test_and_conversely(vocab, tmp_path):
    """The owner asked for both directions, so both are tested."""
    d = tmp_path / "decisions.json"
    av.save_decision("green", av.NAME, d, evidence=(30, 2))
    av.write({"green": (30, 300)}, [], vocab)
    av._CACHE = av._EVIDENCE = av._AUTHORS = av._DECISIONS = None
    row = next(r for r in av.review_queue(vocab, d) if r["word"] == "green")
    assert row["changed_since_you_decided"] is True
    assert row["suggestion"] == av.COMMON


def test_a_small_drift_does_not_reopen_a_settled_word(vocab, tmp_path):
    """Otherwise the queue never empties and the owner stops reading it."""
    d = tmp_path / "decisions.json"
    av.save_decision("green", av.NAME, d, evidence=(60, 2))
    av.write({"green": (64, 3)}, [], vocab)      # same verdict, more data
    av._CACHE = av._EVIDENCE = av._AUTHORS = av._DECISIONS = None
    assert "green" not in {r["word"] for r in av.review_queue(vocab, d)}


def test_a_reopened_word_is_asked_before_the_undecided_ones(vocab, tmp_path):
    d = tmp_path / "decisions.json"
    av.save_decision("may", av.COMMON, d, evidence=(1, 40))
    av.write({"green": (6, 10), "may": (80, 10)}, [], vocab)
    av._CACHE = av._EVIDENCE = av._AUTHORS = av._DECISIONS = None
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
    av.write({"green": (1, 999)}, [], vocab)
    av._CACHE = av._EVIDENCE = av._AUTHORS = av._DECISIONS = None
    assert "green" not in {r["word"] for r in av.review_queue(vocab, d)}


# ------------------------------------------------------------ degrading safely

def test_everything_degrades_when_the_files_are_missing(tmp_path):
    missing = tmp_path / "nope.json"
    assert av.preserved(missing, missing) == set()
    assert av.review_queue(missing, missing) == []
    assert av.load_decisions(missing) == {}


def test_a_corrupt_decisions_file_does_not_take_the_page_down(tmp_path, vocab):
    d = tmp_path / "decisions.json"
    d.write_text("{ this is not json", encoding="utf-8")
    assert av.load_decisions(d) == {}
    assert "bourbaki" in av.preserved(vocab, d)


def test_a_decision_for_an_unmined_word_is_still_honoured(vocab, tmp_path):
    """The owner may know a name the author blocks have never seen."""
    d = tmp_path / "decisions.json"
    av.save_decision("gronwall", av.NAME, d, evidence=None)
    av._CACHE = av._EVIDENCE = av._AUTHORS = av._DECISIONS = None
    assert "gronwall" in av.preserved(vocab, d)


class TestTheCensusCoversEveryWord:
    """Months, places and classical eponyms, without a single list.

    The vocabulary used to be author surnames only, which reached 986 of the
    2,964 destroyed capitals. Generalising the census to EVERY mid-title word
    reaches 2,297 — and it does months, places, Roman numerals and
    mathematicians who never published here in one rule, because the library
    already writes "Saint-Flour" 59 times and "flour" never.
    """

    @pytest.mark.parametrize("word", [
        "flour",      # Saint-Flour, 59/0
        "june", "april", "august", "july", "january", "september",
        "japan", "sendai", "paris", "germany", "italy",
        "fock", "landau", "gronwall", "hartree", "bourbaki",
        "ii", "iii", "xii",     # Roman numerals: 224/0, 63/0, 11/0
    ])
    def test_the_library_teaches_it_the_proper_nouns(self, word):
        assert word in av.preserved(), (
            f"{word!r} is written capitalised in this library's titles and "
            f"never in lower case"
        )

    @pytest.mark.parametrize("word", [
        "the", "an", "stochastic", "convex", "law", "risk", "price",
        "posedness", "browniens",
    ])
    def test_and_the_ordinary_words(self, word):
        assert word not in av.preserved(), (
            f"{word!r} is written in lower case throughout this library"
        )

    def test_a_title_that_is_itself_title_cased_is_not_evidence(self, tmp_path):
        """Its capitals are a house style, not a claim about any word."""
        lib = tmp_path / "lib" / "01 - Published papers" / "S"
        lib.mkdir(parents=True)
        (lib / "Smith, A. - A Study Of The Convex Hull Problem.pdf").write_bytes(b"%PDF")
        (lib / "Smith, A. - On the convex hull of a set.pdf").write_bytes(b"%PDF")
        ev, _au = av.mine(tmp_path / "lib")
        up, low = ev.get("convex", (0, 0))
        assert up == 0, (
            f"the Title Cased title must contribute no capitals: got {up}"
        )
        assert low >= 1


class TestTheAuthorFallback:
    """Where the census is silent, the author blocks still speak."""

    def test_a_name_that_never_appears_in_a_title_is_still_kept(self, tmp_path):
        """"Le Cam" and "Le Gall" are why this exists.

        Neither "cam" nor "gall" appears mid-title anywhere in the library,
        so the census has nothing to say about them, and both are authors.
        Without the fallback the caser produced "Le cam" and "Le gall".
        """
        vocab = tmp_path / "v.json"
        av.write({"stochastic": (0, 500)}, ["cam", "gall"], vocab)
        av._CACHE = av._EVIDENCE = av._AUTHORS = av._DECISIONS = None
        keep = av.preserved(vocab, tmp_path / "none.json")
        assert {"cam", "gall"} <= keep
        assert "stochastic" not in keep

    def test_the_census_still_wins_where_it_has_spoken(self, tmp_path):
        """However many people are called Law, "law" is a common word here."""
        vocab = tmp_path / "v.json"
        av.write({"law": (0, 240)}, ["law"], vocab)
        av._CACHE = av._EVIDENCE = av._AUTHORS = av._DECISIONS = None
        assert "law" not in av.preserved(vocab, tmp_path / "none.json"), (
            "the fallback is for silence, not for overruling the evidence"
        )

    def test_the_real_library_keeps_le_cam(self):
        from core.sentence_case import to_sentence_case_academic as f
        out = f("The Le Cam and Le Gall theorems")
        out = out[0] if isinstance(out, tuple) else out
        assert "Le Cam" in out and "Le Gall" in out, out


class TestTheFlaggedClass:
    """French adjectives built from a name: applied, but shown."""

    def test_they_are_flagged_rather_than_held(self, tmp_path):
        vocab = tmp_path / "v.json"
        av.write({"gaussiennes": (4, 0), "bourbaki": (64, 0)}, [], vocab)
        av._CACHE = av._EVIDENCE = av._AUTHORS = av._DECISIONS = None
        q = av.review_queue(vocab, tmp_path / "none.json")
        rows = {r["word"]: r for r in q}
        assert "gaussiennes" in rows, (
            "French lower-cases an adjective built from a name, so a "
            "unanimous library is exactly where it might be wrong"
        )
        assert rows["gaussiennes"]["kind"] == "flagged"
        assert rows["gaussiennes"]["held_back"] is False
        assert "gaussiennes" in av.preserved(vocab, tmp_path / "none.json"), (
            "flagged means shown, not withheld — the measurement is believed "
            "until the owner says otherwise"
        )
        assert "bourbaki" not in rows, "an ordinary name must not be flagged"

    def test_the_plurals_the_census_already_catches_are_not_double_handled(self):
        """gaussiens 9/7 and markoviens 5/1 are HELD by the census itself."""
        rows = {r["word"]: r for r in av.review_queue()}
        for w in ("gaussiens", "markoviens"):
            if w in rows:
                assert rows[w]["kind"] == "held", rows[w]

    def test_a_held_word_outranks_a_flagged_one(self, tmp_path):
        vocab = tmp_path / "v.json"
        av.write({"gaussiennes": (4, 0), "green": (6, 10)}, [], vocab)
        av._CACHE = av._EVIDENCE = av._AUTHORS = av._DECISIONS = None
        q = av.review_queue(vocab, tmp_path / "none.json")
        assert [r["word"] for r in q] == ["green", "gaussiennes"], q


class TestTheWhitelistMayNotImpose:
    """A capitalization_whitelist entry raises a lower-case word.

    MEASURED on the shipped 848-entry list: five bare entries between them
    imposed 267 wrong capitals. "Le" turned "sur le grossissement" into
    "sur Le grossissement" 131 times; "posedness" turned "well-posedness"
    into "well-Posedness" 86 times; then White 23, Bank 18, Hold 9.

    An entry may no longer overrule the library's own usage. This only ever
    blocks an entry from RAISING a lower-case word — an already-capitalised
    phrase is untouched, so no entry loses its ability to fix a spelling or a
    dash.
    """

    @pytest.mark.parametrize("title,must_stay", [
        ("Sur le grossissement des tribus", "le grossissement"),
        ("On the well-posedness of the equation", "well-posedness"),
        ("A study of white noise", "white noise"),
        ("A bank of estimates", "bank of estimates"),
    ])
    def test_a_common_word_is_not_raised(self, title, must_stay):
        """The fragment checked never starts a title — the caser is supposed
        to capitalise the first word, and asserting over it would test the
        wrong thing."""
        from core.sentence_case import to_sentence_case_academic as f
        out = f(title)
        out = out[0] if isinstance(out, tuple) else out
        assert must_stay in out, (
            f"a whitelist entry imposed a capital against the library's own "
            f"usage: {out!r}"
        )

    def test_an_entry_can_still_fix_an_already_capitalised_word(self):
        """The guard must not disarm the whitelist's real job."""
        from core.sentence_case import to_sentence_case_academic as f
        out = f("An Ito formula for processes")
        out = out[0] if isinstance(out, tuple) else out
        assert "Ito" in out or "Itô" in out, out

    def test_is_common_reports_the_librarys_view(self):
        assert av.is_common("le") is True
        assert av.is_common("posedness") is True
        assert av.is_common("bourbaki") is False
        assert av.is_common("zzzznotaword") is False, (
            "an unknown word is not 'common' — that is UNKNOWN, and the "
            "guard must not fire on it"
        )
