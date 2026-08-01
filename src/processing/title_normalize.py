"""Safe-default sentence-casing for titles — never damage a proper noun.

The classic failure of whitelist-based sentence casing is its DEFAULT:
"lowercase any capitalized word not on the whitelist", which mangles
names the whitelist never heard of (empirically: "Stefano Franscini,
Ascona, May 2002" → "stefano franscini, ascona, may 2002").  This module
INVERTS the default:

  A capitalized mid-title word is lowercased ONLY when we can prove it
  is an ordinary common word — it is in the dictionary (spellchecker)
  or the owner ruled it "common" — AND nothing marks it as proper (the
  848-entry sentence-case whitelists, the owner's vocabulary, an
  acronym/mixed-case/accented shape, or a digit neighbour like
  "May 2002" / "Volume XV").

  Anything unprovable is PRESERVED verbatim and queued in the title
  vocabulary (``processing.title_vocab``) for a one-click owner ruling
  that then applies library-wide.

``propose_title_case`` is pure (no I/O beyond loading vocab/whitelists);
callers decide whether to auto-apply (confident: no uncertain words) or
just record the pending words.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Word tokens: alphabetic runs incl. apostrophes and internal hyphens
# ("Girsanov's", "time-inconsistent", "McKean–Vlasov" arrives as one token
# via the en-dash class below).
_WORD_RE = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)
_HYPHENS = "-–—‐"
# Quote characters that OPEN an embedded title/citation.  French usage
# separates them with a space ("« Notes historiques »"), so the opener can
# be a token of its own — the inline ``prev_char`` test alone misses it.
#
# Only UNAMBIGUOUS openers belong here: a straight ``"`` is far more often the
# CLOSING quote at the end of a token ('… "local time" Estimates'), and
# treating it as an opener wrongly preserved the word after the closing quote.
_OPEN_QUOTES = "“‘«"
# Longest run of consecutive Capitalized words still treated as a possible
# proper phrase ("Reproducing Kernel Hilbert Space").  Beyond this a run is
# Title-Cased prose, where a single unknown word must not block casing.
_MAX_PROPER_RUN = 4
_MONTHS = {
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
}
# Places that are ALSO ordinary dictionary words (or just very common in
# proceedings titles).  Dictionary membership must not downcase these —
# "…Montecatini Terme, Italy, June 12–20, 1995" keeps "Italy".
_GEO_SEED = {
    "italy", "france", "germany", "switzerland", "japan", "china", "spain",
    "poland", "hungary", "austria", "canada", "brazil", "india", "russia",
    "england", "scotland", "ireland", "israel", "turkey", "greece", "norway",
    "sweden", "denmark", "finland", "netherlands", "belgium", "portugal",
    "australia", "mexico", "chile", "argentina", "usa", "uk",
    "paris", "berlin", "zurich", "zürich", "geneva", "lausanne", "ascona",
    "vienna", "rome", "milan", "pisa", "florence", "madrid", "barcelona",
    "london", "oxford", "cambridge", "princeton", "berkeley", "warsaw",
    "krakow", "budapest", "prague", "moscow", "kyoto", "tokyo", "osaka",
    "beijing", "shanghai", "singapore", "montreal", "toronto", "nice",
    "marseille", "lyon", "grenoble", "toulouse", "bordeaux", "konstanz",
    "montecatini", "cetraro", "saint-flour", "cortona", "oberwolfach",
    "luminy", "banff", "trieste", "bologna", "padova", "torino",
}
# Words after INTERNAL sentence punctuation are preserved verbatim (we
# neither downcase ". Lectures" nor upcase "vs. singular" — abbreviations
# like vs./cf./no. make period-based sentence detection unsound).
_SENTENCE_END = (".", "!", "?")

# Lowercase name particles: a capitalized word right after one of these is
# almost certainly a surname ("résolvantes de Ray", "travaux de Peano") —
# never a downcase candidate.
_PARTICLES = {
    "de", "von", "van", "du", "della", "delle", "di", "da", "le", "la",
    "der", "den", "ter", "ten", "el", "al", "dos", "das", "zur", "zum",
}

# Built-in common words: function words + core math-title vocabulary.
# This is the FLOOR of the commonness oracle (works in tests and tiny
# libraries); the real signal comes from the owner's corpus statistics
# (``title_corpus``) — a word their 29k filenames overwhelmingly write
# lowercase is common by their own convention.
_FUNCTION_WORDS = {
    "a", "an", "the", "and", "or", "nor", "but", "of", "in", "on", "at",
    "to", "for", "with", "without", "by", "from", "into", "onto", "over",
    "under", "between", "among", "through", "via", "versus", "vs", "per",
    "as", "its", "their", "his", "her", "our", "your", "some", "any",
    "all", "both", "each", "every", "no", "not", "than", "then", "when",
    "where", "which", "that", "this", "these", "those", "what", "how",
    "why", "who", "whose", "is", "are", "was", "were", "be", "been",
    "being", "do", "does", "did", "done", "can", "could", "may", "might",
    "must", "shall", "should", "will", "would", "one", "two", "three",
    "new", "old", "toward", "towards", "against", "within", "beyond",
    "about", "above", "below", "after", "before", "during", "since",
    "until", "up", "down", "out", "off", "so", "if", "else", "it", "we",
    "i", "ii", "you", "they", "he", "she", "them", "us", "non", "based",
}
_ACADEMIC_COMMON = {
    "existence", "uniqueness", "solutions", "solution", "equations",
    "equation", "applications", "application", "problems", "problem",
    "methods", "method", "theory", "theorem", "theorems", "approach",
    "approaches", "analysis", "results", "result", "properties",
    "property", "systems", "system", "models", "model", "modelling",
    "modeling", "numbers", "number", "functions", "function", "spaces",
    "space", "processes", "process", "games", "game", "control",
    "controls", "optimal", "optimality", "stochastic", "deterministic",
    "backward", "forward", "reflected", "generalized", "general",
    "nonlinear", "linear", "convergence", "estimates", "estimate",
    "estimator", "estimators", "estimation", "inequalities", "inequality",
    "boundary", "conditions", "condition", "random", "measures",
    "measure", "probability", "probabilistic", "convex", "concave",
    "continuous", "discrete", "finite", "infinite", "dimensional",
    "asymptotic", "asymptotics", "approximation", "approximations",
    "representation", "representations", "characterization", "principle",
    "principles", "dynamic", "dynamics", "programming", "differential",
    "integral", "integrals", "derivative", "derivatives", "operator",
    "operators", "semigroup", "semigroups", "martingale", "martingales",
    "diffusion", "diffusions", "jump", "jumps", "drift", "volatility",
    "utility", "risk", "pricing", "hedging", "portfolio", "market",
    "markets", "insurance", "finance", "financial", "economic",
    "economics", "equilibrium", "equilibria", "agent", "agents",
    "investment", "consumption", "time", "horizon", "stopping",
    "singular", "regular", "regularity", "smooth", "smoothness", "weak",
    "strong", "mild", "viscosity", "classical", "mean", "field", "fields",
    "large", "small", "deviations", "deviation", "limit", "limits",
    "central", "law", "laws", "distribution", "distributions", "moment",
    "moments", "bounded", "unbounded", "growth", "quadratic", "monotone",
    "monotonicity", "lipschitz", "expectations", "expectation",
    "observation", "observations", "likelihood", "maximum", "minimum",
    "exact", "explicit", "implicit", "duality", "dual", "primal",
    "framework", "study", "survey", "introduction", "lecture", "lectures",
    "notes", "note", "remarks", "remark", "comments", "comment",
    "revisited", "extensions", "extension", "examples", "example",
    "counterexample", "counterexamples", "proof", "proofs", "simple",
    "short", "long", "value", "values", "existence", "stability",
    "instability", "sensitivity", "robust", "robustness", "uncertain",
    "uncertainty", "ambiguity", "information", "learning", "filtering",
    "filter", "prediction", "term", "structure",
}
_BUILTIN_COMMON = _FUNCTION_WORDS | _ACADEMIC_COMMON


@dataclass
class TitleProposal:
    original: str
    proposed: str
    uncertain: list = field(default_factory=list)   # words we preserved unproven

    @property
    def changed(self) -> bool:
        return self.proposed != self.original

    @property
    def confident(self) -> bool:
        return not self.uncertain


# ---------------------------------------------------------------------------
# Classification oracles
# ---------------------------------------------------------------------------
# NB: the project spellchecker is NOT usable here — its dictionary
# deliberately contains mathematician names (Edgeworth, Nirenberg, Saks…)
# so they don't flag as typos, which makes "in the dictionary" unsound as
# a commonness proof (empirically it downcased those very names).  The
# sound oracle is the built-in list + the owner's own corpus statistics.


def _whitelists() -> set:
    """Union of the sentence-case engine's proper-noun-ish whitelists."""
    try:
        from core.sentence_case import _load_sentence_case_config
        cfg = _load_sentence_case_config()
        out = set()
        for key in ("capitalization_whitelist", "name_dash_whitelist",
                    "proper_adjectives", "mixed_case_words", "compound_terms"):
            out |= {str(w) for w in cfg.get(key, ())}
        return out
    except Exception:  # pragma: no cover
        return set()




# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def _is_plain_capitalized(seg: str) -> bool:
    """True for the ONLY shape we ever consider lowercasing: ``Xxxx…`` —
    initial uppercase ASCII-or-not letter, all remaining letters lowercase,
    no accents anywhere.  Acronyms (BSDE), mixed case (McKean), accented
    words (Équations, Itô) and single letters are never candidates."""
    if len(seg) < 2:
        return False
    if not seg[0].isupper() or not seg[1:].islower():
        return False
    # Accented letters anywhere -> almost always a name in this corpus;
    # preserve and let the vocabulary decide.
    return all(ord(c) < 128 for c in seg)


def propose_title_case(
    title: str,
    library_root: Optional[Path] = None,
) -> TitleProposal:
    """Sentence-case ``title`` under the safe default.  Pure function.

    * First word: first letter capitalized (unless it looks like a math
      prefix such as ``p-adic`` — a single letter before a hyphen).
    * Mid-title ``Xxxx`` words: lowercased only when PROVABLY common;
      preserved (and reported in ``uncertain``) otherwise.
    * Words inside math-ish tokens (digits, ^, _, \\, $) and everything
      that is not a plain ``Xxxx`` shape are preserved verbatim.
    """
    title = unicodedata.normalize("NFC", title)
    vocab = {"proper": set(), "common": set()}
    corpus_stats: dict = {}
    if library_root is not None:
        try:
            from processing.title_vocab import load_vocab
            v = load_vocab(library_root)
            vocab["proper"] = v["proper"]
            vocab["common"] = v["common"]
        except Exception:  # pragma: no cover
            pass
        try:
            from processing.title_corpus import load_word_stats
            corpus_stats = load_word_stats(library_root)
        except Exception:  # pragma: no cover
            pass
    wl = _whitelists()
    proper_all = vocab["proper"] | wl

    def provably_common(base: str) -> bool:
        low = base.lower()
        if low in vocab["common"] or low in _BUILTIN_COMMON:
            return True
        if corpus_stats:
            from processing.title_corpus import corpus_says_common
            return corpus_says_common(low, corpus_stats)
        return False

    # Two passes over space-separated tokens.
    #
    # Pass 1 classifies every word segment: sentence starts, proper (ruled /
    # whitelisted / month-with-year / geo), provably-common downcase
    # candidates, uncertain (preserve + queue), or untouchable shapes.
    #
    # Pass 2 rebuilds the string, PROMOTING a downcase candidate to
    # "preserve + queue" when it sits across a comma from a proper-ish
    # neighbour ("Montecatini Terme, Italy" — Italy is a dictionary word,
    # but the comma-adjacent proper phrase says it's a place here).
    tokens = title.split(" ")
    n = len(tokens)

    def tok_has_digit(i: int) -> bool:
        return 0 <= i < n and any(ch.isdigit() for ch in tokens[i])

    def is_mathish(tok: str) -> bool:
        return any(ch.isdigit() for ch in tok) or any(ch in "^_\\$" for ch in tok)

    KEEP, FIRST, PROPER, COMMON, UNCERTAIN = "keep", "first", "proper", "common", "uncertain"

    classified: list = []          # per token: list of (span, seg, base, cls)
    token_properish: list = [False] * n
    very_first = True              # only the TITLE's first word is upcased
    after_period = False           # words after internal ./!/? are preserved
    prev_word_lower = ""           # particle guard ("de Ray")
    after_open_quote = False       # previous token was a bare opening quote

    for i, tok in enumerate(tokens):
        words: list = []
        if is_mathish(tok):
            # Any leading digit token ("25 years of …") consumes the
            # sentence start — the following word is NOT upcased.
            very_first = False
            after_period = False
            prev_word_lower = ""
        else:
            for m in _WORD_RE.finditer(tok):
                seg = m.group(0)
                base = seg.split("'")[0].split("’")[0]   # Girsanov's -> Girsanov
                prev_char = tok[m.start() - 1] if m.start() > 0 else ""
                # An opening quote either hugs the word ("«Notes") or stands
                # as its own token ("« Notes") — both open an embedded title.
                if (prev_char and prev_char in "\"'“‘«") or (after_open_quote and not words):
                    # Opening quote: an embedded title/citation starts here
                    # ("On the integral…").  Preserve verbatim.
                    very_first = False
                    after_period = False
                    cls = KEEP
                    if base[:1].isupper():
                        token_properish[i] = True
                elif very_first:
                    very_first = False
                    after_period = False
                    after = tok[m.end():m.end() + 1]
                    if len(base) == 1 and after in _HYPHENS:
                        # Math prefixes like "p-adic" at the very start stay.
                        cls = KEEP
                    elif base.lower() in _PARTICLES and base.islower():
                        # "de Finetti style theorems" — a leading name
                        # particle stays lowercase.
                        cls = KEEP
                        prev_word_lower = base.lower()
                    elif not (base.islower() or _is_plain_capitalized(base)):
                        # Mixed-case or acronym identifier ("mlOSP", "iOS",
                        # "BSDE", "École").  Upcasing the first letter would
                        # CORRUPT a real name ("mlOSP" -> "MlOSP", "iOS" ->
                        # "IOS"); only all-lowercase or plainly-capitalized
                        # first words are safe to upcase.
                        #
                        # Deliberately does NOT set token_properish: an
                        # acronym title ("HANK, Heterogeneous agent…") would
                        # otherwise look like a proper phrase to the
                        # comma-adjacency rule and stop the subtitle being
                        # sentence-cased.
                        cls = KEEP
                    else:
                        cls = FIRST
                elif seg != base and _is_plain_capitalized(base):
                    # Capitalized possessive ("Root's barrier", "Girsanov's
                    # example") — almost always an eponym; never downcase.
                    cls = UNCERTAIN if base not in proper_all else PROPER
                elif after_period:
                    # Internal sentence boundary: preserve verbatim.  We
                    # neither downcase ". Lectures" nor upcase "vs. singular"
                    # (period-based sentence detection is unsound with
                    # abbreviations like vs./cf./no.).
                    after_period = False
                    cls = KEEP
                    if base[:1].isupper():
                        token_properish[i] = True
                elif not _is_plain_capitalized(base):
                    cls = KEEP
                    if base[:1].isupper() or any(ord(c) > 127 for c in base):
                        token_properish[i] = True        # acronym/mixed/accented
                elif base in proper_all or seg in proper_all:
                    cls = PROPER
                elif base.lower() in _GEO_SEED:
                    cls = PROPER
                elif base.lower() in _MONTHS and (tok_has_digit(i - 1) or tok_has_digit(i + 1)):
                    cls = PROPER
                elif prev_word_lower in _PARTICLES:
                    cls = UNCERTAIN                      # "de Ray" -> a surname
                elif provably_common(base):
                    cls = COMMON
                else:
                    cls = UNCERTAIN
                if cls in (PROPER, UNCERTAIN):
                    token_properish[i] = True
                words.append((m.span(), seg, base, cls))
                prev_word_lower = base.lower() if base.islower() else ""
        classified.append(words)
        # Internal sentence punctuation: the next word is preserved.
        if tok.rstrip().endswith(_SENTENCE_END):
            after_period = True
            prev_word_lower = ""
        # A token ending in an opening quote ("«") opens an embedded title
        # whose first word lives in the NEXT token.
        stripped = tok.rstrip()
        after_open_quote = bool(stripped) and stripped[-1] in _OPEN_QUOTES

    # Pass 1.5 — CAPITAL-RUN COHERENCE.
    #
    # Inside a run of >=2 consecutive Capitalized words, a provably-common
    # word is promoted to "preserve + queue" when some OTHER member of the
    # run is UNCERTAIN (a word we cannot classify at all).
    #
    # The distinction that makes this safe is KNOWN vs UNKNOWN neighbour:
    #   * "Hilbert Space Methods" — Hilbert is a KNOWN proper noun, so the
    #     run is the ordinary maths shape <Name> + <common nouns> and must
    #     still downcase to "Hilbert space methods".
    #   * "Sciences Sociales" / "Stochastic Calculus" — the neighbour is a
    #     word we know nothing about, so the run may well be a proper
    #     phrase.  Downcasing only the half we recognise yields incoherent
    #     output ("sciences Sociales", "and stochastic Calculus"), which
    #     reads as a typo.  Preserve the whole run and let the vocabulary
    #     review settle the unknown word once, library-wide.
    flat = [(ti, wi) for ti, ws in enumerate(classified) for wi in range(len(ws))]
    promoted: set = set()
    r = 0
    while r < len(flat):
        ti, wi = flat[r]
        if classified[ti][wi][1][:1].isupper():
            end = r
            while end + 1 < len(flat):
                tj, wj = flat[end + 1]
                if not classified[tj][wj][1][:1].isupper():
                    break
                end += 1
            members = flat[r:end + 1]
            # A run of >=2 but <= _MAX_PROPER_RUN.  Longer runs are a
            # Title-Cased SENTENCE ("On The Existence Of Zorglub Solutions"),
            # not a proper phrase — one unknown word must not veto casing the
            # whole title, so those are left to the ordinary rules.
            if 2 <= len(members) <= _MAX_PROPER_RUN:
                kinds = {classified[a][b][3] for a, b in members}
                # A KNOWN proper noun in the run means we DO understand the
                # phrase: it is the ordinary <Name> + <common nouns> shape
                # ("Reproducing kernel Hilbert space"), so casing proceeds.
                # Only a run we cannot read at all — an UNCERTAIN member and
                # no known name to explain it — is preserved wholesale.
                if UNCERTAIN in kinds and PROPER not in kinds:
                    promoted.update(
                        (a, b) for a, b in members
                        # Function words and name particles are lowercase even
                        # INSIDE a genuine proper name ("United States of
                        # America", "von Mises", "de Moivre"), so they always
                        # stay downcase candidates.
                        if classified[a][b][3] == COMMON
                        and classified[a][b][2].lower()
                        not in _FUNCTION_WORDS and classified[a][b][2].lower()
                        not in _PARTICLES
                    )
            r = end + 1
        else:
            r += 1

    def properish_neighbor(i: int) -> bool:
        """Comma-adjacent proper-phrase test for token i's candidates."""
        prev_ok = i > 0 and tokens[i - 1].rstrip().endswith(",") and token_properish[i - 1]
        next_ok = (
            i + 1 < n and tokens[i].rstrip().endswith(",") and token_properish[i + 1]
        )
        return prev_ok or next_ok

    uncertain: list = []
    out_tokens: list = []
    for i, tok in enumerate(tokens):
        words = classified[i]
        if not words:
            out_tokens.append(tok)
            continue
        rebuilt = []
        last = 0
        for wi, ((start, end), seg, base, cls) in enumerate(words):
            rebuilt.append(tok[last:start])
            if cls == FIRST:
                rebuilt.append(seg[0].upper() + seg[1:])
            elif cls == COMMON:
                if properish_neighbor(i) or (i, wi) in promoted:
                    uncertain.append(base)               # proper-phrase context
                    rebuilt.append(seg)
                else:
                    rebuilt.append(seg[0].lower() + seg[1:])
            elif cls == UNCERTAIN:
                uncertain.append(base)
                rebuilt.append(seg)
            else:                                        # KEEP / PROPER
                rebuilt.append(seg)
            last = end
        rebuilt.append(tok[last:])
        out_tokens.append("".join(rebuilt))

    return TitleProposal(
        original=title,
        proposed=" ".join(out_tokens),
        uncertain=uncertain,
    )
