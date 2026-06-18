"""Cached classifier text (abstract) — extraction, backfill, and the
end-to-end recall lift it enables."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))


def _write_text_pdf(path: Path, text: str) -> None:
    """Author a real PDF with an extractable text layer via PyMuPDF."""
    import fitz
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page()
    # Wrap so long text lays out on the page.
    page.insert_textbox(fitz.Rect(36, 36, 560, 760), text, fontsize=11)
    doc.save(str(path))
    doc.close()


# ---------------------------------------------------------------------------
# Sidecar field
# ---------------------------------------------------------------------------

class TestSidecarField:

    def test_classifier_text_round_trips(self, tmp_path):
        from processing.identity import PaperIdentity, enable_sidecar_mirror
        enable_sidecar_mirror(tmp_path)
        pdf = tmp_path / "X - t.pdf"
        _write_text_pdf(pdf, "hello world")
        ident = PaperIdentity()
        ident.classifier_text = "cached abstract about BSDEs"
        ident.save(pdf)
        assert PaperIdentity.load(pdf).classifier_text == "cached abstract about BSDEs"

    def test_old_sidecar_without_field_loads(self, tmp_path):
        # A sidecar JSON missing the new field must still load (default "").
        from processing.identity import PaperIdentity, enable_sidecar_mirror, sidecar_path
        import json
        enable_sidecar_mirror(tmp_path)
        pdf = tmp_path / "X - t.pdf"
        _write_text_pdf(pdf, "hello")
        sp = sidecar_path(pdf)
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(json.dumps({"schema_version": 1, "doi": "10.1/x"}))
        assert PaperIdentity.load(pdf).classifier_text == ""


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

class TestExtract:

    def test_extracts_page_text(self, tmp_path):
        from processing.classifier_text import extract_classifier_text
        pdf = tmp_path / "p.pdf"
        _write_text_pdf(pdf, "Reflected backward stochastic differential equations")
        txt = extract_classifier_text(pdf)
        assert "backward stochastic" in txt.lower()

    def test_caps_length(self, tmp_path):
        from processing.classifier_text import extract_classifier_text
        pdf = tmp_path / "p.pdf"
        _write_text_pdf(pdf, "word " * 5000)
        assert len(extract_classifier_text(pdf, max_chars=500)) <= 500

    def test_garbage_file_returns_empty(self, tmp_path):
        from processing.classifier_text import extract_classifier_text
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a pdf")
        assert extract_classifier_text(bad) == ""


# ---------------------------------------------------------------------------
# Backfill
# ---------------------------------------------------------------------------

class TestBackfill:

    def test_populates_and_is_resumable(self, tmp_path):
        from processing.identity import enable_sidecar_mirror, PaperIdentity
        from processing.classifier_text import backfill_classifier_text
        enable_sidecar_mirror(tmp_path)
        pdf = tmp_path / "01 - Published papers" / "S" / "S - On BSDEs.pdf"
        _write_text_pdf(pdf, "We study backward stochastic differential equations.")
        s1 = backfill_classifier_text(tmp_path)
        assert s1["extracted"] == 1
        assert "backward stochastic" in PaperIdentity.load(pdf).classifier_text.lower()
        # Second run skips the already-populated paper.
        s2 = backfill_classifier_text(tmp_path)
        assert s2["skipped"] == 1 and s2["extracted"] == 0

    def test_excludes_non_routable(self, tmp_path):
        from processing.identity import enable_sidecar_mirror
        from processing.classifier_text import backfill_classifier_text
        enable_sidecar_mirror(tmp_path)
        # A paper in a non-routable special collection is skipped.
        pdf = tmp_path / "08 - Séminaires" / "x.pdf"
        _write_text_pdf(pdf, "some text")
        s = backfill_classifier_text(tmp_path)
        assert s["scanned"] == 0

    def test_max_seconds_stops_early(self, tmp_path):
        # A zero-second budget stops before processing anything and flags
        # it, so the run never blows past a harness/cron timeout.
        from processing.identity import enable_sidecar_mirror
        from processing.classifier_text import backfill_classifier_text
        enable_sidecar_mirror(tmp_path)
        for i in range(3):
            _write_text_pdf(tmp_path / "01 - Published papers" / f"X - p{i}.pdf",
                            "some text about equations")
        s = backfill_classifier_text(tmp_path, max_seconds=0)
        assert s.get("stopped_early") is True
        assert s["extracted"] == 0

    def test_limit(self, tmp_path):
        from processing.identity import enable_sidecar_mirror
        from processing.classifier_text import backfill_classifier_text
        enable_sidecar_mirror(tmp_path)
        for i in range(4):
            _write_text_pdf(tmp_path / "01 - Published papers" / f"X - p{i}.pdf",
                            "text about something")
        s = backfill_classifier_text(tmp_path, limit=2)
        assert s["scanned"] == 2


# ---------------------------------------------------------------------------
# The payoff: abstract flips a recall-miss to confident-correct
# ---------------------------------------------------------------------------

class TestRecallLift:

    def test_abstract_flips_miss_to_confident(self, tmp_path):
        from processing.identity import enable_sidecar_mirror, PaperIdentity
        from processing.pipeline_preview import preview_paper
        enable_sidecar_mirror(tmp_path)
        # Title has NO topic signal; the paper is in a standard folder.
        pdf = (tmp_path / "01 - Published papers" / "S"
               / "Smith, J. - On a class of nonlinear equations.pdf")
        _write_text_pdf(pdf, "irrelevant page text")

        # Title-only: no confident topic -> not a move.
        assert preview_paper(pdf, tmp_path, enrich=False).status == "none"

        # Cache an abstract that clearly names the topic.
        ident = PaperIdentity()
        ident.classifier_text = (
            "We study reflected backward stochastic differential equations "
            "(BSDEs) with quadratic growth and their numerical approximation.")
        ident.save(pdf)

        # With the abstract, it becomes a confident move into 07a.
        prop = preview_paper(pdf, tmp_path, enrich=True)
        assert prop.status == "move"
        assert prop.proposed_topic == "07a"
