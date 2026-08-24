"""The training corpus must not be taught a series number as an author.

``ml/pdf-meta-llm/scripts/extract_text.py`` builds the (front-matter text ->
title + authors) corpus by reading the filename. It used to do that with
``stem.split(" - ", 1)`` behind a regex that stripped one leading number,
which is wrong for 3,889 of the library's 27,160 names -- and wrong in the
direction that teaches the model a lie and then scores it correct.

The visible consequence is in ``results/eval_llm_100_v2.json``: one sample has
``gt_authors: ["08"]`` -- an SMF series number -- and the model scored 1.0 for
reproducing it. Nine of its hundred samples carry a corrupted ground truth,
and they score 0.44 where the clean ninety-one score 0.89.

Measured over the whole library, replacing the split with the shared
decomposer changes 502 labels, refuses 1,436 rows that were corrupt, and
recovers 27 that were silently lost -- 7.2% of the corpus.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "ml" / "pdf-meta-llm" / "scripts"


@pytest.fixture(scope="module")
def extract_text():
    spec = importlib.util.spec_from_file_location(
        "_corpus_extract_text", SCRIPTS / "extract_text.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_corpus_extract_text"] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:                     # pragma: no cover
        pytest.skip(f"corpus builder not importable: {exc}")
    return module


def _parse(extract_text, name, directory="", tmp_path=None, monkeypatch=None):
    """Parse a name as if the file sat in ``directory`` of the library."""
    root = tmp_path / "lib"
    folder = root / directory if directory else root
    folder.mkdir(parents=True, exist_ok=True)
    pdf = folder / f"{name}.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setenv("MATH_LIBRARY", str(root))
    return extract_text.parse_filename(pdf)


AST = "05 - Books and lecture notes/05 - Asterisque"
SEM = "08 - Seminaires/Seminaire 12 - 1978"
CR = "05 - Books and lecture notes/01 - Comptes rendus"


class TestTheCorruptLabelsAreGone:
    def test_a_series_number_is_not_an_author(self, extract_text, tmp_path, monkeypatch):
        """The gt_authors == ["08"] case, in the form that produced it."""
        title, authors = _parse(
            extract_text,
            "08 - Audin, M. - Les systemes hamiltoniens et leur integrabilite",
            "05 - Books and lecture notes/04 - Cours specialises", tmp_path, monkeypatch)
        assert authors == ["M. Audin"]
        assert title == "Les systemes hamiltoniens et leur integrabilite"

    def test_an_asterisque_volume_number_is_not_an_author(self, extract_text, tmp_path, monkeypatch):
        title, authors = _parse(
            extract_text, "Asterisque 390 - Baues, O. - Symplectic Lie groups",
            AST, tmp_path, monkeypatch)
        assert authors == ["O. Baues"]
        assert title == "Symplectic Lie groups"

    def test_a_two_part_page_ordinal_is_fully_removed(self, extract_text, tmp_path, monkeypatch):
        """The old regex stripped "740-" and left "1-Dellacherie, C."."""
        title, authors = _parse(
            extract_text, '740-1-Dellacherie, C. - Correction "Un crible generalise"',
            SEM, tmp_path, monkeypatch)
        assert authors == ["C. Dellacherie"]
        assert title == 'Correction "Un crible generalise"'


class TestARowIsRefusedRatherThanGuessed:
    """A wrong label is worse than a missing one: the model learns it AND the
    test set scores it as correct."""

    def test_a_bound_journal_volume_produces_no_row(self, extract_text, tmp_path, monkeypatch):
        title, authors = _parse(
            extract_text,
            "Comptes rendus hebdomadaires des seances de l'academie des sciences, "
            "tome 301, serie I - Mathematique, no12 - 20 mars 1985",
            CR, tmp_path, monkeypatch)
        assert (title, authors) == (None, [])

    def test_an_edited_volume_produces_no_row(self, extract_text, tmp_path, monkeypatch):
        """The names are non-empty AND correctly decomposed -- they are just
        editors. A check on "are there names" passes them through; only a
        check on the ROLE stops them. Every Messenger title page reads
        "EDITED BY" above exactly these four."""
        title, authors = _parse(
            extract_text,
            "017-Glaisher, J. W. L. - Messenger of mathematics, volume XVII, May, 1887-April, 1888",
            "05 - Books and lecture notes/09 - Messenger of mathematics", tmp_path, monkeypatch)
        assert (title, authors) == (None, [])

    def test_a_malformed_author_block_produces_no_row(self, extract_text, tmp_path, monkeypatch):
        """The decomposition is right; the label would still teach a typo."""
        title, authors = _parse(
            extract_text, "Zhang. Y. - Some result about diffusions",
            "01 - Published papers/Z", tmp_path, monkeypatch)
        assert (title, authors) == (None, [])

    def test_a_name_the_parser_cannot_settle_produces_no_row(self, extract_text, tmp_path, monkeypatch):
        title, authors = _parse(
            extract_text, "Document 3, rapport Bertillon",
            "09 - JEHPS", tmp_path, monkeypatch)
        assert (title, authors) == (None, [])


class TestOrdinaryPapersAreUnaffected:
    @pytest.mark.parametrize("name,expect_authors,expect_title", [
        ("Rogers, L. C. G. - Which model for term-structure of interest rates should one use",
         ["L. C. G. Rogers"], "Which model for term-structure of interest rates should one use"),
        ("Leon, J. A., Nualart, D. - An extension of the divergence operator",
         ["J. A. Leon", "D. Nualart"], "An extension of the divergence operator"),
    ])
    def test_unchanged(self, extract_text, tmp_path, monkeypatch, name, expect_authors, expect_title):
        title, authors = _parse(extract_text, name, "01 - Published papers/R",
                                tmp_path, monkeypatch)
        assert authors == expect_authors
        assert title == expect_title

    def test_a_trailing_year_is_kept_because_it_is_sometimes_the_title(
            self, extract_text, tmp_path, monkeypatch):
        """The old code stripped "(1998)" unconditionally. Of the 19 titles
        ending that way, "Recursive equilibrium in Krusell and Smith (1998)"
        needs it and "Abstract dynamic programming-Athena Scientific (2013)"
        does not, so a blanket strip is wrong either way. The filename is the
        ground truth, so the filename is what gets recorded."""
        title, _ = _parse(extract_text,
                          "Cao, D. - Recursive equilibrium in Krusell and Smith (1998)",
                          "01 - Published papers/C", tmp_path, monkeypatch)
        assert title == "Recursive equilibrium in Krusell and Smith (1998)"


class TestItWorksWithoutTheLibraryRoot:
    def test_no_directory_evidence_still_parses_an_ordinary_name(
            self, extract_text, tmp_path, monkeypatch):
        """A paper arriving in the inbox has no folder yet."""
        monkeypatch.delenv("MATH_LIBRARY", raising=False)
        pdf = tmp_path / "Rogers, L. C. G. - Which model for term-structure.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        title, authors = extract_text.parse_filename(pdf)
        assert authors == ["L. C. G. Rogers"]
        assert title == "Which model for term-structure"
