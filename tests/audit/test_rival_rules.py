"""Facts about rival implementations, pinned so they cannot rot quietly.

docs/duplicated-rules-review.md records which implementation of each rule is
live and which is not. Those claims are the reason some rivals were deleted
and others deliberately kept. A claim nothing checks is a claim that will be
wrong in six months.
"""
import ast
import pathlib

import pytest

SRC = pathlib.Path(__file__).resolve().parents[2] / "src"


def _module_defines(rel: str, name: str) -> bool:
    tree = ast.parse((SRC / rel).read_text(encoding="utf-8"))
    return any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
               and n.name == name for n in tree.body)


class TestTheDeletedOnesStayDeleted:
    @pytest.mark.parametrize("rel", ["validators/manual_validation.py"])
    def test_module_is_gone(self, rel):
        """It ran its checks AT IMPORT TIME, all seven failed, and it imported
        five modules that do not exist."""
        assert not (SRC / rel).exists()

    @pytest.mark.parametrize("name", ["to_sentence_case_academic", "to_sentence_case"])
    def test_the_orphaned_casing_copies_stay_gone(self, name):
        """The live casing path imports from core.sentence_case. These copies
        had zero callers and disagreed with the live one on 38.7% of titles."""
        assert not _module_defines("validators/filename_checker/text_processing.py", name)


class TestTheCasingPathHasOneImplementation:
    def test_the_checker_imports_it_from_core(self):
        src = (SRC / "validators/filename_checker/core.py").read_text(encoding="utf-8")
        assert "from core.sentence_case import to_sentence_case_academic" in src

    def test_core_sentence_case_still_provides_it(self):
        assert _module_defines("core/sentence_case.py", "to_sentence_case_academic")


class TestTheRenamePathDoesNotRecase:
    """This is what makes the 38.6% disagreement between the two
    find_math_regions implementations harmless for renames. If it ever
    changes, that disagreement becomes a data problem and this test is the
    warning."""

    def test_normalize_full_name_passes_sentence_case_false(self):
        src = (SRC / "processing/move_normalizer.py").read_text(encoding="utf-8")
        assert "sentence_case=False" in src

    def test_the_canonical_name_builder_does_too(self):
        src = (SRC / "arxivbot/models/cmo.py").read_text(encoding="utf-8")
        assert "sentence_case=False" in src


class TestTheThreeComparisonRulesAreDifferentOnPurpose:
    """Same name, three questions. Merging them would be a bug: folding an en
    dash to a hyphen is right for near-duplicate hunting and wrong for
    deciding whether a name is canonical, because this library distinguishes
    them -- Hamilton–Jacobi versus mean-field."""

    NAME = "Lévy–Itô decomposition of the Brownian motion"

    def test_the_duplicate_hunter_keeps_the_dash_type(self):
        from processing.duplicate_finder import normalize_for_comparison
        assert "–" in normalize_for_comparison(self.NAME)

    def test_the_unicode_handler_folds_it(self):
        from validators.unicode_handler import normalize_for_comparison
        out = normalize_for_comparison(self.NAME)
        assert "–" not in out and "Lévy-Itô" in out

    def test_they_therefore_disagree(self):
        from processing.duplicate_finder import normalize_for_comparison as dup
        from validators.unicode_handler import normalize_for_comparison as uni
        assert dup(self.NAME) != uni(self.NAME)


class TestEveryNfcWrapperAgrees:
    """Seven of them, measured identical over 8,007 real strings. Kept
    because each is a one-line call to the stdlib -- the stdlib is the single
    implementation. This fails if one of them starts doing something else."""

    SAMPLES = ["Émery", "ℝ^∞", "Bₜ", "Röckner, M.", "  x  ", "", "Astérisque 390"]

    def _impls(self):
        from core.text_processing.text_normalization import normalize_nfc_cached
        from core.text_processing.unicode_utils import nfc as core_nfc
        from maintenance.conformance import _nfc as conf
        from processing.filename_ground_truth import _nfc as gt
        from processing.library_normalize import _nfc as ln
        from validators.filename_checker.unicode_utils import nfc as fc
        from validators.unicode_handler import nfc as uh
        return [conf, gt, ln, fc, uh, normalize_nfc_cached, core_nfc]

    @pytest.mark.parametrize("text", SAMPLES)
    def test_all_seven_agree(self, text):
        outs = {fn(text) for fn in self._impls()}
        assert len(outs) == 1, f"the nfc wrappers have diverged: {outs}"

    @pytest.mark.parametrize("text", SAMPLES)
    def test_and_all_seven_are_strictly_nfc(self, text):
        import unicodedata
        want = unicodedata.normalize("NFC", text)
        for fn in self._impls():
            assert fn(text) == want, f"{fn.__module__}.{fn.__name__} does more than NFC"
