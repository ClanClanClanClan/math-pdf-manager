"""What tooling may touch, and what it must leave alone.

The owner has given the archival instruction more than once. That is a defect
in the code, not in his patience: before this module every tool carried its
own private skip list -- ``SKIP_PREFIXES`` in duplicate_finder, ``_STAGING_DIR``
in library_normalize, ``TO_BE_SORTED`` in organization.system -- they did not
agree, and each new tool started by forgetting something.
"""
import unicodedata

import pytest

from processing.library_scope import (
    ARCHIVAL_COLLECTIONS, NON_LIBRARY, STAGING,
    exclusion_reason, filter_in_scope, in_scope,
)

JEHPS = "09 - Journal Électronique d'Histoire des Probabilités et de la Statistique"
CR = "05 - Books and lecture notes/01 - Comptes rendus hebdomadaires de l'académie des sciences"
HIST = "05 - Books and lecture notes/00 - Histoire de l'académie royale des sciences"
DIVERS = ("05 - Books and lecture notes/02 - Mémoires présentés par divers savants "
          "à l'académie royale des sciences de l'institut de France")
LVIV = "05 - Books and lecture notes/11 - Lviv Scottish book"


class TestTheArchivalCollections:
    """All five the owner named, and nothing else."""

    @pytest.mark.parametrize("folder", [JEHPS, CR, HIST, DIVERS, LVIV])
    def test_excluded(self, folder):
        assert not in_scope(f"{folder}/anything.pdf")
        assert "leave alone" in exclusion_reason(f"{folder}/anything.pdf")

    @pytest.mark.parametrize("folder", [
        "01 - Published papers/R",
        "03 - Working papers/B/2024",
        "05 - Books and lecture notes/05 - Astérisque",
        "05 - Books and lecture notes/03 - Mémoires de la société mathématique de France",
        "05 - Books and lecture notes/06 - Saint-Flour",
        "06 - Theses/Z",
        "08 - Séminaires de probabilités de Strasbourg/Séminaire 12 - 1978",
        "07b - Contract theory/01 - Published papers/C",
    ])
    def test_neighbours_are_still_in_scope(self, folder):
        """Astérisque and the SMF Mémoires live in the same parent as two of
        the excluded collections, and the Séminaire is a different 08."""
        assert in_scope(f"{folder}/x.pdf"), exclusion_reason(f"{folder}/x.pdf")

    def test_the_folder_itself_is_excluded_not_only_its_contents(self):
        assert not in_scope(CR)

    def test_a_folder_that_merely_starts_the_same_is_not_excluded(self):
        """A prefix test without a boundary would swallow this."""
        assert in_scope(CR + " TWO/x.pdf")

    def test_they_can_be_included_deliberately(self):
        """A dedicated pass over them is expected -- completing the runs and
        checking their naming -- and must be able to ask."""
        assert in_scope(f"{CR}/x.pdf", include_archival=True)


class TestNfd:
    """macOS returns decomposed paths, and every one of these folder names is
    dense with accents. A precomposed constant compared against a decomposed
    path never matches, which would make this module a silent no-op."""

    @pytest.mark.parametrize("folder", [JEHPS, CR, HIST, DIVERS])
    def test_a_decomposed_path_is_still_excluded(self, folder):
        nfd = unicodedata.normalize("NFD", f"{folder}/x.pdf")
        assert nfd != f"{folder}/x.pdf", "this test needs a genuinely decomposed input"
        assert not in_scope(nfd)


class TestTheOtherTwoKinds:
    @pytest.mark.parametrize("folder", STAGING)
    def test_staging_is_excluded_because_it_is_not_renamed_yet(self, folder):
        assert "staging" in exclusion_reason(f"{folder}/x.pdf")

    def test_staging_can_be_included_deliberately(self):
        assert in_scope("12 - To be sorted/x.pdf", include_staging=True)

    @pytest.mark.parametrize("folder", NON_LIBRARY)
    def test_non_library_content_is_excluded(self, folder):
        assert not in_scope(f"{folder}/x.pdf")

    def test_non_library_is_excluded_at_any_depth(self):
        """.trash sits inside the library folders, not beside them."""
        assert not in_scope("01 - Published papers/.trash/retired/x.pdf")

    def test_non_library_cannot_be_opted_back_in(self):
        """Scripts is the code that manages the library. There is no flag for
        treating it as library content, because it never is."""
        assert not in_scope("Scripts/src/x.py", include_archival=True, include_staging=True)


class TestNothingIsDroppedSilently:
    def test_the_filter_reports_what_it_removed_and_why(self):
        paths = [
            "01 - Published papers/R/a.pdf",
            f"{CR}/b.pdf",
            f"{JEHPS}/c.pdf",
            "12 - To be sorted/d.pdf",
            "Scripts/e.py",
        ]
        kept, dropped = filter_in_scope(paths)
        assert kept == ["01 - Published papers/R/a.pdf"]
        assert sum(dropped.values()) == 4
        assert len(dropped) == 4, "each exclusion must name its own reason"

    def test_an_empty_path_is_in_scope_rather_than_crashing(self):
        assert in_scope("")
        assert in_scope(None)


class TestItMatchesTheRealLibrary:
    """A count, so that a rule quietly ceasing to match gets noticed."""

    def test_the_archival_list_names_five_collections(self):
        assert len(ARCHIVAL_COLLECTIONS) == 5


# ----------------------------------------------------------------------
# The sweeps must actually honour it
# ----------------------------------------------------------------------
class TestTheSweepsHonourScope:
    """A scope module nothing calls is a shelf ornament.

    These build a tiny library holding one ordinary paper and one file in
    each excluded collection, run the real sweeps, and check what came back.
    """

    @staticmethod
    def _library(tmp_path):
        root = tmp_path / "Maths"
        placed = {}
        for rel, name in [
            ("01 - Published papers/R", "Zzz,A.B. - An Ordinary Paper"),
            (CR, "Comptes rendus hebdomadaires des séances de l'académie des sciences, tome 099"),
            (JEHPS, "Document 3, rapport Bertillon"),
            (LVIV, "Book 0"),
            ("12 - To be sorted", "2105.10623v1"),
        ]:
            folder = root / rel
            folder.mkdir(parents=True, exist_ok=True)
            pdf = folder / f"{name}.pdf"
            pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
            placed[rel] = pdf
        return root, placed

    def test_the_rename_sweep_skips_them_and_says_so(self, tmp_path):
        from processing.library_normalize import scan
        root, _ = self._library(tmp_path)
        result = scan(root)
        touched = {p["old"] for p in result["proposals"]}
        for excluded in (CR, JEHPS, LVIV, "12 - To be sorted"):
            assert not any(excluded in t for t in touched), \
                f"the rename sweep proposed a change inside {excluded}"
        # and it reports the skip rather than swallowing it
        assert result["skipped_total"] == 4
        assert len(result["skipped"]) >= 2, "each kind of exclusion names itself"

    def test_the_duplicate_scan_skips_them(self, tmp_path):
        """The academy volumes are near-identical BY DESIGN -- "tome 271" and
        "tome 272" differ by one digit -- so before this every one of them
        looked like a near-duplicate of its neighbour."""
        from processing.duplicate_finder import find_duplicates
        root, _ = self._library(tmp_path)
        for rel in (CR, JEHPS):
            folder = root / rel
            for n in ("volume A", "volume B"):
                (folder / f"Same, A. - {n}.pdf").write_bytes(b"%PDF-1.4\n")
        seen = " ".join(str(g) for g in find_duplicates(root))
        for excluded in (CR, JEHPS, LVIV):
            assert excluded not in seen, f"the duplicate scan looked inside {excluded}"

    def test_the_ordinary_paper_is_still_reached(self, tmp_path):
        """The exclusions must not turn the sweep off entirely -- a test that
        only checks 'nothing from the excluded folders' passes when the sweep
        is broken."""
        from processing.library_normalize import scan
        root, _ = self._library(tmp_path)
        result = scan(root)
        assert any("01 - Published papers" in p["old"] for p in result["proposals"]), \
            "the sweep found nothing at all, so proving it skipped things proves nothing"
