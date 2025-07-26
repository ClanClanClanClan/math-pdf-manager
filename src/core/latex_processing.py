#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/latex_processing.py - LaTeX Text Processing
Extracted from utils.py to improve modularity
"""

import os
import regex as re

# LaTeX regex patterns
_LATEX_INLINE = re.compile(r"\$[^$]*\$|\\\(.+?\\\)|\\\[.+?\\\]", re.S | re.UNICODE)
_TEXTCMD = re.compile(r"\\([a-zA-Z]+)\s*\{([^{}]*)\}", re.S | re.UNICODE)
_LATEX_CMD_BARE = re.compile(r"\\(?:textbf|textit|emph|begin|end|section|subsection|item|alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega)\b", re.UNICODE)  # Only known LaTeX commands
_BRACES = re.compile(r"[{}]", re.UNICODE)


def _strip_latex_common(text: str, *, keep_cmds: bool) -> str:
    """Common LaTeX stripping logic."""
    if not text:
        return ""

    txt = _LATEX_INLINE.sub("", text)  # remove inline maths

    def repl(m: re.Match[str]) -> str:
        cmd, body = m.group(1), _LATEX_INLINE.sub("", m.group(2)).strip()
        if keep_cmds:
            return rf"\{cmd}{body}" if body else rf"\{cmd}"
        if cmd == "emph":  # drop emphasised words entirely
            return ""
        return body

    txt = _TEXTCMD.sub(repl, txt)
    if not keep_cmds:
        txt = _LATEX_CMD_BARE.sub("", txt)

    txt = _BRACES.sub("", txt)
    txt = re.sub(r"\s+", " ", txt).strip()

    # keep trailing dot only when it is glued to a word (…text.) ;
    # strip when preceded by a space (…in .)  -> "in"
    if txt.endswith(".") and (len(txt) > 1 and txt[-2].isspace()):
        txt = txt[:-1].rstrip()
    return txt


def strip_latex(text: str) -> str:
    """Strip LaTeX commands and formatting from text."""
    return _strip_latex_common(text, keep_cmds=False)


def strip_latex_for_comparison(text: str) -> str:
    """Strip LaTeX commands but keep some structure for comparison."""
    return _strip_latex_common(text, keep_cmds=True)


def normalize_filename(name: str) -> str:
    """Normalize filename by replacing dashes and normalizing spaces."""
    stem = os.path.splitext(name)[0]
    # Replace various dashes with hyphen
    stem = re.sub(r"[‒–—―⸺⸻﹘﹣－‐−]", "-", stem)
    return re.sub(r"\s+", " ", stem).lower().strip()


def safe_compare_titles(a: str, b: str) -> bool:
    """Safely compare titles after stripping LaTeX and normalizing."""
    return normalize_filename(strip_latex_for_comparison(a)) == normalize_filename(
        strip_latex_for_comparison(b)
    )


# Export all functions
__all__ = [
    'strip_latex',
    'strip_latex_for_comparison',
    'safe_compare_titles',
    'normalize_filename'
]