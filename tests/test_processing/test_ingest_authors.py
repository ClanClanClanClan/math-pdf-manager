"""Tests for the author parser used by paper ingest.

The parser is the most error-prone piece of the ingest pipeline because PDF
embedded metadata, ArXiv API, Crossref, and existing filenames all use
different formats. These fixtures lock down the formats we know about so
regressions are caught.
"""
from __future__ import annotations

import pytest

from arxivbot.models.cmo import Author
from processing.ingest import parse_authors_string, metadata_to_cmo


def _names(authors):
    """Convenience: convert list[Author] to a list of (family, given) tuples."""
    return [(a.family, a.given) for a in authors]


# ---------------------------------------------------------------------------
# Format A: PDF embedded metadata — full names, comma-separated
# ---------------------------------------------------------------------------

class TestPDFEmbeddedFormat:
    """Format A: ``"First Last, First Last & First Last"`` (PDF embedded)."""

    def test_three_authors_with_ampersand(self):
        # The exact case that broke the pipeline before this fix
        result = parse_authors_string(
            "Romain Abraham, Jean-François Delmas & Julien Weibel"
        )
        assert _names(result) == [
            ("Abraham", "Romain"),
            ("Delmas", "Jean-François"),
            ("Weibel", "Julien"),
        ]

    def test_three_authors_all_commas(self):
        result = parse_authors_string(
            "Romain Abraham, Jean-François Delmas, Julien Weibel"
        )
        assert _names(result) == [
            ("Abraham", "Romain"),
            ("Delmas", "Jean-François"),
            ("Weibel", "Julien"),
        ]

    def test_two_authors_with_and(self):
        result = parse_authors_string("Jane Smith and John Doe")
        assert _names(result) == [("Smith", "Jane"), ("Doe", "John")]

    def test_single_author_full_name(self):
        result = parse_authors_string("Jean-Pierre Dupont")
        assert _names(result) == [("Dupont", "Jean-Pierre")]

    def test_nobiliary_particle_inline(self):
        # "Nicole el Karoui" → family="el Karoui" (particle attached)
        result = parse_authors_string("Nicole el Karoui")
        assert _names(result) == [("el Karoui", "Nicole")]

    def test_nobiliary_particle_two_words(self):
        # "Johannes van der Waals" → family="van der Waals"
        result = parse_authors_string("Johannes van der Waals")
        assert _names(result) == [("van der Waals", "Johannes")]


# ---------------------------------------------------------------------------
# Format B: filename / Crossref — Last, Initials repeated
# ---------------------------------------------------------------------------

class TestFilenameFormat:
    """Format B: ``"Last, F., Last, F."``"""

    def test_three_authors_filename_format(self):
        result = parse_authors_string("Abraham, R., Delmas, J.-F., Weibel, J.")
        assert _names(result) == [
            ("Abraham", "R."),
            ("Delmas", "J.-F."),
            ("Weibel", "J."),
        ]

    def test_two_authors_filename_format(self):
        result = parse_authors_string("Crandall, M.G., Lions, P.-L.")
        assert _names(result) == [
            ("Crandall", "M.G."),
            ("Lions", "P.-L."),
        ]

    def test_cyrillic_initials(self):
        # "Yu.M." is a Russian-style compound initial used in math papers.
        result = parse_authors_string("Yu.M. Kabanov")
        assert _names(result) == [("Kabanov", "Yu.M.")]

    def test_initials_first_form(self):
        result = parse_authors_string("M.G. Crandall, H. Ishii, P.-L. Lions")
        assert _names(result) == [
            ("Crandall", "M.G."),
            ("Ishii", "H."),
            ("Lions", "P.-L."),
        ]


# ---------------------------------------------------------------------------
# Format C: Crossref-style with ' and ' separator
# ---------------------------------------------------------------------------

class TestCrossrefFormat:
    """Format C: ``"Last, F. and Last, F. and Last, F."``"""

    def test_three_authors_with_and(self):
        result = parse_authors_string(
            "Abraham, R. and Delmas, J.-F. and Weibel, J."
        )
        assert _names(result) == [
            ("Abraham", "R."),
            ("Delmas", "J.-F."),
            ("Weibel", "J."),
        ]

    def test_semicolon_separator(self):
        result = parse_authors_string("Dupont, J.-P.; el Karoui, N.")
        assert _names(result) == [
            ("Dupont", "J.-P."),
            ("el Karoui", "N."),
        ]


# ---------------------------------------------------------------------------
# Format D: list input (already structured)
# ---------------------------------------------------------------------------

class TestListInput:
    """Format D: a list of strings."""

    def test_list_of_full_names(self):
        result = parse_authors_string(
            ["Romain Abraham", "Jean-François Delmas", "Julien Weibel"]
        )
        assert _names(result) == [
            ("Abraham", "Romain"),
            ("Delmas", "Jean-François"),
            ("Weibel", "Julien"),
        ]

    def test_list_with_initials_format(self):
        result = parse_authors_string(["Smith, J.", "Doe, A.B."])
        assert _names(result) == [("Smith", "J."), ("Doe", "A.B.")]

    def test_empty_list(self):
        assert parse_authors_string([]) == []


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_string(self):
        assert parse_authors_string("") == []

    def test_none(self):
        assert parse_authors_string(None) == []

    def test_et_al(self):
        assert parse_authors_string("et al.") == []

    @pytest.mark.parametrize("raw", [
        "Smith, J., Brown, A., et al.",
        "Smith, J., Brown, A. et al.",   # no comma before et al.
        "Smith, J., Brown, A., et al",   # no trailing period
        "Smith, J., Brown, A., ET AL.",  # case-insensitive
    ])
    def test_et_al_trailing_is_stripped(self, raw):
        # 'et al.' at the END of a list must not be parsed as a fake author
        result = parse_authors_string(raw)
        assert _names(result) == [("Smith", "J."), ("Brown", "A.")], (
            f"failed on {raw!r}: {_names(result)}"
        )

    def test_et_al_with_full_names(self):
        result = parse_authors_string(
            "Romain Abraham, Jean-François Delmas, et al."
        )
        assert _names(result) == [
            ("Abraham", "Romain"),
            ("Delmas", "Jean-François"),
        ]

    def test_list_with_blank_entries(self):
        # PDFs sometimes have empty strings in author lists (PDF metadata bugs)
        result = parse_authors_string(["Smith, J.", "", "Brown, A."])
        assert _names(result) == [("Smith", "J."), ("Brown", "A.")]

    def test_only_particle_name(self):
        # Pathological: family name is ONLY a nobiliary particle
        # Should not crash; result is one Author with that as family
        result = parse_authors_string("van der")
        assert len(result) == 1
        assert result[0].family == "van der"

    def test_single_word(self):
        result = parse_authors_string("Smith")
        assert _names(result) == [("Smith", None)]

    def test_whitespace_only(self):
        assert parse_authors_string("   ") == []

    def test_leading_trailing_whitespace(self):
        result = parse_authors_string("  Smith, J.  ")
        assert _names(result) == [("Smith", "J.")]

    def test_unicode_names(self):
        result = parse_authors_string("Étienne Pardoux, Łukasz Stettner")
        assert _names(result) == [
            ("Pardoux", "Étienne"),
            ("Stettner", "Łukasz"),
        ]


# ---------------------------------------------------------------------------
# metadata_to_cmo: priority of structured authors vs raw fallback
# ---------------------------------------------------------------------------

class TestMetadataToCmo:
    """Verify that metadata_to_cmo correctly chooses the author source."""

    def test_uses_structured_when_non_empty(self, tmp_path):
        pdf = tmp_path / "x.pdf"
        meta = {
            "title": "Some title",
            "authors": [
                {"family": "Smith", "given": "J."},
                {"family": "Doe", "given": "A."},
            ],
            "authors_raw": "ignored, should not be used",
        }
        cmo = metadata_to_cmo(meta, pdf)
        assert _names(cmo.authors) == [("Smith", "J."), ("Doe", "A.")]

    def test_falls_back_to_raw_when_structured_empty(self, tmp_path):
        # The original bug: authors=[] should NOT win over a good authors_raw
        pdf = tmp_path / "x.pdf"
        meta = {
            "title": "Some title",
            "authors": [],
            "authors_raw": "Romain Abraham, Jean-François Delmas & Julien Weibel",
        }
        cmo = metadata_to_cmo(meta, pdf)
        assert _names(cmo.authors) == [
            ("Abraham", "Romain"),
            ("Delmas", "Jean-François"),
            ("Weibel", "Julien"),
        ]

    def test_falls_back_to_raw_when_authors_missing(self, tmp_path):
        pdf = tmp_path / "x.pdf"
        meta = {
            "title": "Some title",
            "authors_raw": "Smith, J., Doe, A.",
        }
        cmo = metadata_to_cmo(meta, pdf)
        assert _names(cmo.authors) == [("Smith", "J."), ("Doe", "A.")]

    def test_string_authors_are_parsed(self, tmp_path):
        # ArXiv API returns authors as a list of plain strings ("First Last")
        pdf = tmp_path / "x.pdf"
        meta = {
            "title": "T",
            "authors": ["Romain Abraham", "Jean-François Delmas", "Julien Weibel"],
        }
        cmo = metadata_to_cmo(meta, pdf)
        assert _names(cmo.authors) == [
            ("Abraham", "Romain"),
            ("Delmas", "Jean-François"),
            ("Weibel", "Julien"),
        ]

    def test_uses_filename_stem_when_title_missing(self, tmp_path):
        pdf = tmp_path / "fallback_name.pdf"
        meta = {"authors_raw": "Smith, J."}
        cmo = metadata_to_cmo(meta, pdf)
        assert cmo.title == "fallback_name"

    def test_dict_author_with_only_family(self, tmp_path):
        pdf = tmp_path / "x.pdf"
        meta = {"title": "T", "authors": [{"family": "Smith"}]}
        cmo = metadata_to_cmo(meta, pdf)
        assert _names(cmo.authors) == [("Smith", None)]

    def test_dict_author_missing_family_skipped(self, tmp_path):
        pdf = tmp_path / "x.pdf"
        meta = {"title": "T", "authors": [{"given": "J."}, {"family": "Doe"}]}
        cmo = metadata_to_cmo(meta, pdf)
        # Entry without family is silently dropped
        assert _names(cmo.authors) == [("Doe", None)]


# ---------------------------------------------------------------------------
# Regression: the exact failure case that motivated this rewrite
# ---------------------------------------------------------------------------

def test_centre_mersenne_paper_filename_round_trip(tmp_path):
    """End-to-end: PDF metadata → CMO → canonical filename.

    This is the precise paper that broke the previous parser:
    the author field was 'Romain Abraham, Jean-François Delmas & Julien Weibel'
    and the result used to be 'Romain Abraham, J.-F.D., Weibel, J.' filed in /Z/.
    """
    pdf = tmp_path / "10.5802_igt.7.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    meta = {
        "title": "Probability-graphons: Limits of large dense weighted graphs",
        "authors": [],  # ArXiv returned nothing
        "authors_raw": "Romain Abraham, Jean-François Delmas & Julien Weibel",
        "doi": "10.5802/igt.7",
    }
    cmo = metadata_to_cmo(meta, pdf)
    fn = cmo.get_canonical_filename()
    # First author is Abraham → should file under A, not Z
    assert fn.startswith("Abraham, R."), f"got: {fn!r}"
    # All three authors must appear (or "et al." truncation, but here we have room)
    assert "Delmas, J.-F." in fn
    assert "Weibel, J." in fn
