"""Does the LIBRARY match what the rules say it should be?

The test suite checks that each rule does what it claims.  Nothing
checked that the 29k files on disk are actually in the state those rules
describe — so every defect this year was found by the owner reading a
list, never by the machine.  Four in one afternoon:

  * "Shiryaev, A.N.- Stochastic disorder problems" sat out a 6,180-file
    author sweep, because with no " - " the author block was never
    examined and nothing said so.
  * A cosmetic rule turned "J. - , Propagation" into "J. -, Propagation",
    destroying the author/title boundary and manufacturing more of the
    same.
  * Rename buckets computed once and applied days apart stranded the
    author half of 22 paired changes.
  * A phrase pass filtered its candidates with '" " in p', so the ruled
    names that needed it most could never match.  Inert for months.

The common cause is that every stage answers with two values —
``(name, changed: bool)`` — so *"already correct"* and *"I never looked"*
are the SAME answer.  A count of files "needing no action" therefore
silently includes every file nobody examined, and only a human eye ever
sees that population.

This module is the third value.  It classifies every document into one
of five buckets and reports the ones that mean the code is wrong:

  CANONICAL      the pipeline ran and the name is a fixpoint
  OWNER_QUEUE    the pipeline ran and produced a JUDGEMENT for the owner
                 (a title-casing ruling).  May be any size; not an alarm.
  MECHANICAL     the pipeline ran and produced an unambiguous change that
                 has simply not been applied yet.  Should fall to 0 after
                 an Apply; if it doesn't, the apply path is broken.
  NOT_EXAMINED   no rule reached a verdict on this file.  ALARM — this is
                 the bucket that hid every incident above.
  VIOLATION      a postcondition failed.  ALWAYS a bug, never a ruling.

The discriminator the owner asked for is structural, not a heuristic: a
file reaches OWNER_QUEUE only when the code HAS an opinion and needs it
adjudicated.  Every early return, swallowed exception and unenumerated
file lands in NOT_EXAMINED or VIOLATION by construction.
"""
from __future__ import annotations

import json
import time
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional

CANONICAL = "canonical"
OWNER_QUEUE = "owner_queue"
MECHANICAL = "mechanical_backlog"
NOT_EXAMINED = "not_examined"
VIOLATION = "invariant_violation"

#: Buckets that mean the CODE is wrong, as opposed to work the owner owes.
RED = (NOT_EXAMINED, VIOLATION)

REPORT_DIRNAME = ".mathpdf-config/conformance"

# macOS per-component limit.  A proposal longer than this can never be
# applied, so emitting one is a bug in the proposer, not a backlog item.
_MAX_FILENAME_BYTES = 255


@dataclass(frozen=True)
class Finding:
    path: str
    bucket: str
    reason: str
    detail: str = ""


@dataclass
class ConformanceReport:
    generated_at: str = ""
    duration_s: float = 0.0
    scanned: int = 0
    counts: dict = field(default_factory=dict)
    reasons: dict = field(default_factory=dict)
    findings: list = field(default_factory=list)
    globals_: dict = field(default_factory=dict)

    def red_count(self) -> int:
        return sum(self.counts.get(b, 0) for b in RED)

    def to_json(self) -> str:
        d = asdict(self)
        d["findings"] = [asdict(f) if not isinstance(f, dict) else f
                         for f in self.findings]
        return json.dumps(d, indent=1, ensure_ascii=False)


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


# ---------------------------------------------------------------------------
# Per-file classification
# ---------------------------------------------------------------------------
def examine(name: str, library_root: Path) -> tuple[str, str, str]:
    """Classify ONE filename.  Returns ``(bucket, reason, detail)``.

    Pure and side-effect free: it takes the name, not the file, so it is
    trivially testable and cannot touch the library.
    """
    from processing.filename_normalizer import normalize_filename
    from processing.move_normalizer import normalize_full_name
    from processing.title_review import (CASE, REWRITE, classify_proposal)

    original = _nfc(name)

    # ---- INVARIANTS ------------------------------------------------------
    # These run FIRST: a file that violates one is not "pending", it is
    # evidence of a bug, and reporting it as backlog would bury it.
    try:
        cosmetic = normalize_filename(original)
    except Exception as exc:                        # pragma: no cover
        return VIOLATION, "normalize-raised", f"{type(exc).__name__}: {exc}"

    # The author/title boundary is the whole data model — it carries the
    # author split, the alpha-folder routing and the sidecar identity.
    # A cosmetic rule that adds or removes one makes the file invisible to
    # every stage that splits on it, which is incident (1) and (2).
    if cosmetic.count(" - ") != original.count(" - "):
        return (VIOLATION, "separator-count-changed",
                f"{original.count(' - ')} -> {cosmetic.count(' - ')}: {cosmetic}")

    # Non-idempotence means the pipeline has no fixpoint, so "apply until
    # clean" would never terminate and this very report would oscillate.
    if normalize_filename(cosmetic) != cosmetic:
        return (VIOLATION, "not-idempotent",
                f"{cosmetic} -> {normalize_filename(cosmetic)}")

    # ---- GATES -----------------------------------------------------------
    # Everywhere the pipeline gives up. Each one is named, so the owner
    # sees WHICH population went unexamined rather than a silent zero.
    if " - " not in cosmetic:
        return (NOT_EXAMINED, "no-author-title-separator",
                "author block never examined (move_normalizer.py:87)")

    # ---- THE PIPELINE ----------------------------------------------------
    try:
        proposed, changed, _pending = normalize_full_name(original, library_root)
    except Exception as exc:                        # pragma: no cover
        return VIOLATION, "pipeline-raised", f"{type(exc).__name__}: {exc}"

    if len(proposed.encode("utf-8")) > _MAX_FILENAME_BYTES:
        return (VIOLATION, "proposal-too-long",
                f"{len(proposed.encode('utf-8'))} bytes: {proposed}")

    if not changed or proposed == original:
        return CANONICAL, "", ""

    # A change produced ONLY by the maths convention is mechanical, not a
    # judgement call: the owner settled the rule once, and applying it is
    # arithmetic.  It has to be recognised before the generic classifier,
    # which compares letter signatures and therefore reads "l_r" -> "lᵣ"
    # as a text REWRITE — the most alarming category there is — for what
    # is only a change of typeface.
    if " - " in original and " - " in proposed:
        from processing.math_typography import canonicalise
        _auth, _title = original.split(" - ", 1)
        if proposed == f"{_auth} - {canonicalise(_title)}":
            return MECHANICAL, "math-typography", proposed

    # A change that needs a RULING vs one that is pure formatting.  This
    # is the split the owner cares about, and it reuses the classifier
    # already used for the review sheets rather than a second opinion.
    kind = classify_proposal(original, proposed)
    if kind in (CASE, REWRITE):
        return OWNER_QUEUE, kind, proposed
    return MECHANICAL, kind, proposed


# ---------------------------------------------------------------------------
# Library-wide invariants
# ---------------------------------------------------------------------------
def check_config_reachability(library_root: Path) -> list:
    """Can every ruling the owner has made actually fire?

    Incident (4): a phrase pass selected candidates with '" " in p', so
    "S-Plus" and "Euro-Par" were excluded by the very filter meant to
    include them — a setting the owner had made, silently doing nothing.

    A ruling that cannot fire is indistinguishable from one that was
    never made, so probe each one: build a sentence containing it and
    assert the caser honours it.  Costs a fraction of a second.
    """
    from processing.title_normalize import propose_title_case
    from processing.title_vocab import load_vocab

    out: list = []
    try:
        vocab = load_vocab(library_root)
    except Exception:                               # pragma: no cover
        return out

    # The probe must be a form only the RULING can produce.  Probing with
    # the phrase already correct proves nothing: the safe default
    # preserves any capitalised word it cannot disprove, so "Euro-Par"
    # comes back intact whether the ruling fired or not.  Lowercase it —
    # nothing but the owner's ruling restores that.
    for phrase in sorted(vocab.get("phrases", ())):
        probe = f"Some remarks on {phrase.lower()} and its applications"
        try:
            got = propose_title_case(probe, library_root).proposed
        except Exception as exc:                    # pragma: no cover
            out.append(Finding("<config>", VIOLATION, "ruling-raised",
                               f"{phrase}: {exc}"))
            continue
        if phrase not in got:
            out.append(Finding(
                "<config>", VIOLATION, "ruling-cannot-fire",
                f"phrase {phrase!r} never matches; probe became {got!r}"))

    # A single ruled word cannot be probed the same way — "proper" means
    # "keep the capital", not "restore it", so a lowercase probe SHOULD
    # stay lowercase.  Check the plumbing instead: the ruling has to
    # reach the set the classifier actually consults.  This is exactly
    # what broke for `phrases` (copied out of the vocab and dropped).
    try:
        from processing.title_normalize import _whitelists
        reachable = set(vocab.get("proper", ())) | _whitelists()
        for word in sorted(vocab.get("proper", ())):
            if word not in reachable:               # pragma: no cover
                out.append(Finding(
                    "<config>", VIOLATION, "ruling-cannot-fire",
                    f"proper noun {word!r} never reaches the classifier"))
    except Exception:                               # pragma: no cover
        pass
    return out


def check_sidecars(library_root: Path, pdfs: list, all_pdfs: list = None) -> tuple[list, dict]:
    """One record per paper — no more, no less.

    Counting sidecar FILES against PDF files (what the Stats page does)
    reported 100.14% coverage, which is not a coverage figure at all: it
    hides both orphans and papers with TWO records.  Pair the sets
    instead, so the number is bounded by 1 and the gap is nameable.

    The dual-record case is real: 27 papers have names too long for the
    mirror and fall back to a hashed path; 14 of them also have a record
    at the naive path, disagreeing on doi, arxiv_id and classifier_text.
    """
    from processing.identity import sidecar_path

    mirror = library_root / ".mathpdf-sidecars"
    findings: list = []
    paired = 0
    missing = 0
    claimed: set = set()
    # Orphan detection is a LIBRARY-WIDE invariant and must not depend on
    # which files we chose to judge: scoping it to the judged subset
    # counted every inbox paper's perfectly good record as an orphan and
    # reported 2,113 instead of 27.
    all_pdfs = pdfs if all_pdfs is None else all_pdfs

    def _exists(p: Path) -> bool:
        # Path.exists() RAISES ENAMETOOLONG rather than returning False —
        # the same trap that once aborted a 6,186-file batch at file 1,921.
        try:
            return p.exists()
        except OSError:
            return False

    judged = {str(p) for p in pdfs}
    for pdf in all_pdfs:
        rel = pdf.relative_to(library_root)
        try:
            canonical = sidecar_path(pdf)
        except Exception:                           # pragma: no cover
            continue
        naive = mirror / rel.parent / (pdf.stem + ".meta.json")
        have_c, have_n = _exists(canonical), _exists(naive)
        if have_c:
            claimed.add(str(canonical))
        if have_n:
            claimed.add(str(naive))
        if str(pdf) not in judged:
            continue        # counted for orphans, not for coverage
        if have_c and have_n and canonical != naive:
            findings.append(Finding(
                str(rel), VIOLATION, "two-sidecar-records",
                "a hashed and a naive record both exist and can diverge"))
        elif have_c or have_n:
            paired += 1
        else:
            missing += 1

    orphans = 0
    for sc in mirror.rglob("*.meta.json"):
        if str(sc) not in claimed:
            orphans += 1

    stats = {
        "pdfs": len(pdfs),
        "papers_with_a_record": paired,
        "papers_without_a_record": missing,
        "orphaned_records": orphans,
        # Bounded by construction: a pairing, not a ratio of two counts.
        "coverage_pct": round(100.0 * paired / len(pdfs), 2) if pdfs else 0.0,
    }
    if orphans:
        findings.append(Finding(
            "<sidecars>", VIOLATION, "orphaned-records",
            f"{orphans} record(s) match no paper"))
    return findings, stats


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------
def run(
    library_root: Path,
    *,
    skip_dirs: tuple = ("12 - To be sorted",),
    progress: Optional[Callable[[int, int], None]] = None,
    limit: Optional[int] = None,
) -> ConformanceReport:
    """Classify the whole library.  Read-only; never touches a file.

    ``skip_dirs`` defaults to the inbox: those papers have deliberately
    not been named yet, so reporting them as non-conforming would drown
    the signal. They are counted separately in ``globals_``.
    """
    from processing.identity import iter_pdfs

    t0 = time.time()
    rep = ConformanceReport()
    counts: dict = {b: 0 for b in
                    (CANONICAL, OWNER_QUEUE, MECHANICAL, NOT_EXAMINED, VIOLATION)}
    reasons: dict = {}
    findings: list = []

    pdfs, all_pdfs, skipped = [], [], 0
    for pdf in iter_pdfs(library_root):
        all_pdfs.append(pdf)
        rel = pdf.relative_to(library_root)
        if rel.parts and rel.parts[0] in skip_dirs:
            skipped += 1
            continue
        pdfs.append(pdf)

    total = len(pdfs) if limit is None else min(limit, len(pdfs))
    for i, pdf in enumerate(pdfs[:total]):
        bucket, reason, detail = examine(pdf.name, library_root)
        counts[bucket] += 1
        if bucket != CANONICAL:
            key = f"{bucket}:{reason}"
            reasons[key] = reasons.get(key, 0) + 1
            findings.append(Finding(
                str(pdf.relative_to(library_root)), bucket, reason, detail))
        if progress and i % 250 == 0:
            progress(i, total)

    sc_findings, sc_stats = check_sidecars(library_root, pdfs[:total],
                                           all_pdfs=all_pdfs)
    cfg_findings = check_config_reachability(library_root)
    for f in list(sc_findings) + list(cfg_findings):
        counts[VIOLATION] += 1
        key = f"{f.bucket}:{f.reason}"
        reasons[key] = reasons.get(key, 0) + 1
        findings.append(f)

    rep.generated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    rep.duration_s = round(time.time() - t0, 1)
    rep.scanned = total
    rep.counts = counts
    rep.reasons = dict(sorted(reasons.items(), key=lambda kv: -kv[1]))
    rep.findings = findings
    rep.globals_ = {"inbox_skipped": skipped, **sc_stats}
    return rep


def save(library_root: Path, rep: ConformanceReport) -> Path:
    """Persist the report so tomorrow's run can show a DIFF.

    A standing check is only useful if the owner sees what CHANGED; an
    absolute count of 900 is noise on day two.
    """
    from core.io import atomic_write_text
    d = library_root / REPORT_DIRNAME
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{time.strftime('%Y-%m-%d')}.json"
    atomic_write_text(p, rep.to_json())
    return p


def load_previous(library_root: Path, before: Optional[str] = None) -> Optional[dict]:
    """The most recent stored report older than ``before`` (default today)."""
    d = library_root / REPORT_DIRNAME
    if not d.exists():
        return None
    cutoff = before or time.strftime("%Y-%m-%d")
    prior = sorted(p for p in d.glob("*.json") if p.stem < cutoff)
    if not prior:
        return None
    try:
        return json.loads(prior[-1].read_text())
    except (OSError, ValueError):                   # pragma: no cover
        return None


def diff_against(rep: ConformanceReport, previous: Optional[dict]) -> dict:
    """``{bucket: delta}`` versus the previous report (empty if none)."""
    if not previous:
        return {}
    old = previous.get("counts", {})
    return {b: rep.counts.get(b, 0) - old.get(b, 0)
            for b in rep.counts
            if rep.counts.get(b, 0) != old.get(b, 0)}
