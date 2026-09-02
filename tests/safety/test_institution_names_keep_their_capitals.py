"""A generic word is capitalised in a NAME and lower-case in a DESCRIPTION.

The owner asked whether "Rutgers University" or "Rutgers university" is
the pedantically correct form, and whether the answer belongs in the
rules. It is "Rutgers University", and it does.

THE RULE (Chicago 8.68). A generic like *University*, *Society* or
*Institute* is capitalised when it is part of an institution's official
NAME, and lower-case when it is merely descriptive:

    "Rutgers University"               the institution's name
    "the University of Durham"         also a name, generic leading
    "a university course"              a description
    "the Lvov school of mathematics"   a school of THOUGHT, not a place
    "CIMPA summer school"              an event, not an institution

WHY THIS IS ENTRIES AND NOT A HEURISTIC. A mechanical version was
written and MEASURED -- "capitalise the generic when the preceding word
is a proper name" -- and it got 3 of the 6 universities in this library
right while firing on "French school" and "Lvov school", which are
movements in mathematics. It misses "Brown University" because "brown"
is a colour and fires on "Lvov school" because Lvov is a city. Nothing
in the text separates those; only knowing which institutions exist does.
So the knowledge is written down rather than guessed at.

WHAT A CONFIG ENTRY CAN AND CANNOT DO. It only ever PRESERVES a capital
that is already there; it can never impose one. That limit is by design
-- it is what stops a one-line config edit from becoming a bulk rename
of 29k files -- and it is asserted at the bottom of this file. Imposing
a capital on an already-lower-case title is a separate power, reserved
to the owner's own phrase rulings (title_vocab.decide_phrase).

WHY THE LIBRARY HERE IS SYNTHETIC. tests/conftest.py points MATH_LIBRARY
at an empty session library, where NOTHING is provably common, so the
caser preserves every capital and an assertion that a capital survived
would pass without the whitelist being consulted at all. The first
version of this file did exactly that. The fixture below therefore
supplies a census in which the generics ARE common, and
``test_the_census_really_is_live`` fails if that ever stops being true.

MEASURED 2026-09-02 over all 25,252 in-scope PDFs: these entries rename
nothing. They prevent damage; they do not repair any.
"""
import json

import pytest

from processing.title_normalize import propose_title_case
from processing.title_vocab import VOCAB_DIRNAME, VOCAB_FILENAME

# Words the real library's census marks common, and which therefore get
# lowered unless something says otherwise.
# NB "brown" is in the proper-noun whitelist on its own account (Brownian
# motion), so it can never serve as a control here -- the first draft of
# this file used it and the control silently proved nothing.
COMMON = ["brown", "university", "mathematical", "society", "institute",
          "statistical", "indian", "national", "imperial", "school",
          "summer", "french", "lvov", "class", "world", "program"]


@pytest.fixture
def lib(tmp_path):
    """A library whose census marks the generics common."""
    d = tmp_path / VOCAB_DIRNAME
    d.mkdir(parents=True, exist_ok=True)
    (d / VOCAB_FILENAME).write_text(json.dumps(
        {"proper": [], "common": COMMON, "phrases": [], "pending": {}}))
    return tmp_path


def test_the_census_really_is_live(lib):
    """The control. Without this the whole file can pass vacuously.

    If the fixture's census stops being consulted, every assertion below
    becomes "a capital survived in a library with no evidence", which is
    true no matter what the whitelist says.
    """
    got = propose_title_case(
        "Notes from a University, a Society and a School", lib).proposed
    assert got == "Notes from a university, a society and a school", (
        f"the census is not lowering provably-common words: {got!r}")


# --------------------------------------------------------------- names

@pytest.mark.parametrize("title", [
    "A workshop held at Rutgers University in 1991",
    "Lectures given at Brown University",
    "Proceedings of the London Mathematical Society",
    "A report from the Indian Statistical Institute",
    "Held at the University of Durham",
    "The science reports of the Tōhoku Imperial University",
    "Collected papers of the New York University seminar",
    "Introduction to mathematical finance. American Mathematical Society",
])
def test_an_institution_name_keeps_its_capital(lib, title):
    assert propose_title_case(title, lib).proposed == title


# --------------------------------------------------------- descriptions

@pytest.mark.parametrize("title,must_stay", [
    ("Notes for a university course on probability", "university course"),
    ("The lvov school of mathematics", "lvov school"),
    ("A CIMPA summer school on control", "summer school"),
    ("The french school of probability", "french school"),
])
def test_a_descriptive_generic_is_not_raised(lib, title, must_stay):
    out = propose_title_case(title, lib).proposed
    assert must_stay in out, (
        f"a description was capitalised as if it were a name: {out!r}")


def test_the_same_title_can_hold_both_and_must_split_them(lib):
    """The strongest evidence, verbatim from the library.

    One real filename contains a description ("world class university
    program") and a name ("Ajou University"). A rule that cannot tell
    them apart gets one of the two wrong; measured, this splits them.
    """
    t = ("Real options, ambiguity, risk and insurance, world class "
         "university program in financial engineering, Ajou University, "
         "volume two")
    out = propose_title_case(t, lib).proposed
    assert "world class university program" in out, out
    assert "Ajou University" in out, out


# ------------------------------------------------- the structural limit

def test_a_config_entry_can_never_IMPOSE_a_capital(lib):
    """The guarantee that makes entries safe to add in bulk.

    If this ever fails, adding a name to the whitelist becomes a bulk
    rename of the library rather than a preservation rule, and the
    "measure, present, wait" gate has been bypassed by a config edit.
    """
    out = propose_title_case("A workshop held at rutgers university", lib)
    assert "rutgers university" in out.proposed, (
        "a config entry imposed a capital; entries must only preserve, "
        f"got {out.proposed!r}")


# ------------------------------------------- the OTHER caser (validators)
#
# There are two casers and they have deliberately different powers.
# propose_title_case (above) drives moves and ingest and only preserves.
# to_sentence_case_academic drives validators/filename_checker/core.py and
# DOES raise a whitelisted phrase, which is why the guard below has to be
# scoped precisely: too wide and institution names never get fixed, too
# narrow and an ordinary word gets a capital it has not earned.

def _sc(title):
    from core.sentence_case import to_sentence_case_academic
    out = to_sentence_case_academic(title)
    return str(out[0] if isinstance(out, tuple) else out)


@pytest.mark.parametrize("title,want", [
    ("A conference at the university of durham",
     "A conference at the University of Durham"),
    ("Proceedings of the london mathematical society",
     "Proceedings of the London Mathematical Society"),
    ("A workshop at rutgers university",
     "A workshop at Rutgers University"),
    ("Notes from the indian statistical institute",
     "Notes from the Indian Statistical Institute"),
    ("Held at brown university", "Held at Brown University"),
])
def test_a_MULTI_word_entry_may_raise_the_whole_phrase(title, want):
    """A multi-word phrase is specific enough not to collide with prose.

    The guard that stops a whitelist entry raising a common word used to
    look only at the entry's FIRST token, so "University of Durham" was
    blocked because "university" is common on its own (measured: 2
    capitalised against 32 lower-case). Scoping the guard to single-word
    entries is what lets a name be fixed without letting a word be.
    """
    assert _sc(title) == want


@pytest.mark.parametrize("title", [
    "A university course on probability",
    "The society of actuaries met",
    "A school of thought in analysis",
])
def test_a_common_word_is_still_not_raised_on_its_own(title):
    """The other half of the guard: the reason it exists at all."""
    assert _sc(title) == title
