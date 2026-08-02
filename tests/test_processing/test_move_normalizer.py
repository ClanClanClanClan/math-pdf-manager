"""Author-block normalization on move (synthetic only)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402


class TestNormalizeName:

    def test_spaces_initials(self):
        from processing.move_normalizer import normalize_authors_in_name
        new, changed = normalize_authors_in_name(
            "Dalang, R.C., Dozzi, M., Russo, F. - Stochastic analysis.pdf")
        assert changed
        assert new.startswith("Dalang, R. C., Dozzi, M., Russo, F. - ")

    def test_preserves_hyphenated_and_particles(self):
        from processing.move_normalizer import normalize_authors_in_name
        new, _ = normalize_authors_in_name(
            "le Bris, C.L., Lions, P.-L. - Existence and uniqueness.pdf")
        assert new.startswith("le Bris, C. L., Lions, P.-L. - ")

    def test_title_is_preserved_verbatim(self):
        # The danger case: title re-casing would lowercase proper nouns.
        # Author block is fixed but the title MUST be byte-preserved.
        from processing.move_normalizer import normalize_authors_in_name
        title = ("Seminar on stochastic analysis, random fields and "
                 "applications IV, centro Stefano Franscini, Ascona, May 2002")
        new, _ = normalize_authors_in_name(
            f"Dalang, R.C., Dozzi, M., Russo, F. - {title}.pdf")
        assert "Dalang, R. C." in new
        assert f"- {title}.pdf" in new           # title untouched
        assert "stefano franscini" not in new    # NOT lowercased
        assert "ascona, may 2002" not in new

    def test_already_correct_is_noop(self):
        from processing.move_normalizer import normalize_authors_in_name
        name = "Élie, R., Pérolat, J. - On mean field games.pdf"
        new, changed = normalize_authors_in_name(name)
        assert not changed and new == name

    def test_in_place_rename_is_reversible(self, tmp_path):
        from processing.identity import enable_sidecar_mirror
        from processing.move_normalizer import normalize_file_in_place
        from processing.undo_log import UndoLog
        enable_sidecar_mirror(tmp_path)
        p = tmp_path / "Dalang, R.C. - Stochastic analysis.pdf"
        _write_minimal_pdf(p, title="t", author="Dalang, R.C.")
        log = UndoLog(log_dir=tmp_path / ".operation_log")
        log.begin_transaction("normalize")
        changed, msg = normalize_file_in_place(p, undo_log=log)
        log.commit()
        assert changed
        fixed = tmp_path / "Dalang, R. C. - Stochastic analysis.pdf"
        assert fixed.exists() and not p.exists()
        log.undo_transaction(log.list_transactions()[-1]["id"])
        assert p.exists() and not fixed.exists()


class TestFileIntoTopicNormalizes:

    @pytest.fixture
    def lib(self, tmp_path):
        from processing.identity import enable_sidecar_mirror
        for d in ["01 - Published papers", "07a - BSDEs"]:
            (tmp_path / d).mkdir(parents=True)
        (tmp_path / "07a - BSDEs" / "01 - Published papers").mkdir(parents=True)
        enable_sidecar_mirror(tmp_path)
        return tmp_path

    def test_move_fixes_author_initials(self, lib):
        from processing.publication_topic_router import file_into_topic
        from processing.undo_log import UndoLog
        src = (lib / "01 - Published papers" / "D"
               / "Dalang, R.C. - Reflected BSDEs and backward equations.pdf")
        src.parent.mkdir(parents=True, exist_ok=True)
        _write_minimal_pdf(src, title="t", author="Dalang, R.C.")
        log = UndoLog(log_dir=lib / ".operation_log")
        log.begin_transaction("file")
        ok, msg = file_into_topic(src, "07a", lib, undo_log=log)
        log.commit()
        assert ok, msg
        dest = (lib / "07a - BSDEs" / "01 - Published papers" / "D"
                / "Dalang, R. C. - Reflected BSDEs and backward equations.pdf")
        assert dest.exists()
        assert not src.exists()

    def test_normalize_false_keeps_name(self, lib):
        from processing.publication_topic_router import file_into_topic
        src = (lib / "01 - Published papers" / "D"
               / "Dalang, R.C. - Reflected BSDEs and backward equations.pdf")
        src.parent.mkdir(parents=True, exist_ok=True)
        _write_minimal_pdf(src, title="t", author="Dalang, R.C.")
        ok, msg = file_into_topic(src, "07a", lib, normalize=False)
        assert ok, msg
        dest = (lib / "07a - BSDEs" / "01 - Published papers" / "D"
                / "Dalang, R.C. - Reflected BSDEs and backward equations.pdf")
        assert dest.exists()


class TestMultiLetterInitials:
    """Transliterated Cyrillic given names need 2-3 letter initials.

    "Kabanov, Yu. A." is the correct canonical form — Yu is the single
    Cyrillic letter Ю.  The spacing fixer used to test a fixed
    four-character window (upper, dot, upper, dot), so "Yu.A." never
    matched at all, and in a mixed author list it produced half-spaced
    output like "Kozlov, I. V., Veretennikov, A.Yu." — 45 such files were
    measured in the real library.
    """

    @pytest.mark.parametrize("raw,expected", [
        ("Kabanov, Yu.A. - Pricing.pdf", "Kabanov, Yu. A. - Pricing.pdf"),
        ("Neretin, Yu.V. - Gamma.pdf", "Neretin, Yu. V. - Gamma.pdf"),
        ("Zhang, Zh.Q. - Estimates.pdf", "Zhang, Zh. Q. - Estimates.pdf"),
        ("Ivanov, Ya.S. - A theorem.pdf", "Ivanov, Ya. S. - A theorem.pdf"),
        ("Djumanova, R.Kh. - Spectra.pdf", "Djumanova, R. Kh. - Spectra.pdf"),
        # single letter FOLLOWED by a multi-letter one — the half-spaced shape
        ("Veretennikov, A.Yu. - Moments.pdf", "Veretennikov, A. Yu. - Moments.pdf"),
        # a whole mixed list must come out uniformly spaced
        ("Kozlov, I.V., Veretennikov, A.Yu. - SLLN.pdf",
         "Kozlov, I. V., Veretennikov, A. Yu. - SLLN.pdf"),
    ])
    def test_multi_letter_initials_are_spaced(self, raw, expected):
        from processing.move_normalizer import normalize_authors_in_name
        assert normalize_authors_in_name(raw)[0] == expected

    @pytest.mark.parametrize("name", [
        # Hyphenated initials keep their hyphen and gain no space.
        "Lions, J.-P. - Analysis.pdf",
        "Le Gall, J.-F. - Brownian motion.pdf",
        # Already correct: the pass must be idempotent.
        "Kabanov, Yu. A. - Pricing.pdf",
        # A dotted abbreviation inside the TITLE is not an author initial.
        "Smith, J. - A trip to St.Petersburg.pdf",
    ])
    def test_non_initials_are_left_alone(self, name):
        from processing.move_normalizer import normalize_authors_in_name
        assert normalize_authors_in_name(name)[0] == name


class TestAccentedInitials:
    """The fast-path gate must not be ASCII-only.

    A pre-gate skips the (expensive) author checker when a name has no
    glued initials.  Written as ``re.compile(r"\\.[A-Z]")`` it missed
    every non-ASCII capital, so "Nielsen, M.Ø." was never even offered to
    the checker — which handles it correctly.  135 such names sat
    unfixed in the real library while the pipeline reported nothing to do.
    """

    @pytest.mark.parametrize("raw,expected", [
        ("Nielsen, M.Ø. - Test.pdf", "Nielsen, M. Ø. - Test.pdf"),
        ("Johansen, S., Nielsen, M.Ø. - X.pdf",
         "Johansen, S., Nielsen, M. Ø. - X.pdf"),
        ("Émery, M.É. - Martingales.pdf", "Émery, M. É. - Martingales.pdf"),
    ])
    def test_non_ascii_initials_are_spaced(self, raw, expected):
        from processing.move_normalizer import normalize_authors_in_name
        assert normalize_authors_in_name(raw)[0] == expected

    def test_gate_still_skips_clean_names(self):
        # The gate exists for speed; it must keep saying "nothing to do"
        # for an already-canonical block.
        from processing.move_normalizer import _has_unspaced_initials
        assert not _has_unspaced_initials("Smith, J. A., Doe, R. B.")
        assert not _has_unspaced_initials("Lions, J.-P.")
        assert _has_unspaced_initials("Smith, J.A.")
        assert _has_unspaced_initials("Nielsen, M.Ø.")
