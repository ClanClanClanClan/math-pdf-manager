"""Read-only pipeline-preview analyzer (the bulk-classify trust gate)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

class TestHelpers:

    def test_current_topic_of_detects_code(self, tmp_path):
        from processing.pipeline_preview import current_topic_of
        p = tmp_path / "07a - BSDEs" / "01 - Published papers" / "S" / "x.pdf"
        assert current_topic_of(p, tmp_path) == "07a"

    def test_current_topic_of_standard_is_none(self, tmp_path):
        from processing.pipeline_preview import current_topic_of
        p = tmp_path / "01 - Published papers" / "S" / "x.pdf"
        assert current_topic_of(p, tmp_path) is None

    def test_title_from_filename(self, tmp_path):
        from processing.pipeline_preview import title_from_filename
        p = tmp_path / "Smith, J. - Reflected BSDEs (2020).pdf"
        assert title_from_filename(p) == "Reflected BSDEs (2020)"

    def test_title_from_filename_no_separator(self, tmp_path):
        from processing.pipeline_preview import title_from_filename
        assert title_from_filename(tmp_path / "loosefile.pdf") == "loosefile"


# ---------------------------------------------------------------------------
# Status matrix (deterministic via monkeypatched classifier)
# ---------------------------------------------------------------------------

class TestStatusMatrix:

    def _patch_decision(self, monkeypatch, *, topic_code=None, suggested=None, conf=0.0):
        import processing.publication_topic_router as r

        class D:
            pass
        d = D()
        d.topic_code = topic_code
        d.suggested_code = suggested
        d.confidence = conf
        d.needs_review = suggested is not None and topic_code is None
        monkeypatch.setattr(r, "resolve_topic", lambda *a, **k: d)

    def test_agree(self, tmp_path, monkeypatch):
        from processing.pipeline_preview import preview_paper
        self._patch_decision(monkeypatch, topic_code="07a", conf=0.9)
        p = tmp_path / "07a - BSDEs" / "01 - Published papers" / "X - t.pdf"
        assert preview_paper(p, tmp_path).status == "agree"

    def test_disagree(self, tmp_path, monkeypatch):
        from processing.pipeline_preview import preview_paper
        self._patch_decision(monkeypatch, topic_code="07b", conf=0.9)
        p = tmp_path / "07a - BSDEs" / "01 - Published papers" / "X - t.pdf"
        assert preview_paper(p, tmp_path).status == "disagree"

    def test_recall_miss(self, tmp_path, monkeypatch):
        from processing.pipeline_preview import preview_paper
        self._patch_decision(monkeypatch, topic_code=None, conf=0.1)
        p = tmp_path / "07a - BSDEs" / "01 - Published papers" / "X - t.pdf"
        assert preview_paper(p, tmp_path).status == "recall_miss"

    def test_move(self, tmp_path, monkeypatch):
        from processing.pipeline_preview import preview_paper
        self._patch_decision(monkeypatch, topic_code="07a", conf=0.9)
        p = tmp_path / "01 - Published papers" / "X - t.pdf"
        assert preview_paper(p, tmp_path).status == "move"

    def test_suggest(self, tmp_path, monkeypatch):
        from processing.pipeline_preview import preview_paper
        self._patch_decision(monkeypatch, topic_code=None, suggested="07a", conf=0.4)
        p = tmp_path / "01 - Published papers" / "X - t.pdf"
        assert preview_paper(p, tmp_path).status == "suggest"

    def test_none(self, tmp_path, monkeypatch):
        from processing.pipeline_preview import preview_paper
        self._patch_decision(monkeypatch, topic_code=None, conf=0.0)
        p = tmp_path / "01 - Published papers" / "X - t.pdf"
        assert preview_paper(p, tmp_path).status == "none"


# ---------------------------------------------------------------------------
# Aggregation + trust metrics
# ---------------------------------------------------------------------------

class TestPreviewAggregation:

    def test_summary_and_agreement_rate(self, tmp_path, monkeypatch):
        # Two hand-filed BSDE papers: classifier agrees on one, disagrees
        # on the other -> agreement_rate 0.5; one un-topiced confident
        # move.
        import processing.publication_topic_router as r
        from processing.pipeline_preview import preview_topic_filing

        def fake_resolve(title, text="", **k):
            class D:
                pass
            d = D()
            d.suggested_code = None
            d.confidence = 0.9
            # title encodes the desired proposed topic for the test
            d.topic_code = "07a" if "AGREE" in title or "MOVE" in title else "07b"
            d.needs_review = False
            return d

        monkeypatch.setattr(r, "resolve_topic", fake_resolve)

        a = tmp_path / "07a - BSDEs" / "01 - Published papers"
        a.mkdir(parents=True)
        _write_minimal_pdf(a / "X - AGREE one.pdf", title="t", author="X")
        _write_minimal_pdf(a / "X - disagree two.pdf", title="t", author="X")
        std = tmp_path / "01 - Published papers"
        std.mkdir(parents=True)
        _write_minimal_pdf(std / "X - MOVE three.pdf", title="t", author="X")

        summary, proposals = preview_topic_filing(tmp_path)
        assert summary.scanned == 3
        assert summary.in_topic == 2
        assert summary.agree == 1
        assert summary.disagree == 1
        assert summary.agreement_rate == pytest.approx(0.5)
        assert summary.proposed_moves == 1
        d = summary.to_dict()
        assert d["counts"]["agree"] == 1 and d["counts"]["move"] == 1

    def test_limit_caps_scan(self, tmp_path, monkeypatch):
        import processing.publication_topic_router as r
        from processing.pipeline_preview import preview_topic_filing
        monkeypatch.setattr(r, "resolve_topic",
                            lambda *a, **k: type("D", (), {
                                "topic_code": None, "suggested_code": None,
                                "confidence": 0.0, "needs_review": False})())
        std = tmp_path / "01 - Published papers"
        std.mkdir(parents=True)
        for i in range(5):
            _write_minimal_pdf(std / f"X - p{i}.pdf", title="t", author="X")
        summary, proposals = preview_topic_filing(tmp_path, limit=3)
        assert summary.scanned == 3
        assert len(proposals) == 3

    def test_extras_doctype_and_subtopic_surface(self, tmp_path):
        # Combined scan surfaces a misfiled thesis and a sub-subtopic fit.
        from processing.pipeline_preview import preview_topic_filing
        # A thesis sitting in an article folder -> doctype_mismatch.
        art = tmp_path / "01 - Published papers" / "S"
        art.mkdir(parents=True)
        _write_minimal_pdf(art / "S - A PhD thesis on rough paths.pdf",
                           title="t", author="S")
        # A BSDE topic with sub-subtopics; a numerical-methods paper at
        # the topic root -> subtopic suggestion.
        topic = tmp_path / "07a - BSDEs"
        for d in ["01 - Published papers", "07a - Numerical methods"]:
            (topic / d).mkdir(parents=True)
        nm = topic / "01 - Published papers" / "X - Deep learning scheme for numerical simulation of BSDEs.pdf"
        _write_minimal_pdf(nm, title="t", author="X")

        summary, proposals = preview_topic_filing(tmp_path)
        assert summary.doctype_mismatches >= 1
        assert summary.subtopic_suggestions >= 1
        assert any(p.doc_kind == "thesis" and p.doc_mismatch for p in proposals)
        assert any(p.subtopic == "Numerical methods" for p in proposals)

    def test_real_classifier_bsde_agreement(self, tmp_path):
        # End-to-end with the REAL classifier: a BSDE paper hand-filed in
        # 07a should be 'agree'; the same title in a standard folder
        # should be 'move'.
        from processing.pipeline_preview import preview_paper
        a = tmp_path / "07a - BSDEs" / "01 - Published papers"
        a.mkdir(parents=True)
        in_topic = a / "X - Reflected BSDEs and backward stochastic equations.pdf"
        _write_minimal_pdf(in_topic, title="t", author="X")
        std = tmp_path / "01 - Published papers"
        std.mkdir(parents=True)
        in_std = std / "X - Reflected BSDEs and backward stochastic equations.pdf"
        _write_minimal_pdf(in_std, title="t", author="X")

        assert preview_paper(in_topic, tmp_path).status == "agree"
        assert preview_paper(in_std, tmp_path).status == "move"
