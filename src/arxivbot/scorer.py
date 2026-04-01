"""Scoring utilities for ranking harvested CMOs."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from .models import CMO


@dataclass
class SemanticFilter:
    """A minimal semantic rule used during filtering."""

    filter_id: str
    rule_type: str  # "allow" or "deny"
    rule_text: str

    def evaluate(self, cmo: CMO) -> Optional[bool]:
        """Return True/False when the rule matches, else ``None``."""

        haystack = f"{cmo.title}\n{cmo.abstract or ''}".lower()
        pattern = self.rule_text.lower()
        if "contains" in pattern:
            keyword = pattern.split("contains", 1)[1].strip()
        else:
            keyword = pattern
        if not keyword:
            return None
        found = keyword in haystack
        if self.rule_type == "allow":
            return True if found else None
        if self.rule_type == "deny":
            return False if found else None
        return None


@dataclass
class ScorerConfig:
    """Configuration knobs for :class:`Scorer`."""

    k_neighbours: int = 5
    default_tau: float = 0.35
    filters: List[SemanticFilter] = field(default_factory=list)


class Scorer:
    """Assigns heuristic relevance scores to CMOs."""

    def __init__(self, config: Optional[ScorerConfig] = None):
        self.config = config or ScorerConfig()
        self.tau: float = self.config.default_tau

    # ------------------------------------------------------------------
    def batch_score(self, cmos: Iterable[CMO]) -> List[CMO]:
        scored: List[CMO] = []
        for cmo in cmos:
            cmo.score = self._score(cmo)
            scored.append(cmo)
        return scored

    def filter_by_threshold(self, cmos: Iterable[CMO], threshold: Optional[float] = None) -> List[CMO]:
        thr = self.tau if threshold is None else threshold
        accepted: List[CMO] = []
        for cmo in cmos:
            score = cmo.score if cmo.score is not None else self._score(cmo)
            if not self._passes_filters(cmo):
                continue
            if score >= thr:
                accepted.append(cmo)
        return accepted

    # ------------------------------------------------------------------
    def _score(self, cmo: CMO) -> float:
        length_bonus = min(len((cmo.abstract or "").split()) / 200.0, 0.3)
        category_bonus = min(len(cmo.categories) * 0.05, 0.2)
        base = 0.4 + length_bonus + category_bonus
        # Gentle boost for allow filters
        for flt in self.config.filters:
            verdict = flt.evaluate(cmo)
            if verdict is True:
                base = max(base, 0.65)
            elif verdict is False:
                base = min(base, 0.1)
        return max(0.0, min(1.0, base))

    def _passes_filters(self, cmo: CMO) -> bool:
        for flt in self.config.filters:
            verdict = flt.evaluate(cmo)
            if verdict is False:
                return False
        return True


__all__ = ["Scorer", "ScorerConfig", "SemanticFilter"]
