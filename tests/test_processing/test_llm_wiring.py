"""LLM extractor wiring into the live ingest path (Phase 3b).

Regression guards for two real bugs:
  * ingest passed the PDF *path* where extract() wants the TEXT (so the
    LLM never actually ran), and
  * instantiating the extractor in the hot path would auto-download a
    multi-GB model.  The fix gates on a locally-present model and passes
    the cached front-matter text.
"""
from __future__ import annotations

from pathlib import Path


def _write_text_pdf(path: Path, text: str) -> None:
    import fitz
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(36, 36, 560, 760), text, fontsize=11)
    doc.save(str(path))
    doc.close()


class TestLocalModelPath:

    def test_none_when_no_model_cached(self, tmp_path, monkeypatch):
        import pdf_processing.llm_extractor as lx
        monkeypatch.setattr(lx.Path, "home", lambda: tmp_path)
        assert lx.LLMMetadataExtractor.local_model_path() is None

    def test_finds_cached_model(self, tmp_path, monkeypatch):
        import pdf_processing.llm_extractor as lx
        monkeypatch.setattr(lx.Path, "home", lambda: tmp_path)
        gguf = tmp_path / ".mathpdf_models" / "gguf" / "qwen2.5-7b-instruct-q4_k_m.gguf"
        gguf.parent.mkdir(parents=True)
        gguf.write_bytes(b"x")
        assert lx.LLMMetadataExtractor.local_model_path() == gguf

    def test_prefers_finetuned(self, tmp_path, monkeypatch):
        import pdf_processing.llm_extractor as lx
        monkeypatch.setattr(lx.Path, "home", lambda: tmp_path)
        d = tmp_path / ".mathpdf_models" / "gguf"
        d.mkdir(parents=True)
        (d / "qwen2.5-7b-instruct-q4_k_m.gguf").write_bytes(b"x")
        (d / "qwen2.5-7b-pdfmeta-q4_k_m.gguf").write_bytes(b"x")
        assert lx.LLMMetadataExtractor.local_model_path().name == "qwen2.5-7b-pdfmeta-q4_k_m.gguf"


class TestIngestLLMWiring:

    def _fake_llm(self, tmp_path, captured):
        class FakeLLM:
            def __init__(self, *a, **k):
                pass
            @staticmethod
            def is_available():
                return True
            @staticmethod
            def local_model_path():
                return tmp_path / "fake.gguf"
            def extract(self, text):
                captured["arg"] = text
                return {"title": "Recovered Title", "authors": ["A. Author"]}
            def close(self):
                captured["closed"] = True
        return FakeLLM

    def test_llm_receives_text_not_path_and_marks_source(self, tmp_path, monkeypatch):
        import pdf_processing.llm_extractor as lx
        captured = {}
        monkeypatch.setattr(lx, "LLMMetadataExtractor", self._fake_llm(tmp_path, captured))
        # A text PDF with NO Info-dict title -> all earlier extractors miss
        # -> the LLM fallback runs.
        pdf = tmp_path / "notitle.pdf"
        _write_text_pdf(
            pdf,
            "We study reflected backward stochastic differential equations "
            "with applications. " * 6)
        from processing.ingest import extract_metadata_from_pdf
        meta = extract_metadata_from_pdf(pdf)
        # The extractor got the TEXT (a str), not a Path.
        assert isinstance(captured.get("arg"), str)
        assert "backward stochastic" in captured["arg"].lower()
        assert meta["title"] == "Recovered Title"
        assert meta.get("title_source") == "llm"
        assert captured.get("closed") is True  # VRAM freed

    def test_llm_skipped_when_no_model_present(self, tmp_path, monkeypatch):
        # If no model is cached, ingest must NOT instantiate the extractor
        # (which would trigger a multi-GB download).
        import pdf_processing.llm_extractor as lx
        instantiated = {"yes": False}

        class FakeLLM:
            def __init__(self, *a, **k):
                instantiated["yes"] = True
            @staticmethod
            def is_available():
                return True
            @staticmethod
            def local_model_path():
                return None  # nothing cached
            def extract(self, text):
                return {"title": "X", "authors": []}
            def close(self):
                pass

        monkeypatch.setattr(lx, "LLMMetadataExtractor", FakeLLM)
        pdf = tmp_path / "notitle.pdf"
        _write_text_pdf(pdf, "Some body text here that is reasonably long. " * 6)
        from processing.ingest import extract_metadata_from_pdf
        meta = extract_metadata_from_pdf(pdf)
        assert instantiated["yes"] is False
        assert meta.get("title_source") != "llm"
