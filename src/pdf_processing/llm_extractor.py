#!/usr/bin/env python3
"""
LLM-Based Metadata Extractor
==============================

Uses a local GGUF model via ``llama-cpp-python`` with **GBNF grammar
constraints** to extract title and authors from PDF text.

Key design decisions:

1. **GBNF grammar**: Guarantees the output is always valid JSON with
   exactly ``{"title": "...", "authors": ["...", ...]}``.  No regex
   fallback or JSON-repair needed.

2. **Qwen2.5-7B-Instruct-Q4_K_M** (~4.5 GB) as the default model — best
   structured-output quality at this size.  Qwen2.5-3B-Instruct-Q4_K_M
   (~2.1 GB) is available as a lightweight alternative.

3. **Metal backend** on Apple Silicon — llama.cpp uses Metal (not MPS),
   giving ~30–60 tok/s on M1/M2/M3.

4. **Deterministic** (``temperature=0.0``) for reproducible results.

This module is imported lazily by the ``EnhancedPDFParser`` — users
without ``llama-cpp-python`` installed will never see an import error.
"""

import json
import logging
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# GBNF grammar that constrains LLM output to valid JSON
# -----------------------------------------------------------------------
METADATA_GRAMMAR = r'''
root   ::= "{" ws "\"title\"" ws ":" ws string "," ws "\"authors\"" ws ":" ws array ws "}"
string ::= "\"" ([^"\\] | "\\" .)* "\""
array  ::= "[" ws string (ws "," ws string)* ws "]" | "[" ws "]"
ws     ::= [ \t\n]*
'''

# -----------------------------------------------------------------------
# Default model configurations
# -----------------------------------------------------------------------
_MODEL_CONFIGS: Dict[str, Dict[str, str]] = {
    "qwen2.5-7b-finetuned": {
        "repo_id": "",  # Local only — no download
        "filename": "qwen2.5-7b-pdfmeta-q4_k_m.gguf",
        "description": "Qwen2.5 7B fine-tuned for PDF metadata (~4.5 GB)",
    },
    "qwen2.5-7b": {
        "repo_id": "Qwen/Qwen2.5-7B-Instruct-GGUF",
        "filename": "qwen2.5-7b-instruct-q4_k_m.gguf",
        "description": "Qwen2.5 7B Instruct Q4_K_M (~4.5 GB) — best quality",
    },
    "qwen2.5-3b": {
        "repo_id": "Qwen/Qwen2.5-3B-Instruct-GGUF",
        "filename": "qwen2.5-3b-instruct-q4_k_m.gguf",
        "description": "Qwen2.5 3B Instruct Q4_K_M (~2.1 GB) — lightweight",
    },
}

DEFAULT_MODEL = "qwen2.5-7b"

# Auto-detect fine-tuned model: prefer it if available locally
_FINETUNED_PATH = (
    Path.home() / ".mathpdf_models" / "gguf" / "qwen2.5-7b-pdfmeta-q4_k_m.gguf"
)
if _FINETUNED_PATH.exists():
    DEFAULT_MODEL = "qwen2.5-7b-finetuned"

# -----------------------------------------------------------------------
# Prompt template
# -----------------------------------------------------------------------
_SYSTEM_PROMPT = """\
You are a metadata extraction assistant for academic mathematics papers.
Given the first pages of a PDF, extract the paper's title and all author names.
Return a JSON object with exactly two keys:
  "title" — the full paper title (string)
  "authors" — all author names (array of strings, each "Firstname Lastname")
Rules:
- Use the title exactly as it appears in the text (preserve the original language).
- Do NOT include affiliations, emails, or other data.
- If the text is too short or unclear to determine the title, return {"title": "", "authors": []}."""

_USER_TEMPLATE = """\
<PDF text>
{text}
</PDF text>

Extract the title and authors from the above academic paper text."""


class LLMMetadataExtractor:
    """Extract metadata from PDF text using a local GGUF model.

    Usage::

        extractor = LLMMetadataExtractor()      # auto-downloads model
        result = extractor.extract(first_pages)  # {"title": ..., "authors": [...]}
        extractor.close()                        # free VRAM
    """

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        model_name: str = DEFAULT_MODEL,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,
    ):
        """Initialise the LLM.

        Parameters
        ----------
        model_path:
            Explicit path to a ``.gguf`` file.  When ``None``, the model
            identified by *model_name* is downloaded automatically via
            ``huggingface_hub``.
        model_name:
            One of the keys in ``_MODEL_CONFIGS`` (default ``"qwen2.5-7b"``).
            Ignored when *model_path* is given.
        n_ctx:
            Context window size in tokens (4096 is enough for 2–3 pages).
        n_gpu_layers:
            Number of layers to offload to GPU.  ``-1`` = all (Metal/CUDA).
        """
        try:
            from llama_cpp import Llama, LlamaGrammar
        except ImportError:
            raise ImportError(
                "llama-cpp-python is required for LLM metadata extraction.  "
                "Install it with:  pip install 'llama-cpp-python>=0.3.0'"
            )

        if model_path is None:
            model_path = self._ensure_model(model_name)

        logger.info(f"Loading GGUF model from {model_path}")
        self._llm = Llama(
            model_path=str(model_path),
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            verbose=False,
        )
        self._grammar = LlamaGrammar.from_string(METADATA_GRAMMAR)
        logger.info("LLM metadata extractor ready")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def extract(self, first_pages_text: str) -> Dict[str, Any]:
        """Extract title and authors from PDF text.

        Parameters
        ----------
        first_pages_text:
            Raw text from the first 2–3 pages of the PDF.

        Returns
        -------
        ``{"title": "...", "authors": ["Author One", ...]}``
        """
        # Guard: skip LLM for empty/scanned PDFs — avoids hallucinations
        if not first_pages_text or len(first_pages_text.strip()) < 100:
            logger.info("Text too short for LLM extraction (<100 chars), skipping")
            return {"title": "", "authors": []}

        # Truncate to fit context window (leave room for system prompt + output)
        max_input_chars = 6000  # ~2000 tokens
        text = first_pages_text[:max_input_chars]

        prompt = self._build_prompt(text)

        output = self._llm.create_completion(
            prompt,
            max_tokens=512,
            grammar=self._grammar,
            temperature=0.0,
            stop=["}\n", "}\r"],
        )

        raw_text = output["choices"][0]["text"].strip()

        # The grammar guarantees valid JSON, but add a safety net
        if not raw_text.endswith("}"):
            raw_text += "}"

        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM output: {raw_text[:200]}")
            return {"title": "", "authors": []}

        # Normalise
        result.setdefault("title", "")
        result.setdefault("authors", [])
        if isinstance(result["authors"], str):
            result["authors"] = [result["authors"]]

        # NFC-normalise title and author names (model outputs NFC, which is
        # the correct canonical form for Unicode text)
        result["title"] = unicodedata.normalize("NFC", result["title"]).strip()
        result["authors"] = [
            unicodedata.normalize("NFC", a).strip()
            for a in result["authors"] if a.strip()
        ]

        return result

    def close(self):
        """Release model resources."""
        if hasattr(self, "_llm"):
            del self._llm
            self._llm = None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _build_prompt(self, text: str) -> str:
        """Build the chat-style prompt for the model."""
        user_msg = _USER_TEMPLATE.format(text=text)

        # Use Qwen2.5 chat template (also works reasonably for other models)
        return (
            f"<|im_start|>system\n{_SYSTEM_PROMPT}<|im_end|>\n"
            f"<|im_start|>user\n{user_msg}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

    @staticmethod
    def _ensure_model(model_name: str) -> Path:
        """Download the model GGUF file if it doesn't exist locally.

        Uses ``huggingface_hub.hf_hub_download`` for robust, cached downloads.
        """
        if model_name not in _MODEL_CONFIGS:
            raise ValueError(
                f"Unknown model '{model_name}'.  "
                f"Available: {list(_MODEL_CONFIGS.keys())}"
            )

        config = _MODEL_CONFIGS[model_name]
        cache_dir = Path.home() / ".mathpdf_models" / "gguf"

        local_path = cache_dir / config["filename"]
        if local_path.exists():
            logger.debug(f"Model already cached: {local_path}")
            return local_path

        # Fine-tuned model is local-only — can't be downloaded
        if not config.get("repo_id"):
            raise FileNotFoundError(
                f"Fine-tuned model not found at {local_path}. "
                f"Run the training pipeline first, or use --model qwen2.5-7b "
                f"for the base model."
            )

        logger.info(
            f"Downloading {config['description']} from "
            f"HuggingFace ({config['repo_id']})…"
        )

        try:
            from huggingface_hub import hf_hub_download

            downloaded = hf_hub_download(
                repo_id=config["repo_id"],
                filename=config["filename"],
                cache_dir=str(cache_dir),
                local_dir=str(cache_dir),
            )
            logger.info(f"Model downloaded to {downloaded}")
            return Path(downloaded)

        except ImportError:
            raise ImportError(
                "huggingface_hub is required for automatic model downloads.  "
                "Install it with:  pip install huggingface_hub"
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to download model {model_name}: {e}\n"
                f"You can manually download it from "
                f"https://huggingface.co/{config['repo_id']} "
                f"and place it at {local_path}"
            )

    @staticmethod
    def is_available() -> bool:
        """Check whether llama-cpp-python is installed."""
        try:
            import llama_cpp  # noqa: F401
            return True
        except ImportError:
            return False
