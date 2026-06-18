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

# Top-level folders the pipeline actually routes into.  The real library
# also has non-routable special collections ("08 - Séminaires…",
# "09 - …", "10 - Math slides"), an ``archive`` tree, and the code repo
# ("Scripts") — none of which the classifier should touch.  A top-level
# folder is routable iff its name starts with a standard status prefix
# (01–06), a topic prefix (07a–07f), or the inbox ("12 ").
_ROUTABLE_TOP_RE = re.compile(r"^(0[1-6] |07[a-f]\b|12 )", re.IGNORECASE)


def is_routable(pdf_path: Path, library_root: Path) -> bool:
    """True if the paper sits under a routable top-level folder."""
    try:
        rel = pdf_path.relative_to(library_root)
    except ValueError:
        return False
    return bool(rel.parts and _ROUTABLE_TOP_RE.match(rel.parts[0]))


@dataclass
class TopicProposal:
    path: str
    current_topic: Optional[str]      # "07a".."07f" or None
    proposed_topic: Optional[str]     # auto-file code, or None
    suggested_topic: Optional[str]    # review-band best guess, or None
    confidence: float
    status: str                       # agree|disagree|move|suggest|recall_miss|none
    # Document-type layer (extras):
    doc_kind: str = "article"         # article|book|thesis (detected)
    doc_mismatch: bool = False        # detected book/thesis but in an article bucket
    # Sub-subtopic layer (extras): a finer folder suggestion within the
    # (current or proposed) topic, when that topic has sub-subtopics.
    subtopic: Optional[str] = None        # suggested sub-subtopic label
    current_subtopic: Optional[str] = None  # sub-subtopic it's already in

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
    doctype_mismatches: int = 0     # books/theses sitting in article folders
    subtopic_suggestions: int = 0   # topic-root papers a sub-subtopic fits

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
            "doctype_mismatches": self.doctype_mismatches,
            "subtopic_suggestions": self.subtopic_suggestions,
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


def _subtopics_for_code(code: str, library_root: Path) -> list:
    """Discover sub-subtopics for a topic code (folder lookup)."""
    from organization.system import OrganizationSystem
    from processing.subtopic_classifier import discover_subtopics
    topic_dir = OrganizationSystem(library_root, topic=code).router._topic_dir
    if topic_dir is None:
        return []
    return discover_subtopics(topic_dir)


def _current_subtopic_of(pdf_path: Path, library_root: Path) -> Optional[str]:
    """The sub-subtopic label the paper currently sits in, or None.

    Sub-subtopic folders are the SECOND ``07x - …`` component in the
    path (the first is the top-level topic)."""
    try:
        rel = pdf_path.relative_to(library_root)
    except ValueError:
        rel = pdf_path
    seen_topic = False
    for part in rel.parts:
        m = re.match(r"^07[a-f] - (.+)$", part, re.IGNORECASE)
        if m:
            if not seen_topic:
                seen_topic = True   # this is the top-level topic
            else:
                return m.group(1).strip()  # the sub-subtopic
    return None


def preview_paper(
    pdf_path: Path,
    library_root: Path,
    *,
    enrich: bool = False,
    with_extras: bool = True,
    subtopic_cache: Optional[dict] = None,
) -> TopicProposal:
    """Classify one paper and compare to its current location. Read-only.

    ``with_extras`` also computes the document-type mismatch and
    sub-subtopic suggestion (set False for a faster topic-only pass, e.g.
    inside the bulk-apply re-derivation)."""
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

    prop = TopicProposal(
        path=str(pdf_path),
        current_topic=current,
        proposed_topic=proposed,
        suggested_topic=suggested,
        confidence=round(decision.confidence, 4),
        status=status,
    )

    if with_extras:
        # Document-type: flag a book/thesis sitting in an article bucket
        # (01/02/03).  The article-direction is not flagged — we can't
        # tell a paper's publication status from the path.
        from processing.doctype_classifier import (
            classify_document_type, current_doc_bucket,
        )
        doc = classify_document_type(pdf_path.name)
        prop.doc_kind = doc.kind
        prop.doc_mismatch = (doc.folder is not None
                             and current_doc_bucket(pdf_path, library_root) == "article")

        # Sub-subtopic: only meaningful within a topic that has them.
        topic_for_sub = current or proposed
        if topic_for_sub:
            if subtopic_cache is None:
                subtopic_cache = {}
            subs = subtopic_cache.get(topic_for_sub)
            if subs is None:
                subs = _subtopics_for_code(topic_for_sub, library_root)
                subtopic_cache[topic_for_sub] = subs
            if subs:
                from processing.subtopic_classifier import classify_subtopic
                sd = classify_subtopic(title, extra, subs)
                if sd:
                    prop.subtopic = sd.label
                prop.current_subtopic = _current_subtopic_of(pdf_path, library_root)

    return prop


def preview_topic_filing(
    library_root: Path,
    *,
    scope: Optional[Path] = None,
    limit: Optional[int] = None,
    enrich: bool = False,
    with_extras: bool = True,
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

    # When scanning the whole library, skip non-routable special
    # collections (08/09/10, archive, the code repo).  When the caller
    # passes an explicit ``scope`` they've already chosen the subtree, so
    # honour it as-is.
    filter_routable = scope is None
    subtopic_cache: dict = {}

    for pdf in iter_pdfs(root):
        if filter_routable and not is_routable(pdf, library_root):
            continue
        if limit is not None and summary.scanned >= limit:
            break
        prop = preview_paper(pdf, library_root, enrich=enrich,
                             with_extras=with_extras, subtopic_cache=subtopic_cache)
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
        if prop.doc_mismatch:
            summary.doctype_mismatches += 1
        # A sub-subtopic suggestion that the paper isn't already in.
        if prop.subtopic and prop.subtopic != prop.current_subtopic:
            summary.subtopic_suggestions += 1

    return summary, proposals


def apply_topic_proposals(
    library_root: Path,
    *,
    statuses: tuple = ("move",),
    scope: Optional[Path] = None,
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> dict:
    """Apply the classifier's proposals to the library (the gated bulk
    file).  DESTRUCTIVE unless ``dry_run``.

    Safety design:
      * Re-derives proposals from a FRESH scan (never trusts stale UI
        state) so it acts on the library as it is right now.
      * Only ``statuses`` are eligible; the default is ``("move",)`` --
        confident new filings of un-topiced papers.  ``"disagree"`` (re-
        filing papers you placed by hand) is deliberately NOT a default.
      * Every move goes through ``file_into_topic`` -> ``logged_move``
        inside ONE undo transaction, so the whole batch reverses as a
        unit from the cockpit Activity tab.

    Returns a result dict with ``applied`` / ``failed`` lists and (when
    not a dry run) the ``tx_id`` for undo.
    """
    from processing.publication_topic_router import file_into_topic

    _, proposals = preview_topic_filing(library_root, scope=scope, with_extras=False)
    targets = [p for p in proposals
               if p.status in statuses and p.proposed_topic]
    if limit is not None:
        targets = targets[:limit]

    result: dict = {
        "selected": len(targets),
        "statuses": list(statuses),
        "dry_run": dry_run,
        "applied": [],
        "failed": [],
    }
    if dry_run:
        result["would_apply"] = [
            {"path": p.path, "topic": p.proposed_topic} for p in targets
        ]
        return result

    if not targets:
        return result

    from processing.undo_log import UndoLog
    # The undo log lives WITH the library being operated on (not the
    # global default), so the batch is reversible from that library's
    # Activity log / .operation_log.
    log = UndoLog(log_dir=library_root / ".operation_log")
    tx_id = log.begin_transaction(f"Bulk topic apply: {len(targets)} paper(s)")
    for p in targets:
        ok, msg = file_into_topic(
            Path(p.path), p.proposed_topic, library_root, undo_log=log,
        )
        entry = {"path": p.path, "topic": p.proposed_topic, "msg": msg}
        (result["applied"] if ok else result["failed"]).append(entry)
    log.commit()
    result["tx_id"] = tx_id
    return result
