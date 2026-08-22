"""Suspected misspellings in filenames — detection only, never correction.

WHY THIS EXISTS.  "Mortini, R. - Solutions to problems in Amererican
Mathematical Monthly, ..." sat in the library carrying that typo through
every check.  There was no live spell check anywhere on the naming path:
``core/text_processing/my_spellchecker.py`` answered every word of two or
more characters "spelled correctly" because its dictionary backend had
been removed from the dependencies, and the one caller that took a
spellchecker argument never read it.

The rule this module is built around: **"I did not look" and "it is fine"
must never be the same return value.**  Hence three verdicts, not two.

WHY IT NEVER CORRECTS.  Measured on this library, three of the suggested
partners are wrong: "lobal" suggests "local" but means *global*, "netral"
suggests "neural" but means *neutral*, "expaction" suggests "expansion"
but means *expectation*.  A suggestion is evidence for the owner, never
an instruction to the filesystem.

MEASURED BEHAVIOUR (27,382 in-scope filenames): 160 suspect words across
156 files, 0.57% of the library, 71.3% precision against a hand-labelled
census of all 160.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import enum
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

# --- tuning, every value with the measurement behind it ------------------
#
# Each threshold sits at a measured knee; the sweep is in the design note.
#   MIN_LEN   6 costs 10 real typos to save 19 rows; 4 adds 5 rows for none
#   MIN_PARTNER_FREQ  50 costs 31 real typos to save 49 rows; 10 adds 36
#                     rows for no known gain
#   the SCALED distance is not a preference: editdistance("amererican",
#   "american") == 2, so any fixed max-distance-1 configuration misses the
#   very case this module was written for.
MIN_LEN = 5
MIN_PARTNER_FREQ = 20
LONG_WORD = 8               # at or above this length, allow 2 edits
LANGS = ("en", "en_GB", "fr", "de", "it", "es")
ENGLISH = ("en", "en_GB")
NON_ENGLISH = ("fr", "de", "it", "es")

# A word unknown to every dictionary is only evidence of a typo when the
# REST OF THE TITLE is English.  "Stochastik" is missing from macOS's
# German dictionary, but it sits in "Stochastik für das Lehramt", where
# every other word is German -- so the honest verdict is "I cannot check
# this language", not "misspelled".  Measured separation on the real
# queue: foreign-language false positives score 0.33-1.00 on these
# signals, real English typos score 0.06-0.25.
MIN_CONTEXT_WORDS = 3
UNKNOWN_FRAC = 0.4

_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
SEPARATOR = " - "

# NSSpellChecker accepts ANY all-caps string of this length or shorter --
# "WIITH", "CONTOL", "QZXVQZ" all come back correct, while the same string
# one character longer is rejected.  That is an answer given without
# looking, so such tokens are UNKNOWN and never CLEAN.
ALLCAPS_BLIND_LEN = 6

# f-ligatures and control characters: no dictionary, no threshold, and no
# false positive is possible -- a filename has no business containing
# either.  Measured: 13 + 7 files, and the word-level detector below sees
# only 3 of the 20.
LIGATURES = "ﬀﬁﬂﬃﬄﬅﬆ"


class Verdict(enum.Enum):
    """Three states.  Never two.

    CLEAN is a positive claim: an oracle was consulted and accepted the
    word.  UNKNOWN is the honest "I could not look".  Collapsing UNKNOWN
    into CLEAN is precisely the defect this module exists to end.
    """

    TYPO = "typo"
    CLEAN = "clean"
    UNKNOWN = "unknown"


class TypoOracleUnavailable(RuntimeError):
    """The dictionary bridge is dead.  SYSTEMIC, not per-word.

    Raised once at construction, never per token.  Four blanket
    ``except Exception`` handlers sit on the live naming paths, so a
    per-word raise would be swallowed one word at a time and the module
    would look fixed while behaving exactly as before.
    """


@dataclass(frozen=True)
class Suspect:
    word: str            # surface form exactly as it appears in the name
    lower: str
    suggestion: str      # nearest frequent corpus word -- EVIDENCE ONLY
    distance: int
    suggestion_freq: int


@dataclass(frozen=True)
class TypoReport:
    verdict: Verdict
    suspects: tuple = ()
    unjudged: tuple = ()      # tokens the oracle answered without looking
    unknown_reason: str = ""

    def __post_init__(self) -> None:
        # An UNKNOWN that cannot say why is indistinguishable from a clean
        # result to every caller, so make it unconstructible.
        if (self.verdict is Verdict.UNKNOWN) != bool(self.unknown_reason):
            raise ValueError(
                "UNKNOWN requires a reason and only UNKNOWN may carry one; "
                f"got verdict={self.verdict} reason={self.unknown_reason!r}"
            )


# ---------------------------------------------------------------------------
# the oracle: macOS NSSpellChecker over six languages, via stdlib ctypes
# ---------------------------------------------------------------------------

class _NSSpell:
    """Six-language spelling oracle. No third-party dependency.

    The union of languages is what makes this usable on this corpus: it
    accepts "behaviour" AND "behavior", "modelling" AND "modeling", and
    the French/German/Italian titles that make up a large part of the
    library -- while still rejecting "Amererican".
    """

    def __init__(self) -> None:
        objc_path = ctypes.util.find_library("objc")
        appkit_path = ctypes.util.find_library("AppKit")
        if not objc_path or not appkit_path:
            raise TypoOracleUnavailable(
                "libobjc/AppKit not found; NSSpellChecker is unavailable"
            )
        try:
            objc = ctypes.CDLL(objc_path)
            ctypes.CDLL(appkit_path)
            objc.objc_getClass.restype = ctypes.c_void_p
            objc.objc_getClass.argtypes = [ctypes.c_char_p]
            objc.sel_registerName.restype = ctypes.c_void_p
            objc.sel_registerName.argtypes = [ctypes.c_char_p]
            send_addr = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value

            def send(rtype, argtypes):
                # A fresh CFUNCTYPE per selector: reusing one function
                # object clobbers argtypes and the next call reads garbage.
                return ctypes.CFUNCTYPE(rtype, *argtypes)(send_addr)

            class NSRange(ctypes.Structure):
                _fields_ = [("location", ctypes.c_long),
                            ("length", ctypes.c_long)]

            nsstring = objc.objc_getClass(b"NSString")
            sel_with = objc.sel_registerName(b"stringWithUTF8String:")
            make = send(ctypes.c_void_p,
                        [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p])
            self._nsstr = lambda s: make(nsstring, sel_with, s.encode("utf-8"))

            checker_cls = objc.objc_getClass(b"NSSpellChecker")
            self._shared = send(ctypes.c_void_p,
                                [ctypes.c_void_p, ctypes.c_void_p])(
                checker_cls, objc.sel_registerName(b"sharedSpellChecker"))
            if not self._shared:
                raise TypoOracleUnavailable("sharedSpellChecker returned nil")
            self._sel = objc.sel_registerName(
                b"checkSpellingOfString:startingAt:language:wrap:"
                b"inSpellDocumentWithTag:wordCount:")
            self._check = send(
                NSRange,
                [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                 ctypes.c_long, ctypes.c_void_p, ctypes.c_bool,
                 ctypes.c_long, ctypes.POINTER(ctypes.c_long)])
        except TypoOracleUnavailable:
            raise
        except Exception as exc:                       # pragma: no cover
            raise TypoOracleUnavailable(
                f"could not bind NSSpellChecker: {type(exc).__name__}: {exc}"
            ) from exc

    def accepts(self, word: str, lang: str) -> bool:
        count = ctypes.c_long(0)
        found = self._check(self._shared, self._sel, self._nsstr(word), 0,
                            self._nsstr(lang), False, 0, ctypes.byref(count))
        # A "not found" range is NSNotFound (NSIntegerMax), which some
        # bridges surface as -1; treat either as "no misspelling here".
        return found.location < 0 or found.location > 100_000_000

    def known(self, word: str) -> bool:
        return any(self.accepts(word, lang) for lang in LANGS)


_ORACLE: "_NSSpell | None" = None


def _oracle() -> _NSSpell:
    global _ORACLE
    if _ORACLE is None:
        _ORACLE = _NSSpell()
        self_check(_ORACLE)
    return _ORACLE


# Sentinels: every one verified on this machine.  If any fails, the bridge
# is answering nonsense and must not be used at all.
_SENTINELS_CLEAN = ("American", "behaviour", "behavior", "modelling",
                    "modeling", "Volterra", "McKean")
_SENTINELS_TYPO = ("Amererican", "teh", "qqqqzzzz")


def self_check(oracle: "_NSSpell | None" = None) -> None:
    """Assert known verdicts; raise on any mismatch.

    MUST raise rather than return a degraded object -- a bridge that
    cannot tell "American" from "Amererican" is not a bridge, and one
    that quietly answers False for everything is the exact failure this
    module replaces.
    """
    oracle = oracle or _NSSpell()
    for word in _SENTINELS_CLEAN:
        if not oracle.known(word):
            raise TypoOracleUnavailable(
                f"oracle rejects {word!r}, which is correctly spelled")
    for word in _SENTINELS_TYPO:
        if oracle.known(word):
            raise TypoOracleUnavailable(
                f"oracle accepts {word!r}, which is misspelled")


@lru_cache(maxsize=200_000)
def oracle_verdict(word: str) -> Verdict:
    """Three-state dictionary lookup for ONE token.

    UNKNOWN, not CLEAN, whenever the oracle would answer without looking.
    """
    if not word or not any(ch.isalpha() for ch in word):
        return Verdict.UNKNOWN
    if word.isupper() and len(word) <= ALLCAPS_BLIND_LEN:
        return Verdict.UNKNOWN
    oracle = _oracle()
    # NO camelCase splitting.  It looks necessary -- NSSpellChecker splits
    # at internal capitals and accepts when every segment is known, so
    # "xAmerican" and "MeanField" are accepted whole.  But measured, it
    # buys nothing and costs a whole class of real names: a corruption
    # glued to a word is ALREADY rejected whole ("xAmererican",
    # "MeanFeild", "stochasticContol" all come back False), while
    # splitting turns "McKean" into "Mc" + "Kean" and flags every Mc- and
    # Mac- surname in the library.  The residual hole is a compound of
    # genuinely real words, which is not a typo.
    #
    # Case matters to the oracle: "american" is rejected while "American"
    # is accepted, and German nouns only pass capitalised ("Funktion").
    # Query the surface form first, then the ordinary variants -- but
    # NEVER .upper(), which lands in the all-caps blind zone and would
    # silently bless "wiith" and "contol".
    for variant in (word, word.lower(), word.capitalize()):
        if oracle.known(variant):
            return Verdict.CLEAN
    return Verdict.TYPO


# ---------------------------------------------------------------------------
# corpus
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CorpusStats:
    """Document frequencies over TITLES, plus the author-block vocabulary.

    Built from filenames alone; this class performs no I/O whatsoever, so
    nothing here can touch the library.
    """

    title_df: dict = field(default_factory=dict)
    author_tokens: frozenset = frozenset()
    frequent: tuple = ()          # words with df >= MIN_PARTNER_FREQ
    # Words the owner has ruled correctly spelled. Carried here so that
    # examine_title stays pure -- it must never read the library itself.
    ruled_correct: frozenset = frozenset()


def split_name(name: str) -> tuple:
    """(author block, title). Filenames are 'Authors - Title.pdf'."""
    stem = name[:-4] if name.lower().endswith(".pdf") else name
    head, sep, tail = stem.partition(SEPARATOR)
    return (head, tail) if sep else ("", stem)


def _tokens(text: str) -> list:
    return _WORD.findall(text)


def build_corpus_stats(names, ruled_correct=frozenset()) -> CorpusStats:
    """Pure: filenames in, statistics out.

    Document frequency, not token frequency -- a word repeated inside one
    title is still evidence from a single document.
    """
    title_df: dict = {}
    authors: set = set()
    for raw in names:
        name = unicodedata.normalize("NFC", raw)
        author, title = split_name(name)
        # .lower(), NEVER .casefold(): casefold maps U+FB00 to "ff", so
        # "diﬀerential" would fold to a correctly-spelled frequent word
        # and every ligature corruption would become invisible.
        for word in {w.lower() for w in _tokens(title)}:
            title_df[word] = title_df.get(word, 0) + 1
        authors.update(w.lower() for w in _tokens(author))
    frequent = tuple(sorted(w for w, n in title_df.items()
                            if n >= MIN_PARTNER_FREQ))
    return CorpusStats(title_df=title_df,
                       author_tokens=frozenset(authors),
                       frequent=frequent,
                       ruled_correct=frozenset(
                           w.lower() for w in ruled_correct))


def _within(a: str, b: str, limit: int) -> "int | None":
    """Levenshtein distance if it is <= limit, else None."""
    if abs(len(a) - len(b)) > limit:
        return None
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1,
                               current[j - 1] + 1,
                               previous[j - 1] + (ca != cb)))
        if min(current) > limit:
            return None
        previous = current
    return previous[-1] if previous[-1] <= limit else None


def max_distance(word: str) -> int:
    return 2 if len(word) >= LONG_WORD else 1


def nearest_frequent(word: str, stats: CorpusStats):
    """The most frequent corpus word within the allowed edit distance.

    Restricted to partners sharing a first letter: typos rarely change
    it, and the restriction removes a large slice of false positives at
    no measured recall cost.
    """
    limit = max_distance(word)
    best = None
    for candidate in stats.frequent:
        if candidate[0] != word[0]:
            continue
        dist = _within(word, candidate, limit)
        if dist is None or dist == 0:
            continue
        freq = stats.title_df[candidate]
        if best is None or freq > best[2]:
            best = (candidate, dist, freq)
    return best


def _accepts(word: str, langs) -> bool:
    """Membership, including the capitalised variant.

    German nouns are only accepted capitalised, so "funktion" needs
    "Funktion" to be judged fairly.

    Used to judge whether a WORD is misspelled. To classify a title's
    LANGUAGE use _accepts_strict instead -- see the note there.
    """
    oracle = _oracle()
    variants = (word, word.lower(), word.capitalize())
    return any(oracle.accepts(v, lang) for v in variants for lang in langs)


def _accepts_strict(word: str, langs) -> bool:
    """Membership WITHOUT the capitalised variant, for classifying a
    title's LANGUAGE.

    Capitalising an unknown word makes every checker accept it as a
    proper noun, so the permissive form says yes to almost anything:
    "Methodus" and "academiae" pass, the Latin titles stop looking Latin,
    and the unsupported-language rule goes quiet. Measured over the real
    library: strict suppresses 16 false positives, permissive only 12.

    This distinction was once deleted as an "equivalent mutant" because a
    monkeypatched A/B reported no difference. That measurement was wrong,
    which is why the comparison is now done by editing the source.
    """
    oracle = _oracle()
    return any(oracle.accepts(v, lang)
               for v in (word, word.lower()) for lang in langs)


def _accepts_lowercase(word: str, langs) -> bool:
    """Strict membership: the exact lowercase form only.

    Capitalising makes every checker permissive, because a capitalised
    unknown word reads as a proper noun -- "Stochastic" is accepted by
    the German AND French dictionaries while "stochastic" is accepted by
    neither. Asking "is this a word of language L" therefore has to use
    the uncapitalised form, or the answer is yes for almost anything.

    Load-bearing for the SUGGESTION test and, measured, nowhere else.
    """
    oracle = _oracle()
    return any(oracle.accepts(word.lower(), lang) for lang in langs)


def title_languages(tokens: list, skip: str) -> frozenset:
    """The non-English languages this title is written in, if any.

    Judged on the OTHER words, never on the candidate itself: a short
    title would otherwise vote itself foreign on the strength of the one
    word being questioned.  Returns an empty set for an English title.
    """
    english = 0
    votes: dict = {}
    for word in tokens:
        if len(word) < 3 or word.lower() == skip:
            continue
        if _accepts_strict(word, ENGLISH):
            english += 1
            continue
        for lang in NON_ENGLISH:
            if _accepts_strict(word, (lang,)):
                votes[lang] = votes.get(lang, 0) + 1
    if not votes:
        return frozenset()
    best = max(votes.values())
    if best < english:
        return frozenset()
    return frozenset(lang for lang, n in votes.items() if n == best)


def title_is_unsupported_language(tokens: list, skip: str) -> bool:
    """Is the title in a language macOS ships no dictionary for?

    Latin ("Methodus facilis inueniendi Integrale") and Czech
    ("Poznámka k problemu ruinováni hrácu") are unknown to all six
    dictionaries, so there is no language to compare a suggestion
    against and the cross-language rule above cannot fire. The signal
    is the share of words no dictionary recognises at all.

    Measured on the real queue: Latin and Czech titles score 0.44-1.00,
    while English titles carrying a genuine typo score at most 0.25 --
    and that worst case is a series-prefixed filename whose author block
    lands on the title side of the first " - ".
    """
    unknown = total = 0
    for word in tokens:
        if len(word) < 3 or word.lower() == skip:
            continue
        total += 1
        if not _accepts_strict(word, LANGS):
            unknown += 1
    return total >= MIN_CONTEXT_WORDS and unknown / total >= UNKNOWN_FRAC


def suggestion_is_cross_language(word: str, suggestion: str,
                                 languages: frozenset) -> bool:
    """Is the suggested partner merely the English cousin of a foreign word?

    "Stochastik" is missing from macOS's German dictionary, so the corpus
    offers "stochastic" -- one edit away and very frequent. But the title
    is "Stochastik für das Lehramt", and "stochastic" is not a German
    word: the pair is a language correspondence, not a misspelling. Same
    for bayésien/bayesian, ergodicité/ergodicity, multivariée/multivariate.

    The test must be this narrow. Suppressing EVERY unknown word in a
    foreign title was tried and measured: it removed 20 false positives
    but also ten genuine ones -- "aspets" for aspects, "inforamtion" for
    information, "oprérateurs" for opérateurs, "inégaltés" for inégalités
    -- because a French title can perfectly well contain a French typo.
    Those survive here, since their partners are themselves French.
    """
    if not languages:
        return False
    return (_accepts_lowercase(suggestion, ENGLISH)
            and not _accepts_lowercase(suggestion, languages))


def examine_title(name: str, stats: CorpusStats) -> TypoReport:
    """Pure. Takes the NAME, not the file: no I/O, no library access."""
    name = unicodedata.normalize("NFC", name)
    _author, title = split_name(name)
    suspects_found: list = []
    unjudged: list = []
    tokens = _tokens(title)
    for word in tokens:
        lower = word.lower()
        if len(word) < MIN_LEN:
            continue
        # Hapax only. A word that appears in a second file is either real
        # or a habit, and this design is blind to habits by construction.
        if stats.title_df.get(lower, 0) != 1:
            continue
        if lower in stats.author_tokens:
            continue
        # The owner has looked at this word and said it is a real one.
        if lower in stats.ruled_correct:
            continue
        verdict = oracle_verdict(word)
        if verdict is Verdict.UNKNOWN:
            unjudged.append(word)
            continue
        if verdict is Verdict.CLEAN:
            continue
        near = nearest_frequent(lower, stats)
        if near is None:
            continue
        suggestion, distance, freq = near
        # Last gate, and the only one that needs the whole title rather
        # than the word alone: in a non-English title, an English partner
        # is a language correspondence rather than a correction.
        if suggestion_is_cross_language(lower, suggestion,
                                        title_languages(tokens, lower)) \
                or title_is_unsupported_language(tokens, lower):
            unjudged.append(word)
            continue
        suspects_found.append(Suspect(word=word, lower=lower,
                                      suggestion=suggestion,
                                      distance=distance,
                                      suggestion_freq=freq))
    if suspects_found:
        return TypoReport(Verdict.TYPO, tuple(suspects_found), tuple(unjudged))
    return TypoReport(Verdict.CLEAN, (), tuple(unjudged))


# ---------------------------------------------------------------------------
# the parameter-free scanners: no dictionary, no threshold, no judgement
# ---------------------------------------------------------------------------

def broken_characters(name: str) -> list:
    """Characters that cannot legitimately appear in a filename.

    An f-ligature means text was extracted from a PDF without
    normalisation ("diﬀerential"); a control character means the name was
    corrupted outright.  Neither needs a dictionary and neither can
    produce a false positive, which is why this is separate from the
    statistical detector above -- and why it finds 20 files the detector
    only sees 3 of.
    """
    faults = []
    for index, ch in enumerate(unicodedata.normalize("NFC", name)):
        if ch in LIGATURES:
            faults.append((index, ch, "f-ligature",
                           unicodedata.normalize("NFKD", ch)))
        elif unicodedata.category(ch) == "Cc" or (
                unicodedata.category(ch) == "Cf" and ch != "﻿"):
            faults.append((index, ch, "control character", ""))
    return faults


# ---------------------------------------------------------------------------
# the oracle is OS state, so pin it
# ---------------------------------------------------------------------------

# NSSpellChecker is not a fixed table.  It consults ~/Library/Spelling --
# a LocalDictionary of words the owner once clicked "Learn", and a
# dynamic-counts.dat that macOS rewrites as it is used -- so the same
# filename can be judged differently on two different days.  This bit us
# during development: one sweep reported 143 suspect words and a later
# sweep of the identical corpus with identical code reported 147.
#
# The defence is not to pretend it is stable but to MEASURE it: a fixed
# probe list, hashed, recorded alongside every report.  Two reports whose
# fingerprints differ were produced by two different oracles, and any
# change in the counts between them has to be read in that light.
_FINGERPRINT_PROBE = (
    "American", "Amererican", "behaviour", "behavior", "modelling",
    "modeling", "stochastic", "stochastik", "Volterra", "McKean",
    "Vlasov", "teh", "qqqqzzzz", "WIITH", "aspects", "aspets",
    "opérateurs", "information", "Methodus", "academiae", "problemu",
    "processus", "differential", "diﬀerential",
)


def oracle_fingerprint() -> str:
    """A short, stable hash of what this machine's dictionaries say today.

    Record it with any measurement taken from this module. If it changes,
    the oracle changed, and a difference in the numbers is not evidence
    that the library changed.
    """
    import hashlib
    verdicts = "".join(f"{w}={oracle_verdict(w).value};"
                       for w in _FINGERPRINT_PROBE)
    return hashlib.sha256(verdicts.encode("utf-8")).hexdigest()[:12]


def learned_words_in_play(library_root=None) -> int:
    """How many words the OWNER once taught macOS are in the dictionary.

    Every one of them is a word this detector will call correctly spelled
    without the owner ever ruling on it here. The spec found that store
    polluted with LaTeX debris -- hbox, sqrt, newcommand, utf8 -- and at
    least one learned misspelling, so its size is worth surfacing rather
    than leaving as invisible influence.
    """
    from pathlib import Path
    local = Path.home() / "Library" / "Spelling" / "LocalDictionary"
    try:
        return sum(1 for line in local.read_text(
            encoding="utf-8", errors="replace").splitlines() if line.strip())
    except OSError:
        return 0
