#!/usr/bin/env python3
"""Tests for the LLM metadata extractor (mocked — no model needed)."""

import json
import sys
import importlib
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_completion(title="On the Convergence of SGD", authors=None):
    """Build a mock create_completion return value."""
    if authors is None:
        authors = ["John Smith", "Jane Doe"]
    return {
        "choices": [{"text": json.dumps({"title": title, "authors": authors})}]
    }


@pytest.fixture()
def llm_module():
    """Import pdf_processing.llm_extractor with llama_cpp mocked.

    The mock stays active for the entire test, so that ``__init__`` can
    do ``from llama_cpp import Llama, LlamaGrammar`` without error.
    """
    mock_llama_mod = MagicMock()
    mock_llm_instance = MagicMock()
    mock_llm_instance.create_completion.return_value = _make_mock_completion()
    mock_llama_mod.Llama.return_value = mock_llm_instance
    mock_llama_mod.LlamaGrammar.from_string.return_value = MagicMock()

    saved = sys.modules.get("llama_cpp")
    sys.modules["llama_cpp"] = mock_llama_mod

    try:
        import pdf_processing.llm_extractor as mod
        importlib.reload(mod)
        yield mod
    finally:
        if saved is not None:
            sys.modules["llama_cpp"] = saved
        else:
            sys.modules.pop("llama_cpp", None)
        # Reload to restore clean state
        try:
            importlib.reload(mod)
        except Exception:
            pass


@pytest.fixture()
def extractor(llm_module):
    """Return a ready-to-use LLMMetadataExtractor with mocked model."""
    with patch.object(
        llm_module.LLMMetadataExtractor,
        "_ensure_model",
        return_value=Path("/fake/model.gguf"),
    ):
        ext = llm_module.LLMMetadataExtractor()
    return ext


# ---------------------------------------------------------------------------
# Tests — extraction
# ---------------------------------------------------------------------------


class TestLLMMetadataExtractor:
    """Test LLMMetadataExtractor with mocked llama_cpp."""

    def test_extract_returns_title_and_authors(self, extractor):
        """extract() should return dict with title and authors list."""
        result = extractor.extract("Some PDF text about convergence of SGD")

        assert result["title"] == "On the Convergence of SGD"
        assert result["authors"] == ["John Smith", "Jane Doe"]

    def test_extract_truncates_long_input(self, extractor):
        """Input text should be truncated to max_input_chars."""
        long_text = "A" * 20000
        extractor.extract(long_text)

        call_args = extractor._llm.create_completion.call_args
        prompt = call_args[0][0]
        # The text portion inside the prompt must be ≤ 6000 chars
        assert "A" * 6001 not in prompt

    def test_extract_handles_malformed_json(self, extractor):
        """If LLM output can't be parsed, return empty result."""
        extractor._llm.create_completion.return_value = {
            "choices": [{"text": "not valid json at all"}]
        }
        result = extractor.extract("Some text")

        assert result == {"title": "", "authors": []}

    def test_extract_normalises_string_authors(self, extractor):
        """If authors is a string instead of list, wrap it."""
        extractor._llm.create_completion.return_value = {
            "choices": [
                {"text": json.dumps({"title": "Test", "authors": "Solo Author"})}
            ]
        }
        result = extractor.extract("Some text")

        assert result["authors"] == ["Solo Author"]

    def test_extract_strips_whitespace_from_authors(self, extractor):
        """Author names should be stripped; empty strings removed."""
        extractor._llm.create_completion.return_value = {
            "choices": [
                {"text": json.dumps({"title": "T", "authors": ["  Alice  ", "", " Bob "]})}
            ]
        }
        result = extractor.extract("text")

        assert result["authors"] == ["Alice", "Bob"]

    def test_extract_appends_closing_brace(self, extractor):
        """If LLM output is missing trailing }, it should be appended."""
        extractor._llm.create_completion.return_value = {
            "choices": [{"text": '{"title": "Test", "authors": ["A"]'}]
        }
        result = extractor.extract("text")

        assert result["title"] == "Test"
        assert result["authors"] == ["A"]

    def test_close_releases_model(self, extractor):
        """close() should delete the internal LLM reference."""
        extractor.close()
        assert extractor._llm is None

    def test_build_prompt_uses_qwen_template(self, extractor):
        """The prompt should use Qwen2.5 chat template markers."""
        prompt = extractor._build_prompt("test text")

        assert "<|im_start|>system" in prompt
        assert "<|im_start|>user" in prompt
        assert "<|im_start|>assistant" in prompt
        assert "<|im_end|>" in prompt
        assert "test text" in prompt

    def test_create_completion_called_with_grammar(self, extractor):
        """extract() should pass the grammar to create_completion."""
        extractor.extract("text")

        call_kwargs = extractor._llm.create_completion.call_args
        assert "grammar" in call_kwargs.kwargs or (
            len(call_kwargs.args) > 1
        )

    def test_temperature_is_zero(self, extractor):
        """Extraction should be deterministic (temperature=0.0)."""
        extractor.extract("text")

        call_kwargs = extractor._llm.create_completion.call_args.kwargs
        assert call_kwargs.get("temperature") == 0.0


# ---------------------------------------------------------------------------
# Tests — model management
# ---------------------------------------------------------------------------


class TestEnsureModel:
    """Test model download/caching logic."""

    def test_unknown_model_raises(self, llm_module):
        """Unknown model name should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown model"):
            llm_module.LLMMetadataExtractor._ensure_model("nonexistent-model")

    def test_cached_model_returns_immediately(self, llm_module, tmp_path):
        """If model file exists locally, skip download."""
        model_dir = tmp_path / ".mathpdf_models" / "gguf"
        model_dir.mkdir(parents=True)
        fake_model = model_dir / "qwen2.5-7b-instruct-q4_k_m.gguf"
        fake_model.write_text("fake model data")

        with patch.object(Path, "home", return_value=tmp_path):
            result = llm_module.LLMMetadataExtractor._ensure_model("qwen2.5-7b")

        assert result == fake_model

    def test_downloads_when_not_cached(self, llm_module, tmp_path):
        """If model is not cached, call hf_hub_download."""
        model_dir = tmp_path / ".mathpdf_models" / "gguf"
        expected_path = model_dir / "qwen2.5-7b-instruct-q4_k_m.gguf"

        mock_hf = MagicMock()
        mock_hf.hf_hub_download.return_value = str(expected_path)

        with patch.object(Path, "home", return_value=tmp_path), \
             patch.dict("sys.modules", {"huggingface_hub": mock_hf}):
            result = llm_module.LLMMetadataExtractor._ensure_model("qwen2.5-7b")

        assert result == expected_path
        mock_hf.hf_hub_download.assert_called_once()


# ---------------------------------------------------------------------------
# Tests — is_available
# ---------------------------------------------------------------------------


class TestIsAvailable:
    """Test the is_available() static method."""

    def test_available_when_installed(self, llm_module):
        """is_available() should return True when llama_cpp is importable."""
        # llama_cpp is already in sys.modules via the fixture
        assert llm_module.LLMMetadataExtractor.is_available() is True

    def test_not_available_when_missing(self):
        """is_available() should return False when llama_cpp is not importable."""
        # Remove any existing mock
        saved = sys.modules.pop("llama_cpp", None)
        try:
            import pdf_processing.llm_extractor as mod
            importlib.reload(mod)
            assert mod.LLMMetadataExtractor.is_available() is False
        finally:
            if saved is not None:
                sys.modules["llama_cpp"] = saved


# ---------------------------------------------------------------------------
# Tests — module-level constants
# ---------------------------------------------------------------------------


class TestGrammarAndModelConfigs:
    """Test module-level constants."""

    def test_grammar_is_nonempty(self, llm_module):
        """METADATA_GRAMMAR should be a non-empty string."""
        assert isinstance(llm_module.METADATA_GRAMMAR, str)
        assert len(llm_module.METADATA_GRAMMAR) > 50

    def test_model_configs_have_required_keys(self, llm_module):
        """Each model config should have repo_id, filename, description."""
        for name, config in llm_module._MODEL_CONFIGS.items():
            assert "repo_id" in config, f"{name} missing repo_id"
            assert "filename" in config, f"{name} missing filename"
            assert "description" in config, f"{name} missing description"
            assert config["filename"].endswith(".gguf"), f"{name} filename not .gguf"

    def test_default_model_exists_in_configs(self, llm_module):
        """DEFAULT_MODEL should be a valid key in _MODEL_CONFIGS."""
        assert llm_module.DEFAULT_MODEL in llm_module._MODEL_CONFIGS
