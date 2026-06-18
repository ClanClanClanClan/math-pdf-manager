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
# lower-cased label.  Unknown labels fall back to matching the label's
# own significant words against the title (see ``_label_fallback``).
_SUBTOPIC_KEYWORDS = {
    "numerical methods": [
        r"\bnumerical\b", r"\bscheme(?:s)?\b", r"\bdiscreti[sz]ation\b",
        r"\bmonte[- ]carlo\b", r"\bsimulation(?:s)?\b",
        r"\bdeep (?:learning|bsde|solver|splitting)\b", r"\bneural network",
        r"\bmachine learning\b", r"\bfinite[- ]difference\b",
        r"\balgorithm(?:s)?\b", r"\beuler scheme\b", r"\bregression\b",
    ],
    "2bsdes": [
        r"\b2bsde(?:s)?\b", r"\bsecond[- ]order (?:bsde|backward)",
        r"\bfully nonlinear\b", r"\bg-?expectation\b",
    ],
    "g-bsdes": [
        r"\bg-?bsde(?:s)?\b", r"\bg-?expectation(?:s)?\b", r"\bg-?brownian\b",
        r"\bsublinear expectation", r"\bg-?martingale", r"\bg-?stochastic",
    ],
    "esg": [
        r"\besg\b", r"environment\w*[\s,]+social[\s,]+(?:and )?governance",
        r"\bsustainab", r"\bclimate\b", r"\bcarbon\b",
        r"\bgreen (?:finance|bond|investing)", r"\bimpact investing\b",
        r"\bresponsible investing\b",
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


def _label_fallback(label: str) -> list[str]:
    """Significant words from an unknown sub-subtopic label, as loose
    patterns, so newly-added folders still get *some* matching without a
    code change."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z-]{3,}", label)]
    stop = {"with", "from", "into", "and", "the", "for", "methods", "theory"}
    return [rf"\b{re.escape(w)}" for w in words if w.lower() not in stop]


def classify_subtopic(
    title: str,
    text: str,
    subtopics: list[tuple[str, str]],
) -> Optional[SubtopicDecision]:
    """Pick the best-matching sub-subtopic for a paper, or ``None``.

    ``subtopics`` is the output of :func:`discover_subtopics`.  Scoring
    counts distinct keyword hits across title+text; the strongest
    sub-subtopic above the confidence floor wins."""
    if not subtopics:
        return None
    hay = f"{title}\n{text}".lower()

    best: Optional[SubtopicDecision] = None
    for folder_name, label in subtopics:
        patterns = _SUBTOPIC_KEYWORDS.get(label.lower()) or _label_fallback(label)
        if not patterns:
            continue
        hits = sum(1 for p in patterns if re.search(p, hay, re.IGNORECASE))
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
