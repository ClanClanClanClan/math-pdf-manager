"""Decompose a library filename into the parts it actually has.

The library convention is ``Authors - Title.pdf``, and for 23,271 of the
27,160 named PDFs that is exactly what the name is.  For the other 3,889 it
is not: the first segment holds a series name, a volume number, an expose
number or a page range, and splitting on the first ``" - "`` therefore
returns a WRONG author and often a wrong title.

That mattered quietly for a long time.  It corrupts

  * the ground truth used to score metadata extraction, and
  * the training and eval corpus under ``ml/pdf-meta-llm``.

One eval sample in ``results/eval_llm_100_v2.json`` has ``gt_authors ==
["08"]`` -- a series number -- and the model scored 1.0 for reproducing it.
Nine of its hundred samples have the author block leaked into the "title";
they score 0.44 where the clean ninety-one score 0.89.

THE FILENAMES ARE NOT WRONG.  The owner deliberately puts the series first
so that volumes sort together, and nothing here proposes renaming anything.
This module only works out what the parts of a name are.

Three-state, like every other check in this project: a decomposition is
RELIABLE or it is UNKNOWN-with-a-reason.  ``authors == ""`` on a RELIABLE
result is a positive finding -- a bound volume of *Comptes rendus* has no
author, it has an academy -- and is not the same thing as "I could not
tell".  "I did not look" and "it is fine" must not be the same return
value.
"""
from __future__ import annotations

import re
import unicodedata
import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from functools import lru_cache
from typing import Callable, Iterable, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "Kind", "Role", "Reliability", "Decomposition", "decompose",
    "looks_like_author_block", "looks_like_western_author_list",
    "looks_like_malformed_author_block", "repair_author_block", "AUTHOR_BLOCK_RE",
]


class Kind(str, Enum):
    ARTICLE = "article"
    VOLUME = "volume"
    PROCEEDINGS = "proceedings"
    UNKNOWN = "unknown"


class Role(str, Enum):
    """Whether the name block holds authors, editors, or something unsettled."""

    AUTHOR = "author"
    EDITOR = "editor"
    UNCERTAIN = "uncertain"
    NONE = "none"


class Reliability(str, Enum):
    RELIABLE = "reliable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Decomposition:
    """What a filename is made of.

    ``authors`` is the canonical block (``"Meyer, P.-A."``) or ``""`` when the
    work genuinely has none.  ``series`` and ``ordinal`` are ``""`` when
    absent.  ``rule`` names the rule that fired, so a surprising answer can be
    traced without re-deriving it.
    """

    stem: str
    directory: str = ""
    series: str = ""
    ordinal: str = ""
    authors: str = ""
    #: What the people in ``authors`` DID.
    #:
    #: A filename does not say.  Every Messenger of mathematics title page
    #: reads "EDITED BY" above exactly the names its filename carries, so
    #: calling them authors attributes a whole journal volume to its four
    #: editors -- but "Cauchy, A.-L. - Oeuvres completes d'Augustin Cauchy,
    #: tome I" has the same shape and Cauchy wrote it.  Guessing either way
    #: is wrong for a few hundred files, so the uncertainty is recorded
    #: instead of resolved, and a consumer that cares can filter on it.
    name_role: "Role" = None  # type: ignore[assignment]
    title: str = ""
    kind: Kind = Kind.UNKNOWN
    reliability: Reliability = Reliability.UNKNOWN
    reason: str = ""
    rule: str = ""
    #: For a result that came from the override table: what settled it.
    #: A reason explains an abstention; evidence justifies an answer, and
    #: conflating the two is how "we checked" and "we assumed" become the
    #: same field.
    evidence: str = ""

    def __post_init__(self) -> None:
        if self.name_role is None:
            object.__setattr__(
                self, "name_role", Role.AUTHOR if self.authors else Role.NONE)
        # The invariant that keeps the three states from collapsing into two.
        if self.reliability is Reliability.UNKNOWN and not self.reason:
            raise ValueError(
                f"UNKNOWN decomposition of {self.stem!r} carries no reason; "
                "an unexplained abstention is indistinguishable from a clean "
                "result, which is the failure this class exists to prevent"
            )
        if self.reliability is Reliability.RELIABLE and self.reason:
            raise ValueError(
                f"RELIABLE decomposition of {self.stem!r} carries a reason "
                f"({self.reason!r}); reasons belong only to abstentions"
            )
        if self.reliability is Reliability.RELIABLE and not self.title:
            raise ValueError(
                f"RELIABLE decomposition of {self.stem!r} has an empty title"
            )

    @property
    def is_reliable(self) -> bool:
        return self.reliability is Reliability.RELIABLE


# ----------------------------------------------------------------------
# Primitive: is this segment an author block?
# ----------------------------------------------------------------------
#
# Measured against the whole library: 23,271 first segments that ARE author
# blocks and the 23,271 titles that follow them.
#
#     recall on author blocks     99.87%
#     false positives on titles    0.00%   (0 of 23,271)
#
# The asymmetry is deliberate.  Accepting a title as an author block invents
# an author, which is the corruption being removed here; failing to recognise
# an author block only produces an honest abstention.  So the pattern is
# tight, and the residue is reported rather than absorbed.
#
# Of the 329 first segments it rejects, 149 are not author blocks at all (a
# volume of "Table des comptes rendus...", correctly refused) and the rest are
# genuine typographic defects in the filenames themselves -- "Zhang. Y." with
# a period where the comma belongs, "van Handel R." with no comma at all,
# "Caffarelli, LA.." with a doubled period.  Those want fixing in the library,
# not accommodating in the regex.

def _uppercase_class() -> str:
    """Every uppercase letter in Latin, Greek and Cyrillic, from Unicode.

    Hand-enumerating this was a mistake and a measurable one: the first
    version spelled out the accented capitals it could think of and missed
    S-cedilla in "Sengul, B.", L-caron in "Banas, L.", and a dozen more, so
    219 perfectly ordinary author blocks were refused.  Asking unicodedata
    cannot forget a letter.
    """
    ranges = ((0x41, 0x24F), (0x370, 0x3FF), (0x400, 0x52F), (0x1E00, 0x1EFF))
    chars = [chr(c) for lo, hi in ranges for c in range(lo, hi + 1)
             if unicodedata.category(chr(c)) == "Lu"]
    return "".join(re.escape(c) for c in chars)


_UPPER = _uppercase_class()

#: Nobiliary and patronymic particles, which are lowercase by convention and
#: may sit anywhere inside a surname: "Chaudru de Raynal", "van Handel",
#: "da Prato", "ben Tahar", "uz Zaman", "in 't Hout".
_PARTICLE = (
    r"(?:d[aeiou]|dai|dal|dalla|dalle|de[lnrs]?|dela|della|delle|dei|degli|"
    r"van|von|der|den|te[nr]|dos|das|du|la|las|le|les|los|el|al|ibn|ben|bin|"
    r"abd|abu|ould|op|zur?|af|av|mac|mc|st|y|uz|in|aus|of|ap|ver|bel|bin|"
    r"dello|degli|dell[oae]?|i|['’]t|"
    r"(?:d|l|n|o|t|dell|dall|nell|sull|all)['’])"
)
# A word inside a surname is a capitalised token, an elided-article token
# ("d'Agostini", "t'Hout" in "in 't Hout"), or one of the closed set of
# lowercase particles.
_WORD = (rf"(?:[{_UPPER}][^\s,()]*"
         rf"|(?:d|l|n|o|t|dell|dall|nell|sull|all)[’'][{_UPPER}][^\s,()]*"
         rf"|{_PARTICLE}(?=[\s'’]|$))")
#: A surname may carry a parenthetical -- "Seifried (nee Muller), S." is one
#: person, and dropping her married name would be a different author.
_PAREN = r"(?:\([^()]*\))"
_SURNAME = rf"(?:{_WORD}(?:[-\s'’]*(?:{_WORD}|{_PAREN}))*)"
#: Initials are not always one letter.  Cyrillic transliterations need two or
#: three -- "Kabanov, Yu. A.", "Zhikov, V. V.", "Khasminskii, R. Z." -- and
#: hyphenated given names keep the hyphen: "Bouchaud, J.-P.".
_INITIAL = rf"(?:[{_UPPER}](?:[a-zà-ÿ]{{1,2}})?\.)"
_INITIALS = rf"(?:{_INITIAL}(?:[-\s]*{_INITIAL})*)"
#: "Harvey, F.R., Lawson, Jr., H.B." -- the suffix is its own comma-separated
#: part, which is why it has to be modelled rather than stripped.
_SUFFIX = r"(?:Jr|Sr|II|III|IV)\.?"
_ONE_AUTHOR = rf"{_SURNAME},\s*(?:{_SUFFIX},\s*)?{_INITIALS}"

AUTHOR_BLOCK_RE = re.compile(
    rf"^{_ONE_AUTHOR}(?:,\s*{_ONE_AUTHOR})*(?:,?\s*et\s+al\.?)?,?$"
)


def _nfc(text: str) -> str:
    """Normalise to NFC.

    macOS hands back filenames NFD-DECOMPOSED, so "Asterisque" with its acute
    accent arrives as "e" + U+0301 and any pattern written with a precomposed
    character silently fails to match.  That is not hypothetical: 335
    Asterisque files were misclassified for exactly this reason before this
    call existed.
    """
    return unicodedata.normalize("NFC", text or "")


def looks_like_author_block(segment: str) -> bool:
    """Is this segment a canonical ``Surname, I. N.`` author block?"""
    return bool(AUTHOR_BLOCK_RE.match(_nfc(segment).strip()))


#: A second, weaker recogniser for author lists written in Western order --
#: "Diego Compagna and Stefanie Steinhart".  The library's canonical form is
#: "Surname, I.", but a few hundred names were filed before that convention
#: settled and the people in them are still authors.  Deliberately stricter
#: than it looks: every word must be capitalised, which is what keeps ordinary
#: sentence-case titles out.
_WESTERN_NAME = rf"(?:(?:{_PARTICLE}\s+)*[{_UPPER}][^\s,]*(?:[-\s][{_UPPER}][^\s,]*){{0,3}})"
_WESTERN_LIST_RE = re.compile(
    rf"^{_WESTERN_NAME}(?:\s*,\s*{_WESTERN_NAME})*"
    rf"(?:\s*(?:,\s*)?(?:and|&|et)\s+{_WESTERN_NAME})?$"
)


def looks_like_western_author_list(segment: str) -> bool:
    """``"Diego Compagna and Stefanie Steinhart"`` -- authors, non-canonical."""
    seg = _nfc(segment).strip()
    if not seg or looks_like_author_block(seg):
        return False
    # A single capitalised word is a surname with no given name, which is far
    # more often a series word ("Asterisque") than an author.
    if " " not in seg:
        return False
    # A block that repairs into a canonical one is a mispunctuated canonical
    # block, NOT a deliberate Western-order list, and the two must not both
    # claim it -- otherwise which label a block gets depends on the order the
    # caller asks, which is exactly the kind of accident that leaves a
    # plausible wrong answer in place.
    if looks_like_malformed_author_block(seg):
        return False
    return bool(_WESTERN_LIST_RE.match(seg))


#: A block that was TRYING to be canonical and missed -- "Almgren, R, Chriss,
#: N. A." (no period after R), "Zhang. Y." (period where the comma belongs),
#: "Caffarelli, LA.." (doubled period), "van Handel R." (no comma at all).
#:
#: This class exists because without it those blocks fell through to the
#: Western-order recogniser, which happily matched them and reported
#: author_form="western".  The decomposition was right and the provenance was
#: a lie -- and the provenance is what the cockpit shows a human deciding
#: whether to trust the row.  154 blocks were being mislabelled.
#:
#: The test is NOT a pattern for "looks a bit broken".  That was the first
#: attempt and it matched 134 real titles, because ", I," in "Exponential
#: functionals of Brownian motion, I, probability laws" looks exactly like an
#: initial.  Instead: apply a short list of single-character repairs and ask
#: whether the result is canonical.  A title does not repair into an author
#: block, so the false-positive rate falls out of the construction rather than
#: having to be tuned.
_REPAIRS = (
    # An initial that lost its period, before a comma or at the end.
    (re.compile(rf"([{_UPPER}])(,|$)"), r"\1.\2"),
    # A period where the comma between two authors belongs: "Zhang. Y.".
    (re.compile(rf"([a-zà-ÿ])\.\s+([{_UPPER}]\.)"), r"\1, \2"),
    # A doubled period: "Caffarelli, LA..".
    (re.compile(r"\.\.+"), "."),
    # No separator at all between two authors: "Reitich, F. Soner, H. M.".
    (re.compile(rf"([{_UPPER}]\.)\s+([{_UPPER}][a-zà-ÿ])"), r"\1, \2"),
    # A comma before a hyphenated initial: "Bouchaud, J, -P.".
    (re.compile(rf"([{_UPPER}]),\s*-([{_UPPER}])"), r"\1.-\2"),
    # A missing comma before the initials, at the end of the block
    # ("van Handel R.") or in the middle of a list ("Capponi, A., Jia R.,
    # Yu, S.").
    (re.compile(rf"([a-zà-ÿ])\s+([{_UPPER}]\.(?:\s*[{_UPPER}]\.)*)(,|$)"), r"\1, \2\3"),
    # Initials run together: "Caffarelli, LA." for "Caffarelli, L. A.".
    (re.compile(rf"(,\s*)([{_UPPER}])([{_UPPER}])\."), r"\1\2. \3."),
    # Initials with no space: "Kedlaya, K.S." -- legal in the library, but it
    # appears here because some blocks need it BEFORE another repair applies.
    (re.compile(rf"([{_UPPER}]\.)([{_UPPER}]\.)"), r"\1 \2"),
)

#: How many distinct repairs may be applied before the block stops being a
#: typo and starts being something else.  Three is enough for every real case
#: in the library and small enough that a title cannot reach canonical form.
_MAX_REPAIRS = 3


def looks_like_malformed_author_block(segment: str) -> bool:
    """Canonical in intent, defective in punctuation.

    True when at most ``_MAX_REPAIRS`` of the repairs above turn ``segment``
    into something ``AUTHOR_BLOCK_RE`` accepts.
    """
    seg = _nfc(segment).strip()
    if not seg or looks_like_author_block(seg):
        return False
    # A canonical block always carries at least one comma (surname from
    # initials) or one period (the initials themselves).  A segment with
    # NEITHER is not a mispunctuated author block, it is a different kind of
    # string -- and without this guard the book title "Analysis I" repaired
    # into "Analysis, I." and was reported as an author.  One false positive
    # in 23,271 titles, but it is the exact shape this class must not have.
    if "," not in seg and "." not in seg:
        return False
    frontier = {seg}
    for _ in range(_MAX_REPAIRS):
        nxt = set()
        for candidate in frontier:
            for pattern, replacement in _REPAIRS:
                repaired = pattern.sub(replacement, candidate)
                if repaired == candidate:
                    continue
                if looks_like_author_block(repaired):
                    return True
                nxt.add(repaired)
        if not nxt:
            return False
        frontier = nxt
    return False


def repair_author_block(segment: str) -> Optional[str]:
    """The canonical form a malformed block repairs into, or ``None``.

    Separate from the predicate on purpose: knowing a name is broken and
    knowing what it should say are different claims, and the cockpit needs
    the second one to offer a fix.
    """
    seg = _nfc(segment).strip()
    if looks_like_author_block(seg):
        return seg
    frontier = {seg}
    for _ in range(_MAX_REPAIRS):
        nxt = set()
        for candidate in sorted(frontier):
            for pattern, replacement in _REPAIRS:
                repaired = pattern.sub(replacement, candidate)
                if repaired == candidate:
                    continue
                if looks_like_author_block(repaired):
                    return repaired
                nxt.add(repaired)
        if not nxt:
            return None
        frontier = nxt
    return None


# ----------------------------------------------------------------------
# Collection knowledge
# ----------------------------------------------------------------------
#
# Two kinds of collection, and the distinction is the whole design:
#
#   AUTHOR-FIRST folders (01, 02, 03, 06, 07*, 09, 10) hold individual papers,
#   and the convention there guarantees the first segment is the author block.
#   A first segment that is not canonical is a MALFORMED AUTHOR, not a series.
#
#   SERIES folders (05, 08) hold bound volumes and numbered series, where the
#   first segment is routinely a collection name or an ordinal.
#
# Gating on the directory is what makes this tractable, but it must not be the
# only evidence: a new arrival has no folder yet, so every rule below also
# tests the NAME.  The directory raises or lowers confidence; it never decides
# alone.

#: Series whose files are BOUND VOLUMES: the entire stem is the title, and
#: the work has no author.  A volume of *Comptes rendus* was written by the
#: Academy, not by a person, and its filename says so.  These are matched at
#: the START of the stem, before any " - " splitting, because their own
#: designations contain " - " ("..., serie I - Mathematique, no12 - ...").
_WHOLE_VOLUME_PREFIXES = (
    r"Comptes\s+rendus\b",
    r"Table\s+des\s+comptes\s+rendus\b",
    r"Tables?\s+g[ée]n[ée]rales?\b",
    r"Histoire\s+de\s+l['’]acad[ée]mie\b",
    r"M[ée]moires?\s+de\s+l['’]acad[ée]mie\b",
    r"M[ée]moires?\s+pr[ée]sent[ée]s\s+par\s+divers\s+savants\b",
    r"M[ée]moires?\s+de\s+math[ée]matique\b",
    r"Suite\s+des\s+m[ée]moires\b",
    r"Proc[èe]s[-\s]verbaux\b",
    r"S[ée]minaire\s+Bourbaki,\s*volume\b",
    r"The\s+science\s+reports\s+of\s+the\s+T[ōo]hoku\b",
    r"The\s+Oxford,\s+Cambridge,?\s+and\s+Dublin\s+messenger\b",
    r"Annales\s+de\s+la\s+facult[ée]\b",
)
_WHOLE_VOLUME_RE = re.compile("|".join(_WHOLE_VOLUME_PREFIXES), re.I)

#: Numbered series where the stem is "<Series> <number> - <rest>".  The number
#: may be a range with an en dash ("367-368"), zero-padded ("086"), or carry a
#: supplement letter ("S131").
_SERIES_PREFIXES = (
    (r"Ast[ée]risque", "Astérisque"),
    (r"M[ée]moires\s+de\s+la\s+S\.?M\.?F\.?[^-]*", "Mémoires de la S.M.F."),
    (r"Panoramas\s+et\s+synth[èe]ses", "Panoramas et synthèses"),
    (r"Documents\s+math[ée]matiques", "Documents mathématiques"),
    (r"Cours\s+sp[ée]cialis[ée]s", "Cours spécialisés"),
)
_SERIES_RE = re.compile(
    r"^(?P<series>(?:" + "|".join(p for p, _ in _SERIES_PREFIXES) + r"))"
    # A volume number can be a RANGE, and the range can have more than two
    # parts: "Asterisque 198-199-200" is one book.  A two-part pattern left
    # "200 - Journees arithmetiques..." behind and reported no author.
    r"\s*(?P<ordinal>[A-Z]?\d+(?:\s*[-–—]\s*\d+)*)?"
    r"\s*[-–]\s+(?P<rest>.+)$",
    re.I,
)

#: A leading ordinal glued on with a hyphen and no spaces.
#:
#: For the Seminaire de probabilites this is the article's FIRST PAGE in the
#: bound volume, not an expose number -- volume 12 holds 62 articles numbered
#: 1, 20, 22, 35, 47, 114 ... 740, and the gaps are article lengths.  The
#: document says so itself: "134-Lepingle, D. - Une inegalite de martingales"
#: opens with "Seminaire de probabilites (Strasbourg), tome 12 (1978),
#: p. 134-137."  (I had this wrong and called it an expose number; a subagent
#: caught it and the PDF settled it.)  For the Messenger of mathematics the
#: same slot holds the volume number.
#:
#: The ordinal can have TWO parts.  "740-1-Dellacherie, C. - Correction ..."
#: is the second item beginning on page 740 -- an erratum sharing a page with
#: the article before it -- and "0-1-Murmann, M. G. - Erratum ..." is the same
#: shape.  A one-part pattern took "740" and left "1-Dellacherie, C." in the
#: author slot, which is not an author block, so 34 Seminaire articles fell
#: through to "this volume has no author" -- inventing an absence exactly the
#: way the naive split invents a presence.
#:
#: Candidates are tried LONGEST FIRST and each is accepted only if what
#: follows really is an author block, so a hyphenated title cannot be mistaken
#: for an ordinal.
def _glued_ordinal_candidates(stem: str):
    """Every ``(ordinal, rest)`` split of a glued numeric prefix, longest first."""
    out = []
    # The two parts join with a hyphen ("740-1") or a period ("032.2").
    m = re.match(r"^(\d{1,4})(?:([.\-])(\d{1,2}))?([a-z]?)-(\S.*)$", stem)
    if not m:
        return out
    first, joiner, second, suffix, _ = m.groups()
    if second is not None:
        long_ordinal = f"{first}{joiner}{second}{suffix}"
        out.append((long_ordinal, stem[len(long_ordinal) + 1:]))
    if joiner != ".":
        out.append((f"{first}{suffix}", stem[len(f"{first}{suffix}") + 1:]))
    return [(o, r) for o, r in out if r]

#: A leading ordinal or page range as its own segment: "001 - Bretagnolle...",
#: "279-298 - Bourgain, J. - ...".
_SPACED_ORDINAL_RE = re.compile(
    r"^(?P<ordinal>\d{1,4}[a-z]?(?:\s*[-–—]\s*\d{1,4})?)\s+[-–]\s+(?P<rest>.+)$"
)

#: Folders whose convention guarantees an author block first.
_AUTHOR_FIRST_DIR_RE = re.compile(r"^(0[123679]|07[a-f])\b")
_SERIES_DIR_RE = re.compile(r"^(05|08)\b")

#: A title that designates a whole issue or volume of a journal -- "Messenger
#: of mathematics, volume XVII, May, 1887-April, 1888".  When a name block
#: sits in front of one of these, those people EDITED the volume; they did
#: not write it.
#:
#: The designation must FOLLOW A COMMA or open the title, and be followed by
#: whitespace and a complete numeral.  The first version was
#: ``\b(?:volume|tome|vol\.)\s*[IVXLCDM0-9]`` with re.I, which made
#: "The role of volume in order book dynamics" a journal volume -- the "i" of
#: "in" is a Roman numeral once you ignore case -- and turned its three
#: authors into editors.
#:
#: Measured on the library's 23,271 titles, the three changes contribute
#: unequally: 297 raw matches originally, 264 with the anchor alone, 283 with
#: ``\s+`` and a whole-numeral alone, 285 with case-sensitivity alone, 258
#: with all three.  So the ANCHOR did most of the work, and the case fix is
#: redundant once it is in place: loosening case in the final pattern changes
#: the verdict on exactly ZERO library filenames.  It stays as defence in
#: depth, and a mutation that reverts it is equivalent -- recorded here so
#: nobody has to rediscover that it is untestable.
_JOURNAL_VOLUME_TITLE_RE = re.compile(
    r"(?:^|,)\s*(?:[Vv]olume|[Tt]ome|[Vv]ol\.)\s+(?:[IVXLCDM]{1,7}|\d{1,4})\b")

#: Series where the name block was CHECKED against the documents and is
#: editors.  Every Messenger of mathematics title page examined reads
#: "EDITED BY" above exactly the names in the filename; the ICM proceedings
#: name their volume editors the same way.  Anything not on this list gets
#: Role.UNCERTAIN, not a guess.
_KNOWN_EDITED_SERIES_RE = re.compile(
    r"\b(?:Messenger\s+of\s+mathematics"
    r"|Proceedings\s+of\s+the\s+international\s+congress\s+of\s+mathematicians"
    r"|Handbook\s+of\b"
    r"|Quantum\s+probability\s+communications"
    r"|The\s+new\s+Palgrave\s+dictionary)\b", re.I)

#: A title that announces a COLLECTIVE work -- a colloquium, a seminar, a set
#: of proceedings.  Only for these does the absence of a name block establish
#: that the work has no author.
#:
#: The distinction was a subagent's finding and it matters: of eight
#: authorless-looking Asterisque volumes it opened, TWO were single works
#: whose authors appear only on the title page.  Reporting authors="" for
#: those asserts the monograph has no author, which is a different and false
#: claim from "the filename does not say".
_COLLECTIVE_TITLE_RE = re.compile(
    r"\b(?:s[ée]minaire|colloque|colloquium|journ[ée]es|congr[èe]s|"
    r"proceedings|actes|conference|expos[ée]s|table\s+g[ée]n[ée]rale|"
    r"pages\s+pr[ée]liminaires|m[ée]langes|volume|tome|ann[ée]e|"
    r"in\s+memoriam|hommage|en\s+l['’]honneur|festschrift)\b", re.I)

#: Titles that announce themselves as a bound volume rather than an article.
_VOLUME_TITLE_RE = re.compile(
    r"\b(tome|volume|vol\.|ann[ée]e|expos[ée]s|s[ée]rie|fascicule|"
    r"premi[èe]re\s+s[ée]rie|band|heft)\b", re.I,
)


# ----------------------------------------------------------------------
# The decomposition itself
# ----------------------------------------------------------------------

def _split_author_and_title(rest: str, directory: str, rule: str,
                            series: str, ordinal: str) -> Decomposition:
    """Decide whether ``rest`` opens with an author block, and split it.

    This is the step the naive ``split(" - ", 1)`` gets wrong.  It does not
    assume the first segment is an author; it asks.
    """
    rest = rest.strip()
    head, sep, tail = rest.partition(" - ")
    head, tail = head.strip(), tail.strip()

    if sep and looks_like_author_block(head):
        if _JOURNAL_VOLUME_TITLE_RE.search(tail):
            # "017-Glaisher, J. W. L. - Messenger of mathematics, volume XVII,
            # May, 1887-April, 1888".  Glaisher EDITED that volume.  But
            # "Cauchy, A.-L. - Oeuvres completes d'Augustin Cauchy, tome I"
            # has the identical shape and Cauchy wrote it.  The names are
            # kept either way; only the role is left open.
            role = Role.EDITOR if _KNOWN_EDITED_SERIES_RE.search(tail) else Role.UNCERTAIN
            return Decomposition(
                stem="", directory=directory, series=series, ordinal=ordinal,
                authors=head, name_role=role, title=tail, kind=Kind.VOLUME,
                reliability=Reliability.RELIABLE,
                rule=rule + ("+editors" if role is Role.EDITOR else "+role-uncertain"),
            )
        return Decomposition(
            stem="", directory=directory, series=series, ordinal=ordinal,
            authors=head, title=tail or head, kind=Kind.ARTICLE,
            reliability=Reliability.RELIABLE, rule=rule + "+author",
        )

    if sep and looks_like_malformed_author_block(head):
        # The decomposition is sound -- these ARE the authors -- but the block
        # itself needs repair, and the rule name says so rather than pretending
        # the name was written in Western order on purpose.
        return Decomposition(
            stem="", directory=directory, series=series, ordinal=ordinal,
            authors=head, title=tail or head, kind=Kind.ARTICLE,
            reliability=Reliability.RELIABLE, rule=rule + "+malformed-block",
        )

    if sep and looks_like_western_author_list(head):
        return Decomposition(
            stem="", directory=directory, series=series, ordinal=ordinal,
            authors=head, title=tail or head, kind=Kind.ARTICLE,
            reliability=Reliability.RELIABLE, rule=rule + "+western-author",
        )

    # No author block at the front.  In an AUTHOR-FIRST folder that is a
    # malformed author, not an absent one, and guessing either way would be
    # wrong -- so abstain and say which it is.
    if sep and _AUTHOR_FIRST_DIR_RE.match(directory):
        return Decomposition(
            stem="", directory=directory, series=series, ordinal=ordinal,
            kind=Kind.UNKNOWN, reliability=Reliability.UNKNOWN,
            reason=(f"{head!r} sits in the author slot of an author-first "
                    f"folder but is not a recognisable author block"),
            rule=rule + "+malformed-author",
        )

    # A series folder with no author block.  Whether that means the work HAS
    # no author depends on what kind of work it is, and the two answers are
    # not interchangeable.
    if _COLLECTIVE_TITLE_RE.search(rest):
        kind = Kind.VOLUME if _VOLUME_TITLE_RE.search(rest) else Kind.PROCEEDINGS
        return Decomposition(
            stem="", directory=directory, series=series, ordinal=ordinal,
            authors="", title=rest, kind=kind,
            reliability=Reliability.RELIABLE, rule=rule + "+collective",
        )
    return Decomposition(
        stem="", directory=directory, series=series, ordinal=ordinal,
        title=rest, kind=Kind.UNKNOWN, reliability=Reliability.UNKNOWN,
        reason=("no author block in the name, and the title does not announce "
                "a collective work -- this may be a monograph whose author is "
                "only on the title page"),
        rule=rule + "+no-author-in-name",
    )


def decompose(stem: str, directory: str = "", *,
              use_overrides: bool = True) -> Decomposition:
    """Work out what the parts of ``stem`` are.

    ``stem`` is the filename without its ``.pdf``.  ``directory`` is the path
    relative to the library root; it sharpens several rules and is optional,
    because a paper arriving in the inbox has no folder yet.

    ``use_overrides=False`` reports what the RULES alone can do, which is what
    the tests measure the parser by -- otherwise the override table would
    silently flatter it.
    """
    result = _decompose_by_rules(stem, directory)
    if result.is_reliable or not use_overrides:
        return result
    entry = _overrides().get(_nfc(stem).strip())
    if entry is None:
        return result
    return Decomposition(
        stem=stem, directory=directory,
        series=entry.get("series", result.series),
        ordinal=entry.get("ordinal", result.ordinal),
        authors=entry.get("authors", ""),
        name_role=Role(entry.get("name_role", "none")),
        title=entry.get("title") or result.title or _nfc(stem),
        kind=Kind(entry.get("kind", "unknown")),
        reliability=Reliability.RELIABLE,
        rule=f"override({entry.get('confidence', '?')})",
        evidence=entry.get("evidence", ""),
    )


def _decompose_by_rules(stem: str, directory: str = "") -> Decomposition:
    """The rules alone, with no override table behind them."""
    raw = stem
    stem = _nfc(stem).strip()
    directory = _nfc(directory)

    if not stem:
        return Decomposition(stem=raw, directory=directory,
                             reliability=Reliability.UNKNOWN,
                             reason="empty filename", rule="empty")

    def _fill(d: Decomposition) -> Decomposition:
        return Decomposition(
            stem=raw, directory=directory, series=d.series, ordinal=d.ordinal,
            authors=d.authors, name_role=d.name_role, title=d.title, kind=d.kind,
            reliability=d.reliability, reason=d.reason, rule=d.rule,
        )

    # 1. Bound volumes of a named series.  Matched before any " - " splitting,
    #    because their designations contain " - " themselves:
    #    "Comptes rendus ..., tome 301, serie I - Mathematique, no12 - ...".
    if _WHOLE_VOLUME_RE.match(stem):
        return Decomposition(
            stem=raw, directory=directory, series=_whole_volume_series(stem),
            ordinal=_volume_ordinal(stem), authors="", title=stem,
            kind=Kind.VOLUME, reliability=Reliability.RELIABLE,
            rule="whole-volume-series",
        )

    # 2. "<Series> <number> - <rest>".
    m = _SERIES_RE.match(stem)
    if m:
        series = m.group("series").strip()
        ordinal = (m.group("ordinal") or "").strip()
        return _fill(_split_author_and_title(
            m.group("rest"), directory, "series-prefix",
            series=(series + (" " + ordinal if ordinal else "")).strip(),
            ordinal=ordinal))

    # 3. Ordinal glued on with a hyphen: "16-Leandre, R., ... - ...".
    #    Only when what follows really does open with an author block, so a
    #    hyphenated title ("2-approximation - ...") is not mistaken for one.
    for ordinal, rest in _glued_ordinal_candidates(stem):
        head = rest.partition(" - ")[0]
        if (looks_like_author_block(head)
                or looks_like_malformed_author_block(head)
                or looks_like_western_author_list(head)):
            return _fill(_split_author_and_title(
                rest, directory, "glued-ordinal",
                series=_directory_series(directory), ordinal=ordinal))

    # 4. Ordinal or page range as its own segment: "001 - Bretagnolle, J.L...".
    m = _SPACED_ORDINAL_RE.match(stem)
    if m:
        return _fill(_split_author_and_title(
            m.group("rest"), directory, "spaced-ordinal",
            series=_directory_series(directory),
            ordinal=re.sub(r"\s*", "", m.group("ordinal"))))

    # 5. No separator at all.  In a series folder that is a bound volume; in
    #    an author-first folder it is a paper whose author is simply missing
    #    from the name, and we must not invent one.
    if " - " not in stem:
        if _SERIES_DIR_RE.match(directory) or _VOLUME_TITLE_RE.search(stem):
            # "14-The science reports of the Tohoku imperial university, ..."
            # carries its volume number glued on the front.  Leaving it in the
            # title makes the title wrong and the ordinal blank.
            vol_ordinal, vol_title = _volume_ordinal(stem), stem
            m_pref = re.match(r"^(\d{1,4}[a-z]?)-(\S.*)$", stem)
            if m_pref:
                vol_ordinal, vol_title = m_pref.group(1), m_pref.group(2)
            return Decomposition(
                stem=raw, directory=directory,
                series=_directory_series(directory),
                ordinal=vol_ordinal, authors="", title=vol_title,
                kind=Kind.VOLUME if _VOLUME_TITLE_RE.search(stem) else Kind.PROCEEDINGS,
                reliability=Reliability.RELIABLE, rule="no-separator-volume")
        return Decomposition(
            stem=raw, directory=directory, title=stem, kind=Kind.UNKNOWN,
            reliability=Reliability.UNKNOWN,
            reason="no ' - ' separator, and nothing marks it as a volume",
            rule="no-separator")

    # 6. The ordinary case: "Authors - Title".
    return _fill(_split_author_and_title(stem, directory, "plain",
                                         series="", ordinal=""))


#: Ground truth for names the parser cannot settle, each entry carrying the
#: evidence that settled it -- almost always the document's own title page.
#:
#: The table is consulted ONLY after ``decompose`` has already abstained, so
#: an entry cannot shadow a working rule.  That is a structural guarantee, not
#: a convention: there is no code path from a RELIABLE parse into this
#: function.  Override tables normally rot because they quietly accumulate
#: workarounds for parser bugs; this one cannot.
_OVERRIDES_PATH = (Path(__file__).resolve().parents[2]
                   / "data" / "filename_ground_truth_overrides.json")


@lru_cache(maxsize=1)
def _overrides() -> dict:
    try:
        with _OVERRIDES_PATH.open(encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, ValueError) as exc:
        logger.warning("filename ground-truth overrides unreadable (%s): %s",
                       _OVERRIDES_PATH, exc)
        return {}
    return {_nfc(e["stem"]): e for e in payload.get("entries", [])
            if e.get("confidence") != "review"}


def _whole_volume_series(stem: str) -> str:
    """The series label of a bound volume: everything before the first comma."""
    return stem.split(",")[0].strip()


def _volume_ordinal(stem: str) -> str:
    """"..., tome 301, ..." -> "301";  "..., Annee 1718" -> "1718"."""
    m = re.search(r"\b(?:tome|volume|vol\.?|band)\s+([0-9IVXLC]+)", stem, re.I)
    if m:
        return m.group(1)
    m = re.search(r"\bann[ée]e\s+(\d{4})", stem, re.I)
    return m.group(1) if m else ""


def _directory_series(directory: str) -> str:
    """The collection a folder names, e.g. "05 - .../05 - Asterisque"."""
    if not directory:
        return ""
    for part in reversed(directory.split("/")):
        cleaned = re.sub(r"^\d+[a-z]?\s*-\s*", "", part).strip()
        if cleaned and not re.fullmatch(r"[A-Z]", cleaned):
            return cleaned
    return ""
