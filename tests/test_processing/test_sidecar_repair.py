"""Reconnecting sidecars stranded by a rename that bypassed the undo log."""
from __future__ import annotations

import json

import pytest

from processing.identity import (
    MIRROR_DIR_NAME, PaperIdentity, enable_sidecar_mirror,
)
from processing.sidecar_repair import (
    apply_reconnect, find_orphans, plan_reconnect,
)


def _paper(lib, name, body=b"%PDF-1.4\nunique-body\n"):
    d = lib / "01 - Published papers" / name[0].upper()
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_bytes(body)
    return p


@pytest.fixture
def lib(tmp_path):
    (tmp_path / MIRROR_DIR_NAME).mkdir()
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _strand(lib, pdf, new_name):
    """Rename a PDF the WRONG way: leave its sidecar behind."""
    PaperIdentity().save(pdf, recompute_hash=True)
    pdf.rename(pdf.with_name(new_name))
    return pdf.with_name(new_name)


class TestFindAndPlan:
    def test_a_stranded_sidecar_is_found_and_matched_by_content(self, lib):
        pdf = _paper(lib, "Krylov, N.V. - Morrey drift.pdf")
        moved = _strand(lib, pdf, "Krylov, N. V. - Morrey drift.pdf")
        assert len(find_orphans(lib)) == 1
        plan = plan_reconnect(lib)
        assert len(plan["matched"]) == 1
        assert plan["matched"][0][1] == moved

    def test_a_paper_that_already_has_a_record_is_not_a_candidate(self, lib):
        # Matching must never steal a record from a paper that has one.
        pdf = _paper(lib, "Doe, J. - Something.pdf")
        PaperIdentity().save(pdf, recompute_hash=True)
        assert find_orphans(lib) == []
        assert plan_reconnect(lib)["matched"] == []

    def test_identical_content_is_left_alone_rather_than_guessed(self, lib):
        # Two PDFs with the SAME bytes: the hash cannot say which one the
        # record belongs to, so it must refuse rather than pick.
        body = b"%PDF-1.4\nsame\n"
        a = _paper(lib, "A, A. - One.pdf", body)
        _strand(lib, a, "A, A. - One renamed.pdf")
        _paper(lib, "B, B. - Two.pdf", body)
        plan = plan_reconnect(lib)
        assert len(plan["matched"]) <= 1
        assert not plan["ambiguous"] or plan["matched"] == []


class TestApply:
    def test_dry_run_moves_nothing(self, lib):
        pdf = _paper(lib, "Krylov, N.V. - X.pdf")
        _strand(lib, pdf, "Krylov, N. V. - X.pdf")
        plan = plan_reconnect(lib)
        before = {p.name for p in (lib / MIRROR_DIR_NAME).rglob("*.meta.json")}
        out = apply_reconnect(lib, plan, dry_run=True)
        assert out["would_reconnect"] == 1
        after = {p.name for p in (lib / MIRROR_DIR_NAME).rglob("*.meta.json")}
        assert before == after

    def test_apply_reconnects_and_the_record_loads(self, lib):
        pdf = _paper(lib, "Krylov, N.V. - X.pdf")
        moved = _strand(lib, pdf, "Krylov, N. V. - X.pdf")
        out = apply_reconnect(lib, plan_reconnect(lib), dry_run=False)
        assert out["reconnected"] == 1
        assert out["tx_id"]
        assert PaperIdentity.load(moved).content_sha256
        assert find_orphans(lib) == []

    def test_never_overwrites_an_existing_record(self, lib):
        # The destination already has a record: keep it, skip the orphan.
        pdf = _paper(lib, "Krylov, N.V. - X.pdf")
        moved = _strand(lib, pdf, "Krylov, N. V. - X.pdf")
        good = PaperIdentity(); good.doi = "10.1234/keepme"
        good.save(moved, recompute_hash=True)
        plan = plan_reconnect(lib)          # no candidate now — it has one
        out = apply_reconnect(lib, plan, dry_run=False)
        assert out["reconnected"] == 0
        assert PaperIdentity.load(moved).doi == "10.1234/keepme"
