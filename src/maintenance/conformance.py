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
TYPO = "suspected_typo"

#: Buckets that mean the CODE is wrong, as opposed to work the owner owes.
#
#: TYPO is deliberately NOT here.  A misspelling is work the owner owes,
#: exactly like OWNER_QUEUE; putting it in RED would flip is_all_clear()
#: permanently and file the spelling backlog under "the code is wrong",
#: which is the category error this module exists to prevent.
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
        return (sum(self.counts.get(b, 0) for b in RED)
                + self.globals_.get("library_wide_findings", 0))

    def is_all_clear(self) -> bool:
        """Green means "I examined things and they were fine".

        Never "there was nothing to examine": an empty library, an
        unreadable folder or a mistyped root all scanned 0 files and
        reported "Every file reached a verdict ✓" — the same sentence,
        and the same lie, as the cockpit banner this module was written
        to replace.
        """
        return self.scanned > 0 and self.red_count() == 0

    def to_json(self) -> str:
        d = asdict(self)
        d["findings"] = [asdict(f) if not isinstance(f, dict) else f
                         for f in self.findings]
        return json.dumps(d, indent=1, ensure_ascii=False)


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _prose_outside_maths(title: str) -> str:
    """Everything that is NOT mathematics.

    THIS DOCSTRING USED TO CLAIM INDEPENDENCE AND THE CLAIM IS NOW FALSE.

    It read: "``core.text_processing.math_detector`` is a different
    implementation from the converter under test, which is the point ...
    that conclusion does not depend on the converter agreeing with
    itself."  That was true when written.  Commit 20f039c unified the
    three rival ``find_math_regions`` into ``core.math_regions`` and
    pointed ``math_detector`` at it -- a good change on its own terms,
    and it silently converted this check into the converter agreeing
    with itself.  Nothing failed; the redundancy just stopped existing,
    which is the quiet way a safety net goes.

    So the honest statement of what this function now buys: it confirms
    the change is confined to the region the SAME detector calls
    mathematics.  That still catches a converter that rewrites prose it
    never claimed -- the failure mode actually seen, where a growth step
    swallowed ".pdf" -- but it can no longer catch a converter and a
    detector that are wrong together.

    Restoring real independence needs a second opinion that is not a
    rival detector (two detectors is the duplication that was just
    removed).  The shape that would work is a different QUESTION: strip
    every character that a typeface change could touch and compare the
    residue.  Not built -- recorded here so the gap is visible rather
    than implied by a docstring that no longer holds.
    """
    from core.text_processing.math_detector import find_math_regions
    try:
        regions = sorted(find_math_regions(title))
    except Exception:                               # pragma: no cover
        return title
    # The detector is ASYMMETRIC across the very change we are checking:
    # for "l_r" it returns the whole expression, but for "lᵣ" it returns
    # only the "ᵣ", leaving the base letter behind in the prose. Compared
    # naively, the prose then differs and a correct conversion is judged
    # unconfined. Extend each region left over its base so both spellings
    # of the same expression reduce to the same prose.
    from processing.title_normalize import _SCRIPT_GLYPHS
    grown = []
    for a, b in regions:
        while a > 0 and title[a] in _SCRIPT_GLYPHS and title[a - 1].isalnum():
            a -= 1
        grown.append((a, b))

    # MERGE overlaps, do not skip them.  The detector splits "εᵢ" into
    # two adjacent regions, ['ε', 'ᵢ']; growing the second one leftwards
    # made it overlap the first, and a plain "if a >= last" then dropped
    # it — leaving the subscript in the prose and judging a correct
    # conversion unconfined.
    merged: list = []
    for a, b in sorted(grown):
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))

    out, last = [], 0
    for a, b in merged:
        out.append(title[last:a])
        last = b
    out.append(title[last:])
    return "".join(out)


def _change_confined_to_maths(old_title: str, new_title: str) -> bool:
    """True when the ONLY difference lies inside mathematical notation."""
    if old_title == new_title:
        return False
    return _prose_outside_maths(old_title) == _prose_outside_maths(new_title)


# ---------------------------------------------------------------------------
# Per-file classification
# ---------------------------------------------------------------------------
def examine(name: str, library_root: Path,
            corpus=None) -> tuple[str, str, str]:
    """Classify ONE filename.  Returns ``(bucket, reason, detail)``.

    It takes the NAME, not the file, so it is trivially testable and
    never renames anything.  It is not, however, side-effect free: the
    caser it calls regenerates ``.mathpdf-config/title_corpus_stats.json``
    under ``library_root`` when that file is stale.  The docstring used
    to claim purity; it was wrong, and a probe writing into a throwaway
    library root is how that surfaced.

    ``corpus`` is the typo detector's document-frequency table, which
    cannot be derived from one filename.  :func:`run` builds it once for
    the whole sweep and passes it here.  Omitting it SKIPS the spelling
    check rather than guessing — a single-name caller has no corpus and
    would otherwise get a fabricated verdict from a corpus of one.
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
        proposed, changed, pending = normalize_full_name(original, library_root)
    except Exception as exc:                        # pragma: no cover
        return VIOLATION, "pipeline-raised", f"{type(exc).__name__}: {exc}"

    if len(proposed.encode("utf-8")) > _MAX_FILENAME_BYTES:
        return (VIOLATION, "proposal-too-long",
                f"{len(proposed.encode('utf-8'))} bytes: {proposed}")

    # The maths module's own refusal list.  It exists precisely to say
    # "I looked and would not touch this"; not consulting it was the same
    # mistake in miniature — 5 files with unbalanced brackets or nested
    # scripts were reported CANONICAL.
    try:
        from processing.math_typography import problems as _math_problems
        _mp = _math_problems(original.split(" - ", 1)[1]) if " - " in original else []
    except Exception:                               # pragma: no cover
        _mp = []
    if _mp:
        return NOT_EXAMINED, "maths-refused", "; ".join(_mp[:2])

    # ---- SPELLING --------------------------------------------------------
    # Placed here on purpose: after the invariants and the two gates (a
    # bug, and "there is no title to read", both outrank a spelling
    # opinion) but BEFORE the fixpoint return and the classifier.
    #
    # Measured on the real library, all 143 files carrying a suspected
    # typo are currently CANONICAL — the bucket the owner reads as
    # settled.  A check placed on any later branch would never see them.
    # And where a file has both a typo and a proposed rename, the typo
    # wins: the rename proposed for the Mortini line was
    # "Amererican mathematical Monthly", i.e. the casing engine building
    # on a misspelling.  Fix the spelling first, then re-examine.
    if corpus is not None:
        try:
            from maintenance.typos import Verdict, examine_title
            _typo = examine_title(original, corpus)
        except Exception as exc:                    # a genuine bug
            return VIOLATION, "typo-check-raised", f"{type(exc).__name__}: {exc}"
        if _typo.verdict is Verdict.UNKNOWN:
            # "I could not look" is NOT_EXAMINED, never CANONICAL.
            return (NOT_EXAMINED, "typo-oracle-unavailable",
                    _typo.unknown_reason)
        if _typo.verdict is Verdict.TYPO:
            return (TYPO, "suspected-typo",
                    "; ".join(f"{s.word} → {s.suggestion}"
                              for s in _typo.suspects[:4]))

    if not changed or proposed == original:
        # The NAME is a fixpoint — but the caser may have reached it by
        # preserving words it could not prove either way.  That is a real
        # open question and it must not hide inside "canonical", which
        # the owner reads as settled.  It is NOT the owner's review queue
        # either: the queue is for a proposed change, and there is none.
        # So: canonical, with the uncertainty reported alongside.
        return CANONICAL, ("rests-on-undecided-words" if pending else ""), \
            (", ".join(sorted(set(pending))[:6]) if pending else "")

    # A change produced ONLY by the maths convention is mechanical, not a
    # judgement call: the owner settled the rule once, and applying it is
    # arithmetic.  It has to be recognised before the generic classifier,
    # which compares letter signatures and therefore reads "l_r" -> "lᵣ"
    # as a text REWRITE — the most alarming category there is — for what
    # is only a change of typeface.
    #
    # Verified with an INDEPENDENT detector, not by re-running the
    # converter.  The first version asked `proposed == canonicalise(...)`,
    # which is a tautology: the pipeline had just applied canonicalise,
    # so the equality always held and ANY output that function produced —
    # including a wrong one — was stamped "unambiguous, auto-applyable".
    # A checker must not grade its subject with the subject's own answer.
    if " - " in original and " - " in proposed:
        if _change_confined_to_maths(original.split(" - ", 1)[1],
                                     proposed.split(" - ", 1)[1]):
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
    # load_vocab degrades a corrupt or missing file to an EMPTY vocabulary
    # and never raises, so the loop below then iterated zero times and
    # returned [] — the same answer as "all fifteen rulings work". Read
    # the file independently and compare, so "no rulings survived the
    # load" cannot masquerade as "no rulings are broken".
    from processing.title_vocab import vocab_path
    vp = vocab_path(library_root)
    raw: dict = {}
    if vp.exists():
        try:
            raw = json.loads(vp.read_text())
        except (OSError, ValueError) as exc:
            out.append(Finding("<config>", VIOLATION, "vocabulary-unreadable",
                               f"{vp.name}: {exc}"))
            return out
    try:
        vocab = load_vocab(library_root)
    except Exception:                               # pragma: no cover
        return out
    for _k in ("phrases", "proper", "common"):
        _want, _got = len(raw.get(_k, ())), len(vocab.get(_k, ()))
        if _want != _got:
            out.append(Finding(
                "<config>", VIOLATION, "rulings-lost-on-load",
                f"{_k}: {_want} in the file, {_got} reached the classifier"))

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

    # A single ruled word cannot be probed behaviourally — "proper" means
    # "keep the capital", not "restore it", so a lowercase probe SHOULD
    # stay lowercase and tells us nothing.
    #
    # The loop that used to sit here was dead by construction: it built
    # `reachable = set(vocab['proper']) | _whitelists()` and then asked
    # whether each member of vocab['proper'] was in it. Always true, in
    # 0 of 2000 random vocabularies false. It looked like a check and
    # was a tautology. The count comparison above covers the real
    # failure — a ruling that does not survive the load — so this is
    # deleted rather than replaced with another one.
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
    from processing.identity import _NON_LIBRARY_DIRS
    for sc in mirror.rglob("*.meta.json"):
        # The mirror shadows .trash too, and a retired paper's record is
        # unclaimable BY CONSTRUCTION — no PDF will ever match it.  Not
        # excluding it made 133 of the 159 "orphans" the owner's own
        # deliberate deletions, a red number that can never reach zero
        # and grows every time they throw something away.
        if any(part in _NON_LIBRARY_DIRS
               for part in sc.relative_to(mirror).parts):
            continue
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
                    (CANONICAL, OWNER_QUEUE, MECHANICAL, TYPO,
                     NOT_EXAMINED, VIOLATION)}
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

    # One corpus for the whole sweep.  Per-file construction would be
    # O(n^2) over 27,000 names; and a corpus built from ONE name has no
    # frequent words at all, so it would silently declare every file
    # clean -- the failure this detector was written to end.
    corpus = None
    oracle_fp = ""
    try:
        from maintenance.typos import (build_corpus_stats, oracle_fingerprint,
                                       self_check)
        self_check()          # raises if the dictionaries are unusable
        from processing.spelling_vocab import accepted_words
        corpus = build_corpus_stats((p.name for p in pdfs),
                                    ruled_correct=accepted_words(library_root))
        oracle_fp = oracle_fingerprint()
    except Exception as exc:
        # Record WHY rather than quietly sweeping without a spell check.
        reasons[f"{NOT_EXAMINED}:typo-oracle-unavailable"] = 1
        findings.append(Finding("(library)", NOT_EXAMINED,
                                "typo-oracle-unavailable",
                                f"{type(exc).__name__}: {exc}"))

    for i, pdf in enumerate(pdfs[:total]):
        bucket, reason, detail = examine(pdf.name, library_root, corpus)
        counts[bucket] += 1
        # "or reason": examine() returns (CANONICAL, "rests-on-undecided-words",
        # words) precisely SO the uncertainty travels with the verdict, and
        # this line used to drop both the reason and the finding for every
        # canonical row -- 1,613 files (5.9%), 1,450 distinct words, counted
        # as settled.  The string is produced in one place and was consumed
        # in none.
        if bucket != CANONICAL or reason:
            key = f"{bucket}:{reason}"
            reasons[key] = reasons.get(key, 0) + 1
            findings.append(Finding(
                str(pdf.relative_to(library_root)), bucket, reason, detail))
        if progress and i % 250 == 0:
            progress(i, total)

    # Library-wide findings are NOT files.  Adding them into the per-file
    # counters made sum(counts) exceed `scanned` by 15 — a file-shaped
    # metric quietly carrying non-file entries, which is the sort of
    # arithmetic that makes a whole report untrustworthy.  Keep them
    # separate and report both.
    sc_findings, sc_stats = check_sidecars(library_root, pdfs[:total],
                                           all_pdfs=all_pdfs)
    cfg_findings = check_config_reachability(library_root)
    library_wide = 0
    for f in list(sc_findings) + list(cfg_findings):
        library_wide += 1
        key = f"{f.bucket}:{f.reason}"
        reasons[key] = reasons.get(key, 0) + 1
        findings.append(f)

    rep.generated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    rep.duration_s = round(time.time() - t0, 1)
    rep.scanned = total
    rep.counts = counts
    rep.reasons = dict(sorted(reasons.items(), key=lambda kv: -kv[1]))
    rep.findings = findings
    rep.globals_ = {"typo_oracle": oracle_fp,
                    "inbox_skipped": skipped,
                    "library_wide_findings": library_wide,
                    "documents_out_of_scope": _out_of_scope(library_root),
                    **sc_stats}
    return rep


def _out_of_scope(library_root: Path) -> int:
    """Documents the check cannot speak for at all.

    ``iter_pdfs`` globs ``*.pdf``, so 188 .djvu and 9 .epub files are in
    no bucket and no skip count.  Reporting five buckets that sum to the
    PDF population, and saying nothing else, invites the reader to
    conclude the library is accounted for.  It is not — and that is this
    module's own disease.
    """
    from processing.identity import _NON_LIBRARY_DIRS
    n = 0
    try:
        for p in library_root.rglob("*"):
            if not p.is_file() or p.suffix.lower() == ".pdf":
                continue
            rel = p.relative_to(library_root)
            if any(x in _NON_LIBRARY_DIRS or x.startswith(".") for x in rel.parts):
                continue
            if p.suffix.lower() in (".djvu", ".epub", ".ps", ".dvi", ".chm") \
                    or not p.suffix:
                n += 1
    except OSError:                                 # pragma: no cover
        return -1
    return n


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
