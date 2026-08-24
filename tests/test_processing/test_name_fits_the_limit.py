"""Keep the title entire; drop authors minimally with ", et al.".

The rule already existed -- ``CMO._build_with_max_authors`` binary-searches
for the largest number of authors that still fits -- but the rename sweep did
not use it. It checked the byte limit and SKIPPED, so three papers could
never have their initials corrected: spacing a 15-author block pushes the
name from 249 bytes to 257 against a 255 limit.

The algorithm is now module-level in ``cmo`` and both callers share it.
"""
import re

import pytest

from arxivbot.models.cmo import ET_AL, build_with_max_authors
from processing.library_normalize import _MAX_FILENAME_BYTES, _fit_to_limit

TITLE = " - Adaptive human behavior in epidemiological models.pdf"


def _authors(n, name="Fenichel"):
    return ", ".join(f"{name}{i}, E. P." for i in range(n))


class TestTheTitleIsNeverTouched:
    @pytest.mark.parametrize("n", [13, 20, 40, 80])
    def test_however_many_authors_are_dropped(self, n):
        out = _fit_to_limit(_authors(n) + TITLE)
        assert out is not None
        assert out.endswith(TITLE), "the title was altered to make room"

    def test_a_title_too_long_on_its_own_is_refused_not_mangled(self):
        """Returning None sends it to the skip list, where a human sees it.
        Truncating the title would hide the problem and lose the paper's
        name."""
        huge = " - " + "A" * 300 + ".pdf"
        assert _fit_to_limit("Smith, J." + huge) is None


class TestItFitsAndIsMinimal:
    @pytest.mark.parametrize("n", [13, 15, 20, 50])
    def test_the_result_fits(self, n):
        out = _fit_to_limit(_authors(n) + TITLE)
        assert len(out.encode("utf-8")) <= _MAX_FILENAME_BYTES

    def test_it_keeps_as_many_authors_as_will_fit(self, ):
        """Minimal means minimal: adding one more author must overflow."""
        out = _fit_to_limit(_authors(30) + TITLE)
        kept = out.split(" - ")[0]
        assert kept.endswith("et al.")
        names = [p for p in re.findall(r"Fenichel\d+, E\. P\.", kept)]
        one_more = ", ".join(
            [f"Fenichel{i}, E. P." for i in range(len(names) + 1)]) + ET_AL + TITLE
        assert len(one_more.encode("utf-8")) > _MAX_FILENAME_BYTES

    def test_a_name_that_already_fits_is_returned_unchanged_by_the_algorithm(self):
        segs = ["Smith, J.", "Jones, A."]
        assert build_with_max_authors(segs, TITLE, 255) == "Smith, J., Jones, A." + TITLE


class TestAnExistingEtAlSurvives:
    """The bug this class exists for: ``parse_authors_string`` DISCARDS a
    trailing "et al.", so rebuilding a name through the parser produced one
    claiming eleven authors for a paper that has more. Two of the three real
    files were affected."""

    def test_it_is_not_silently_dropped(self):
        original = (
            "Oliu-Barton, M., Pradelski, B. S. R., Algan, Y., Baker, M. G., "
            "Binagwaho, A., Dore, G. J., El-Mohandes, A., Fontanet, A., "
            "Peichl, A., Priesemann, V., Wolff, G. B., et al."
            " - Elimination versus mitigation of SARS-CoV-2 in the presence "
            "of effective vaccines.pdf")
        out = _fit_to_limit(original)
        assert out is not None
        assert "et al." in out, "the paper has more authors than the name now says"
        assert len(out.encode("utf-8")) <= _MAX_FILENAME_BYTES

    def test_only_one_et_al_ends_up_in_the_name(self):
        out = _fit_to_limit(_authors(40)[:200] + ", et al." + TITLE)
        assert out is None or out.count("et al.") == 1


class TestTheHouseSpelling:
    def test_it_is_a_comma_then_et_al(self):
        """Measured: 10 of the 12 existing names that carry it write
        ", et al.". The other two are defects -- one missing the comma, one
        spelled "etal"."""
        assert ET_AL == ", et al."
        out = _fit_to_limit(_authors(30) + TITLE)
        assert ", et al. - " in out


class TestPathologies:
    @pytest.mark.parametrize("name", [
        "", "x", "no-separator.pdf", " - only a title.pdf", "Smith, J. - .pdf",
        "Smith, J.pdf", "A" * 300 + ".pdf",
    ])
    def test_never_raises(self, name):
        out = _fit_to_limit(name)
        assert out is None or isinstance(out, str)

    def test_a_short_name_is_not_disturbed(self):
        """_fit_to_limit is only ever called on an over-long name, but it must
        not corrupt a short one if it ever is."""
        short = "Rogers, L. C. G. - A short title.pdf"
        out = _fit_to_limit(short)
        assert out in (short, None)


class TestTheRenameSweepUsesIt:
    """A helper nothing calls is a helper that does not work.

    apply_renames used to check the byte limit and append to ``skipped``.
    Testing ``_fit_to_limit`` alone left that path untested, and a mutation
    that restored the skip survived.
    """

    @staticmethod
    def _library(tmp_path):
        root = tmp_path / "Maths"
        folder = root / "01 - Published papers" / "F"
        folder.mkdir(parents=True)
        (root / ".mathpdf-sidecars").mkdir()
        return root, folder

    def test_an_over_long_target_is_truncated_not_skipped(self, tmp_path):
        from processing.library_normalize import apply_renames
        root, folder = self._library(tmp_path)
        # The real shape: the CURRENT name fits and the CORRECTED one does
        # not, because spacing each author's initials costs a byte. Sizing it
        # by eye does not work -- my first attempt built a source name the
        # filesystem itself refused to create.
        n = 12
        old_stem = ", ".join(f"Fenichel{i}, E.P." for i in range(n))
        new_stem = ", ".join(f"Fenichel{i}, E. P." for i in range(n))
        room = _MAX_FILENAME_BYTES - len(f"{old_stem} - .pdf".encode("utf-8"))
        title = " - " + "A" * (room - 1)
        old = folder / f"{old_stem}{title}.pdf"
        proposed = f"{new_stem}{title}.pdf"
        assert len(old.name.encode("utf-8")) <= _MAX_FILENAME_BYTES, \
            "the source must be a name that can actually exist"
        assert len(proposed.encode("utf-8")) > _MAX_FILENAME_BYTES, \
            "this test needs a target that genuinely overflows"
        old.write_bytes(b"%PDF-1.4\n")

        res = apply_renames(
            root,
            [{"old": str(old.relative_to(root)),
              "new": str((folder / proposed).relative_to(root)),
              "name": proposed, "old_name": old.name}],
            dry_run=False)

        assert res["renamed"] == 1, f"skipped instead of truncating: {res.get('skipped')}"
        assert not old.exists()
        landed = [p for p in folder.iterdir() if p.suffix == ".pdf"]
        assert len(landed) == 1
        name = landed[0].name
        assert len(name.encode("utf-8")) <= _MAX_FILENAME_BYTES
        assert name.endswith(f"{title}.pdf"), "the title was cut"
        assert ", et al. - " in name
        assert "E. P." in name and "E.P." not in name, "the spacing fix was lost"

    def test_a_target_that_cannot_be_made_to_fit_is_still_skipped(self, tmp_path):
        """The escape hatch must stay open: a title too long on its own is
        reported, not silently shortened."""
        from processing.library_normalize import apply_renames
        root, folder = self._library(tmp_path)
        old = folder / "Smith, J.P. - short.pdf"
        old.write_bytes(b"%PDF-1.4\n")
        huge = "Smith, J. P. - " + "A" * 300 + ".pdf"
        res = apply_renames(
            root,
            [{"old": str(old.relative_to(root)),
              "new": str((folder / huge).relative_to(root)),
              "name": huge, "old_name": old.name}],
            dry_run=False)
        assert res["renamed"] == 0
        assert res["skipped"][0]["reason"] == "name too long"
        assert old.exists(), "the source was moved despite the skip"
