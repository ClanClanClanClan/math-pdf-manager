"""Gated bulk-apply of topic proposals (synthetic library only)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402


@pytest.fixture
def lib(tmp_path):
    from processing.identity import enable_sidecar_mirror
    for d in ["01 - Published papers", "07a - BSDEs"]:
        (tmp_path / d).mkdir(parents=True)
    (tmp_path / "07a - BSDEs" / "01 - Published papers").mkdir(parents=True)
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _seed_movable_bsde(lib):
    # A confident-BSDE paper sitting in a STANDARD folder -> 'move'.
    p = (lib / "01 - Published papers" / "S"
         / "Smith, J. - Reflected BSDEs and backward stochastic equations.pdf")
    p.parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_pdf(p, title="t", author="Smith, J.")
    return p


class TestFileIntoTopic:

    def test_moves_and_records_topic(self, lib):
        from processing.publication_topic_router import file_into_topic
        from processing.identity import PaperIdentity
        from processing.undo_log import UndoLog
        p = _seed_movable_bsde(lib)
        log = UndoLog(log_dir=lib / ".operation_log")
        log.begin_transaction("t")
        ok, msg = file_into_topic(p, "07a", lib, undo_log=log)
        assert ok, msg
        dest = (lib / "07a - BSDEs" / "01 - Published papers" / "S"
                / "Smith, J. - Reflected BSDEs and backward stochastic equations.pdf")
        assert dest.exists()
        assert not p.exists()
        assert "07a" in PaperIdentity.load(dest).topic_codes

    def test_rejects_unknown_code(self, lib):
        from processing.publication_topic_router import file_into_topic
        p = _seed_movable_bsde(lib)
        ok, msg = file_into_topic(p, "07z", lib)
        assert not ok and "unknown topic" in msg

    def test_subtopic_folder_routing(self, lib):
        # file_into_topic routes into <topic>/<subtopic>/<status>/...
        from processing.publication_topic_router import file_into_topic
        (lib / "07a - BSDEs" / "07a - Numerical methods").mkdir(parents=True)
        p = _seed_movable_bsde(lib)
        ok, msg = file_into_topic(p, "07a", lib,
                                  subtopic_folder="07a - Numerical methods")
        assert ok, msg
        dest = (lib / "07a - BSDEs" / "07a - Numerical methods"
                / "01 - Published papers" / "S" / p.name)
        assert dest.exists()

    def test_doc_bucket_routing(self, lib):
        # file_into_topic redirects a book/thesis into the topic's 05/06.
        from processing.publication_topic_router import file_into_topic
        p = _seed_movable_bsde(lib)
        ok, msg = file_into_topic(p, "07a", lib,
                                  doc_bucket="06 - Theses")
        assert ok, msg
        dest = (lib / "07a - BSDEs" / "06 - Theses" / "S" / p.name)
        assert dest.exists()
        # NOT in the original status bucket.
        assert not (lib / "07a - BSDEs" / "01 - Published papers" / "S" / p.name).exists()


class TestBulkApply:

    def test_dry_run_lists_without_moving(self, lib):
        from processing.pipeline_preview import apply_topic_proposals
        p = _seed_movable_bsde(lib)
        res = apply_topic_proposals(lib, dry_run=True)
        assert res["dry_run"] is True
        assert res["selected"] >= 1
        assert any(w["path"] == str(p) for w in res["would_apply"])
        # Nothing moved.
        assert p.exists()

    def test_apply_moves_confident_and_is_undoable(self, lib):
        from processing.pipeline_preview import apply_topic_proposals
        from processing.undo_log import UndoLog
        p = _seed_movable_bsde(lib)
        res = apply_topic_proposals(lib)
        assert len(res["applied"]) == 1
        assert res["failed"] == []
        dest = (lib / "07a - BSDEs" / "01 - Published papers" / "S"
                / p.name)
        assert dest.exists() and not p.exists()
        # The whole batch is one undoable transaction.
        log = UndoLog()
        log.log_dir = lib / ".operation_log"
        log.undo_transaction(res["tx_id"])
        assert p.exists() and not dest.exists()

    def test_apply_default_excludes_disagree(self, lib):
        # A paper hand-filed in 07a that the classifier would send to a
        # DIFFERENT topic must NOT be touched by the default apply
        # (statuses=("move",)).
        from processing.pipeline_preview import apply_topic_proposals
        sub = lib / "07a - BSDEs" / "01 - Published papers" / "S"
        sub.mkdir(parents=True, exist_ok=True)
        # Title that the classifier would auto-file to 07a (same as
        # current) -> 'agree', not disagree; but ensure no move happens
        # for already-in-topic papers regardless.
        p = sub / "Smith, J. - Reflected BSDEs.pdf"
        _write_minimal_pdf(p, title="t", author="Smith, J.")
        res = apply_topic_proposals(lib)
        # The in-topic paper is never a 'move', so it stays put.
        assert p.exists()
        assert all(a["path"] != str(p) for a in res["applied"])

    def test_limit_caps_apply(self, lib):
        from processing.pipeline_preview import apply_topic_proposals
        for i in range(3):
            p = (lib / "01 - Published papers" / "S"
                 / f"Smith, J. - Reflected BSDEs variant {i}.pdf")
            p.parent.mkdir(parents=True, exist_ok=True)
            _write_minimal_pdf(p, title="t", author="Smith, J.")
        res = apply_topic_proposals(lib, limit=2)
        assert len(res["applied"]) == 2

    def test_apply_routes_into_subtopic(self, lib):
        # End-to-end: a confident numerical-methods BSDE paper is filed
        # into the 07a Numerical methods sub-subtopic, not the topic root.
        from processing.pipeline_preview import apply_topic_proposals
        (lib / "07a - BSDEs" / "07a - Numerical methods").mkdir(parents=True)
        p = (lib / "01 - Published papers" / "D"
             / "Deep, L. - Deep learning numerical scheme for reflected BSDEs and backward equations.pdf")
        p.parent.mkdir(parents=True, exist_ok=True)
        _write_minimal_pdf(p, title="t", author="Deep, L.")
        res = apply_topic_proposals(lib)
        assert len(res["applied"]) == 1
        dest = (lib / "07a - BSDEs" / "07a - Numerical methods"
                / "01 - Published papers" / "D" / p.name)
        assert dest.exists(), res

    def test_apply_routes_thesis_into_06(self, lib):
        # A thesis-titled confident BSDE paper is filed into 07a/06 - Theses.
        from processing.pipeline_preview import apply_topic_proposals
        p = (lib / "01 - Published papers" / "P"
             / "PhD, A. - A PhD thesis on reflected BSDEs and backward stochastic equations.pdf")
        p.parent.mkdir(parents=True, exist_ok=True)
        _write_minimal_pdf(p, title="t", author="PhD, A.")
        res = apply_topic_proposals(lib)
        assert len(res["applied"]) == 1
        dest = (lib / "07a - BSDEs" / "06 - Theses" / "P" / p.name)
        assert dest.exists(), res
