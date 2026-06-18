#!/usr/bin/env python3
"""Sub-subtopic routing within a topic folder.

Some topics carry a finer layer.  In the real library, ``07a - BSDEs``
contains ``07a - Numerical methods``, ``07b - 2BSDEs`` and
``07c - G-BSDEs``; ``07b - Contract theory`` contains ``07a - ESG``.
Each sub-subtopic mirrors the full status structure (01/02/03/…).

This module is **data-driven**: it discovers the sub-subtopic folders
that actually exist under a topic at runtime (so adding a folder needs
no code change), then classifies a paper into one of them by keyword.
It is conservative — when no sub-subtopic clearly matches it returns
``None`` and the paper stays at the topic root.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# A sub-subtopic folder inside a topic is named like the topic codes
# themselves restart ("07a - Numerical methods").  We capture the label
# after the "07x - " prefix.
_SUBTOPIC_DIR_RE = re.compile(r"^07[a-f] - (.+)$", re.IGNORECASE)

# Status sub-buckets are NOT sub-subtopics.
_STATUS_DIR_RE = re.compile(r"^0[1-6] - ")

# Curated keyword signals for the known sub-subtopics, keyed by the
# lower-cased label.  Each entry is ``(regex, case_sensitive)``: a
# case-sensitive pattern is matched against the ORIGINAL text (case
# preserved); a case-insensitive one with IGNORECASE.  Unknown labels
# fall back to matching the label's own significant words
# (see ``_label_fallback``).
#
# The G-BSDEs entry is deliberately subtle.  In the BSDE literature
# *small-g* "g-expectation" is Peng's nonlinear expectation defined by an
# ORDINARY BSDE with generator g — core BSDE theory that belongs in the
# BSDE root, NOT here.  *Capital-G* "G-expectation" / "G-Brownian motion"
# is the separate sublinear-expectation framework, and G-BSDEs (driven by
# G-Brownian motion) get this folder.  A single letter's case in
# extracted PDF text is fragile, so we lean on DISTINCTIVE companion
# terms that disambiguate regardless of case ("G-Brownian", "sublinear
# expectation" — there is no "g-Brownian"), and match the genuinely
# case-dependent terms ("G-BSDE", "G-expectation") CASE-SENSITIVELY.
# Bare "g-expectation" is intentionally NOT a signal, so small-g papers
# fall through to the BSDE root.
_SUBTOPIC_KEYWORDS = {
    "numerical methods": [
        (r"\bnumerical\b", False), (r"\bscheme(?:s)?\b", False),
        (r"\bdiscreti[sz]ation\b", False), (r"\bmonte[- ]carlo\b", False),
        (r"\bsimulation(?:s)?\b", False),
        (r"\bdeep (?:learning|bsde|solver|splitting)\b", False),
        (r"\bneural network", False), (r"\bmachine learning\b", False),
        (r"\bfinite[- ]difference\b", False), (r"\balgorithm(?:s)?\b", False),
        (r"\beuler scheme\b", False), (r"\bregression\b", False),
    ],
    "2bsdes": [
        (r"\b2bsde(?:s)?\b", False),
        (r"\bsecond[- ]order (?:bsde|backward)", False),
        (r"\bsecond[- ]order backward stochastic\b", False),
    ],
    "g-bsdes": [
        # Distinctive capital-G framework phrases (case-insensitive is
        # safe — no small-g "g-Brownian"/"g-heat equation" notions exist).
        (r"\bg-brownian\b", False),
        (r"\bsublinear expectation", False),
        (r"\bg-heat equation\b", False),
        (r"\bg-martingale", False),
        (r"\bg-(?:ito|itô)\b", False),
        (r"\bg-stochastic\b", False),
        (r"\bg-normal\b", False),
        # Case-SENSITIVE: capital "G-BSDE"/"G-expectation" only, so the
        # small-g "g-expectation"/"g-bsde" never lands in this folder.
        (r"G-BSDE", True),
        (r"G-expectation", True),
    ],
    "esg": [
        (r"\besg\b", False),
        (r"environment\w*[\s,]+social[\s,]+(?:and )?governance", False),
        (r"\bsustainab", False), (r"\bclimate\b", False), (r"\bcarbon\b", False),
        (r"\bgreen (?:finance|bond|investing)", False),
        (r"\bimpact investing\b", False), (r"\bresponsible investing\b", False),
    ],
}

_MIN_SUBTOPIC_CONFIDENCE = 0.6


@dataclass
class SubtopicDecision:
    folder_name: str        # e.g. "07a - Numerical methods"
    label: str              # e.g. "Numerical methods"
    confidence: float
    reason: str

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


def discover_subtopics(topic_dir: Path) -> list[tuple[str, str]]:
    """Return ``[(folder_name, label), …]`` for the sub-subtopic folders
    that exist directly under ``topic_dir``.  Empty if none (or the topic
    dir is missing)."""
    out: list[tuple[str, str]] = []
    if not topic_dir.exists():
        return out
    for child in sorted(topic_dir.iterdir()):
        if not child.is_dir():
            continue
        if _STATUS_DIR_RE.match(child.name):
            continue  # a status bucket, not a sub-subtopic
        m = _SUBTOPIC_DIR_RE.match(child.name)
        if m:
            out.append((child.name, m.group(1).strip()))
    return out


def _label_fallback(label: str) -> list[tuple[str, bool]]:
    """Significant words from an unknown sub-subtopic label, as loose
    (case-insensitive) patterns, so newly-added folders still get *some*
    matching without a code change."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z-]{3,}", label)]
    stop = {"with", "from", "into", "and", "the", "for", "methods", "theory"}
    return [(rf"\b{re.escape(w)}", False) for w in words if w.lower() not in stop]


def classify_subtopic(
    title: str,
    text: str,
    subtopics: list[tuple[str, str]],
) -> Optional[SubtopicDecision]:
    """Pick the best-matching sub-subtopic for a paper, or ``None``.

    ``subtopics`` is the output of :func:`discover_subtopics`.  Scoring
    counts distinct keyword hits across title+text; the strongest
    sub-subtopic above the confidence floor wins.  Patterns carry a
    case-sensitivity flag (see ``_SUBTOPIC_KEYWORDS``) so the small-g vs
    capital-G distinction is preserved — the original-cased text is
    matched for case-sensitive patterns."""
    if not subtopics:
        return None
    hay = f"{title}\n{text}"   # original case preserved

    best: Optional[SubtopicDecision] = None
    for folder_name, label in subtopics:
        patterns = _SUBTOPIC_KEYWORDS.get(label.lower()) or _label_fallback(label)
        if not patterns:
            continue
        hits = sum(
            1 for pat, cs in patterns
            if re.search(pat, hay, 0 if cs else re.IGNORECASE)
        )
        if hits == 0:
            continue
        conf = min(0.85, 0.5 + 0.15 * hits)
        if conf < _MIN_SUBTOPIC_CONFIDENCE:
            continue
        if best is None or conf > best.confidence:
            best = SubtopicDecision(
                folder_name=folder_name, label=label,
                confidence=round(conf, 4),
                reason=f"{hits} keyword hit(s) for {label!r}",
            )
    return best


def resolve_subtopic(
    pdf_path: Path,
    topic_code: str,
    library_root: Path,
    *,
    title: Optional[str] = None,
    text: str = "",
) -> Optional[SubtopicDecision]:
    """Convenience: find ``topic_code``'s folder, discover its
    sub-subtopics, and classify ``pdf_path`` into one (or ``None``).

    ``title`` defaults to the paper's filename-derived title."""
    from organization.system import OrganizationSystem
    topic_dir = OrganizationSystem(library_root, topic=topic_code).router._topic_dir
    if topic_dir is None:
        return None
    subs = discover_subtopics(topic_dir)
    if not subs:
        return None
    if title is None:
        from processing.pipeline_preview import title_from_filename
        title = title_from_filename(pdf_path)
    return classify_subtopic(title, text, subs)
