"""Whole-library exact-duplicate detection + reversible resolution.

Synthetic library only -- never touches the real Dropbox tree.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402


@pytest.fixture
def lib(tmp_path):
    from processing.identity import enable_sidecar_mirror
    for d in [
        "01 - Published papers", "04 - Papers to be downloaded",
        "07a - BSDEs", "10 - Math slides", "12 - To be sorted",
    ]:
        (tmp_path / d).mkdir(parents=True)
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _identical(*paths: Path) -> None:
    """Write byte-identical PDFs at every path (first is the template)."""
    paths[0].parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_pdf(paths[0], title="Dup", author="Smith, J.")
    data = paths[0].read_bytes()
    for p in paths[1:]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)


class TestDetection:

    def test_status_topic_dup_keeps_topic(self, lib):
        from processing.duplicate_scan import find_exact_duplicates
        status = lib / "01 - Published papers" / "S" / "Smith, J. - Paper.pdf"
        topic = (lib / "07a - BSDEs" / "01 - Published papers" / "S"
                 / "Smith, J. - Paper.pdf")
        _identical(status, topic)
        groups = find_exact_duplicates(lib)
        assert len(groups) == 1
        g = groups[0]
        assert g.kind == "status+topic"
        assert g.keep == str(topic)            # topic wins
        assert g.remove == [str(status)]
        assert g.auto_safe is True

    def test_staging_copy_loses_to_real_home(self, lib):
        from processing.duplicate_scan import find_exact_duplicates
        staging = lib / "04 - Papers to be downloaded" / "2301.0001v1.pdf"
        home = lib / "01 - Published papers" / "S" / "Smith, J. - Paper.pdf"
        _identical(staging, home)
        g = find_exact_duplicates(lib)[0]
        assert g.kind == "staging-leftover"
        assert g.keep == str(home)
        assert g.remove == [str(staging)]
        assert g.auto_safe is True

    def test_special_collection_flagged_review(self, lib):
        from processing.duplicate_scan import find_exact_duplicates
        slides = lib / "10 - Math slides" / "Smith, J. - Paper.pdf"
        home = lib / "01 - Published papers" / "S" / "Smith, J. - Paper.pdf"
        _identical(slides, home)
        g = find_exact_duplicates(lib)[0]
        assert g.auto_safe is False              # curated collection -> review
        assert str(slides) not in g.remove       # never auto-remove the special copy

    def test_distinct_content_not_grouped(self, lib):
        from processing.duplicate_scan import find_exact_duplicates
        a = lib / "01 - Published papers" / "S" / "Smith, J. - Paper.pdf"
        b = lib / "07a - BSDEs" / "01 - Published papers" / "S" / "Smith, J. - Paper.pdf"
        a.parent.mkdir(parents=True, exist_ok=True)
        b.parent.mkdir(parents=True, exist_ok=True)
        _write_minimal_pdf(a, title="Alpha", author="Smith, J.")
        _write_minimal_pdf(b, title="A completely different and longer paper title here",
                           author="Jones, K.")
        # Different content (and almost certainly different size) -> no group.
        assert find_exact_duplicates(lib) == []

    def test_inbox_copy_loses(self, lib):
        from processing.duplicate_scan import find_exact_duplicates
        inbox = lib / "12 - To be sorted" / "Smith, J. - Paper.pdf"
        home = lib / "01 - Published papers" / "S" / "Smith, J. - Paper.pdf"
        _identical(inbox, home)
        g = find_exact_duplicates(lib)[0]
        assert g.keep == str(home)
        assert str(inbox) in g.remove

    def test_name_divergent_byte_identical_is_review(self, lib):
        # Two byte-identical files with DIFFERENT titles in the same folder
        # = a possible mis-file (one paper's content may actually be
        # missing).  Must NOT auto-resolve.
        from processing.duplicate_scan import find_exact_duplicates
        a = lib / "01 - Published papers" / "G" / "Geiss, S., Gobet, E. - Fractional smoothness of functionals.pdf"
        b = lib / "01 - Published papers" / "G" / "Geiss, S., Toivola, A. - Weak convergence of error processes in Besov spaces.pdf"
        _identical(a, b)
        g = find_exact_duplicates(lib)[0]
        assert g.auto_safe is False
        assert any("mis-file" in n for n in g.notes)

    def test_cross_home_is_review(self, lib):
        # Same paper byte-identical in Published AND Books -> the user must
        # pick the correct home; not auto-safe.
        from processing.duplicate_scan import find_exact_duplicates
        (lib / "05 - Books and lecture notes" / "S").mkdir(parents=True, exist_ok=True)
        pub = lib / "01 - Published papers" / "S" / "Smith, J. - Paper.pdf"
        book = lib / "05 - Books and lecture notes" / "S" / "Smith, J. - Paper.pdf"
        _identical(pub, book)
        g = find_exact_duplicates(lib)[0]
        assert g.kind == "cross-folder"
        assert g.auto_safe is False


class TestIngestGuard:

    def test_finds_existing_byte_identical_copy(self, lib):
        from processing.duplicate_scan import find_library_duplicate
        filed = lib / "01 - Published papers" / "S" / "Smith, J. - X.pdf"
        arrival = lib / "12 - To be sorted" / "dropped.pdf"
        _identical(filed, arrival)
        hit = find_library_duplicate(arrival, lib, ignore=[arrival.parent])
        assert hit == str(filed)

    def test_distinct_arrival_is_not_flagged(self, lib):
        from processing.duplicate_scan import find_library_duplicate
        filed = lib / "01 - Published papers" / "S" / "Smith, J. - X.pdf"
        filed.parent.mkdir(parents=True, exist_ok=True)
        _write_minimal_pdf(filed, title="X", author="Smith, J.")
        arrival = lib / "12 - To be sorted" / "new.pdf"
        arrival.parent.mkdir(parents=True, exist_ok=True)
        _write_minimal_pdf(arrival, title="A genuinely new and different paper",
                           author="Jones, K.")
        assert find_library_duplicate(arrival, lib, ignore=[arrival.parent]) is None

    def test_ignore_excludes_inbox_siblings(self, lib):
        # Two identical files both in the inbox: with the inbox ignored,
        # the arrival must not match its own sibling.
        from processing.duplicate_scan import find_library_duplicate
        a = lib / "12 - To be sorted" / "a.pdf"
        b = lib / "12 - To be sorted" / "b.pdf"
        _identical(a, b)
        assert find_library_duplicate(a, lib, ignore=[a.parent]) is None

    def test_ingest_with_dedup_check_skips_duplicate(self, lib):
        # End-to-end: ingest_paper(dedup_check=True) must refuse to file a
        # second copy of an already-filed paper.
        from processing.ingest import ingest_paper
        filed = lib / "01 - Published papers" / "S" / "Smith, J. - X.pdf"
        arrival = lib / "12 - To be sorted" / "dropped.pdf"
        _identical(filed, arrival)
        res = ingest_paper(arrival, library_root=lib, dedup_check=True)
        assert res.get("duplicate_of") == str(filed)
        assert res["success"] is False
        assert arrival.exists()                # source left in place

    def test_ingest_without_dedup_check_is_unchanged(self, lib):
        # Default (dedup_check off) must NOT consult the guard, so an
        # idempotent re-ingest path keeps its old behaviour.
        from processing.ingest import ingest_paper
        filed = lib / "01 - Published papers" / "S" / "Smith, J. - X.pdf"
        arrival = lib / "12 - To be sorted" / "dropped.pdf"
        _identical(filed, arrival)
        res = ingest_paper(arrival, library_root=lib)   # no dedup_check
        assert "duplicate_of" not in res


class TestResolution:

    def test_dry_run_touches_nothing(self, lib):
        from processing.duplicate_scan import apply_duplicate_resolutions
        status = lib / "01 - Published papers" / "S" / "Smith, J. - Paper.pdf"
        topic = (lib / "07a - BSDEs" / "01 - Published papers" / "S"
                 / "Smith, J. - Paper.pdf")
        _identical(status, topic)
        res = apply_duplicate_resolutions(lib, dry_run=True)
        assert res["dry_run"] is True
        assert res["selected"] == 1
        assert res["would_remove"] == 1
        assert status.exists() and topic.exists()   # nothing moved

    def test_apply_trashes_and_is_reversible(self, lib):
        from processing.duplicate_scan import apply_duplicate_resolutions
        from processing.undo_log import UndoLog
        status = lib / "01 - Published papers" / "S" / "Smith, J. - Paper.pdf"
        topic = (lib / "07a - BSDEs" / "01 - Published papers" / "S"
                 / "Smith, J. - Paper.pdf")
        _identical(status, topic)
        res = apply_duplicate_resolutions(lib, dry_run=False)
        assert res["removed"] == 1
        assert res["failed"] == []
        assert topic.exists()                        # keeper stays
        assert not status.exists()                   # redundant copy trashed
        trashed = lib / ".trash" / "duplicates" / "Smith, J. - Paper.pdf"
        assert trashed.exists()
        # One-click reversible.
        log = UndoLog(log_dir=lib / ".operation_log")
        log.undo_transaction(res["tx_id"])
        assert status.exists() and not trashed.exists()

    def test_keeper_inherits_removed_sidecar_metadata(self, lib):
        # Regression (adversarial audit): the keeper must absorb the
        # removed copy's sidecar knowledge.  The merge has to run BEFORE
        # the copy is trashed — once moved, its sidecar lives in the trash
        # mirror and the merge would silently find nothing.
        from processing.duplicate_scan import resolve_group, DuplicateGroup
        from processing.identity import PaperIdentity
        from processing.undo_log import UndoLog
        keep = (lib / "07a - BSDEs" / "01 - Published papers" / "S"
                / "Smith, J. - Paper.pdf")
        rem = lib / "01 - Published papers" / "S" / "Smith, J. - Paper.pdf"
        _identical(keep, rem)
        PaperIdentity().save(keep)                       # bare keeper sidecar
        rid = PaperIdentity()
        rid.topic_codes = ["07a"]
        rid.doi = "10.1/xyz"
        rid.save(rem)                                    # removed carries knowledge
        grp = DuplicateGroup(
            sha256="deadbeef", size=keep.stat().st_size,
            paths=[str(keep), str(rem)], keep=str(keep), remove=[str(rem)],
            kind="status+topic", reason="", auto_safe=True,
        )
        log = UndoLog(log_dir=lib / ".operation_log")
        log.begin_transaction("dedup")
        resolve_group(grp, lib, undo_log=log)
        log.commit()
        merged = PaperIdentity.load(keep)
        assert "07a" in merged.topic_codes
        assert merged.doi == "10.1/xyz"
        assert not rem.exists()                          # the copy was trashed

    def test_auto_only_skips_special_collection(self, lib):
        from processing.duplicate_scan import apply_duplicate_resolutions
        slides = lib / "10 - Math slides" / "Smith, J. - Paper.pdf"
        home = lib / "01 - Published papers" / "S" / "Smith, J. - Paper.pdf"
        _identical(slides, home)
        res = apply_duplicate_resolutions(lib, dry_run=False, auto_only=True)
        assert res["removed"] == 0                   # review-only, untouched
        assert slides.exists() and home.exists()

    def test_exclude_skips_group(self, lib):
        from processing.duplicate_scan import apply_duplicate_resolutions
        status = lib / "01 - Published papers" / "S" / "Smith, J. - Paper.pdf"
        topic = (lib / "07a - BSDEs" / "01 - Published papers" / "S"
                 / "Smith, J. - Paper.pdf")
        _identical(status, topic)
        res = apply_duplicate_resolutions(lib, dry_run=False, exclude={str(topic)})
        assert res["removed"] == 0
        assert status.exists() and topic.exists()
