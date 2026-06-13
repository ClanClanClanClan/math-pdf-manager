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


@dataclass
class TopicDecision:
    """Where a published paper should be filed, and why."""

    topic_code: Optional[str]          # "07a".."07f" or None (standard)
    topic_name: str                    # human label, "" for standard
    score: float                       # classifier score behind the choice
    runner_up: Optional[str] = None    # second-place topic code, if close
    all_scores: Optional[list] = None  # full classifier output for display
    subtopic_supported: bool = False   # always False until sub-buckets exist

    @property
    def is_standard(self) -> bool:
        return self.topic_code is None


def resolve_topic(
    title: str,
    text: str = "",
    *,
    threshold: float = DEFAULT_TOPIC_THRESHOLD,
) -> TopicDecision:
    """Classify a paper and decide its destination topic.

    Returns a :class:`TopicDecision`.  ``topic_code is None`` means
    "file in the standard top-level Published folder".

    Conservative by design: ties or weak signals fall back to
    standard.  The caller is expected to SHOW the decision to the
    user before moving anything -- this function never touches the
    filesystem.
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
    runner_up = scored[1]["topic_code"] if len(scored) > 1 else None

    # Only route into a topic if the score clears the threshold AND the
    # code is one of the six real topics.
    if score < threshold or code not in _TOPIC_CODES:
        return TopicDecision(
            None, "", score, runner_up=runner_up, all_scores=scored,
        )

    return TopicDecision(
        topic_code=code,
        topic_name=top.get("topic_name", code),
        score=score,
        runner_up=runner_up,
        all_scores=scored,
        subtopic_supported=False,
    )


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
