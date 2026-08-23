r"""Four ways a title got mangled on its way to a filename.

Measured on the real inbox: of 1,873 papers carrying an embedded /Title,
89 contain a backslash and 19 contain a slash. Every one of the 89 was
having an en dash fabricated for it.
"""
from __future__ import annotations

import pytest

from arxivbot.models.cmo import _clean_for_fs
from processing.ingest import _decode_entities, _unlatex


def pipeline(raw: str) -> str:
    return _clean_for_fs(_unlatex(_decode_entities(raw)))


class TestTheBackslashIsNotPunctuation:
    r"""It was rewritten to an en dash "for filesystem safety". The
    backslash is not illegal on macOS — verified: "\\", ":", "|" and "?"
    are all legal in a filename; only "/" is not. So the rewrite bought
    nothing and cost the library its most meaningful mark, since an en
    dash there means two co-equal entities.
    """

    @pytest.mark.parametrize("raw", [
        r"Coming up from $-\infty$ for KPZ via stochastic control",
        r"$\mathbb{L}^p$-solutions for BSDEs and reflected BSDEs",
        r"Boundary regularity on $C^{1,\alpha}$ domains",
    ])
    def test_latex_residue_never_becomes_an_en_dash(self, raw):
        out = pipeline(raw)
        assert "–" not in out, (
            f"an en dash was fabricated from LaTeX residue: {out}")

    def test_residue_is_left_visible_rather_than_disguised(self):
        r"""Leaving "$-\infty$" is not a cosmetic failure — it is what
        lets the conformance and spelling checks see it. Disguised as an
        en dash it is invisible and, worse, it reads as meaningful."""
        assert "\\" in pipeline(r"Coming up from $-\infty$ for KPZ")

    def test_a_backslash_is_actually_legal_in_a_filename(self, tmp_path):
        """The premise of the whole rewrite, checked rather than assumed."""
        p = tmp_path / r"a\backslash name.pdf"
        p.write_bytes(b"%PDF-")
        assert p.exists()


class TestTheSlashTakesAHyphen:
    """A slash IS illegal and must be replaced — but with the mark the
    house convention prescribes. "on/off" is one word built from parts,
    which is a hyphen; an en dash would claim two co-equal entities.
    """

    @pytest.mark.parametrize("raw,expected", [
        ("The on/off Brownian snake", "The on-off Brownian snake"),
        ("Generalizing super/sub mot", "Generalizing super-sub mot"),
        ("Noncooperative/Mixed differential games",
         "Noncooperative-Mixed differential games"),
    ])
    def test_a_slash_becomes_a_hyphen(self, raw, expected):
        assert pipeline(raw) == expected

    def test_no_slash_survives_into_a_filename(self):
        """Whatever else changes, this one is a filesystem requirement."""
        assert "/" not in pipeline("a/b/c/d")


class TestBraceWrappedAccents:
    r"""The accent pattern handled "\^{o}" but not "{\^o}", where the
    brace wraps the command instead of the letter. Publishers emit that
    form and it left an orphan brace: "It{\^o}" became "It{ô".
    """

    @pytest.mark.parametrize("raw,expected", [
        (r"The It{\^o}-F\"ollmer formula", "The Itô-Föllmer formula"),
        (r"It{\^{o}} calculus", "Itô calculus"),
        (r"L\'{e}vy processes", "Lévy processes"),      # the form that worked
        (r"Sch\"{u}tzenberger", "Schützenberger"),
    ])
    def test_the_accent_is_applied_and_no_brace_is_left(self, raw, expected):
        out = pipeline(raw)
        assert out == expected
        assert "{" not in out and "}" not in out


class TestHtmlEntities:

    @pytest.mark.parametrize("raw,expected", [
        ("Baez-Duarte&#x2019;s Hilbert space", "Baez-Duarte’s Hilbert space"),
        ("Hardy &amp; Littlewood", "Hardy & Littlewood"),
        ("&#8220;quoted&#8221; title", "“quoted” title"),
    ])
    def test_an_entity_is_decoded(self, raw, expected):
        assert pipeline(raw) == expected

    def test_double_escaping_is_also_handled(self):
        """Some producers escape an already-escaped string."""
        assert pipeline("Hardy &amp;amp; Littlewood") == "Hardy & Littlewood"

    def test_a_bare_ampersand_is_left_alone(self):
        assert pipeline("Hardy & Littlewood") == "Hardy & Littlewood"


class TestNothingElseMoved:

    @pytest.mark.parametrize("raw", [
        "Reflected BSDEs and optimal stopping",
        "Hamilton–Jacobi–Bellman equations on networks",   # real en dashes
        "Mean-field games with common noise",
        "C^{1,α} regularity for viscosity solutions",
    ])
    def test_an_ordinary_title_is_unchanged(self, raw):
        assert pipeline(raw) == raw

    def test_control_characters_are_still_stripped(self):
        assert pipeline("Quelques aspets\x1cde la quantiation") == \
            "Quelques aspetsde la quantiation"
