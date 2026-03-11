#!/usr/bin/env python3
"""
Statistical Pattern Matcher
============================

Learns from successful metadata extractions to improve future predictions.
Tracks font-size, position, and bold/italic patterns that correlate with
titles, authors, and other metadata fields across a corpus of PDFs.

This is a lightweight online learner — it accumulates statistics in memory
and uses them to score candidate text blocks during extraction.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class FeatureStats:
    """Running statistics for a single numeric feature."""

    count: int = 0
    total: float = 0.0
    min_val: float = float("inf")
    max_val: float = float("-inf")

    def update(self, value: float) -> None:
        self.count += 1
        self.total += value
        self.min_val = min(self.min_val, value)
        self.max_val = max(self.max_val, value)

    @property
    def mean(self) -> float:
        return self.total / self.count if self.count > 0 else 0.0


@dataclass
class ElementPattern:
    """Accumulated statistics for a particular element type (title, author, etc.)."""

    font_size: FeatureStats = field(default_factory=FeatureStats)
    position: FeatureStats = field(default_factory=FeatureStats)
    bold_count: int = 0
    italic_count: int = 0
    total_count: int = 0


class StatisticalPatternMatcher:
    """Learn and apply statistical patterns for metadata element detection.

    Usage::

        matcher = StatisticalPatternMatcher()

        # Learn from a successful extraction
        matcher.learn_from_extraction(
            text="A Great Paper Title",
            font_size=18.0,
            position=0.12,        # normalised y-position (0 = top, 1 = bottom)
            is_bold=True,
            is_italic=False,
            actual_type="title",
            publisher="arxiv",
            document_id="2301.12345",
        )

        # Score a candidate block
        score = matcher.score_candidate(
            font_size=16.0,
            position=0.15,
            is_bold=True,
            is_italic=False,
            candidate_type="title",
            publisher="arxiv",
        )
    """

    def __init__(self) -> None:
        # patterns[publisher][element_type] → ElementPattern
        self._patterns: Dict[str, Dict[str, ElementPattern]] = defaultdict(
            lambda: defaultdict(ElementPattern)
        )
        # Global (publisher-agnostic) patterns
        self._global: Dict[str, ElementPattern] = defaultdict(ElementPattern)

    # ------------------------------------------------------------------
    # Learning
    # ------------------------------------------------------------------

    def learn_from_extraction(
        self,
        text: str,
        font_size: float,
        position: float,
        is_bold: bool,
        is_italic: bool,
        actual_type: str,
        publisher: str = "Unknown",
        document_id: str = "",
    ) -> None:
        """Record a confirmed extraction to refine future scoring.

        Parameters
        ----------
        text:
            The extracted text (used for logging only).
        font_size:
            Font size of the text block.
        position:
            Normalised vertical position on the page (0.0 = top, 1.0 = bottom).
        is_bold / is_italic:
            Font style flags.
        actual_type:
            Element type — ``"title"``, ``"author"``, ``"abstract_heading"``, etc.
        publisher:
            Publisher template identifier (``"arxiv"``, ``"elsevier"``, …).
        document_id:
            Optional identifier for the source document.
        """
        # Update publisher-specific stats
        pat = self._patterns[publisher][actual_type]
        pat.font_size.update(font_size)
        pat.position.update(position)
        pat.bold_count += int(is_bold)
        pat.italic_count += int(is_italic)
        pat.total_count += 1

        # Update global stats
        gpat = self._global[actual_type]
        gpat.font_size.update(font_size)
        gpat.position.update(position)
        gpat.bold_count += int(is_bold)
        gpat.italic_count += int(is_italic)
        gpat.total_count += 1

        logger.debug(
            f"PatternMatcher learned: {actual_type} "
            f"(size={font_size:.1f}, pos={position:.2f}, bold={is_bold}) "
            f"[{publisher}] doc={document_id}"
        )

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def score_candidate(
        self,
        font_size: float,
        position: float,
        is_bold: bool,
        is_italic: bool,
        candidate_type: str,
        publisher: str = "Unknown",
    ) -> float:
        """Score how likely a candidate block matches the given element type.

        Returns a value in [0.0, 1.0] where higher = better match.
        Falls back to global patterns when publisher-specific data is sparse.
        """
        # Choose the best available pattern source
        pat = self._patterns.get(publisher, {}).get(candidate_type)
        if pat is None or pat.total_count < 3:
            pat = self._global.get(candidate_type)

        if pat is None or pat.total_count < 2:
            # Not enough data — return neutral score
            return 0.5

        score = 0.0
        weights_total = 0.0

        # Font size similarity (weight 0.4)
        if pat.font_size.count > 0:
            mean_size = pat.font_size.mean
            if mean_size > 0:
                size_ratio = min(font_size, mean_size) / max(font_size, mean_size)
                score += 0.4 * size_ratio
            weights_total += 0.4

        # Position similarity (weight 0.3)
        if pat.position.count > 0:
            pos_diff = abs(position - pat.position.mean)
            pos_score = max(0.0, 1.0 - pos_diff * 3)  # 0.33 distance → 0 score
            score += 0.3 * pos_score
            weights_total += 0.3

        # Bold match (weight 0.2)
        if pat.total_count > 0:
            bold_prob = pat.bold_count / pat.total_count
            bold_match = bold_prob if is_bold else (1.0 - bold_prob)
            score += 0.2 * bold_match
            weights_total += 0.2

        # Italic match (weight 0.1)
        if pat.total_count > 0:
            italic_prob = pat.italic_count / pat.total_count
            italic_match = italic_prob if is_italic else (1.0 - italic_prob)
            score += 0.1 * italic_match
            weights_total += 0.1

        return score / weights_total if weights_total > 0 else 0.5

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, int]:
        """Return summary statistics about learned patterns."""
        total = sum(p.total_count for p in self._global.values())
        by_type = {k: v.total_count for k, v in self._global.items()}
        publishers = len(self._patterns)
        return {
            "total_observations": total,
            "by_type": by_type,
            "publishers_seen": publishers,
        }

    def has_learned(self, element_type: str, min_observations: int = 3) -> bool:
        """Check whether enough data exists for a given element type."""
        pat = self._global.get(element_type)
        return pat is not None and pat.total_count >= min_observations
