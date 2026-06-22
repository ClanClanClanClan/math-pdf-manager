"""Gold training-pair capture + model-free scoring helpers (Phase 3b)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402


class TestIngestCaptureHook:

    def test_authoritative_resolution_is_captured(self, tmp_path, monkeypatch):
        # An API-resolved ingest records a gold pair; LLM-sourced does not.
        import processing.ingest as ing
        from processing.metadata_training import load_pairs
        (tmp_path / "01 - Published papers").mkdir(parents=True)
        src = tmp_path / "_in" / "drop.pdf"
        src.parent.mkdir()
        _write_minimal_pdf(src, title="x", author="x")

        def fake_extract(pdf_path):
            return {"title": "Reflected BSDEs", "authors": ["Jane Doe"],
                    "doi": None, "arxiv_id": None, "year": 2021,
                    "title_source": "crossref",
                    "fulltext_sample": "We study reflected BSDEs. " * 12}
        monkeypatch.setattr(ing, "extract_metadata_from_pdf", fake_extract)

        ing.ingest_paper(src, library_root=tmp_path, status="published",
                         dry_run=False,
                         canonical_override="Doe, J. - Reflected BSDEs")
        pairs = load_pairs(tmp_path)
        assert len(pairs) == 1
        assert pairs[0]["title"] == "Reflected BSDEs"
        assert pairs[0]["source"] == "crossref"

    def test_llm_source_not_captured(self, tmp_path, monkeypatch):
        import processing.ingest as ing
        from processing.metadata_training import load_pairs
        (tmp_path / "01 - Published papers").mkdir(parents=True)
        src = tmp_path / "_in" / "drop.pdf"
        src.parent.mkdir()
        _write_minimal_pdf(src, title="x", author="x")
        monkeypatch.setattr(ing, "extract_metadata_from_pdf", lambda p: {
            "title": "Guessed", "authors": [], "doi": None, "arxiv_id": None,
            "year": None, "title_source": "llm",
            "fulltext_sample": "body " * 40})
        ing.ingest_paper(src, library_root=tmp_path, status="published",
                         dry_run=False, canonical_override="X - Guessed")
        assert load_pairs(tmp_path) == []  # model output is not gold


class TestRecordAndLoad:

    def test_record_and_load(self, tmp_path):
        from processing.metadata_training import record_pair, load_pairs
        ok = record_pair(
            tmp_path, text="We study reflected BSDEs. " * 10,
            title="Reflected BSDEs", authors=["Jane Doe", "P. Martin"],
            source="crossref")
        assert ok
        pairs = load_pairs(tmp_path)
        assert len(pairs) == 1
        assert pairs[0]["title"] == "Reflected BSDEs"
        assert pairs[0]["authors"] == ["Jane Doe", "P. Martin"]
        assert pairs[0]["source"] == "crossref"

    def test_dict_authors_normalised(self, tmp_path):
        from processing.metadata_training import record_pair, load_pairs
        record_pair(tmp_path, text="x " * 60, title="T",
                    authors=[{"family": "Karoui", "given": "N."},
                             {"family": "Quenez", "given": ""}],
                    source="crossref")
        a = load_pairs(tmp_path)[0]["authors"]
        assert a == ["N. Karoui", "Quenez"]

    def test_rejects_thin_text_or_title(self, tmp_path):
        from processing.metadata_training import record_pair, load_pairs
        assert record_pair(tmp_path, text="short", title="T", authors=[], source="x") is False
        assert record_pair(tmp_path, text="x " * 60, title="", authors=[], source="x") is False
        assert load_pairs(tmp_path) == []

    def test_dedup_by_text_keeps_latest(self, tmp_path):
        from processing.metadata_training import record_pair, load_pairs
        txt = "Identical body text about G-Brownian motion. " * 8
        record_pair(tmp_path, text=txt, title="Old Title", authors=[], source="pymupdf")
        record_pair(tmp_path, text=txt, title="Corrected Title", authors=[], source="user")
        pairs = load_pairs(tmp_path)            # dedup on
        assert len(pairs) == 1
        assert pairs[0]["title"] == "Corrected Title"
        assert len(load_pairs(tmp_path, dedup=False)) == 2

    def test_capture_never_raises(self, tmp_path):
        # Passing junk must not raise into the caller (best-effort).
        from processing.metadata_training import record_pair
        assert record_pair(tmp_path, text=None, title=None, authors=None, source="x") is False


class TestScoring:

    def test_title_exact_and_similarity(self):
        from processing.metadata_training import title_exact, title_similarity
        assert title_exact("Reflected BSDEs", "reflected  bsdes!")
        assert not title_exact("Reflected BSDEs", "On BSDEs")
        assert title_similarity("a b c d", "a b c e") == 0.6  # 3 shared / 5 union
        assert title_similarity("", "") == 1.0
        assert title_similarity("x", "") == 0.0

    def test_author_f1(self):
        from processing.metadata_training import author_f1
        assert author_f1(["Jane Doe"], ["J. Doe"]) == 1.0           # last names match
        # "Karoui, N." and "Nicole el Karoui" both reduce to last name
        # "karoui" -> correctly a match.
        assert author_f1(["Karoui, N."], ["Nicole el Karoui"]) == 1.0
        assert author_f1(["Smith"], ["Jones"]) == 0.0               # disjoint
        assert author_f1([], []) == 1.0
        # 2 predicted, 1 gold, 1 overlap -> P=0.5,R=1 -> F1=2/3.
        assert abs(author_f1(["A. Smith", "B. Lee"], ["Smith"]) - 0.6667) < 0.01
