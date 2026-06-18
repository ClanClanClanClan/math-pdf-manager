#!/usr/bin/env python3
"""Read-only "what would the pipeline do" preview over the real library.

This module NEVER touches the filesystem beyond reading.  It runs the
topic classifier across every paper and reports what it *would* do,
compared against where the paper currently lives (which, for the
hand-filed library, is ground truth).  That comparison is the evidence
needed to decide whether the classifier is trustworthy enough to
bulk-classify — without moving a single file.

Output bands per paper (``TopicProposal.status``):
  * ``agree``    -- already in a topic folder; classifier would auto-file
                    it to the SAME topic (confidence-building).
  * ``disagree`` -- already in a topic folder; classifier would auto-file
                    it to a DIFFERENT topic (a misfiling OR a classifier
                    error — the spot-check list).
  * ``move``     -- not in any topic folder; classifier is confident
                    enough to auto-file it (a proposed new filing).
  * ``suggest``  -- not in any topic folder; classifier has a
                    medium-confidence guess for the user to confirm.
  * ``recall_miss`` -- already hand-filed in a topic folder, but the
                    classifier would NOT auto-file it (it can't reproduce
                    the user's decision — a recall gap).
  * ``none``     -- not in a topic folder and no usable signal.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Topic folders are named like "07a - BSDEs"; the code is the prefix.
_TOPIC_DIR_RE = re.compile(r"^(07[a-f])\b", re.IGNORECASE)


@dataclass
class TopicProposal:
    path: str
    current_topic: Optional[str]      # "07a".."07f" or None
    proposed_topic: Optional[str]     # auto-file code, or None
    suggested_topic: Optional[str]    # review-band best guess, or None
    confidence: float
    status: str                       # agree|disagree|move|suggest|recall_miss|none

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


@dataclass
class PreviewSummary:
    scanned: int = 0
    counts: dict = field(default_factory=dict)   # status -> count
    # Agreement metric among papers already in a topic folder:
    in_topic: int = 0           # papers currently under a 07x folder
    agree: int = 0              # of those, classifier auto-files to same
    disagree: int = 0           # of those, classifier auto-files different
    recall_miss: int = 0        # of those, classifier wouldn't auto-file
    # Proposed work for un-topiced papers:
    proposed_moves: int = 0     # confident new filings
    proposed_suggestions: int = 0

    @property
    def agreement_rate(self) -> float:
        """Of hand-filed papers the classifier is confident about,
        the fraction it agrees with.  This is the trust metric."""
        decided = self.agree + self.disagree
        return (self.agree / decided) if decided else 0.0

    @property
    def topic_recall(self) -> float:
        """Fraction of hand-filed topic papers the classifier would
        auto-file at all (agree or disagree, i.e. not a recall miss)."""
        return ((self.agree + self.disagree) / self.in_topic) if self.in_topic else 0.0

    def to_dict(self) -> dict:
        return {
            "scanned": self.scanned,
            "counts": dict(self.counts),
            "in_topic": self.in_topic,
            "agree": self.agree,
            "disagree": self.disagree,
            "recall_miss": self.recall_miss,
            "proposed_moves": self.proposed_moves,
            "proposed_suggestions": self.proposed_suggestions,
            "agreement_rate": round(self.agreement_rate, 4),
            "topic_recall": round(self.topic_recall, 4),
        }


def current_topic_of(pdf_path: Path, library_root: Path) -> Optional[str]:
    """Return the topic code the paper currently lives under, or None.

    Looks for a ``07x - ...`` component anywhere in the path relative to
    the library root (topic folders sit at the root; sub-subtopics live
    beneath them, so the code is always an ancestor directory name)."""
    try:
        rel = pdf_path.relative_to(library_root)
    except ValueError:
        rel = pdf_path
    for part in rel.parts:
        m = _TOPIC_DIR_RE.match(part)
        if m:
            return m.group(1).lower()
    return None


def title_from_filename(pdf_path: Path) -> str:
    """Best-effort title from the curated canonical filename.

    Names look like ``Author, X. - Title (year)``.  Everything after the
    first `` - `` is the title; if there's no separator, use the whole
    stem.  Fast (no PDF parsing), and the user's hand-curated titles are
    a strong classifier signal."""
    stem = pdf_path.stem
    if " - " in stem:
        return stem.split(" - ", 1)[1].strip()
    return stem.strip()


def _enrichment_text(pdf_path: Path) -> str:
    """Optional extra classifier signal from the sidecar (keywords +
    stored title), best-effort.  Never parses the PDF (too slow at
    library scale) and never raises."""
    try:
        from processing.identity import PaperIdentity
        ident = PaperIdentity.load(pdf_path)
        if ident.is_new():
            return ""
        bits = []
        kw = getattr(ident, "keywords", None)
        if kw:
            bits.append(kw if isinstance(kw, str) else " ".join(kw))
        return " ".join(bits)
    except Exception:
        return ""


def preview_paper(pdf_path: Path, library_root: Path, *, enrich: bool = False) -> TopicProposal:
    """Classify one paper and compare to its current location. Read-only."""
    from processing.publication_topic_router import resolve_topic

    title = title_from_filename(pdf_path)
    extra = _enrichment_text(pdf_path) if enrich else ""
    decision = resolve_topic(title, extra)

    current = current_topic_of(pdf_path, library_root)
    proposed = decision.topic_code            # set only when auto
    suggested = decision.suggested_code if decision.needs_review else None

    if current is not None:
        if proposed is not None:
            status = "agree" if proposed == current else "disagree"
        else:
            status = "recall_miss"
    else:
        if proposed is not None:
            status = "move"
        elif suggested is not None:
            status = "suggest"
        else:
            status = "none"

    return TopicProposal(
        path=str(pdf_path),
        current_topic=current,
        proposed_topic=proposed,
        suggested_topic=suggested,
        confidence=round(decision.confidence, 4),
        status=status,
    )


def preview_topic_filing(
    library_root: Path,
    *,
    scope: Optional[Path] = None,
    limit: Optional[int] = None,
    enrich: bool = False,
) -> tuple[PreviewSummary, list[TopicProposal]]:
    """Run the classifier across the library (or ``scope``) read-only.

    Returns ``(summary, proposals)``.  ``scope`` restricts the scan to a
    subtree (e.g. one status or one topic folder); ``limit`` caps the
    number of papers for a quick sample; ``enrich`` adds sidecar
    keywords to the classifier signal (slower).
    """
    from processing.identity import iter_pdfs

    root = scope or library_root
    summary = PreviewSummary()
    proposals: list[TopicProposal] = []
    if not root.exists():
        return summary, proposals

    for pdf in iter_pdfs(root):
        if limit is not None and summary.scanned >= limit:
            break
        prop = preview_paper(pdf, library_root, enrich=enrich)
        proposals.append(prop)
        summary.scanned += 1
        summary.counts[prop.status] = summary.counts.get(prop.status, 0) + 1
        if prop.current_topic is not None:
            summary.in_topic += 1
            if prop.status == "agree":
                summary.agree += 1
            elif prop.status == "disagree":
                summary.disagree += 1
            elif prop.status == "recall_miss":
                summary.recall_miss += 1
        else:
            if prop.status == "move":
                summary.proposed_moves += 1
            elif prop.status == "suggest":
                summary.proposed_suggestions += 1

    return summary, proposals
