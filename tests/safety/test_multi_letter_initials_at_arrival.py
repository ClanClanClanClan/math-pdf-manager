"""An initial of more than one letter keeps every letter at arrival.

THE RULING (docs/FILENAME_CONVENTION.md 2.2). "Surname, A. B.", and a
transliterated initial keeps all its letters: "Kabanov, Yu. M.",
"Rutickii, Ya. B.". An initial is what ``core.initials`` says -- a capital
plus at most three lower-case letters -- the same rule that spaces them.
Measured 2026-10-15: 174 author blocks in the library carry one (Yu. 154,
Ya. 12, Kh./Ch./Th./Ph. 2 each, Ts./Sh./Sz. 1 each), all intact.

THE DEFECT, found the same day. ``cmo.Author.initials`` built a new paper's
author block from the first character of every given-name token:

    "Yu. M."  ->  "Y. M"        "Ch."  ->  "C"
    "Yu.A."   ->  "Y"           one token, so the "A." was lost as well

and ``library_normalize._fit_to_limit``, which refits an over-long name,
rebuilds author blocks through the same method.

The full stop is what marks a written initial. "Yu" without one is a given
name in full and takes "Y."; deriving "Yu." from a full name would need its
language ("Zhang" is Chinese and takes "Z.", not "Zh.").
"""
from __future__ import annotations

import unicodedata

import pytest
from hypothesis import given, settings, strategies as st

from arxivbot.models.cmo import CMO, Author
from core.initials import letters_of_initial


# ------------------------------------------------------------ the pathology

@pytest.mark.parametrize("given_name,expected", [
    # every multi-letter form the library holds
    ("Yu. M.", "Yu. M"), ("Ya. B.", "Ya. B"), ("Kh.", "Kh"), ("Ch.", "Ch"),
    ("Th.", "Th"), ("Ph.", "Ph"), ("Ts.", "Ts"), ("Sh.", "Sh"), ("Sz.", "Sz"),
    # the longest a transliteration needs: Щ
    ("Shch.", "Shch"), ("Zh. Shch.", "Zh. Shch"),
    # glued: one token, which used to lose everything after its first letter
    ("Yu.A.", "Yu. A"), ("J.R.R.", "J. R. R"), ("M.Ø.", "M. Ø"),
    # hyphenated, mixed
    ("Ch.-L.", "Ch.-L"), ("J.-P.", "J.-P"),
])
def test_a_written_initial_keeps_its_letters(given_name, expected):
    assert Author("X", given_name).initials() == expected


@pytest.mark.parametrize("given_name,expected", [
    # a name in full is still cut to its first letter
    ("Yuri", "Y"), ("Yu", "Y"), ("Zhang Wei", "Z. W"), ("Jean-Pierre", "J.-P"),
    ("Paul André", "P. A"), ("Émile", "É"),
    # a lower-case given name still gives a capital
    ("jean", "J"), ("élie marie", "É. M"),
    # not initial-shaped: all capitals, or longer than four letters
    ("YU.", "Y"), ("Shchx.", "S"),
])
def test_a_name_in_full_takes_its_first_letter(given_name, expected):
    assert Author("X", given_name).initials() == expected


def test_decomposed_given_names_keep_their_accent():
    """The first character of an NFD "É" is a bare "E"."""
    assert Author("X", unicodedata.normalize("NFD", "Élie")).initials() == "É"
    assert Author("X", unicodedata.normalize("NFD", "Ét.")).initials() == "Ét"


@pytest.mark.parametrize("token,letters", [
    ("Yu.", "Yu"), ("Shch.", "Shch"), ("A.", "A"), ("Ø.", "Ø"),
    ("Yu", None), ("USA.", None), ("et.", None), ("Shchx.", None), ("", None),
    ("Yu.A.", None),
    (unicodedata.normalize("NFD", "Ét."), "Ét"),     # macOS hands names back NFD
])
def test_what_counts_as_a_written_initial(token, letters):
    assert letters_of_initial(token) == letters


# ------------------------------------------------------------ at arrival

def test_a_new_paper_is_named_with_its_initials_whole():
    cmo = CMO(external_id="x", source="t", title="On the FTAP",
              authors=[Author("Kabanov", "Yu. M."), Author("Stricker", "Ch.")])
    assert cmo.get_canonical_filename() == "Kabanov, Yu. M., Stricker, Ch. - On the FTAP.pdf"


def test_the_arrival_name_is_already_what_every_path_keeps():
    from processing.move_normalizer import normalize_full_name
    name = CMO(external_id="x", source="t", title="Hypergeometric functions",
               authors=[Author("Neretin", "Yu.A.")]).get_canonical_filename()
    assert name == "Neretin, Yu. A. - Hypergeometric functions.pdf"
    assert normalize_full_name(name)[0] == name


def test_the_over_length_refit_keeps_them_too():
    """``_fit_to_limit`` re-parses the author block and rebuilds it."""
    from processing.library_normalize import _MAX_FILENAME_BYTES, _fit_to_limit
    authors = ", ".join(["Kabanov, Yu. M.", "Rutickii, Ya. B."] +
                        [f"Author{i}, Kh. A." for i in range(12)])
    title = "A title long enough to push the whole name over the limit " * 2
    name = f"{authors} - {title.strip()}.pdf"
    assert len(name.encode()) > _MAX_FILENAME_BYTES
    out = _fit_to_limit(name)
    assert out is not None and len(out.encode()) <= _MAX_FILENAME_BYTES
    assert out.startswith("Kabanov, Yu. M., Rutickii, Ya. B., Author0, Kh. A.")
    assert out.split(" - ")[0].endswith(", et al.")


# ------------------------------------------------------------ properties

_INITIAL = st.builds(
    lambda cap, low: cap + low,
    st.sampled_from(list("ABCKMPSTYZÉØŁ")),
    st.text(alphabet=st.sampled_from(list("hsuaz")), max_size=3))
_PART = st.lists(_INITIAL, min_size=1, max_size=2).map(lambda xs: ".-".join(xs))
_WRITTEN = st.lists(_PART, min_size=1, max_size=4)


@settings(max_examples=400)
@given(_WRITTEN)
def test_written_initials_round_trip_exactly(parts):
    """Canonical initials in, the same initials out: nothing cut, nothing
    added."""
    given_name = ". ".join(parts) + "."
    assert Author("X", given_name).initials() + "." == given_name


@settings(max_examples=400)
@given(_WRITTEN)
def test_glued_initials_lose_nothing(parts):
    spaced = ". ".join(parts) + "."
    glued = spaced.replace(". ", ".")
    assert Author("X", glued).initials() == Author("X", spaced).initials()


@settings(max_examples=400)
@given(st.lists(st.text(alphabet=st.sampled_from(list("ABYZabhuo.-")), min_size=1, max_size=6),
                min_size=1, max_size=4))
def test_initials_are_a_fixpoint(tokens):
    """Whatever the given name, initialising its initials changes nothing."""
    once = Author("X", " ".join(tokens)).initials()
    if once:
        assert Author("X", once + ".").initials() == once
