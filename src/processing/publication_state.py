"""Publication-state machine over paper identity sidecars.

This module sits between ``publication_checker`` (which queries
Crossref) and ``identity`` (which persists per-paper state).  The
weekly task hands us a list of ``scan_directory`` results and we:

1. Update each paper's sidecar with the check result (hit/miss).
2. Advance the recheck counter on misses.
3. After N=3 consecutive misses with zero hits ever, mark the paper
   ``permanently_unpublished=True`` so future weekly runs skip it.
4. Return summary lists the caller can surface in the Attention Queue
   or auto-execute (Phase 3).

The state machine is intentionally conservative: a single hit at
any confidence resets the "give up" counter, and we never wipe an
existing positive history.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from processing.identity import PaperIdentity

logger = logging.getLogger(__name__)

# How many consecutive misses across separate weekly runs before we
# mark a paper permanently unpublished.  Three months at one check per
# month is "we tried hard enough" but still recoverable via the
# Attention Queue's reset button.
DEFAULT_MAX_RECHECKS = 3


@dataclass
class StateUpdateSummary:
    """What ``update_publication_state`` did, ready for UI/log surfacing.

    Each list contains absolute PDF paths (as strings).  Keeping plain
    strings rather than ``Path`` objects keeps the summary trivially
    JSON-serialisable for the cockpit and the weekly report.
    """

    checked: list[str] = field(default_factory=list)
    hits: list[dict] = field(default_factory=list)        # high-confidence matches
    skipped: list[str] = field(default_factory=list)      # sidecar said skip
    newly_permanent: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "checked": list(self.checked),
            "hits": list(self.hits),
            "skipped": list(self.skipped),
            "newly_permanent": list(self.newly_permanent),
            "errors": list(self.errors),
        }


def update_publication_state(
    results: list[dict],
    *,
    max_rechecks: int = DEFAULT_MAX_RECHECKS,
    hit_threshold: float = 0.75,
) -> StateUpdateSummary:
    """Apply scan_directory results to each paper's identity sidecar.

    Parameters
    ----------
    results
        The list ``publication_checker.scan_directory`` returns.  Each
        entry is a dict with ``"file"``, ``"published"``, and (on hit)
        ``"match"`` containing ``{"doi", "confidence", ...}``.
    max_rechecks
        After this many misses with zero recorded hits, the paper is
        marked permanently unpublished.
    hit_threshold
        Confidence below this is treated as a miss for state-machine
        purposes even if ``scan_directory`` returned a match.  Keeps
        borderline matches out of the auto-promote pipeline.

    Returns
    -------
    StateUpdateSummary
        A breakdown of what happened.  No exceptions escape — sidecar
        errors are collected into ``summary.errors`` so one bad file
        doesn't poison the whole batch.
    """
    summary = StateUpdateSummary()

    for entry in results:
        path_str = entry.get("file") or ""
        if not path_str:
            continue
        pdf = Path(path_str)
        try:
            identity = PaperIdentity.load(pdf)
        except Exception as exc:
            summary.errors.append(f"{pdf}: load failed: {exc}")
            continue

        # Skip papers we've already given up on, *unless* this scan
        # found a hit — in which case the previous "permanent" verdict
        # was wrong and we should reconsider.
        hit_match = entry.get("match") if entry.get("published") else None
        if (
            identity.should_skip_publication_check(max_rechecks=max_rechecks)
            and not hit_match
        ):
            summary.skipped.append(str(pdf))
            continue

        confidence = float(hit_match.get("confidence", 0)) if hit_match else 0.0
        is_hit = bool(hit_match) and confidence >= hit_threshold

        try:
            identity.record_publication_check(
                hit=is_hit,
                source="crossref",
                confidence=confidence,
                details={"doi": hit_match.get("doi", "")} if hit_match else None,
            )
            # If we recovered from a "permanent" state because a hit
            # arrived after all, unflag and reset the counter.
            if is_hit:
                if identity.permanently_unpublished:
                    identity.permanently_unpublished = False
                identity.recheck_count = 0

            # Tip into permanent only if we *just* exceeded the budget
            # and have zero historical hits.  This means a paper with
            # 2 misses + 1 hit + 2 misses doesn't auto-tip; the hit
            # earned a clean slate.
            became_permanent = False
            if (
                not is_hit
                and not identity.permanently_unpublished
                and identity.recheck_count >= max_rechecks
                and not any(c.get("hit") for c in identity.publication_checks)
            ):
                identity.permanently_unpublished = True
                became_permanent = True

            identity.save(pdf, recompute_hash=False)
        except Exception as exc:
            summary.errors.append(f"{pdf}: save failed: {exc}")
            continue

        summary.checked.append(str(pdf))
        if is_hit:
            summary.hits.append({
                "file": str(pdf),
                "confidence": confidence,
                "doi": hit_match.get("doi", ""),
            })
        if became_permanent:
            summary.newly_permanent.append(str(pdf))

    return summary


def list_permanently_unpublished(library_root: Path) -> list[Path]:
    """Walk the library and return every PDF whose sidecar says permanent."""
    out: list[Path] = []
    if not library_root.exists():
        return out
    for pdf in library_root.rglob("*.pdf"):
        if ".trash" in pdf.parts:
            continue
        identity = PaperIdentity.load(pdf)
        if identity.is_new():
            continue
        if identity.permanently_unpublished:
            out.append(pdf)
    return out


def reset_recheck_state(pdf: Path) -> Optional[PaperIdentity]:
    """Clear the give-up flag and counter on one paper.

    Used by the Attention Queue "re-check this paper" action when the
    user thinks the system gave up prematurely.  Returns the updated
    identity, or ``None`` if the paper has no sidecar yet.
    """
    identity = PaperIdentity.load(pdf)
    if identity.is_new():
        return None
    identity.permanently_unpublished = False
    identity.recheck_count = 0
    identity.last_check_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
    identity.save(pdf, recompute_hash=False)
    return identity
