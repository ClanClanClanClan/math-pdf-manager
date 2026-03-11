#!/usr/bin/env python3
"""
Mathematical Notation Handler
===============================

Normalises mathematical notation in paper titles and author names extracted
from PDFs.  PyMuPDF text extraction often garbles LaTeX-rendered math:

- Superscripts/subscripts become adjacent characters: ``L2`` → ``L²``
- Greek letters render as Symbol-font codepoints or ligatures
- Operators get mangled: ``Rd`` (should be ``ℝ^d``)
- Accented author names lose diacritics: ``Schrodinger`` → ``Schrödinger``

This module applies *conservative* normalisations — it only fixes patterns
that are unambiguously wrong, avoiding over-correction.
"""

import re
import logging
import unicodedata
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Greek letter mappings (Symbol font → Unicode)
# -----------------------------------------------------------------------
# PyMuPDF sometimes extracts Greek letters from the Symbol font as Latin
# characters.  We only map the unambiguous ones that appear in math titles.

_SYMBOL_TO_GREEK: Dict[str, str] = {
    # Lowercase
    "\\alpha": "α",
    "\\beta": "β",
    "\\gamma": "γ",
    "\\delta": "δ",
    "\\epsilon": "ε",
    "\\zeta": "ζ",
    "\\eta": "η",
    "\\theta": "θ",
    "\\iota": "ι",
    "\\kappa": "κ",
    "\\lambda": "λ",
    "\\mu": "μ",
    "\\nu": "ν",
    "\\xi": "ξ",
    "\\pi": "π",
    "\\rho": "ρ",
    "\\sigma": "σ",
    "\\tau": "τ",
    "\\upsilon": "υ",
    "\\phi": "φ",
    "\\chi": "χ",
    "\\psi": "ψ",
    "\\omega": "ω",
    "\\varepsilon": "ε",
    "\\varphi": "φ",
    "\\vartheta": "ϑ",
    # Uppercase
    "\\Gamma": "Γ",
    "\\Delta": "Δ",
    "\\Theta": "Θ",
    "\\Lambda": "Λ",
    "\\Xi": "Ξ",
    "\\Pi": "Π",
    "\\Sigma": "Σ",
    "\\Phi": "Φ",
    "\\Psi": "Ψ",
    "\\Omega": "Ω",
}

# -----------------------------------------------------------------------
# Common math operator / symbol replacements
# -----------------------------------------------------------------------
_MATH_REPLACEMENTS: Dict[str, str] = {
    # Blackboard bold letters (common in probability/analysis)
    "IR": "ℝ",  # but only if isolated
    # Arrows
    "->": "→",
    "<-": "←",
    "=>": "⇒",
    "<=>": "⇔",
    # Common operators
    "\\infty": "∞",
    "\\partial": "∂",
    "\\nabla": "∇",
    "\\forall": "∀",
    "\\exists": "∃",
    "\\in": "∈",
    "\\notin": "∉",
    "\\subset": "⊂",
    "\\subseteq": "⊆",
    "\\cup": "∪",
    "\\cap": "∩",
    "\\times": "×",
    "\\cdot": "·",
    "\\leq": "≤",
    "\\geq": "≥",
    "\\neq": "≠",
    "\\approx": "≈",
    "\\sim": "∼",
    "\\equiv": "≡",
    "\\pm": "±",
    "\\mp": "∓",
    "\\ell": "ℓ",
}

# -----------------------------------------------------------------------
# Accented name corrections
# -----------------------------------------------------------------------
# Common mathematician names where diacritics are often lost in PDF extraction.
_NAME_CORRECTIONS: Dict[str, str] = {
    "Schrodinger": "Schrödinger",
    "Ito": "Itô",
    "Itos": "Itô's",
    "Levy": "Lévy",
    "Frechet": "Fréchet",
    "Holder": "Hölder",
    "Hormander": "Hörmander",
    "Mobius": "Möbius",
    "Poincare": "Poincaré",
    "Bezout": "Bézout",
    "Neron": "Néron",
    "Cesaro": "Cesàro",
    "Bollobas": "Bollobás",
    "Erdos": "Erdős",
    "Renyi": "Rényi",
    "Szegö": "Szegő",
    "Lojasiewicz": "Łojasiewicz",
    "Lasry": "Lasry",
    "McKean": "McKean",
    "Sobolev": "Sobolev",
}

# -----------------------------------------------------------------------
# Compiled patterns
# -----------------------------------------------------------------------

# LaTeX remnants that should be stripped
_LATEX_CMD_RE = re.compile(
    r"\\(?:textbf|textit|textrm|textsf|texttt|emph|mathbb|mathcal|mathfrak|mathrm"
    r"|operatorname|boldsymbol|bm|hat|tilde|bar|vec|dot|ddot|widetilde|widehat)"
    r"\{([^}]*)\}",
    re.IGNORECASE,
)

# LaTeX braces
_LATEX_BRACES_RE = re.compile(r"(?<!\\)[{}]")

# Multiple spaces
_MULTI_SPACE_RE = re.compile(r"  +")

# Soft hyphens and zero-width characters
_INVISIBLE_RE = re.compile(r"[\u00ad\u200b\u200c\u200d\ufeff]")


class MathNotationHandler:
    """Normalise mathematical notation in extracted text.

    Usage::

        handler = MathNotationHandler()
        title = handler.normalize_mathematical_text(raw_title)
        author = handler.normalize_author_name(raw_author)
    """

    def __init__(self) -> None:
        # Build a regex for LaTeX command substitution
        escaped_cmds = sorted(_SYMBOL_TO_GREEK.keys(), key=len, reverse=True)
        self._latex_symbol_re = re.compile(
            "|".join(re.escape(cmd) for cmd in escaped_cmds)
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def normalize_mathematical_text(self, text: str) -> str:
        """Normalise mathematical notation in a title or abstract.

        Applies conservative substitutions:
        1. Replace LaTeX commands (``\\alpha`` → ``α``)
        2. Strip remaining LaTeX formatting (``\\textbf{...}`` → content)
        3. Remove stray braces
        4. Fix whitespace
        """
        if not text:
            return text

        result = text

        # Step 1: Replace LaTeX Greek/symbol commands
        result = self._latex_symbol_re.sub(
            lambda m: _SYMBOL_TO_GREEK.get(m.group(0), m.group(0)),
            result,
        )

        # Step 2: Replace LaTeX math operators
        for latex_cmd, unicode_char in _MATH_REPLACEMENTS.items():
            if latex_cmd.startswith("\\"):
                # Only replace if followed by non-alpha (word boundary)
                pattern = re.escape(latex_cmd) + r"(?![a-zA-Z])"
                result = re.sub(pattern, unicode_char, result)

        # Step 3: Strip LaTeX formatting commands, keeping content
        result = _LATEX_CMD_RE.sub(r"\1", result)

        # Step 4: Remove stray braces
        result = _LATEX_BRACES_RE.sub("", result)

        # Step 5: Remove invisible characters
        result = _INVISIBLE_RE.sub("", result)

        # Step 6: Normalise dollar-sign delimiters (strip inline math markers)
        result = result.replace("$", "")

        # Step 7: Collapse whitespace
        result = _MULTI_SPACE_RE.sub(" ", result).strip()

        return result

    def normalize_author_name(self, name: str) -> str:
        """Normalise an author name, restoring common diacritics.

        Only applies to known mathematician names where the diacritics
        are consistently lost during PDF extraction.
        """
        if not name:
            return name

        result = name.strip()

        # Remove invisible characters
        result = _INVISIBLE_RE.sub("", result)

        # Apply known name corrections (word-boundary aware)
        for wrong, correct in _NAME_CORRECTIONS.items():
            pattern = r"\b" + re.escape(wrong) + r"\b"
            result = re.sub(pattern, correct, result)

        # Collapse whitespace
        result = _MULTI_SPACE_RE.sub(" ", result).strip()

        return result

    def clean_extracted_text(self, text: str) -> str:
        """Light cleanup for raw extracted text — no semantic changes.

        Removes ligature artefacts, normalises Unicode, and fixes
        common extraction glitches without changing mathematical content.
        """
        if not text:
            return text

        result = text

        # Normalise Unicode to NFC (composed form)
        result = unicodedata.normalize("NFC", result)

        # Fix common ligature extractions
        result = result.replace("ﬁ", "fi")
        result = result.replace("ﬂ", "fl")
        result = result.replace("ﬀ", "ff")
        result = result.replace("ﬃ", "ffi")
        result = result.replace("ﬄ", "ffl")

        # Remove invisible characters
        result = _INVISIBLE_RE.sub("", result)

        return result
