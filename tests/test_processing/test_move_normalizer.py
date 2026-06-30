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
