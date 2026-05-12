"""Tests for the organization (filing) system.

Covers ``FolderRouter`` (path resolution + alpha-subdir computation) and
``OrganizationSystem.organize`` (the end-to-end "where does this paper go"
decision). Everything runs against a fresh tmp directory; no real library
files are touched.
"""
from __future__ import annotations

import pytest

from organization.system import (
    BOOKS,
    FolderRouter,
    OrganizationSystem,
    PUBLISHED,
    STATUS_DIRS,
    THESES,
    TO_BE_SORTED,
    UNPUBLISHED,
    WORKING,
)


# ---------------------------------------------------------------------------
# get_alpha_subdir
# ---------------------------------------------------------------------------

class TestGetAlphaSubdir:
    @pytest.fixture
    def router(self, tmp_path):
        return FolderRouter(tmp_path)

    @pytest.mark.parametrize("name,expected", [
        ("Abraham", "A"),
        ("Smith", "S"),
        ("zebra", "Z"),  # already lowercase
    ])
    def test_basic_latin(self, router, name, expected):
        assert router.get_alpha_subdir(name) == expected

    @pytest.mark.parametrize("name,expected", [
        ("Étienne", "E"),
        ("Łukasz", "L"),
        ("Øksendal", "O"),
        ("Æthelstan", "A"),
        ("Müller", "M"),
        ("Žižek", "Z"),
    ])
    def test_diacritics_and_special_letters(self, router, name, expected):
        assert router.get_alpha_subdir(name) == expected

    @pytest.mark.parametrize("name,expected", [
        # Nobiliary particles file under the family name's first letter
        ("el Karoui", "K"),
        ("van der Waals", "W"),
        ("de la Cruz", "C"),
        ("von Neumann", "N"),
    ])
    def test_nobiliary_particles_stripped(self, router, name, expected):
        assert router.get_alpha_subdir(name) == expected

    @pytest.mark.parametrize("name,expected", [
        ("Αλεξανδρης", "A"),  # Greek alpha
        ("Ωμικρον", "O"),     # Greek omega
        ("Иванов", "I"),       # Cyrillic I
    ])
    def test_non_latin_scripts_romanized(self, router, name, expected):
        assert router.get_alpha_subdir(name) == expected

    def test_empty_name_falls_back_to_z(self, router):
        assert router.get_alpha_subdir("") == "Z"

    def test_numeric_prefix_skipped(self, router):
        # Leading digits/punct are ignored; first letter is what counts
        assert router.get_alpha_subdir("123Smith") == "S"


# ---------------------------------------------------------------------------
# determine_publication_status
# ---------------------------------------------------------------------------

class TestPublicationStatus:
    @pytest.fixture
    def router(self, tmp_path):
        return FolderRouter(tmp_path)

    def test_book_overrides_doi(self, router):
        # Books are books even if they have a DOI (10.1515/... etc.)
        meta = {"document_type": "book", "doi": "10.1515/9783111045283"}
        assert router.determine_publication_status(meta) == "book"

    def test_thesis(self, router):
        meta = {"document_type": "thesis"}
        assert router.determine_publication_status(meta) == "thesis"

    def test_doi_means_published(self, router):
        meta = {"doi": "10.1007/s00245-025-10368-x"}
        assert router.determine_publication_status(meta) == "published"

    def test_arxiv_means_unpublished(self, router):
        meta = {"arxiv_id": "2401.07160"}
        assert router.determine_publication_status(meta) == "unpublished"

    def test_no_metadata_means_working(self, router):
        meta = {}
        assert router.determine_publication_status(meta) == "working"

    def test_repository_doi_does_not_count_as_published(self, router):
        # SSRN / arXiv DOIs are repository, not journal publications
        meta = {"doi": "10.2139/ssrn.123456"}
        assert router.determine_publication_status(meta) == "working"


# ---------------------------------------------------------------------------
# Routing — full path resolution
# ---------------------------------------------------------------------------

class TestRouting:
    @pytest.fixture
    def router(self, tmp_path):
        return FolderRouter(tmp_path)

    def test_published_paper_gets_alpha_subdir(self, router, tmp_path):
        meta = {
            "doi": "10.1007/s00245-025-10368-x",
            "authors": [{"family": "Abraham", "given": "R."}],
        }
        dest = router.route(meta, "Abraham, R. - Foo.pdf")
        assert dest == tmp_path / PUBLISHED / "A" / "Abraham, R. - Foo.pdf"

    def test_unpublished_paper_gets_alpha_subdir(self, router, tmp_path):
        meta = {
            "arxiv_id": "2401.07160",
            "authors": [{"family": "Smith", "given": "J."}],
        }
        dest = router.route(meta, "Smith, J. - Bar.pdf")
        assert dest == tmp_path / UNPUBLISHED / "S" / "Smith, J. - Bar.pdf"

    def test_working_paper_with_year(self, router, tmp_path):
        meta = {"authors": [{"family": "Doe", "given": "J."}]}
        dest = router.route(meta, "Doe, J. - Baz.pdf", year=2020)
        # Working papers are routed under year subfolder
        assert dest.parent.parent == tmp_path / WORKING / "D"
        assert dest.parent.name == "2020"

    def test_book_no_alpha_subdir(self, router, tmp_path):
        # Books in this user's library go directly into 05/, no A-Z subfolder
        meta = {
            "document_type": "book",
            "authors": [{"family": "Föllmer", "given": "H."}],
        }
        dest = router.route(meta, "Föllmer, H. - Stochastic finance.pdf")
        assert dest.parent == tmp_path / BOOKS

    def test_thesis_routing(self, router, tmp_path):
        meta = {
            "document_type": "thesis",
            "authors": [{"family": "Smith", "given": "A."}],
        }
        dest = router.route(meta, "Smith, A. - PhD thesis.pdf")
        # Thesis routing depends on the system's convention — at minimum it
        # should NOT end up under PUBLISHED/UNPUBLISHED
        assert THESES in str(dest)

    def test_authors_dict_with_name_field(self, router, tmp_path):
        # Some sources give author dicts with "name" instead of "family"
        meta = {
            "doi": "10.1007/test",
            "authors": [{"name": "Pardoux"}],
        }
        dest = router.route(meta, "Pardoux - X.pdf")
        assert dest.parent == tmp_path / PUBLISHED / "P"

    def test_authors_string_lastname_first_format(self, router, tmp_path):
        # When authors are a list of strings: "Last, F."
        meta = {
            "doi": "10.1007/test",
            "authors": ["Smith, J.", "Doe, A."],
        }
        dest = router.route(meta, "Smith, J. - X.pdf")
        assert dest.parent == tmp_path / PUBLISHED / "S"

    def test_authors_string_firstname_first_format(self, router, tmp_path):
        # "I. Lastname" — last word is treated as the family name
        meta = {
            "doi": "10.1007/test",
            "authors": ["J. Smith"],
        }
        dest = router.route(meta, "Smith, J. - X.pdf")
        assert dest.parent == tmp_path / PUBLISHED / "S"

    def test_no_authors_falls_back_to_z(self, router, tmp_path):
        meta = {"doi": "10.1007/test", "authors": []}
        dest = router.route(meta, "anonymous.pdf")
        assert dest.parent == tmp_path / PUBLISHED / "Z"

    def test_empty_first_lastname_logs_warning(self, router, tmp_path, caplog):
        # Authors present but first one has empty family name (malformed input)
        # — should log a warning so the user can spot data-quality issues,
        # not silently file under Z.
        meta = {"doi": "10.1007/test", "authors": [{"family": "", "given": "X."}]}
        with caplog.at_level("WARNING"):
            dest = router.route(meta, "x.pdf")
        assert dest.parent == tmp_path / PUBLISHED / "Z"
        # Warning was emitted (don't pin the exact text — it's only for ops)
        assert any("empty first author" in r.message for r in caplog.records), (
            "expected a warning about empty first author"
        )


# ---------------------------------------------------------------------------
# Constants exports
# ---------------------------------------------------------------------------

class TestConstants:
    def test_status_dirs_complete(self):
        # Every status used by ingest_paper has a directory
        required = {"published", "unpublished", "working", "book", "thesis"}
        assert required.issubset(set(STATUS_DIRS))

    def test_to_be_sorted_constant(self):
        # The new staging-area constant is exported
        assert TO_BE_SORTED == "12 - To be sorted"
