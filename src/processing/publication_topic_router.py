"""Decide which topic folder a published paper belongs in.

The library has six top-level topic folders, each mirroring the
standard ``01 - Published / 02 - Unpublished / ...`` structure, and
some have sub-sub-topics (BSDEs has Numerical methods / 2BSDEs /
G-BSDEs; Contract theory has ESG).  When a paper is upgraded to
published (or sorted out of ``12 - To be sorted``), it should land in
the topic's ``01 - Published papers/{letter}/`` rather than the flat
top-level one -- unless it doesn't match any topic, in which case the
standard top-level Published folder is correct.

This module classifies a paper and returns the topic *prefix* (e.g.
``"07a"``) that ``organization.system.OrganizationSystem(topic=...)``
already knows how to file into, or ``None`` for the standard folder.

Sub-sub-topic routing (Numerical methods, 2BSDEs, ...) is NOT yet
supported: the keyword classifier has no patterns for those finer
buckets, so we deliberately stop at the top-level topic rather than
guess.  ``resolve_topic`` exposes ``subtopic_supported=False`` in its
result so callers can surface "filed under BSDEs; move to a
sub-bucket by hand if needed."
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Classifier topic codes map 1:1 to the top-level topic folders by
# filename prefix.  The folder's full name is discovered at runtime
# (``OrganizationSystem._find_topic_dir`` matches on the prefix) so we
# only need the prefix here.
_TOPIC_CODES = ("07a", "07b", "07c", "07d", "07e", "07f")

# Minimum keyword score before we route into a topic folder.  Below
# this the classifier's signal is too weak to override the safe
# default of the standard top-level Published folder.  2.0 means at
# least one primary-keyword hit (primary_weight is typically 2.0+).
DEFAULT_TOPIC_THRESHOLD = 2.0

# Confidence bands (0..1).  The classifier's raw keyword score is
# converted to a percentage (see _confidence) so the user gets a
# "how sure are we" number:
#   confidence >= AUTO_CONFIDENCE   -> auto-file into the topic folder
#   REVIEW_CONFIDENCE <= c < AUTO   -> SUGGEST the topic, leave for the
#                                      user to confirm (filed standard,
#                                      flagged in the Attention Queue)
#   confidence < REVIEW_CONFIDENCE  -> standard folder, no suggestion
#
# AUTO_CONFIDENCE was raised 0.70 -> 0.75 after the abstract-signal
# upgrade: measured on the full real library (3,277 hand-filed topic
# papers classified on cached abstracts), 0.75 holds 99.0% precision at
# 87% recall — the empirical knee.  0.70 buys only +1% recall for ~0.4%
# precision; 0.80 costs 13% recall for +0.3% precision.  So 0.75 keeps
# auto-filing at the user's ~99% precision bar while routing the genuinely
# ambiguous 07b/07c/07d boundary to the review queue.
AUTO_CONFIDENCE = 0.75
REVIEW_CONFIDENCE = 0.40

# A top score at/above this is treated as "fully strong" before the
# ambiguity penalty.  ~two primary-keyword hits, or one primary plus
# a couple of secondaries.
_FULL_STRENGTH_SCORE = 4.0


def _confidence(scored: list) -> float:
    """Map classifier scores to a 0..1 confidence for the top topic.

    Combines absolute strength (how strongly the winning topic's
    keywords fired) with dominance (how far ahead of the runner-up it
    is).  A lone strong match -> near 1.0; a strong but contested
    match -> reduced; a single weak keyword -> low.
    """
    if not scored:
        return 0.0
    top = scored[0]["score"]
    second = scored[1]["score"] if len(scored) > 1 else 0.0
    strength = min(1.0, top / _FULL_STRENGTH_SCORE)
    # Ambiguity penalty: the closer the runner-up, the less sure.
    if top + second > 0:
        dominance = (top - second) / (top + second)  # 1.0 if uncontested
    else:
        dominance = 1.0
    return round(strength * (0.5 + 0.5 * dominance), 3)


@dataclass
class TopicDecision:
    """Where a published paper should be filed, and why."""

    topic_code: Optional[str]          # "07a".."07f" or None (standard)
    topic_name: str                    # human label, "" for standard
    score: float                       # raw classifier score behind the choice
    confidence: float = 0.0            # 0..1 "how sure are we" percentage
    runner_up: Optional[str] = None    # second-place topic code, if close
    all_scores: Optional[list] = None  # full classifier output for display
    subtopic_supported: bool = False   # always False until sub-buckets exist
    # The best-guess topic even when confidence is too low to auto-file.
    # Lets the caller record a SUGGESTION for the user to review.
    suggested_code: Optional[str] = None
    suggested_name: str = ""

    @property
    def is_standard(self) -> bool:
        return self.topic_code is None

    @property
    def auto(self) -> bool:
        """High enough confidence to file into the topic automatically."""
        return self.topic_code is not None and self.confidence >= AUTO_CONFIDENCE

    @property
    def needs_review(self) -> bool:
        """A plausible topic the user should confirm before filing.

        True whenever the classifier found a real topic match (a
        ``suggested_code``) that wasn't confident enough to auto-file.
        A perfect tie between two strong topics counts -- the user
        should pick, not have it silently dumped to the standard
        folder.
        """
        return self.suggested_code is not None and not self.auto


def resolve_topic(
    title: str,
    text: str = "",
    *,
    threshold: float = DEFAULT_TOPIC_THRESHOLD,
) -> TopicDecision:
    """Classify a paper and decide its destination topic, with confidence.

    The decision has three bands:
      * ``auto``        -- confidence >= AUTO_CONFIDENCE; ``topic_code``
                           is set so the caller files into the topic.
      * ``needs_review``-- plausible but uncertain; ``topic_code`` is
                           None (file standard) but ``suggested_code``
                           carries the best guess for the user to
                           confirm.
      * neither         -- standard folder, no suggestion.

    Pass as much signal as you have in ``text`` (keywords + abstract +
    first-page body) -- the classifier weighs all of it, not just the
    title.  This function never touches the filesystem.
    """
    try:
        from processing.topic_classifier import classify_by_keywords
    except ImportError as exc:
        logger.warning("topic classifier unavailable: %s", exc)
        return TopicDecision(None, "", 0.0)

    scored = classify_by_keywords(title, text)
    if not scored:
        return TopicDecision(None, "", 0.0, all_scores=[])

    top = scored[0]
    code = top["topic_code"]
    score = top["score"]
    name = top.get("topic_name", code)
    runner_up = scored[1]["topic_code"] if len(scored) > 1 else None
    conf = _confidence(scored)

    if code not in _TOPIC_CODES or score < threshold:
        return TopicDecision(
            None, "", score, confidence=conf,
            runner_up=runner_up, all_scores=scored,
        )

    if conf >= AUTO_CONFIDENCE:
        # Confident enough to file automatically.
        return TopicDecision(
            topic_code=code, topic_name=name, score=score, confidence=conf,
            runner_up=runner_up, all_scores=scored,
            suggested_code=code, suggested_name=name,
        )

    # Plausible but uncertain -> suggest, don't auto-file.
    #
    # Audit-9 F: the paper has ALREADY cleared the classifier's strong
    # per-topic threshold (so it genuinely matches >=1 topic); the only
    # reason confidence is low is CONTENTION (it matches two topics
    # nearly equally -> dominance penalty drops confidence to ~0.38).
    # Those are exactly the papers the user must adjudicate, so we
    # ALWAYS surface a suggestion here rather than gating on
    # REVIEW_CONFIDENCE -- otherwise a strong two-topic tie would
    # silently fall through to the standard folder with no flag.
    return TopicDecision(
        topic_code=None, topic_name="", score=score, confidence=conf,
        runner_up=runner_up, all_scores=scored,
        suggested_code=code, suggested_name=name,
    )


def list_topic_suggestions(library_root: Path) -> list[dict]:
    """Papers filed in a standard folder that carry a pending, medium-
    confidence topic suggestion the user should confirm.

    Returns ``[{"path": str, "topic": "07a", "confidence": 0.55}, ...]``
    sorted by confidence (most confident first), so the Attention
    Queue can present the strongest suggestions at the top.
    """
    from processing.identity import iter_pdfs, PaperIdentity
    out: list[dict] = []
    if not library_root.exists():
        return out
    for pdf in iter_pdfs(library_root):
        identity = PaperIdentity.load(pdf)
        if identity.is_new() or not identity.topic_suggestion:
            continue
        out.append({
            "path": str(pdf),
            "topic": identity.topic_suggestion,
            "confidence": identity.topic_confidence,
        })
    out.sort(key=lambda d: d["confidence"], reverse=True)
    return out


def file_into_topic(
    pdf_path: Path,
    code: str,
    library_root: Path,
    *,
    undo_log=None,  # type: ignore[no-untyped-def]
) -> tuple[bool, str]:
    """Move a paper from its standard status folder into topic ``code``'s
    matching status sub-bucket, recording the topic on the sidecar.

    The shared core behind both the Attention-Queue accept action and
    the bulk-apply (Pipeline Preview).  Uses ``logged_move`` so the move
    carries the sidecar and is reversible via the undo log, and records
    a ``sidecar_edit`` so undo also restores the prior topic fields.
    Returns ``(ok, message)``.  Does NOT require a stored suggestion.
    """
    from processing.identity import PaperIdentity
    from processing.undo_log import logged_move
    from organization.system import (
        OrganizationSystem, PUBLISHED, UNPUBLISHED, WORKING, BOOKS, THESES,
    )

    if code not in _TOPIC_CODES:
        return False, f"unknown topic code: {code}"

    # Figure out which status sub-bucket the paper currently sits in by
    # matching its parent chain against the standard status dir names.
    # Audit-9 C: walk from the DEEPEST component upward so a status name
    # appearing higher in the path doesn't mis-route the tail.
    status_dirs = {PUBLISHED, UNPUBLISHED, WORKING, BOOKS, THESES}
    parts = list(pdf_path.parts)
    status_idx = None
    for i in range(len(parts) - 1, -1, -1):
        if parts[i] in status_dirs:
            status_idx = i
            break
    if status_idx is None:
        return False, "could not determine current status folder"
    current_status_dir = parts[status_idx]

    topic_dir = OrganizationSystem(library_root, topic=code).router._topic_dir
    if topic_dir is None:
        return False, f"topic folder for {code} not found"

    # Preserve the alpha-subdir (and year for working papers) by taking
    # everything after the (closest) status dir in the current path.
    tail = Path(*parts[status_idx + 1:])  # "S/Smith - X.pdf" or "S/2020/..."
    dest = topic_dir / current_status_dir / tail

    if dest.exists():
        return False, f"destination already exists: {dest}"

    # Record the topic on the sidecar at the SOURCE *before* moving, so
    # the sidecar (a) exists even for a freshly-dropped un-topiced paper
    # that never had one, and (b) travels with ``logged_move`` as part of
    # the same reversible transaction.  Capture the prior field values so
    # the recorded ``sidecar_edit`` can restore them on undo.
    identity = PaperIdentity.load(pdf_path)
    old_suggestion = identity.topic_suggestion
    old_confidence = identity.topic_confidence
    old_codes = list(identity.topic_codes)
    identity.topic_suggestion = ""
    identity.topic_confidence = 0.0
    if code not in identity.topic_codes:
        identity.topic_codes.append(code)
    new_codes = list(identity.topic_codes)
    identity.save(pdf_path, recompute_hash=False)

    try:
        logged_move(pdf_path, dest, undo_log=undo_log)
    except Exception as exc:
        return False, f"move failed: {exc}"

    # Audit-11b: record the field edit AFTER the move so undo (reverse
    # order) restores the sidecar fields while the file is still at
    # ``dest``, then reverses the move.
    if undo_log is not None:
        undo_log.record_sidecar_edit(dest, {
            "topic_suggestion": [old_suggestion, ""],
            "topic_confidence": [old_confidence, 0.0],
            "topic_codes": [old_codes, new_codes],
        })
    return True, f"moved to {dest.relative_to(library_root)}"


def accept_topic_suggestion(
    pdf_path: Path,
    library_root: Path,
    *,
    undo_log=None,  # type: ignore[no-untyped-def]
) -> tuple[bool, str]:
    """Move a paper into its *stored* suggested topic, clearing the
    suggestion.  Thin wrapper over :func:`file_into_topic` that reads the
    target code from the sidecar's pending suggestion."""
    from processing.identity import PaperIdentity

    identity = PaperIdentity.load(pdf_path)
    if identity.is_new() or not identity.topic_suggestion:
        return False, "no pending topic suggestion"
    return file_into_topic(pdf_path, identity.topic_suggestion, library_root,
                           undo_log=undo_log)


def reject_topic_suggestion(pdf_path: Path, *, undo_log=None) -> bool:
    """Clear a pending topic suggestion without moving the paper.

    Audit-11b: when an ``undo_log`` (with an open transaction) is
    passed, the cleared fields are recorded so the rejection is
    reversible from the cockpit Activity tab — a rejected suggestion is
    no longer gone forever.
    """
    from processing.identity import PaperIdentity
    identity = PaperIdentity.load(pdf_path)
    if identity.is_new() or not identity.topic_suggestion:
        return False
    old_suggestion = identity.topic_suggestion
    old_confidence = identity.topic_confidence
    identity.topic_suggestion = ""
    identity.topic_confidence = 0.0
    identity.save(pdf_path, recompute_hash=False)
    if undo_log is not None:
        undo_log.record_sidecar_edit(pdf_path, {
            "topic_suggestion": [old_suggestion, ""],
            "topic_confidence": [old_confidence, 0.0],
        })
    return True


def preview_destination(
    library_root: Path,
    decision: TopicDecision,
    canonical_filename: str,
    *,
    status: str = "published",
) -> Path:
    """Compute the full destination path a decision implies, no writes.

    Mirrors what ``OrganizationSystem(topic=code).route(...)`` would
    produce, so the user sees the exact landing spot before approving.
    """
    from organization.system import OrganizationSystem

    org = OrganizationSystem(
        library_root,
        topic=decision.topic_code,   # None -> standard top-level
        dry_run=True,
    )
    # Minimal metadata: status forced to published, author parsed from
    # the canonical filename for the alpha subdir.
    meta = {"doi": "preview"} if status == "published" else {}
    if " - " in canonical_filename:
        first = canonical_filename.split(" - ", 1)[0].split(",")[0].strip()
        meta["authors"] = [{"family": first, "given": ""}]
    return org.router.route(meta, canonical_filename)
