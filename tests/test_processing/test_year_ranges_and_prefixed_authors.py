"""Year ranges take an en dash; a ruled surname is found behind a prefix.

Two of the owner's rulings, 2026-10-09.

YEAR RANGES. "Year ranges should be en-dashes everywhere, for all file
names, otherwise it's an error." Measured that day, in scope: 61 already
right; 35 with the Finder colon (the 34 Astérisque Bourbaki volumes,
"volume 2002/2003" on screen and "2002:2003" on disk, plus one Strasbourg
exposé) and 10 with a hyphen. The archival collections were all right.
What must NOT be taken for a range: a date ("conflicted copy 2023-01-26"),
a DOI fragment ("rose-2025-2029"), a decreasing pair, a ratio ("24:7").

SURNAMES BEHIND A PREFIX. The approved particle rulings ("Le Gall",
"El Karoui", "Del Moral", ...) never reached 34 files, because the surname
authority looked only at the text before the first " - ": Strasbourg
exposés glue their number on with a hyphen ("103-le Gall, J.-F. - ..."),
and series volumes put a prefix first ("Astérisque 281 - Duquesne, T.,
le Gall, J.-F. - ..."). Measured over the whole library, the change alters
exactly those 34 names and the 45 year ranges -- nothing else.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, strategies as st

from processing.author_surnames import canonicalise_filename
from processing.filename_normalizer import _en_dash_year_ranges, normalize_filename

SEPS = ["-", ":", "‐", "‑", "−", "—", "--"]


# --------------------------------------------------------------- year ranges

@given(st.integers(1500, 2098), st.integers(1, 120), st.sampled_from(SEPS))
def test_every_increasing_pair_becomes_an_en_dash(start, gap, sep):
    end = min(start + gap, 2099)
    text = f"Notes ({start}{sep}{end})"
    out = _en_dash_year_ranges(text)
    assert out == f"Notes ({start}–{end})"
    assert _en_dash_year_ranges(out) == out, "idempotent"


@given(st.integers(1500, 2099), st.integers(0, 400), st.sampled_from(SEPS))
def test_a_decreasing_or_equal_pair_is_not_a_range(start, back, sep):
    end = max(start - back, 1500)
    text = f"Notes ({start}{sep}{end})"
    assert _en_dash_year_ranges(text) == text


@pytest.mark.parametrize("text,expected", [
    ("Séminaire Bourbaki, volume 2002:2003, exposés 909–923",
     "Séminaire Bourbaki, volume 2002–2003, exposés 909–923"),
    ("Corrections à des exposés de 1973:1974", "Corrections à des exposés de 1973–1974"),
    ("Obituary Jean Leray (1906-98)", "Obituary Jean Leray (1906–98)"),      # abbreviation kept
    ("the 2009–10 Influenza season", "the 2009–10 Influenza season"),       # already right
    ("Harry Kesten (1931-2019)", "Harry Kesten (1931–2019)"),
])
def test_the_library_cases(text, expected):
    assert _en_dash_year_ranges(text) == expected


@pytest.mark.parametrize("text", [
    "Report (Dropbox conflicted copy 2023-01-26)",   # a date
    "Scan 2025-06-02",                               # a date
    "10.1515_rose-2025-2029",                        # a DOI fragment
    "ISSN 2049-3630",                                # end is not a year
    "Least-cost structuring of 24:7 carbon-free electricity",
    "Brownian motion H<1:2",
    "v2001-2002 release notes",                      # glued to a word
    "codes 1988-19901",                              # longer number
    "1999-00 season",                                # 00 is not after 99
    "pages 1988-1990.5",                             # a decimal
])
def test_what_is_not_a_year_range_is_left_alone(text):
    assert _en_dash_year_ranges(text) == text


def test_the_namer_applies_it_and_is_a_fixpoint():
    name = "Astérisque 361 - Séminaire Bourbaki, volume 2012:2013, exposés 1059–1073.pdf"
    out = normalize_filename(name)
    assert "volume 2012–2013" in out
    assert normalize_filename(out) == out


def test_the_full_pipeline_gives_the_en_dash_too():
    from processing.move_normalizer import normalize_full_name
    new, changed, _ = normalize_full_name(
        "Doob, J. L. - The development of rigor in mathematical probability (1900-1950).pdf")
    assert changed and new.endswith("(1900–1950).pdf")
    again, changed2, _ = normalize_full_name(new)
    assert again == new and not changed2


# ------------------------------------------------- surnames behind a prefix

TABLE = {"le gall": "Le Gall", "le jan": "Le Jan", "el karoui": "El Karoui"}


@pytest.mark.parametrize("name,expected", [
    ("103-le Gall, J.-F. - Marches aléatoires.pdf",
     "103-Le Gall, J.-F. - Marches aléatoires.pdf"),
    ("81-le Gall, J.-F., Yor, M. - Sur l’équation de Tsirelson.pdf",
     "81-Le Gall, J.-F., Yor, M. - Sur l’équation de Tsirelson.pdf"),
    ("95-el Karoui, N., Reinhard, H. - Processus de diffusion.pdf",
     "95-El Karoui, N., Reinhard, H. - Processus de diffusion.pdf"),
    ("Astérisque 281 - Duquesne, T., le Gall, J.-F. - Random trees.pdf",
     "Astérisque 281 - Duquesne, T., Le Gall, J.-F. - Random trees.pdf"),
    ("036-2 - le Jan, Y. - Markov paths, loops and fields.pdf",
     "036-2 - Le Jan, Y. - Markov paths, loops and fields.pdf"),
])
def test_a_ruled_surname_behind_a_prefix_is_found(name, expected):
    assert canonicalise_filename(name, TABLE) == (expected, True)


@pytest.mark.parametrize("name", [
    # the first segment IS an author block: never look past it, even when
    # the title opens with a ruled surname
    "Yor, M. - le Gall, J.-F., some remarks - a letter.pdf",
    # a prefix followed by a title, not authors
    "Astérisque 294 - Séminaire Bourbaki, volume 2002–2003 - part two.pdf",
    # a number glued to a surname with no ruling
    "544-Dellacherie, C. - Corrections.pdf",
    # "le" in a TITLE stays a French article
    "Freidlin, M. I. - Sur le Gall, cas continu.pdf",
])
def test_nothing_else_is_touched(name):
    assert canonicalise_filename(name, TABLE) == (name, False)


def test_the_title_caser_does_not_lower_it_again():
    """Behind a prefix the author block sits in what the namer treats as
    title text, where "le" is a common French word. Measured: the capital
    survives, and the name is a fixpoint."""
    from processing.move_normalizer import normalize_full_name
    name = "Astérisque 281 - Duquesne, T., le Gall, J.-F. - Random trees, Lévy processes and spatial branching processes.pdf"
    new, changed, _ = normalize_full_name(name)
    assert changed and "Le Gall" in new
    assert normalize_full_name(new)[0] == new


def test_a_veto_still_wins_behind_a_prefix(monkeypatch):
    import processing.author_surnames as A
    monkeypatch.setattr(A, "load_vetoes", lambda *a, **k: {"le gall"})
    monkeypatch.setattr(A, "load_map", lambda *a, **k: TABLE)
    name = "103-le Gall, J.-F. - Marches aléatoires.pdf"
    assert canonicalise_filename(name) == (name, False)
