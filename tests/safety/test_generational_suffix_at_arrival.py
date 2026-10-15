"""A generational suffix keeps its author, and its place, at arrival.

THE LIBRARY (measured 2026-10-15, the 25,251 names tooling may touch). 41
author blocks carry "Jr.", written two ways, both typed by the owner over
the same years (2006-2025, per each record's original filename):

    "Cruz Jr., J. B."            32 blocks, 11 people -- inside the surname
    "Smith, Jr., A. A."           9 blocks,  8 people -- its own part

Neither follows the paper: of 18 whose first pages print the name one way,
the shelf agrees with the print in 5. So a block keeps the form it has.
``filename_ground_truth`` already models the second form (``_SUFFIX``,
"Surname, Jr., Initials"); the arrival parser did not.

THE DEFECT. ``processing.ingest.parse_authors_string`` read "Jr." as
initials (a capital, a lower-case letter, a full stop), so the block had
an odd number of comma-separated parts, was not "Surname, I., ...", and
fell through to ONE author with a long given name:

    "Krusell, P., Smith, Jr., A. A."   ->  "Krusell, P. S. J. A. A."
    "Clancy, Jr., D."                  ->  "Clancy, J. D."

All 9 came back wrong; the 32 glued ones were right. The refit of an
over-long name (``library_normalize._fit_to_limit``) rebuilds author
blocks through this parser, and so does a name typed in the Sort Queue
box (for its folder).

"Dr. Z" (3 files) is a pen name -- William Ziemba's column -- and is left
alone on purpose; see ``test_dr_z_is_a_pen_name_and_is_left_alone``.
"""
from __future__ import annotations

import unicodedata

import pytest
from hypothesis import given, settings, strategies as st

from arxivbot.models.cmo import CMO, Author, author_segment
from processing.filename_ground_truth import is_generational_suffix
from processing.ingest import metadata_to_cmo, parse_authors_string


def rebuild(block: str) -> str:
    """The block, parsed and named by the arrival namer, end to end."""
    name = CMO(external_id="x", source="t", title="T",
               authors=parse_authors_string(block)).get_canonical_filename()
    return name[: -len(" - T.pdf")]


def segments(block: str) -> str:
    """The block, parsed and rebuilt by the arrival namer's author step.

    ``rebuild`` costs a quarter of a second (the validator), too slow for a
    property; on every suffix block in the library the validator changes
    nothing in the author block, which the corpus test checks end to end.
    """
    return ", ".join(CMO(external_id="x", source="t", title="T",
                         authors=parse_authors_string(block))._author_segments())


# ------------------------------------------------------------ the pathology

#: Every library block with a suffix written as its own part, verbatim.
SUFFIX_APART = [
    "Bakirova, L. N., Shurygina, M. A., Shurygin, Jr., V. V.",
    "Bennett, Jr., A.",
    "Benton, Jr., S. H.",
    "Clancy, Jr., D.",
    "Goldstein, J. A., Gretsky, N. E., Uhl, Jr., J. J.",
    "Harvey, F. R., Lawson, Jr., H. B.",          # behind "Astérisque 213 - "
    "Krusell, P., Smith, Jr., A. A.",
    "Krusell, P., Smith, Jr., A. A. S.",
    "McShane, E. J., Warfield, Jr., R. B.",
]

#: Every library block with the suffix inside the surname, verbatim. These
#: always worked; they must keep working.
SUFFIX_GLUED = [
    "Chen, C. I., Cruz Jr., J. B.",
    "Chen, Y., Page Jr., F. H.",
    "Cox, J. C., Ingersoll Jr., J. E., Ross, S. A.",
    "Crandall, M. G., Wewcomb II, R. T., Tomita, Y.",
    "Cruz Jr., J. B.",
    "Douglas Jr., J., Ma, J., Protter, P. E.",
    "Dybvig, P. H., Ingersoll Jr., J. E., Ross, S. A.",
    "Fryer Jr., R. G., Harms, P., Jackson, M. O.",
    "Gardner, B., Cruz Jr., J. B.",
    "Garsia, A. M., Rodemich, E., Rumsey Jr., H.",
    "Heinricher Jr., A. C., Mizel, V. J.",
    "Itô, K., McKean Jr., H. P.",
    "Jarrow, R. A., Oldfield Jr., G. S.",
    "Leao Jr., D., Fragoso, M., Ruffino, P.",
    "McKean Jr., H. P.",
    "McKean Jr., H. P., Singer, I. M.",
    "Monteiro, P. K., Page Jr., F. H.",
    "Oldfield Jr., G. S., Rogalski, R. J.",
    "Oldfield Jr., G. S., Rogalski, R. J., Jarrow, R. A.",
    "Page Jr., F. H.",
    "Papavassilopoulos, G., Cruz Jr., J. B.",
    "Simaan, M., Cruz Jr., J. B.",
    "Zheng, Y.-P., Başar, T., Cruz Jr., J. B.",
    "de Araujo, A. L. A., Ferreira Leite Jr., E.",
]


@pytest.mark.parametrize("block", SUFFIX_APART)
def test_every_library_suffix_written_apart_arrives_exactly(block):
    assert rebuild(block) == block


@pytest.mark.parametrize("block", SUFFIX_APART + SUFFIX_GLUED)
def test_every_library_suffix_block_rebuilds_exactly(block):
    assert segments(block) == block


@pytest.mark.parametrize("block", SUFFIX_APART + SUFFIX_GLUED)
def test_and_reads_back_as_written(block):
    """``display_name`` is what the Sort Queue shows for each author."""
    assert ", ".join(a.display_name() for a in parse_authors_string(block)) == block


def test_the_suffix_belongs_to_its_own_author():
    got = parse_authors_string("Krusell, P., Smith, Jr., A. A.")
    assert [(a.family, a.given, a.suffix) for a in got] == [
        ("Krusell", "P.", None), ("Smith", "A. A.", "Jr.")]


def test_a_glued_suffix_stays_inside_the_surname():
    got = parse_authors_string("Itô, K., McKean Jr., H. P.")
    assert [(a.family, a.given, a.suffix) for a in got] == [
        ("Itô", "K.", None), ("McKean Jr.", "H. P.", None)]


@pytest.mark.parametrize("suffix", ["Jr.", "Jr", "Sr.", "Sr", "II", "III", "IV", "III."])
def test_each_suffix_the_decomposer_knows(suffix):
    block = f"Hu, Y., Smith, {suffix}, A. B., Zhou, C."
    got = parse_authors_string(block)
    assert [a.suffix for a in got] == [None, suffix, None]
    assert segments(block) == block


@pytest.mark.parametrize("block,authors", [
    # the strong separators split before the suffix is read
    ("Krusell, P. and Smith, Jr., A. A.",
     [("Krusell", "P.", None), ("Smith", "A. A.", "Jr.")]),
    ("Smith, Jr., A. A. & Krusell, P.",
     [("Smith", "A. A.", "Jr."), ("Krusell", "P.", None)]),
    ("Krusell, P., and Smith, Jr., A. A.",
     [("Krusell", "P.", None), ("Smith", "A. A.", "Jr.")]),
    # first and last, and two in a row
    ("Smith, Jr., A. A., Krusell, P.",
     [("Smith", "A. A.", "Jr."), ("Krusell", "P.", None)]),
    ("Smith, Jr., A., Smith, Sr., B.",
     [("Smith", "A.", "Jr."), ("Smith", "B.", "Sr.")]),
    # a hyphenated or multi-letter initial after the suffix
    ("Lions, Jr., P.-L.", [("Lions", "P.-L.", "Jr.")]),
    ("Kabanov, Jr., Yu. M.", [("Kabanov", "Yu. M.", "Jr.")]),
])
def test_where_the_suffix_sits(block, authors):
    assert [(a.family, a.given, a.suffix)
            for a in parse_authors_string(block)] == authors
    assert segments(block) == ", ".join(
        ", ".join(p for p in (f, s, g) if p) for f, g, s in authors)


@pytest.mark.parametrize("block,authors", [
    # nothing initial-shaped follows, so "Jr." is all Smith has: as before
    ("Smith, Jr., Jones, A.", [("Smith", "Jr.", None), ("Jones", "A.", None)]),
    ("Smith, Jr.", [("Smith", "Jr.", None)]),
    # not one of the decomposer's suffixes
    ("Smith, Jun., A.", [("Smith", "Jun., A.", None)]),
])
def test_a_suffix_needs_initials_after_it(block, authors):
    assert [(a.family, a.given, a.suffix)
            for a in parse_authors_string(block)] == authors


@pytest.mark.parametrize("part,is_suffix", [
    ("Jr.", True), ("Jr", True), ("Sr.", True), ("II", True), ("III", True),
    ("IV", True), ("IV.", True),
    ("J.", False), ("JR.", False), ("jr.", False), ("Jun.", False),
    ("V", False), ("V.", False), ("Vi", False), ("I.", False), ("Jr.,", False),
    (" Jr.", False), ("Jr. ", False), ("", False), ("Smith Jr.", False),
])
def test_what_counts_as_a_suffix(part, is_suffix):
    """One answer for the decomposer and the parser, and the shape that
    matters here: "V." and "I." are initials, not numerals."""
    assert is_generational_suffix(part) is is_suffix


# ------------------------------------------------------------ the paths

def test_the_over_length_refit_keeps_the_suffix():
    """``_fit_to_limit`` re-parses the author block and rebuilds it."""
    from processing.library_normalize import _MAX_FILENAME_BYTES, _fit_to_limit
    authors = ", ".join(["Krusell, P.", "Smith, Jr., A. A."] +
                        [f"Author{i}, B. C." for i in range(12)])
    title = "A title long enough to push the whole name over the limit " * 2
    name = f"{authors} - {title.strip()}.pdf"
    assert len(name.encode()) > _MAX_FILENAME_BYTES
    out = _fit_to_limit(name)
    assert out is not None and len(out.encode()) <= _MAX_FILENAME_BYTES
    assert out.startswith("Krusell, P., Smith, Jr., A. A., Author0, B. C.")
    assert out.split(" - ")[0].endswith(", et al.")


def test_the_refit_drops_a_suffixed_author_whole():
    """When the author with the suffix is the one cut, no stray "Jr." is
    left behind: the suffix goes with its author."""
    from processing.library_normalize import _MAX_FILENAME_BYTES, _fit_to_limit
    title = "x" * 226
    name = f"Krusell, P., Smith, Jr., A. A. - {title}.pdf"
    assert len(name.encode()) > _MAX_FILENAME_BYTES
    assert _fit_to_limit(name) == f"Krusell, P., et al. - {title}.pdf"


def test_a_name_typed_in_the_sort_queue_box_is_parsed_into_its_authors():
    """The box's name is filed verbatim; its author block is parsed for the
    folder. It used to come back as one author, "Krusell", given
    "P., Smith, Jr., A. A."."""
    got = parse_authors_string("Krusell, P., Smith, Jr., A. A.")
    assert [a.family for a in got] == ["Krusell", "Smith"]


def test_every_naming_path_leaves_the_shelf_names_alone():
    from processing.move_normalizer import normalize_full_name
    for block in SUFFIX_APART + SUFFIX_GLUED:
        name = f"{block} - A title.pdf"
        assert normalize_full_name(name)[0] == name


def test_crossrefs_suffix_is_not_read_yet():
    """Which form a new paper should get is the owner's decision (both are
    his); until then a Crossref record arrives as it always has."""
    cmo = metadata_to_cmo({"title": "T", "authors": [
        {"family": "Smith", "given": "Anthony A.", "suffix": "Jr."}]}, _path())
    assert [(a.family, a.given, a.suffix) for a in cmo.authors] == [
        ("Smith", "Anthony A.", None)]


def _path():
    from pathlib import Path
    return Path("/nonexistent/paper.pdf")


def test_an_author_given_as_a_dict_may_carry_a_suffix():
    """``CMO`` accepts authors as dicts (``from_json``); a suffix used to be
    a TypeError there."""
    cmo = CMO(external_id="x", source="t", title="T",
              authors=[{"family": "Smith", "given": "A. A.", "suffix": "Jr."}])
    assert cmo.get_canonical_filename() == "Smith, Jr., A. A. - T.pdf"
    assert CMO.from_json(cmo.to_json()).authors[0].suffix == "Jr."


def test_a_suffix_is_cleaned_like_the_rest_of_the_author_block():
    """"/" is the one character macOS forbids in a name."""
    cmo = CMO(external_id="x", source="t", title="T",
              authors=[Author("Smith", "A.", suffix="J/r.")])
    assert "/" not in cmo.get_canonical_filename()


def test_a_suffix_is_composed_like_the_rest_of_the_author_block():
    """The byte count that decides "et al." is taken on NFC segments."""
    cmo = CMO(external_id="x", source="t", title="T", authors=[
        Author("Smith", "A.", suffix=unicodedata.normalize("NFD", "Jé."))])
    assert cmo._author_segments() == ["Smith, Jé., A."]


def test_a_suffix_written_apart_in_nfd_is_still_its_own_part():
    block = unicodedata.normalize("NFD", "Başar, T., Ünal, Jr., É. M.")
    got = parse_authors_string(block)
    assert [a.suffix for a in got] == [None, "Jr."]
    assert rebuild(block) == "Başar, T., Ünal, Jr., É. M."


@pytest.mark.parametrize("family,initials,suffix,segment", [
    ("Smith", "A. A", "Jr.", "Smith, Jr., A. A."),
    ("Smith", "A. A", None, "Smith, A. A."),
    ("Smith", "A. A", "", "Smith, A. A."),
    # no initials: the one place a suffix stands apart is not there
    ("Smith", "", "Jr.", "Smith"),
    ("Qilegeri", "", None, "Qilegeri"),
    # cleaning ate the surname: nothing, never ", J."
    ("", "J", "Jr.", ""),
    ("", "", None, ""),
])
def test_one_author_segment(family, initials, suffix, segment):
    assert author_segment(family, initials, suffix) == segment


def test_display_name():
    assert Author("Smith", "A. A.", suffix="Jr.").display_name() == "Smith, Jr., A. A."
    assert Author("Smith", "A. A.").display_name() == "Smith, A. A."
    assert Author("Smith", suffix="Jr.").display_name() == "Smith"
    assert Author("Smith").display_name() == "Smith"


# ------------------------------------------------------------ left alone

@pytest.mark.xfail(strict=True, reason=(
    "'Dr. Z' is a pen name (William Ziemba's column), 3 files hand-named in "
    "2006 and filed under D. Nothing in the string tells it from an honorific "
    "before a real name ('Dr. John Smith' should lose the 'Dr.'), so making it "
    "round-trip means listing one pen name -- for a parse no path makes: "
    "every naming path leaves the three names alone (test below), the refit "
    "touches only names over 255 bytes, and their PDFs' /Author fields read "
    "'ISDN', 'William Ziemba', 'ISDN'. Known cost: typed in the Sort Queue "
    "box, 'Dr. Z - ...' would be filed under Z, not D."))
def test_dr_z_is_a_pen_name_and_is_left_alone():
    assert rebuild("Dr. Z") == "Dr. Z"


def test_but_no_path_renames_a_dr_z_paper():
    from processing.move_normalizer import normalize_full_name
    for title in ("Kelly’s heroes", "Luck of the draw", "Take a chance"):
        name = f"Dr. Z - {title}.pdf"
        assert normalize_full_name(name)[0] == name


# ------------------------------------------------------------ properties

_SURNAME = st.builds(
    lambda head, tail: head + tail,
    st.sampled_from(list("ABCKMSTZÉÖŁŞ")),
    st.text(alphabet=st.sampled_from(list("aeiouklmnrstçäüő")), min_size=1, max_size=8))
_INITIAL = st.builds(lambda cap, low: cap + low,
                     st.sampled_from(list("ABCHJKMPSYZÉ")),
                     st.sampled_from(["", "", "", "u", "h"]))
_INITIALS = st.lists(
    st.lists(_INITIAL, min_size=1, max_size=2).map(lambda xs: ".-".join(xs)),
    min_size=1, max_size=3).map(lambda parts: ". ".join(parts) + ".")
_SUFFIX = st.one_of(st.none(), st.sampled_from(["Jr.", "Jr", "Sr.", "II", "III", "IV"]))
_AUTHOR = st.tuples(_SURNAME, _SUFFIX, _INITIALS)


def _block(authors) -> str:
    return ", ".join(", ".join(p for p in (f, s, i) if p) for f, s, i in authors)


@settings(max_examples=300)
@given(st.lists(_AUTHOR, min_size=1, max_size=6))
def test_a_library_form_block_round_trips(authors):
    """Any block in the library's form -- with or without suffixes, written
    apart -- parses into exactly its authors and rebuilds unchanged."""
    block = _block(authors)
    got = parse_authors_string(block)
    assert [(a.family, a.suffix, a.given) for a in got] == list(authors)
    assert segments(block) == block


@settings(max_examples=200)
@given(st.lists(_AUTHOR, min_size=2, max_size=6), st.data())
def test_a_suffix_touches_no_other_author(authors, data):
    """Adding or removing one author's suffix changes that author and no
    other -- the failure mode was the suffix folding into a neighbour."""
    j = data.draw(st.integers(0, len(authors) - 1))
    without = [(f, None, i) for f, _s, i in authors]
    with_one = list(without)
    with_one[j] = (without[j][0], "Jr.", without[j][2])
    a = parse_authors_string(_block(without))
    b = parse_authors_string(_block(with_one))
    assert len(a) == len(b) == len(authors)
    for k, (x, y) in enumerate(zip(a, b)):
        assert (x.family, x.given) == (y.family, y.given)
        assert y.suffix == ("Jr." if k == j else None)


def test_an_empty_part_is_not_an_author():
    """A doubled comma (malformed metadata) must not make an author with no
    surname: ``author_segment`` would drop him, and his initials with him."""
    got = parse_authors_string("Smith, J., , K.")
    assert got and all(a.family.strip() for a in got)


@pytest.mark.parametrize("raw", [", , Smith, J.", "Smith, J., ,", " ;, Smith, J. ,; "])
def test_separators_at_the_edges_are_not_an_author(raw):
    """Found by the property below: stripping one space, one run of commas
    and one space left ", Smith, J." -- an author with no surname, dropped
    from the name and filed under Z."""
    assert [(a.family, a.given) for a in parse_authors_string(raw)] == [("Smith", "J.")]


_PART = st.one_of(_SURNAME, _INITIALS, st.sampled_from(["Jr.", "II", "Sr", "", " ", "Jun."]))


@settings(max_examples=300)
@given(st.lists(_PART, min_size=1, max_size=8))
def test_no_parse_has_an_author_without_a_surname(parts):
    """Whatever the parts, in whatever order: every author the parser
    returns has a surname, so no author silently vanishes from a name."""
    for a in parse_authors_string(", ".join(parts)):
        assert a.family.strip()


@settings(max_examples=200)
@given(st.lists(_AUTHOR, min_size=1, max_size=5))
def test_nfd_reads_like_nfc(authors):
    """macOS hands names back decomposed."""
    block = _block(authors)
    assert segments(unicodedata.normalize("NFD", block)) == block
