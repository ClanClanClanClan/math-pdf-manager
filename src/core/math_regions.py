r"""Which spans of a title are MATHEMATICS.  One rule, one implementation.

    find_math_regions(text) -> [(start, end), ...]

THE OPERATIONAL DEFINITION, and the only one that matters: a span is
mathematics iff REWRITING ITS CASE OR ITS WORDS WOULD BE WRONG, *and* it is
notation rather than a word.  "L^2" must not become "l^2"; "AR(1)" must not
become "Ar(1)" or "AR(one)".  "(Almost) Everything you always wanted to know"
is ordinary English in brackets and is NOT protected.

Bare lexical acronyms -- BSDE, PDE, HJB, COVID-19, 2D, MATLAB, Roman numerals
-- are words, not notation.  Their case must be preserved, but by the acronym
branch of processing/title_normalize.py, which already owns that decision.
Claiming them here would double-own it.  That boundary is inherited from the
hand-labelled corpus, not established here; see REFUSALS.

THE RULE
--------
The title is TOKENISED, then PARSED by recursive descent against a grammar of
notation, and a span is emitted only when the parse DERIVES it *and* carries
positive evidence that what it derived is notation rather than prose.  There
is no "mathy character" test, no phase that claims a bracket for being a
bracket, and no fallback.

    Regions   := Latex | Chain+             (maximal, disjoint, evidence-bearing)
    Chain     := Term ( Link Term )*
    Link      := ""                         juxtaposition   D²u, rπ, CβEₙ
               | Rel                        = < > ≤ ≥ ≠ ∈ ⊂ …  (and € -- see
                                            the note on the _REL table)
               | Arith                      + - * : / · ⋅ × ÷ ± ∓ − …
               | "," | ";" | "…" | "..."
               | Sp                         one space, budgeted, and only
                                            between two notational operands
    Term      := Primary Postfix*
    Primary   := Greek | DoubleStruck | UnicodeOp | VulgarFraction | Script
               | Letter                     a single Latin letter is a variable
               | Number
               | FuncName                   sin cos log exp sqrt lim inf sup …
               | CapsHead                   AR GARCH RCD GL SU CAT  (needs Args)
               | MixedHead                  Lexp Fi GSp Bes         (needs Args)
               | BracketGroup               ( … ) [ … ] { … } < … > | … |
               | SymbolBracket              "(*)" and friends, when a script
                                            is glued to them:  (*)^+  (*)^{++}
    Postfix   := ScriptRun                  L²  ℝⁿ  Bₜ  Aₚ  lᴺ_∞
               | ("^"|"_") ScriptArg        L^2  H_∞  W^{2,p}  L_{d+1}  W^-1
               | Args                       AR(1)  GL(3)  C_b(X)  tan²(rπ)
    ScriptArg := BraceGroup | short token | a spelled-out name (H_infty)
    Args      := "(" chain-list ")"         GLUED to the head; no space
    Latex     := "$…$" | "$$…$$" | "\[…\]" | "\(…\)"
               | "\begin{env}…\end{env}" | "\command{…}"

    Adjectival := Letter ("-"|"–"|"−") word  p-adic  N-player  G-Lévy
    PlusPlus   := name "++"                  C++  Gauss2++  γ++
    Echo       := a single capital already used as a base in the SAME title,
                  standing alone as a word ("… de Cₖ^∞ dans C satisfaisant")

EVIDENCE.  A Chain is emitted only if it carries at least one of
    SYM     a character that exists only for mathematics (Greek, blackboard
            bold, ∞ ∂ ∫ ∑ √ ∈ ±, a super/subscript, a vulgar fraction)
    SCRIPT  an explicit ^ or _ with a well-formed script argument
    ARGS    a head GLUED to a parenthesised argument list that is itself
            notational       -- this is what separates AR(1) from "Heston (2008)"
    REL     a relation whose two operands are both notational
                             -- this is what separates 0<d<2 from "slides + discussion"
    BRK     a bracket whose content is notation, or a tuple of bare variables
            that prose never writes      ( <X, X>, (y,z) )
and lenience is EARNED: a bracket is admitted merely for parsing only when
what stands to its left is already notation.  Without that gate a bare number
drags in the next bracket for free and "155(3)" -- a journal volume and issue
-- becomes mathematics.

THE HYPHEN, because it is the character that broke every predecessor
--------------------------------------------------------------------
U+002D HYPHEN-MINUS is a LINK and is never EVIDENCE.  The parser may cross it,
so "2J_s-R_s" is one span exactly as "2J_s−R_s" is; but meeting one proves
nothing, so "1105-1123" and "Mean-field" stay prose.  U+2212 MINUS is both,
because English never uses U+2212.

Both halves were separately paid for.  Leaving "-" out of the tables
altogether -- the state this module was repaired from -- split or truncated 10
real library titles at 13 hyphen sites, among them "(2Jₛ-Rₛ, s≥0)",
"g(t)=c√(t+b)-a" and "d[X, X]ₜ=dt-X⁺ₜ₋dXₜ".  Putting it in as EVIDENCE was
tried and measured, and it is worse: it gains 5 genuine spans (four "2M-X" and
the "0, n-2" of the ∂b title) and costs 8 over-claims, because "min", "max",
"sup", "inf" and "rank" are operator names, so "min-max control",
"Max-min representations", "Rank-2 swaption formulae", "U-max statistics" and
"SARS-CoV-2" all start claiming their English half.  Making it evidence
without any guard at all is how validators/filename_checker/math_utils.py came
to claim 186 of the 189 characters of an English sentence.

The price of muteness, stated: "2M-X" gets no span, exactly as "2M+X" gets
none, while "2M−X" gets one.  A chain of bare alphanumerics carries no
evidence, and U+2212 supplies some by existing.  That is the one place where
"-" and U+2212 still part company, and it is a consequence of the definition
rather than an oversight.

It was NOT the only place.  The Adjectival production accepted "-", U+2010,
U+2011 and U+2013 but not U+2212, so "G-martingales" gave ['G'] while
"G−martingales" gave [] -- the same contract broken in the OPPOSITE
direction, and a far larger hole.  Measured by respelling every "-" as
U+2212 in each of the 6,313 hyphen-bearing titles and comparing protected
offsets: the interim in-repo module disagrees on 6,103, this module before
the repair on 409, this module on 34 -- and all 34 survivors are the
documented "2M-X" class, U+2212 claiming MORE than "-" and never less.
Before the repair 375 of the 409 ran the other way, the direction that
loses a real span.

LATEX, and why it is supported in a library that contains none
---------------------------------------------------------------
Measured: 0 of the 25,049 unique reliable library titles contain a "$", a
backslash or a "\begin{".  That is an argument about the library, and
find_math_regions is read by CODE, not by the library.  Two of its readers are
live on the filing path -- validators/filename_checker/core.py:224 and, through
core/sentence_case.py, core/math_tokenization.py, whose contract is ONE MATH
token per formula -- and the titles they see come from processing/ingest.py,
i.e. from arXiv and Crossref, which are LaTeX sources.  ingest._unlatex
converts accent commands only; "$", "\alpha" and "\[" pass through untouched.

So a delimited formula is ONE region INCLUDING ITS DELIMITERS, and the
grammar is not allowed to see inside it.  Parsing the payload and leaving the
delimiters outside -- what happened before this phase existed -- is worse than
refusing: "\[f(x) = x^2\]" gave one span "f(x) = x^2" and spilled "\", "[",
"]" into the prose stream a caser may rewrite, and "\begin{equation} E = mc^2
\end{equation}" gave "mc^2" and dropped "E = " into prose.

A "$" is the one delimiter with a competing reading -- money, in a
mathematical FINANCE library -- so a dollar pair whose payload reads as
English is refused: "The $5 trillion question and the $100 answer" yields
nothing.  The backslash forms have no competing reading and carry no guard.

MEASURED, by re-running every candidate over the same corpora
-------------------------------------------------------------
345 hand-labelled titles (201 spans, 1,042 protected characters), character
level:

    R  core/math_regions (the interim in-repo one) P 0.681  R 0.872  exact 272
    this module                                    P 1.000  R 0.996  exact 343

Only those two rows are re-measured here.  B, A and C all now DELEGATE to this
module, so their original behaviour can no longer be run; the figures below are
from the design record, not from this measurement, and are marked as such:

    B  validators/filename_checker/math_utils      P 0.043  R 0.236  exact 106
    A  core/text_processing/math_detector          P 0.495  R 0.755  exact 195
    C  validators/math_handler                     P 1.000  R 0.000  exact 179

Through the tokeniser, of the corpus's 201 gold formulas: this module gives
exactly one full MATH token for 199, no partial and no split; R gives 111
full, 58 PARTIAL, 9 SPLIT and 23 missed.

25,049 unique library titles: fires on 1,344 (5.4%), 1,489 regions in 421
distinct shapes, mean 2.6 characters, longest 39.  It claims 0.22% of an
average title and 3.9% of a title where it fires.
Regions that are a run of two or more ordinary ASCII letters: 0.  (537 are a
SINGLE such letter -- the bare variables of the Adjectival and Echo
productions, G, K, M, N …, which is what those productions are for.)

Structural audit over all 25,049: 0 unsorted, 0 overlapping, 0 empty,
0 out-of-range, 0 starting mid-token, 0 non-deterministic, and 0 regions that
core/math_tokenization.py fails to reproduce as exactly one MATH token.
60,000 fuzz inputs (40,000 random, 20,000 mutated real titles): 0 contract
breaks.  NFC versus NFD over the 3,060 accented titles: 0 disagreements.

COST, and the bound that makes it one
--------------------------------------
Measured here (8-core darwin 26.6, CPython 3.12, load average 8-10, so these
are upper bounds), minimum of repeated runs after warm-up:

    25,049 real titles, mean                     0.021 ms/title
    worst 251-character input found by search    1.9 ms   (max seen 2.7)
    worst 1,000-character input found by search  5.3 ms
    longer than MAX_INPUT_CHARS                 <0.001 ms (refused)

251 is the filename cap; the longest real title is 229 and costs 52 of the
1,500 parser steps a call may spend.

The predecessor was SUPER-LINEAR and claimed "worst adversarial input 7 ms",
which did not reproduce: on the 64-character "(a(b(c(d(e(" * 4 + ")" * 20 it
took 455-620 ms here, against 1.3 ms now.  Two independent causes, both fixed
and both commented at their sites:

  * every bracket interior was re-parsed by a FRESH throw-away parser, once
    per enclosing start position and once per production that looked at it --
    36,256 tokenisations of a 64-character string.  _sub_chainlist,
    _tokenize, _chain and _find_close are memoised now.  The memo cannot
    change an answer (each is pure in its key), verified by differential over
    79,394 inputs -- the 25,049 library titles, the 345 corpus titles, 4,000
    NFD respellings, 30,000 mutated real titles, 20,000 random strings: 0
    differences against the un-memoised version.
  * _find_close skipped its own 60-token bound on meeting an opener, so a run
    of N identical openers was scanned to its end from each of its own N
    positions; '\a' + '{' * 998 spent 36 ms in that loop alone.

The guard meant to stop this, `self.calls > 4000`, was PER PARSER, which is
why it never fired: that 64-character case built 36,256 parsers, each with a
fresh allowance.  It is deleted.  In its place is one step cell shared by
every parser in a call, and a REFUSAL instead of a silent None -- see
_refuse, MAX_INPUT_CHARS, MAX_PARSE_STEPS.

REFUSALS -- decided, not overlooked
------------------------------------
* "1:2" meaning one half, in "…of order greater than 1:2", is missed, and
  deliberately.  The library writes "/" as ":", so a bare digit:digit is
  lexically identical to "Séminaire Bourbaki, volume 2012:2013" and to
  "IFIP-WG 7:1", which are NOT mathematics.  No purely lexical rule separates
  them; settling it needs the document.  Cost: 3 characters of the corpus.
* A bare "e" for Euler's number, in "…products for π, e, and sqrt{2+sqrt{2}}",
  is missed.  A lone letter that is also an English word cannot be told from
  an article without semantics, and refusing it is what stops "the case of
  a √n window" from claiming the article.  Cost: 1 character.
* _ADJ_STOP is a WORDLIST, not a principle: which "X-word" compounds escape
  the adjectival production is a 16-entry denylist ("ray", "shirt", "turn"…).
  It is kept because the operational definition makes its decisions nearly
  free -- the letters it argues about are capitals that stay capital either
  way -- and because deleting it costs corpus precision.  Measured: all 169
  distinct claimed X-word forms over the 25,049 titles were read, and every
  one is genuine.  The boundary will drift with the corpus; that is the price.
* A short snake_case identifier is claimed: "top_k", "data_set", "log_in".
  Separating them from "eps_i" and "L_exp", which are the same shape and are
  genuine, needs a dictionary; a length rule cannot.  Measured: 10 hits over
  the library, all genuine notation (L_d, C_b, B_T, l_r, L_q, L_exp), 0 false
  positives.  Under the operational definition an identifier's case should be
  preserved anyway, so the cost of the over-claim is nil and the cost of a
  wordlist would not be.
* The short-word escape in _rhs can still be reached with NO whitespace at
  all: "Σ⋅the" is claimed.  English does not glue a word to an operator, and
  every spaced form -- "Σ ⋅ the sum", "Bounds when n ≤ the sample size" -- is
  refused.  1 real library title reaches the escape legitimately
  ("∫₀^∞ sin(x):xdx"), which is why it exists at all.
* A Windows path claims its components: "C:\Users\name" -> "\Users\name".
  Backslash-plus-letters is a LaTeX command by the rule above, and a path
  component's case is worth preserving too, so this is left as it is.
* "2M-X" is not protected, and "2M−X" is; see THE HYPHEN.  4 library titles.
* A name glued to "++" IS claimed -- "C++", "Gauss2++", "CIR++", "Freefem++",
  "γ++".  Those five are every occurrence in the 25,049 titles, and all five
  are names whose case must survive.  It is the CO₂ case below, admitted on
  the same ground rather than on a claim that C++ is mathematics.  A SINGLE
  trailing "+" is not enough: 27 titles glue one to a word and they are
  ordinary arithmetic ("1+1", "3x+1", "(n k+1)", "C^{1+α}").
* An input longer than MAX_INPUT_CHARS, or one whose parse runs past
  MAX_PARSE_STEPS, is REFUSED: the whole input comes back as one protected
  region, so every consumer leaves it alone.  A non-str RAISES.  The two are
  not the same decision; the reasons are at _refuse and find_math_regions.
* "CO₂" is claimed.  It is a chemical formula, not mathematics, but its case
  must be preserved and it carries a Unicode subscript, so it satisfies the
  operational definition by accident.  One title.
* "≪ … ≫" (U+226A/U+226B) is used as French guillemets in one title, so those
  two characters are excluded from the relation table.
* The acronym boundary is INHERITED.  BMO, UMD, VMO and BV are genuine
  function spaces (46 titles) and are lexically identical to BSDE and COVID.
  This module leaves all of them to the acronym branch, except inside a
  bracket that already stands inside a formula ("X€{BS, FBS, P}").  If that
  branch does not in fact protect them, roughly 2,000 case-sensitive
  occurrences are protected by nobody.  That is a decision for the owner.
* Precision 1.000 is measured on 345 labelled titles this design was tuned
  against, so it is an upper bound, not a fresh estimate.  The independent
  evidence is the library sweep.

CONTRACT (what the live consumers require)
-------------------------------------------
  * a FRESH, MUTABLE list of hashable (int, int) tuples on every call --
    core/math_tokenization.py appends to the object it is handed
  * half-open [start, end), sorted, pairwise disjoint, never empty-width
  * "" and "   " return []; a non-str raises TypeError -- deliberately, and
    not for the reason the length cap refuses; see find_math_regions
  * a REFUSAL is [(a, b)] over the whole stripped input.  It satisfies every
    clause here, so no caller needs a special case, and it is distinguishable
    from [], which is the point
  * spans start on a word boundary -- core/math_tokenization.py keys a dict
    on region starts and silently drops a region it never lands on
  * CO-VARIANT: two spellings of one expression must leave the SAME prose
    behind, because maintenance/conformance.py runs this on the old and the
    new title separately and compares the residues to decide whether a
    rewrite was "confined to mathematics".  This is why "-" and U+2212 must
    decompose alike, why "0<d<2" and "0 < d < 2" must too, and why U+2206
    INCREMENT must snap as U+0394 GREEK CAPITAL DELTA does -- "BS∆Es" and
    "BSΔEs" are one word spelled two ways.  See _snap_to_tokens.
  * offsets index the string AS PASSED IN.  Nothing is normalised inside,
    because normalising would shift the offsets under the caller.  NFD input
    is nevertheless answered the same as NFC (macOS hands back NFD --
    CLAUDE.md trap #8 -- and src/maintenance/conformance.py:149 passes a
    title straight in): measured over the 3,060 accented library titles,
    0 disagreements.
"""

from __future__ import annotations

import re

__all__ = ["find_math_regions", "MAX_INPUT_CHARS", "MAX_PARSE_STEPS"]

# ────────────────────────────────────────────────────────────── terminals ──

def _chr_set(*specs):
    out = set()
    for spec in specs:
        if isinstance(spec, tuple):
            lo, hi = spec
            out.update(chr(c) for c in range(lo, hi + 1))
        else:
            out.add(spec)
    return out


# Greek, including the variant letterforms (ϑ ϕ ϖ ϰ ϱ ϵ) and MICRO SIGN,
# which this library uses interchangeably with mu.
_GREEK = _chr_set((0x0391, 0x03A9), (0x03B1, 0x03C9), (0x03D0, 0x03F5),
                  "\u00b5", "\u03c2")
_GREEK = {c for c in _GREEK if c.isalpha()}


def _is_dbl(ch: str) -> bool:
    """Blackboard bold / script / fraktur letters: ℝ ℤ ℙ ℓ ℱ 𝕃 𝔼 𝝎 …"""
    o = ord(ch)
    if 0x2100 <= o <= 0x214F:
        return ch.isalpha()          # ™ № ℮ are not letters and do not qualify
    return 0x1D400 <= o <= 0x1D7FF


# Superscripts: Latin-1 ¹²³, the Superscripts block, the spacing modifier
# letters and the phonetic modifier block — minus the nine subscript letters
# that sit inside it (U+1D62-U+1D6A).
_SUB = _chr_set((0x2080, 0x209C), (0x1D62, 0x1D6A), "\u2c7c", "\u2c7d")
_SUPER = (_chr_set("\u00b2", "\u00b3", "\u00b9",
                   (0x2070, 0x207F), (0x02B0, 0x02B8), (0x02E0, 0x02E4),
                   (0x1D2C, 0x1DBF)) - _SUB)

_VULGAR = set("½⅓⅔¼¾⅕⅖⅗⅘⅙⅚⅐⅛⅜⅝⅞⅑⅒↉⅟")

# Relations.  ≪ ≫ are deliberately absent: this library uses them as French
# guillemets, never as much-less-than.
_REL = set("=<>≤≥≠≈≃≅≡≢∈∉∋⊂⊃⊆⊇⊊⊋≺≻≼≽∼≲≳⩽⩾≔≝∝⊥⊨⊢≐"
           # U+20AC EURO SIGN: a mangled ∈.  Both of its two occurrences in
           # this library are set membership ("{Sₙ:n, n € N²}", "X€{BS,FBS,P}")
           # and neither is money.  Measured, not assumed.
           "€")
_REL_UNI = _REL - set("=<>")

# Operators that are, by themselves, proof of notation.
_OPSYM = set(
    "∞∂∫∬∭∮∑∏∐√∛∜∇∅∀∃∄∧∨¬⊕⊗⊙⊘⊞⊠∖∆∡∠′″‴ℵ↦→←↔⇒⇔∪∩⋃⋂"
) | _REL_UNI

# Arithmetic / structural links: never evidence on their own.
#
# U+002D HYPHEN-MINUS is in this table, and that is the whole of the fix for
# the defect that "2J_s-R_s" split into two spans while "2J_s−R_s" stayed one.
# It is a LINK ONLY.  It is not evidence, and it must never become evidence:
# U+2212 MINUS is a character English never uses, so meeting one is proof of
# notation, whereas "-" is the ordinary English hyphen of "mean-field" and
# "1105-1123".  Crossable but mute is exactly the standing "+" already has,
# and it is what makes "-" behave identically to U+2212 INSIDE an expression
# -- which is where the two spellings have to agree -- without letting it
# start one.  See THE HYPHEN in the module docstring.
_ARITH = set("+*·⋅×÷±∓−/:∗•-")
_DASHY = set("–—")           # links two SYM terms only (Δ–Γ), never digits

_MATCH = {"(": ")", "[": "]", "{": "}", "<": ">", "|": "|", "‖": "‖"}

_FUNCS = {
    "sin", "cos", "tan", "cot", "sec", "csc", "sinh", "cosh", "tanh", "coth",
    "arcsin", "arccos", "arctan", "arg", "log", "ln", "lg", "exp", "sqrt",
    "lim", "liminf", "limsup", "inf", "sup", "max", "min", "det", "tr", "rank",
    "dim", "ker", "im", "mod", "gcd", "lcm", "deg", "ord", "card", "sgn",
    "diag", "grad", "div", "curl", "erf", "ess", "esssup", "essinf",
    "re", "var", "cov", "corr", "id", "supp", "osc", "cl", "conv", "span",
}

# Names that may follow a ^ or _ spelled out in Latin letters.  The library
# writes "H_infty" beside "H^∞", and maintenance/conformance.py runs this
# detector on BOTH spellings of the same title and compares the prose that
# is left over.  A name recognised in one spelling and not the other would
# silently break that comparison, so the two must move together.
_SCRIPT_WORDS = {
    "infty", "infinity", "inf", "sup", "max", "min", "exp", "log", "lim",
    "loc", "opt", "reg", "eff", "adj", "obs",
    "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
    "iota", "kappa", "lambda", "mu", "nu", "xi", "pi", "rho", "sigma",
    "tau", "phi", "chi", "psi", "omega",
}

# Single letters that are ordinary words in the languages of this library.
# They may not be claimed as bare variables by the Echo rule.
_WORDY_LETTERS = set("aAIiyYoOuUeE")

# Tails after "X-" that make the construct a word, not a variable.
_ADJ_STOP = {"ens", "ray", "rays", "shirt", "shirts", "mail", "mails",
             "commerce", "turn", "turns", "level", "levels", "bomb", "bombs",
             "shaped", "shape", "axis", "cell", "cells", "ring", "rings"}
_ROMAN_RE = re.compile(r"^[ivxlcdmIVXLCDM]{2,}$")
_WORDTOK_RE = re.compile(r"\w+")

# ─────────────────────────────────────────────────────────────── evidence ──

SYM, SCRIPT, ARGS, REL, BRK = 1, 2, 4, 8, 16
_ANY_EVIDENCE = SYM | SCRIPT | ARGS | REL | BRK

# ─────────────────────────────────────────────────────────────── tokenizer ──

# token kinds
_T_ALPHA, _T_GREEK, _T_DBL, _T_SUP, _T_SUB, _T_NUM = 0, 1, 2, 3, 4, 5
_T_REL, _T_OP, _T_ARITH, _T_DASH, _T_CARET, _T_UNDER = 6, 7, 8, 9, 10, 11
_T_OPEN, _T_CLOSE, _T_SP, _T_COMMA, _T_ELL, _T_OTHER = 12, 13, 14, 15, 16, 17
_T_DOT = 18                  # collapsed to _T_ELL or _T_OTHER by _tokenize


class _Tok:
    __slots__ = ("kind", "s", "e", "txt")

    def __init__(self, kind, s, e, txt):
        self.kind, self.s, self.e, self.txt = kind, s, e, txt


def _classify(ch: str) -> int:
    """Token kind of one character.  Memoised on the character, so the table
    is bounded by the alphabet and never needs clearing."""
    k = _CLASSIFY_CACHE.get(ch)
    if k is None:
        k = _CLASSIFY_CACHE[ch] = _classify_slow(ch)
    return k


_CLASSIFY_CACHE: dict = {}


def _classify_slow(ch: str) -> int:
    if ch in _GREEK:
        return _T_GREEK
    if _is_dbl(ch):
        return _T_DBL
    if ch in _SUPER:
        return _T_SUP
    if ch in _SUB:
        return _T_SUB
    if ch in _VULGAR:
        return _T_OP
    if ch.isdigit():
        return _T_NUM
    if ch.isalpha():
        return _T_ALPHA
    if ch in _REL:
        return _T_REL
    if ch in _OPSYM:
        return _T_OP
    if ch in _ARITH:
        return _T_ARITH
    if ch in _DASHY:
        return _T_DASH
    if ch == "^":
        return _T_CARET
    if ch == "_":
        return _T_UNDER
    if ch in "([{":
        return _T_OPEN
    if ch in ")]}":
        return _T_CLOSE
    if ch in "<>|‖":
        return _T_REL          # re-read as bracket where a group parses
    if ch.isspace():
        return _T_SP
    if ch in ",;":
        return _T_COMMA
    if ch in "…":
        return _T_ELL
    if ch == ".":
        return _T_DOT
    return _T_OTHER


_RUNKINDS = {_T_ALPHA, _T_GREEK, _T_DBL, _T_SUP, _T_SUB, _T_NUM, _T_SP, _T_DOT}


def _tokenize(text: str):
    """Token list of *text*, memoised for one top-level call.  The list and
    its _Tok objects are SHARED and treated as immutable; nothing here writes
    to a token after _tokenize built it."""
    toks = _TOK_CACHE.get(text)
    if toks is None:
        toks = _TOK_CACHE[text] = _tokenize_slow(text)
    return toks


_TOK_CACHE: dict = {}


def _tokenize_slow(text: str):
    toks = []
    i, n = 0, len(text)
    while i < n:
        k = _classify(text[i])
        j = i + 1
        if k in _RUNKINDS:
            while j < n and _classify(text[j]) == k:
                j += 1
            if k == _T_NUM:                       # 1.35, 2.5
                while (j + 1 < n and text[j] == "." and text[j + 1].isdigit()):
                    j += 2
                    while j < n and text[j].isdigit():
                        j += 1
        if k == _T_DOT:
            # "..." is an ellipsis; a lone "." is a full stop, and must stay
            # one, or "A P.D.E. approach to Asian options" becomes notation.
            k = _T_ELL if j - i >= 2 else _T_OTHER
        toks.append(_Tok(k, i, j, text[i:j]))
        i = j
    return toks

# ───────────────────────────────────────────────────────────────── parser ──

_SUB_CACHE: dict = {}


class _Exhausted(Exception):
    """Internal.  The parse ran past MAX_PARSE_STEPS; find_math_regions turns
    it into a refusal.  Never escapes this module."""


def _sub_chainlist(inner, depth, set_ok, budget):
    """Parse a bracket interior as a comma list of chains -- MEMOISED.  The
    single entry to a throw-away parser over a substring, and most of the fix
    for the blowup.  PURE in (inner, depth, set_ok): the parser starts fresh,
    reads no context beyond *inner*, and the grammar is deterministic, so the
    cache cannot change an answer.  Both productions that used to build their
    own parser over the same string come through here."""
    key = (inner, depth, set_ok)
    r = _SUB_CACHE.get(key, _MISS)
    if r is _MISS:
        sub = _P(inner, _tokenize(inner), top=False, budget=budget)
        sub.set_ok = set_ok
        r = sub._full_chainlist(depth)
        # stored only on a completed parse: an _Exhausted raised through here
        # leaves no half-answer behind for the next call to find.
        _SUB_CACHE[key] = r
    return r


_MISS = object()


class _P:
    """Recursive-descent parser over the token list of one title."""

    def __init__(self, text, toks, top=True, budget=None):
        self.text = text
        self.t = toks
        self.n = len(toks)
        #: memo tables.  _chain and _find_close are pure functions of their
        #: arguments given a fixed (text, toks, top, set_ok), and set_ok is
        #: assigned once immediately after construction and never again, so
        #: both are safe to cache for the life of the parser.
        self._fc: dict = {}
        self._ch: dict = {}
        #: shared step counter (MAX_PARSE_STEPS): every parser built for
        #: this call draws on the SAME cell.  The old budget was PER PARSER,
        #: which is why it never fired -- "(a(b(c(d(e(" * 4 built 36,256
        #: parsers, each with a fresh allowance of 4,000.
        self.budget = [MAX_PARSE_STEPS] if budget is None else budget
        #: False for the throw-away parsers built over a bracket's interior,
        #: which have lost the surrounding context and must not judge whether
        #: a letter stands alone.
        self.top = top
        #: True only on the throw-away parser built over the interior of a
        #: bracket that ALREADY stands inside a formula.  There, and only
        #: there, a bare all-caps name is an operand rather than a word:
        #: "X€{BS, FBS, P}" is a membership statement whose members are named
        #: function spaces.  Scoped this tightly on purpose -- granting it to
        #: the top-level parser instead made "α-CIR" and "λ-SABR" claim their
        #: acronym, which double-owns a decision title_normalize's acronym
        #: branch already makes.
        self.set_ok = False

    # ── primaries ────────────────────────────────────────────────────────
    def _alone(self, tk):
        """Is this token a whole whitespace-delimited word?"""
        if not self.top:
            return False          # tested first: it is the cheap half, and
                                  # every sub-parser answers here
        before = self.text[tk.s - 1] if tk.s else " "
        after = self.text[tk.e] if tk.e < len(self.text) else " "
        return before.isspace() and after.isspace()

    def _primary(self, k, depth, lenient=False):
        """-> (next_k, evidence, notational, is_func) or None"""
        if k >= self.n:
            return None
        tk = self.t[k]
        kind = tk.kind

        if kind in (_T_GREEK, _T_DBL):
            return k + 1, SYM, True, False
        if kind in (_T_SUP, _T_SUB):
            return k + 1, SYM, True, False
        if kind == _T_OP:
            return k + 1, SYM, True, False
        if kind == _T_NUM:
            return k + 1, 0, True, False
        if kind == _T_ALPHA:
            s = tk.txt
            if len(s) == 1:
                # A letter that is also an ordinary word ("a", "I", "y") and
                # stands alone BETWEEN SPACES is an article, not a variable:
                # "the case of a √n window" must not yield "a √n".  Inside a
                # bracket it still is one, which is what keeps "(y,z)" whole.
                if s in _WORDY_LETTERS and self._alone(tk):
                    return k + 1, 0, False, False
                return k + 1, 0, True, False
            low = s.lower()
            nxt = self.t[k + 1] if k + 1 < self.n else None
            # word immediately carrying a script is a base: tan², GMCᵞ, sinᵃ
            if nxt is not None and nxt.s == tk.e and nxt.kind in (_T_SUP, _T_SUB):
                if len(s) <= 6:
                    return k + 1, 0, True, low in _FUNCS
                return None
            # a word carrying an explicit script marker is a base: weak^∗,
            # ksqrt^2, eps_i.  '_' counts as well as '^' -- the two spellings
            # of the same expression must be recognised alike, or conformance
            # sees a different prose residue for each.  A stem such as
            # 'affine_structure_signature' is stopped one step later, by
            # _script_arg refusing a whole English word as an index.
            if (nxt is not None and nxt.s == tk.e
                    and nxt.kind in (_T_CARET, _T_UNDER)
                    and len(s) <= 8 and s.isascii()):
                return k + 1, 0, True, low in _FUNCS
            if low in _FUNCS:
                return k + 1, 0, True, True
            if s.isupper() and len(s) <= 6 and s.isascii():
                # CapsHead: needs Args, except inside a lenient bracket.
                return k + 1, 0, self.set_ok, False
            if len(s) <= 6 and s.isascii() and nxt is not None \
                    and nxt.s == tk.e and nxt.kind == _T_OPEN and nxt.txt == "{":
                # A BRACE is notation markup and nothing else; English never
                # glues a word to one.  So the head may be all-lowercase here
                # -- "ksqrt{t}", a real library title -- where before a "("
                # it may not.
                return k + 1, 0, False, False
            if (len(s) <= 4 and s.isascii() and any(c.isupper() for c in s)):
                # MixedHead (Lexp, Fi, GSp, Bes, BM, NB): valid only if Args
                # follow.  A CAPITAL is required and the length is 4, not 6,
                # and both bounds are load-bearing.  Without the capital an
                # all-lowercase English word glued to a bracket was claimed --
                # "author(s)", "effect(s)", "player(s)", "user(s)" -- which is
                # the "(Almost) Everything" class the docstring calls
                # structurally unreachable, arriving by the other door.
                # Without the shorter length a SURNAME glued to a two-digit
                # citation year was claimed -- "Meyer(98)", "Heston(93)" --
                # since _args_ok only refuses a FOUR-digit year.  Measured:
                # all 24 glued word(…) forms in the 25,049 library titles are
                # 4 characters or fewer and every one carries a capital
                # (Lexp, Fi, GSp, Bes, BM, NB, and the all-caps heads that
                # take the CapsHead branch above).
                if nxt is not None and nxt.s == tk.e and nxt.kind == _T_OPEN:
                    return k + 1, 0, False, False
            return None
        if kind in (_T_OPEN, _T_REL) and tk.txt in _MATCH:
            g = self._bracket_group(k, depth, lenient)
            if g is not None:
                return g
            # A bracket of pure operator symbols, glued to a script, is the
            # BASE of that script: the axiom names "(*)^+" and "(*)^{++}".
            # The payload may not contain a letter or a digit, so no amount
            # of "(Almost)" can reach this production.
            end_k = self._find_close(k, tk.txt, _MATCH[tk.txt])
            if end_k is not None and end_k + 1 < self.n:
                nx = self.t[end_k + 1]
                inner = self.text[tk.e:self.t[end_k].s]
                if (nx.s == self.t[end_k].e
                        and nx.kind in (_T_CARET, _T_UNDER, _T_SUP, _T_SUB)
                        and 0 < len(inner) <= 4
                        and not any(c.isalnum() for c in inner)):
                    return end_k + 1, 0, True, False
        return None

    # ── bracket group as a term ──────────────────────────────────────────
    def _bracket_group(self, k, depth, lenient=False):
        if depth > 8:
            return None
        open_ch = self.t[k].txt
        close_ch = _MATCH.get(open_ch)
        if close_ch is None:
            return None
        end_k = self._find_close(k, open_ch, close_ch)
        if end_k is None and open_ch in "[(":
            # the library's half-open intervals and typos: [0, ∞[  C[0, ∞)
            for alt in (open_ch, ")" if open_ch == "[" else "]"):
                end_k = self._find_close(k, open_ch, alt)
                if end_k is not None:
                    break
        if end_k is None:
            return None
        inner = self.text[self.t[k].e:self.t[end_k].s]
        if not inner.strip():
            return None
        ev = self._content_evidence(inner, depth + 1,
                                    lenient=lenient, bars=(open_ch in "|\u2016"))
        if ev is None:
            return None
        return end_k + 1, ev | BRK, True, False

    def _find_close(self, k, open_ch, close_ch):
        key = (k, open_ch, close_ch)
        r = self._fc.get(key, _MISS)
        if r is _MISS:
            r = self._fc[key] = self._find_close_slow(k, open_ch, close_ch)
        return r

    def _find_close_slow(self, k, open_ch, close_ch):
        b = self.budget
        b[0] -= 1
        if b[0] < 0:
            raise _Exhausted
        depth = 0
        for j in range(k, self.n):
            t = self.t[j]
            if t.kind in (_T_OPEN, _T_CLOSE, _T_REL) or t.txt in "|‖":
                if t.txt == open_ch and (open_ch != close_ch or j == k):
                    depth += 1
                    # FALL THROUGH to the two bounds below.  This used to
                    # `continue`, skipping them, so a run of N identical
                    # openers was scanned to its end from each of its own N
                    # positions: '\a' + '{' * 998 spent 36 ms here alone.
                    # The 60-token bound was always the intent; the opener
                    # was the one kind exempt from it, and nothing wanted it.
                elif t.txt == close_ch:
                    depth -= 1
                    if depth == 0:
                        return j
            if self.text[t.s:t.e].strip() == "" and j - k > 25:
                return None
            if j - k > 60:
                return None
        return None

    _TUPLE_RE = re.compile(r"^\s*[A-Za-z0-9]\s*(?:[,;]\s*[A-Za-z0-9]\s*)+$")

    def _content_evidence(self, inner, depth, lenient=False, bars=False):
        """Evidence of a bracket's content, or None if it is not notation."""
        parts = _sub_chainlist(inner, depth, bool(lenient), self.budget)
        if parts is None:
            return None
        ev, terms, allvar = parts
        if ev & (SYM | SCRIPT | ARGS | REL | BRK):
            return ev
        if lenient:
            # already inside a formula: the group only has to parse
            return ev
        if bars and terms >= 1:
            return BRK                      # |X|  ‖x‖  — never prose
        # a tuple of bare variables or coordinates: (y,z)  <X, X>  (0, T)
        if self._TUPLE_RE.match(inner):
            return BRK
        return None

    def _full_chainlist(self, depth):
        """Parse an entire (bracket-interior) string as a comma list of chains.
        -> (evidence, n_terms, all_single_letter_vars) or None"""
        k, ev, terms, allvar = 0, 0, 0, True
        while k < self.n and self.t[k].kind == _T_SP:
            k += 1
        while k < self.n:
            tk = self.t[k]
            if tk.kind in (_T_SP, _T_COMMA, _T_ELL):
                k += 1
                continue
            if not ((tk.kind == _T_ALPHA and len(tk.txt) == 1)
                    or tk.kind == _T_NUM):
                allvar = False
            r = self._chain(k, depth, inside=True)
            if r is None:
                return None
            nk, e2 = r
            if nk == k:
                return None
            ev |= e2
            terms += 1
            k = nk
        if terms == 0:
            return None
        return ev, terms, allvar

    # ── postfixes ────────────────────────────────────────────────────────
    def _postfixes(self, k, depth, glue_end, base_start=0,
                   is_func=False, base_kind=None):
        ev = 0
        # A ^/_ construct requires its base to start at a word boundary,
        # otherwise 'CVT_DG_random_grids_01_12_2025' parses as an exponent.
        # The boundary test looks only at ASCII: a Greek letter is a boundary,
        # or 'Σq^{−n_i}' would lose its exponent because Σ is `isalnum`.
        prev = self.text[base_start - 1] if base_start else ""
        at_bound = not (prev == "_" or (prev.isascii() and prev.isalnum()))
        # A bare number never takes an argument list: '155(3)' is a journal
        # volume and issue, not a function of three.
        may_take_args = base_kind is not _T_NUM
        while k < self.n:
            tk = self.t[k]
            if tk.s != glue_end:
                break
            if tk.kind in (_T_SUP, _T_SUB):
                ev |= SYM | SCRIPT
                glue_end = tk.e
                k += 1
                continue
            if tk.kind in (_T_CARET, _T_UNDER):
                if not at_bound:
                    break
                r = self._script_arg(k + 1, tk.e)
                if r is None:
                    break
                k, glue_end = r
                ev |= SCRIPT
                continue
            if tk.kind == _T_OPEN and tk.txt in "({":
                if not may_take_args:
                    break
                end_k = self._find_close(k, tk.txt, _MATCH[tk.txt])
                if end_k is None:
                    break
                inner = self.text[tk.e:self.t[end_k].s]
                if not self._args_ok(inner, depth + 1, is_func):
                    break
                if not self._head_takes(base_start, k, ev, inner):
                    break
                k = end_k + 1
                glue_end = self.t[end_k].e
                ev |= ARGS
                continue
            break
        return k, ev, glue_end

    def _script_arg(self, k, glue_end):
        """After ^ or _ : a brace group, or a short token."""
        if k >= self.n or self.t[k].s != glue_end:
            return None
        tk = self.t[k]
        if tk.kind == _T_OPEN or tk.txt in "({":
            # tolerate the library's mismatched typos:  C^{1, β)   q^(−n_i}
            depth = 0
            for j in range(k, self.n):
                c = self.t[j].txt
                if c in "({":
                    depth += 1
                elif c in ")}":
                    depth -= 1
                    if depth == 0:
                        if self.t[j].e - tk.s > 24:
                            return None
                        return j + 1, self.t[j].e
                if self.t[j].s - tk.s > 24:
                    return None
            return None
        # short token: ∞ 2 t d p * ∗ + − exp
        j, seen = k, 0
        end = glue_end
        while j < self.n and self.t[j].s == end and seen < 3:
            t = self.t[j]
            if t.kind in (_T_NUM, _T_GREEK, _T_DBL, _T_OP, _T_SUP, _T_SUB):
                end = t.e
                j += 1
                seen += 1
                continue
            if t.kind == _T_ALPHA:
                if len(t.txt) > 3 and t.txt.lower() not in _SCRIPT_WORDS:
                    return None
                if len(t.txt) > 1:
                    # L_exp-summing : the tail must end at a non-letter, and
                    # must not be another underscore-joined stem word
                    if t.e < len(self.text) and (self.text[t.e].isalpha()
                                                 or self.text[t.e] == "_"):
                        return None
                end = t.e
                j += 1
                seen += 1
                continue
            if t.kind == _T_ARITH and t.txt in "+-−*∗":
                # A SIGN may be followed by an index, but never by a WORD.
                # "W^-1" and "W^−1" both keep their exponent; the "-" of
                # "C^∗-algebras", "H_∞-constrained" and "L_exp-summing" is
                # the compound's hyphen and the index stops before it.
                # Reading it greedily is not merely untidy: this loop ABORTS
                # the whole script argument when a later token fails, so a
                # swallowed hyphen cost "C^∗" and "H_∞" their spans outright.
                # A sign with nothing glued after it is terminal and fine:
                # "weak^∗", "(*)^+", "L⁰_+(Ω, ℱ, ℙ)", "ℝ₊^*;ℝ".
                nx = self.t[j + 1] if j + 1 < self.n else None
                if (nx is not None and nx.s == t.e
                        and nx.kind == _T_ALPHA and len(nx.txt) > 1):
                    break
                end = t.e
                j += 1
                seen += 1
                continue
            break
        if end == glue_end:
            return None
        return j, end

    def _head_takes(self, base_start, k, ev_so_far, inner):
        """A BARE single Latin letter applies only to a short or punctuated
        argument.  'F(D²u)', 'O(1:N)', 'R(3, k)', 'C_b(X)' yes; 'A(H1N1)' in
        "the 2009-10 Influenza A(H1N1) pandemic" no -- an unpunctuated run of
        four alphanumerics is a strain designation, not a function call.
        Only bare letters are policed; once a script has attached (G_T, L⁰_+)
        the head is already notation."""
        head = self.text[base_start:self.t[k].s]
        if ev_so_far or len(head) != 1 or not (head.isascii() and head.isalpha()):
            return True
        body = inner.strip()
        return (len(body) <= 2
                or not body.isalnum()
                or not body.isascii())

    def _args_ok(self, inner, depth, head_is_func=False):
        if not inner.strip():
            return False
        stripped = inner.strip()
        if stripped.isdigit() and len(stripped) >= 4:
            return False                      # (2008) is a year, not an order
        if (head_is_func and len(stripped) <= 3 and stripped.isascii()
                and stripped.isalpha() and stripped.islower()):
            # sinᵃ(px), cos(qx), tan(rt): a juxtaposed product of variables.
            # Gated on the head being an OPERATOR NAME, so that the lowercase
            # English head in "FIFA world cup(tm)" still fails.
            return True
        return _sub_chainlist(inner, depth, False, self.budget) is not None

    # ── terms and chains ─────────────────────────────────────────────────
    _LINKS = (_T_REL, _T_OP, _T_ARITH, _T_COMMA, _T_ELL, _T_DASH)

    def _term(self, k, depth, lenient=False):
        p = self._primary(k, depth, lenient)
        if p is None:
            return None
        nk, ev, notational, is_func = p
        glue_end = self.t[nk - 1].e
        nk, ev2, glue_end = self._postfixes(
            nk, depth, glue_end, self.t[k].s, is_func,
            self.t[k].kind if nk == k + 1 else None)
        ev |= ev2
        if not notational and not (ev2 & (ARGS | SCRIPT)):
            # a bare CapsHead / MixedHead (BSDE, PDE, COVID, MATRIX) is a word
            return None
        return nk, ev, is_func

    def _rhs(self, j, depth, inside, ev_left, glue_w):
        """The operand to the right of a link: a whole maximal chain, or a
        short glued word acting as an operand of a symbol (√dt, sin(x):xdx).

        *glue_w* is the widest such word the caller will accept, 0 for none.
        It used to be a boolean, and the boolean was a TAUTOLOGY -- see the
        note at its call site in _chain."""
        if j >= self.n:
            return None
        # LENIENCE IS EARNED, NOT ASSUMED.  A bracket group is admitted on the
        # strength of merely parsing only when what stands to its left is
        # already notation.  Without this gate a bare number or a bare letter
        # drags in the next bracket for free, and "155(3)" (a journal volume
        # and issue) and "Influenza A(H1N1)" become mathematics.
        c = self._chain(j, depth, inside,
                        lenient=bool(ev_left & (SYM | SCRIPT | ARGS | REL)))
        if c is not None:
            return c
        t = self.t[j]
        if (glue_w and (ev_left & SYM) and t.kind == _T_ALPHA
                and len(t.txt) <= glue_w and t.txt.isascii()
                and t.txt.islower()):
            return j + 1, 0
        return None

    def _letters(self, a_tok, b_tok):
        """Does the token range [a_tok, b_tok) contain a case-bearing letter?"""
        if a_tok >= b_tok or b_tok > self.n:
            return False
        seg = self.text[self.t[a_tok].s:self.t[b_tok - 1].e]
        return any(c.isalpha() for c in seg)

    def _chain(self, k, depth, inside=False, lenient=False):
        key = (k, depth, inside, lenient)
        r = self._ch.get(key, _MISS)
        if r is _MISS:
            # No re-entrancy guard needed: the only recursive path back into
            # _chain on THIS parser is _rhs, always called with depth + 1, so
            # a key is never asked for while it is being computed.
            r = self._ch[key] = self._chain_slow(k, depth, inside, lenient)
        return r

    def _chain_slow(self, k, depth, inside=False, lenient=False):
        b = self.budget
        b[0] -= 1
        if b[0] < 0:
            raise _Exhausted
        if depth > 40:
            return None
        r = self._term(k, depth, lenient)
        if r is None:
            return None
        k0 = k
        k, ev, _f = r
        # A chain entered leniently already stands inside a formula, so its
        # own right-hand operands inherit that standing: the '(2n+1)' of
        # '∑_{n=0}^∞ 1:(2n+1)²' is reached through a bare '1'.
        inherited = SYM if lenient else 0
        spaces = 6
        while k < self.n:
            j = k
            sp = False
            while j < self.n and self.t[j].kind == _T_SP:
                sp = True
                j += 1
            if j >= self.n:
                break
            link = self.t[j]
            prev_end = self.t[k - 1].e

            if link.kind in self._LINKS:
                j2 = j + 1
                runs = 0
                while (j2 < self.n and runs < 2
                       and self.t[j2].kind in (_T_ARITH, _T_ELL, _T_DASH)
                       and self.t[j2].s == self.t[j2 - 1].e):
                    j2 += 1
                    runs += 1
                sp2 = False
                while j2 < self.n and self.t[j2].kind == _T_SP:
                    sp2 = True
                    j2 += 1
                uni = not link.txt.isascii()
                is_rel = (link.kind == _T_REL
                          or (link.kind == _T_OP and link.txt in _REL_UNI))
                # the link itself is context for the operand it introduces:
                # in 'H∈(0, 1:2)' the '∈' is what makes the bracket notation
                # GLUE_W is how wide a loose word this link will accept as
                # its right operand, and it used to be a boolean named GLUED
                # meaning "no space between this link and its operand".
                # It used to be computed as `self.t[j2].s == self.t[j2-1].e`
                # AFTER the whitespace-skip loop above had already advanced
                # j2 past the spaces -- and _tokenize emits gapless tokens,
                # so that expression is a constant True for every j2 >= 1.
                # Measured: 0 of 75,850 adjacent token pairs over 4,000 real
                # titles have s != e.  The flag meant to say "no space here"
                # could never say no, which let the short-word escape in
                # _rhs reach across a space and claim an English word:
                # "Bounds when n ≤ the sample size" -> ['n ≤ the'].
                #
                # Two further restrictions, both from the same principle --
                # the escape exists for a juxtaposed FACTOR (√dt, :xᵇdx) and
                # for nothing else:
                #   * a RELATION takes a term, and tolerates at most a
                #     two-letter differential: "d[X, X]ₜ=dt" is one real
                #     library formula and "σ∈the", "σ=the", "5€per" are not
                #     English anybody writes.  Three characters was the width
                #     that let an article through.
                #   * a HYPHEN is the adjectival construction, whose settled
                #     convention is the symbol alone: "α-stable" -> ['α'],
                #     and so "κ-gon" -> ['κ'], not ['κ-gon'].
                if sp2 or link.txt == "-":
                    glue_w = 0
                elif is_rel:
                    glue_w = 2
                else:
                    glue_w = 3
                rhs = self._rhs(j2, depth + 1, inside,
                                ev | inherited | (SYM if uni else 0)
                                | (REL if is_rel else 0),
                                glue_w=glue_w)
                if rhs is None:
                    break
                nk, ev2 = rhs
                if link.kind == _T_DASH:
                    # An en dash joins two NOTATIONAL terms and nothing else.
                    # The test was SYM on both sides, which reads a superscript
                    # as notation and an explicit "^q" as not, so "L^q–Lᵖ" tore
                    # in two while "Lᵖ–L^q" would not.  _ss is the same
                    # question asked of the whole evidence set.  Measured: over
                    # 25,049 titles this joins exactly 2 more, both real
                    # ("L^q–Lᵖ"), and leaves every bibliographic dash alone --
                    # "1915–2002", "1059–1073", "2009–10", "Itô–Clifford",
                    # "x–ens", "Erdős–Mordell", "Chapters (1)–(4)".
                    if not (self._ss(ev) and self._ss(ev2)):
                        break
                elif link.kind == _T_COMMA and not inside:
                    if not ((ev & SYM) and (ev2 & SYM)):
                        break
                if (sp or sp2) and not inside:
                    if uni:
                        pass
                    elif is_rel:
                        # A RELATION across a space is the same statement as a
                        # relation without one: "0<d<2" and "0 < d < 2" are one
                        # expression written two ways, and a detector that
                        # answers differently makes maintenance/conformance.py
                        # report a pure typography change as a rewrite.  The
                        # old test demanded SYM/SCRIPT/ARGS/BRK on one side,
                        # which bare digits and bare letters never carry, so
                        # the spaced spelling was refused outright -- 9 real
                        # occurrences in the library, including the two "(5 2)
                        # proofs that (n k) leq (n k+1) if k < n:2" titles.
                        #
                        # What replaces it is not "nothing".  A span has to
                        # DEFEND something: relaxing this the whole way made
                        # "Volume 3 = 4 pages" claim "3 = 4" and "Is 1 = 2
                        # provable?" claim "1 = 2" -- spans of digits and an
                        # operator, not one character of which a caser could
                        # get wrong.  So one side must carry a LETTER.
                        if not (self._ss(ev) or self._ss(ev2)
                                or self._letters(k0, k)
                                or self._letters(j2, nk)):
                            break
                    elif not (self._ss(ev) and self._ss(ev2)):
                        break
                    spaces -= 1
                    if spaces < 0:
                        break
                ev |= ev2
                if uni:
                    ev |= SYM
                if is_rel:
                    ev |= REL
                k = nk
                continue

            # juxtaposition
            if sp and not inside and (link.kind == _T_OPEN
                                      or link.txt in _MATCH):
                break                      # "Lᵖ (p>1)" is two spans, not one
            rhs = self._rhs(j, depth + 1, inside, ev | inherited,
                            glue_w=3 if link.s == prev_end else 0)
            if rhs is None:
                break
            nk, ev2 = rhs
            if sp and not inside:
                if not (self._ss(ev) and self._ss(ev2)):
                    break
                spaces -= 1
                if spaces < 0:
                    break
            ev |= ev2
            k = nk
        return k, ev

    @staticmethod
    def _ss(ev):
        return bool(ev & (SYM | SCRIPT | ARGS | BRK))

# ───────────────────────────────────────────────────────────────── trimming ──


def _trim(text, s, e):
    while s < e and (text[s].isspace() or text[s] in ",;.·"):
        s += 1
    while e > s and (text[e - 1].isspace() or text[e - 1] in ",;.·"):
        e -= 1
    changed = True
    while changed and s < e:
        changed = False
        a, b = text[s], text[e - 1]
        if a in _MATCH and _MATCH[a] == b and _wraps(text, s, e):
            s, e, changed = s + 1, e - 1, True
            continue
        if b in "([{" or (b in "<|‖" and a not in "<|‖"):
            e, changed = e - 1, True          # trailing unmatched opener: [0, ∞[
            continue
        if a in "([{" and text.count(_MATCH[a], s, e) < text.count(a, s, e):
            s, changed = s + 1, True          # leading unmatched opener
            continue
        if a in ")]}":
            s, changed = s + 1, True
            continue
        while s < e and (text[s].isspace() or text[s] in ",;."):
            s, changed = s + 1, True
        while e > s and (text[e - 1].isspace() or text[e - 1] in ",;."):
            e, changed = e - 1, True
    return s, e


def _wraps(text, s, e):
    """True iff the bracket opening at s is closed exactly at e-1."""
    o, c = text[s], _MATCH[text[s]]
    if o == c:
        return text.count(o, s + 1, e - 1) == 0
    d = 0
    for i in range(s, e):
        if text[i] == o:
            d += 1
        elif text[i] == c:
            d -= 1
            if d == 0:
                return i == e - 1
    return False

# ────────────────────────────────────────────────────────────────── LaTeX ──
#
# THE DECISION, and why it is not "the library has none so drop it".  The
# library really does have none: 0 of 25,049 unique reliable titles contain a
# "$", a backslash or a "\begin{", measured, not assumed.  But find_math_regions
# is not read by the library, it is read by CODE, and two of those readers are
# live on the filing path:
#
#   processing/move_normalizer.py -> validators/filename_checker/core.py:224
#       find_math_regions(title_wo_ext) directly, and :345 the sentence caser
#       -> core/sentence_case.py:274 -> core/math_tokenization.py:123, whose
#       contract is ONE MATH token per formula
#   utils.find_bad_dash_patterns -> core/tokenization.py:55 mask_math_regions
#
# and the titles they see come from processing/ingest.py, which takes them
# from arXiv and Crossref.  Those are LaTeX sources.  ingest._unlatex converts
# accent commands only -- "$", "\alpha" and "\[" pass through it untouched --
# so a dollar-delimited formula reaches the caser intact.
#
# Parsing the payload with the ordinary grammar and leaving the delimiters
# outside, which is what happened before this phase existed, is the WORST of
# the three options: "\[f(x) = x^2\]" gave one span "f(x) = x^2" and spilled
# "\", "[", "]" into the prose stream a caser may rewrite, and
# "\begin{equation} E = mc^2 \end{equation}" gave "mc^2" and dropped "E = " into
# prose.  So: claim the whole formula, delimiters included, or claim nothing.
#
# A "$" is the one delimiter with a competing reading -- money -- and this is a
# mathematical FINANCE library.  So a dollar pair is refused when its payload
# reads as English: "The $5 trillion question and the $100 answer" must not
# have "$5 trillion question and the $" claimed as a formula.  The backslash
# forms have no competing reading and carry no such guard.

_LATEX_RE = re.compile(
    r"\$\$.{1,400}?\$\$"                       # $$…$$ display
    r"|\$[^$]{1,400}\$"                         # $…$   inline
    r"|\\\[.{1,400}?\\\]"                       # \[…\]  display
    r"|\\\(.{1,400}?\\\)"                       # \(…\)  inline
    r"|\\begin\{([A-Za-z][A-Za-z*]{0,15})\}.{0,400}?\\end\{\1\}"
    # \alpha  \mathbb{R}  \mathbb{R}^n  \alpha_i -- a command carries its own
    # scripts, or the span is a PARTIAL one, which is the outcome this phase
    # exists to remove.
    r"|\\[A-Za-z]+(?:\{[^{}]{0,60}\})*"
    r"(?:[\^_](?:\{[^{}]{0,60}\}|[A-Za-z0-9]))*"
    , re.DOTALL)

_TEX_WORD_RE = re.compile(r"[A-Za-z]{3,}")
_TEX_CMD_RE = re.compile(r"\\[A-Za-z]+")


def _tex_is_prose(body: str) -> bool:
    r"""Two or more ordinary English words between dollars is money or a typo.

    Counted after LaTeX command names are removed, and after the operator and
    index names this module already knows are discounted, so "\alpha \leq
    \beta", "\sum_{i=1}^{n} x_i" and "x + y = z" all read as formulas while
    "5 trillion question and the " does not.
    """
    words = [w for w in _TEX_WORD_RE.findall(_TEX_CMD_RE.sub(" ", body))
             if w.lower() not in _FUNCS and w.lower() not in _SCRIPT_WORDS]
    return len(words) >= 2


def _latex_spans(text: str):
    """Whole delimited formulas, delimiters included."""
    if "$" not in text and "\\" not in text:
        return []
    out = []
    for m in _LATEX_RE.finditer(text):
        w = m.group(0)
        if w[0] == "$" and _tex_is_prose(w.strip("$")):
            continue
        out.append(m.span())
    return out


# ─────────────────────────────────────────────────────── extra productions ──

#: The tail is a UNICODE letter run, not an ASCII one.  Written [A-Za-z]{2,}
#: it needed two unaccented characters at the head of the following word, so
#: "G-Lévy" lost its G while "G-BSDEs" and "G-Sobolev" kept theirs -- the
#: decision was made by where the accent fell, not by the operational
#: definition.  5 real library titles.
#:
#: The lookbehind rejects a COMBINING MARK as well as a letter.  macOS hands
#: back NFD (CLAUDE.md trap #8) and src/maintenance/conformance.py:149 passes
#: a title straight in; under NFD the accent of "Erdős" is a separate
#: codepoint, so the "s" after it looked like a word-initial single letter and
#: "Erdős–Mordell" was claimed as maths.  Measured: 22 of the 3,060 accented
#: library titles answered differently under NFD than under NFC.
_COMBINING = "\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff\u20d0-\u20f0\ufe20-\ufe2f"
#: U+2212 MINUS sits in the class beside U+002D, U+2010, U+2011, U+2013.  It
#: was missing, and the hole ran OPPOSITE to the "2M-X" refusal: there the
#: plain hyphen is mute and U+2212 speaks, here U+2212 was mute and the
#: hyphen spoke, so "G-martingales" gave ['G'] and "G−martingales" gave [].
#: Both break the co-variance clause; see THE HYPHEN for the sweep.
_ADJ_RE = re.compile(
    r"(?<![^\W\d_])(?<![" + _COMBINING + r"])"
    r"([A-Za-z])[-‐‑–−](?=[^\W\d_]{2,})")


def _adjectival(text, claimed):
    out = []
    for m in _ADJ_RE.finditer(text):
        i = m.start(1)
        if claimed[i]:
            continue
        prev = text[i - 1] if i else " "
        # "arm's-length" -- the letter is the tail of the word before it.
        # An apostrophe that OPENS a quotation is a different animal, and the
        # library holds one: the case of the 'N-graph'.  A possessive
        # apostrophe follows a letter; an opening quote does not.
        if prev in "'\u2019\u02bc" and i >= 2 and text[i - 2].isalpha():
            continue
        # "lost-in-a-forest" -- a letter that is also a word, sitting BETWEEN
        # hyphens, is part of an English compound and not a variable.  The
        # test is confined to those letters, because "Semi-G-normal" and
        # "Semi-alpha-stable" put a genuine symbol in exactly that position.
        if prev in "-\u2010\u2011\u2013\u2014\u2212" and m.group(1) in _WORDY_LETTERS:
            continue
        j = m.end(1) + 1
        k = j
        while k < len(text) and text[k].isalpha():
            k += 1
        tail = text[j:k]
        if tail.lower() in _ADJ_STOP or _ROMAN_RE.match(tail):
            continue
        out.append((i, i + 1))
    return out


#: A name GLUED to a run of two or more "+".  English never writes one (the
#: brace rule's argument), so the run is notation, and the name it is glued
#: to is the same token: lowercasing "Gauss2" out of "Gauss2++" is as wrong
#: as lowercasing the "+".  This is the CO₂ case, admitted on the same
#: ground rather than on a claim that C++ is mathematics, and it does not
#: collide with title_normalize's acronym branch, which owns BARE acronyms.
#:
#: Measured over the 25,049 titles: FIVE occurrences, all names whose case
#: must survive -- "Le langage C++", "Freefem++", "the calibrated CIR++
#: stochastic intensity model", "The Gauss2++ model", "The variance γ++
#: process".  Zero false positives.  A SINGLE trailing "+" is not enough:
#: 27 titles glue one to a word and they are ordinary arithmetic ("1+1",
#: "3x+1", "(n k+1)", "C^{1+α}"), where it is a link with an operand after
#: it and the grammar has already had its say.
_PLUSPLUS_RE = re.compile(r"(?<![^\W_])[^\W_]+\+{2,}")


def _plusplus(text):
    return [m.span() for m in _PLUSPLUS_RE.finditer(text)]


def _echo(text, spans, claimed):
    """A single capital already used as a base in this title, standing alone."""
    bases = set()
    for s, e in spans:
        for ch in text[s:e]:
            if ch.isalpha() and ch.isascii():
                bases.add(ch)
    bases -= _WORDY_LETTERS
    if not bases:
        return []
    out = []
    # A FULL STOP is not an acceptable right boundary.  A single capital
    # followed by one is an author's INITIAL -- "in honour of S. Watanabe and
    # T. Yamada" -- and initials belong to the author-block rule, not here, for
    # the same reason "P.D.E." does: double-owning a decision is worse than
    # under-claiming it.  Measured: 0 occurrences over the 25,049 library
    # titles either way, so this costs nothing and removes a span that was
    # over a person's name rather than over notation.
    for m in re.finditer(r"(?<![^\s(\[])([A-Za-z])(?![^\s,;:)\]])", text):
        ch, i = m.group(1), m.start(1)
        if ch in bases and not claimed[i]:
            out.append((i, i + 1))
    return out

# ──────────────────────────────────────────────────────────────────── main ──


#: Longest input this module will PARSE; beyond it, _refuse.  Set far above
#: every population that reaches the live callers: the longest of the 25,049
#: reliable library titles is 229 characters and processing/ caps a filename
#: at 251.  Measured cost at the bound: 5.3 ms.
MAX_INPUT_CHARS = 1000

#: Parser steps one call may spend before it refuses.  A step is one uncached
#: _chain or one uncached _find_close -- the two loops the time goes into,
#: with every other cost a constant multiple of them.  The bound is on the
#: WHOLE call, one cell shared by every parser built for it.
#:
#: Sized on measurement, not guessed: the worst of the 25,049 library titles
#: spends 52 steps and the worst of 20,000 mutated real titles spends 94.
#: 1,500 is 16x the latter, and holds the worst 251-character adversarial
#: input to 2.0 ms -- inside the 5 ms this may cost in a Streamlit rerun.
MAX_PARSE_STEPS = 1500


def _refuse(text):
    """Refuse to analyse *text*, in the direction that cannot damage it.

    A refusal must not be spellable as "no mathematics here": that is the
    reading a caser ACTS on, and CLAUDE.md non-negotiable 4 forbids "I didn't
    look" and "it's fine" sharing a return value.  So the whole input, less
    its outer whitespace, comes back as ONE protected region, which every
    live consumer reads as hands-off -- mask_math_regions masks the lot,
    math_tokenization emits a single MATH token so sentence_case returns the
    title unchanged, and filename_checker proposes nothing.

    Raising was rejected: this sits under a live Streamlit page and under
    processing/ingest, neither of which catches, so a raise would turn an
    over-long Crossref title into a broken page instead of an unmodified one.
    """
    s, e = 0, len(text)
    while s < e and text[s].isspace():
        s += 1
    while e > s and text[e - 1].isspace():
        e -= 1
    return [(s, e)]


def find_math_regions(text):
    """Return the mathematical regions of *text* as [(start, end), …].

    A NON-STRING RAISES TypeError.  Decided, not accidental, and the one
    place this module refuses LOUDLY rather than safely: an over-long STRING
    can be protected, because there are offsets to hand back and _refuse
    hands back all of them, but a non-string has none, so the only answers
    available are an exception and [].  [] is a lie of the exact shape
    CLAUDE.md non-negotiable 4 forbids -- spelled "I looked, and there is no
    mathematics here", indistinguishable from that answer about a real title,
    and the answer a caser acts on.

    Checked: no live caller can produce one.  filename_checker/core.py:224
    and :273, math_tokenization.py:123, tokenization.py:55 and
    conformance.py:149 each hold a str by the time they call, and
    math_detector.mask_math_regions guards with isinstance first.
    """
    if not isinstance(text, str):
        raise TypeError("find_math_regions() expects str, got %r"
                        % type(text).__name__)
    if not text.strip():
        return []

    # Memo tables are keyed by SUBSTRINGS of this call's input and dropped
    # between calls: a long-lived Streamlit process must not accumulate one
    # entry per title it ever saw.  Clearing here, not at the end, also means
    # a raise inside the parse cannot leave them behind.
    _TOK_CACHE.clear()
    _SUB_CACHE.clear()

    if len(text) > MAX_INPUT_CHARS:
        return _refuse(text)

    try:
        return _regions(text)
    except _Exhausted:
        return _refuse(text)


def _regions(text):
    # LaTeX first, and MASKED OUT of what the grammar sees.  A formula is one
    # region with its delimiters, and the grammar must not be able to re-derive
    # a smaller, delimiter-less region from the same characters -- that is the
    # partial-span failure this phase exists to remove.  Masking to spaces
    # preserves every offset, so the spans still index the string as passed in.
    tex = _latex_spans(text)
    if tex:
        buf = list(text)
        for a, b in tex:
            buf[a:b] = " " * (b - a)
        text_g = "".join(buf)
    else:
        text_g = text

    toks = _tokenize(text_g)
    p = _P(text_g, toks)

    spans = []
    k = 0
    while k < p.n:
        tk = toks[k]
        if tk.kind in (_T_SP, _T_OTHER, _T_CLOSE):
            k += 1
            continue
        r = p._chain(k, 0)
        if r is None:
            k += 1
            continue
        nk, ev = r
        if nk <= k:
            k += 1
            continue
        if ev & _ANY_EVIDENCE:
            s, e = _trim(text_g, tk.s, toks[nk - 1].e)
            if e > s:
                spans.append((s, e))
            k = nk
        else:
            k += 1                       # no evidence: rescan from next token

    spans = _merge(spans)
    claimed = bytearray(len(text))
    for s, e in spans:
        claimed[s:e] = b"\1" * (e - s)

    extra = _adjectival(text_g, claimed)
    for s, e in extra:
        claimed[s:e] = b"\1" * (e - s)
    spans = _merge(spans + extra)

    spans = _merge(spans + _echo(text_g, spans, claimed))
    # after _echo on purpose: "C++" must not make a bare "C" elsewhere in the
    # title an echo base -- a decision the grammar has not made.
    spans = _merge(spans + _plusplus(text_g))
    spans = _snap_to_tokens(text_g, spans)
    return [(s, e) for s, e in _merge(spans + tex) if e > s]


def _snap_to_tokens(text, spans):
    r"""Never hand back a span that begins or ends in the middle of a word.

    core/math_tokenization.py walks the title with a word scanner and keeps a
    region only if the scanner lands exactly on its start; a region starting
    mid-word is silently dropped, with no error and no counter.  Three titles
    here are in that shape -- 'BSΔEs', 'FBSΔEs', 'THεO' -- where a Greek
    letter sits inside an otherwise Latin token.  Widening to the whole token
    is also the right answer on the merits: 'Bsδes' is as wrong as 'bsΔes'.
    The absorbed material is capped at four ASCII letters a side so that this
    can never reach out and swallow an English word.

    A "word" here is a run the GRAMMAR reads as letter-like, not a run of
    \w.  Written with \w the rule was decided by the Unicode category of the
    interloper: 'BSΔEs' snapped because U+0394 GREEK CAPITAL DELTA is a
    letter, 'BS∆Es' did not because U+2206 INCREMENT is a symbol -- two
    spellings of one word answering differently, which is the contract's
    co-variance clause.  2 library titles use the U+2206 spelling and lost
    their 'BS' and their 'Es' to the caser for it.
    """
    if not spans:
        return spans
    toks = _wordish_runs(text)
    out = []
    for a, b in spans:
        for ts, te in toks:
            if ts < a < te and a - ts <= 4 and text[ts:a].isascii():
                a = ts
            if ts < b < te and te - b <= 4 and text[b:te].isascii():
                b = te
        out.append((a, b))
    return _merge(out)


#: Kinds that stand INSIDE a word for _snap_to_tokens: the letter-like ones
#: plus the operator symbols, which is what makes U+2206 behave as U+0394
#: does.  The LINK kinds (_T_ARITH, _T_REL, _T_DASH) are deliberately out, or
#: 'a+b' and '0<d<2' would be single words and the cap on absorbed material
#: would start reaching across operators.
_WORDISH = frozenset((_T_ALPHA, _T_GREEK, _T_DBL, _T_SUP, _T_SUB, _T_NUM,
                      _T_OP))


def _wordish_runs(text):
    """[(start, end), …] of maximal letter-like runs, underscore included."""
    out = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "_" or _classify(ch) in _WORDISH:
            j = i + 1
            while j < n and (text[j] == "_" or _classify(text[j]) in _WORDISH):
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def _merge(spans):
    if not spans:
        return []
    spans = sorted(spans)
    out = [list(spans[0])]
    for s, e in spans[1:]:
        if s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(s, e) for s, e in out]


# ────────────────────────────────────────────────────────────── self-test ──
_CASES = [
    # ── positives: the grammar's productions, one line each ──────────────
    ("L^2 estimates for the d-bar operator",         ["L^2", "d"]),
    ("On L²-projection on a space of stochastic integrals", ["L²"]),
    ("W^{2,p} and W^{1,p}-estimates at the boundary",     ["W^{2,p}", "W^{1,p}"]),
    ("Existence of viscosity solutions in ℝⁿ",            ["ℝⁿ"]),
    ("Conditional analysis on ℝᵈ",                        ["ℝᵈ"]),
    ("A class of special L_∞ spaces",                     ["L_∞"]),
    ("Monetary utility functions on C_b(X) spaces",       ["C_b(X)"]),
    ("Sharp inequalities for martingales with values in lᴺ_∞", ["lᴺ_∞"]),
    ("Muckenhoupt’s (Aₚ) condition",                       ["Aₚ"]),
    ("β variables as times spent in [0, ∞[",              ["β", "0, ∞"]),
    ("The tracking error rate of the Δ–Γ hedging strategy", ["Δ–Γ"]),
    ("Le théorème de Pitman, le groupe quantique SU_q(2)", ["SU_q(2)"]),
    ("two AR(1) processes",                               ["AR(1)"]),
    ("A continuous time GARCH(p, q) process with delay",  ["GARCH(p, q)"]),
    ("Viscosity solutions in proper CAT(0) spaces",       ["CAT(0)"]),
    ("Une construction du groupe de Fischer Fi(24)",      ["Fi(24)"]),
    ("La conjecture de Langlands locale pour GL(3)",      ["GL(3)"]),
    ("on p-adic L-functions of GL(2)×GL(2) over totally real fields",
     ["p", "L", "GL(2)×GL(2)"]),
    ("Why is the effect of transaction costs O(δ^⅔)?",    ["O(δ^⅔)"]),
    ("A game-theoretic explanation of the √dt effect",    ["√dt"]),
    ("excursions of a d-dimensional Bessel process (0<d<2)", ["d", "0<d<2"]),
    ("Weighted Lᵖ (p≥1) solutions of random time horizon BSDEs", ["Lᵖ", "p≥1"]),
    ("Many proofs that Σ_{n=1}^∞ 1:n² = π²:6 can be found",
     ["Σ_{n=1}^∞ 1:n² = π²:6"]),
    ("The stochastic equation Yₜ₊₁=AₜYₜ + Bₜ with non-stationary coefficients",
     ["Yₜ₊₁=AₜYₜ + Bₜ"]),
    ("Regularity for viscosity solutions of fully nonlinear equations F(D²u)=0",
     ["F(D²u)=0"]),
    ("An {l₁, l₂, l_∞}-regularization approach",           ["l₁, l₂, l_∞"]),
    ("Les intervalles de constance de <X, X>",             ["X, X"]),
    ("A direct proof of the irrationality of tan²(rπ)",    ["tan²(rπ)"]),
    ("Packing 1.35⋅10¹¹ rectangles into a unit square",    ["1.35⋅10¹¹"]),
    ("Semi–G-normal, a hybrid between normal and G-normal", ["G", "G"]),
    ("Universal approximation theorem for deep Q-learning", ["Q"]),
    ("An α-potential game framework for N-player games",   ["α", "N"]),
    ("Sur la fonction ζ de Riemann, 2",                    ["ζ"]),
    ("The Riesz representation theorem and weak^∗ compactness", ["weak^∗"]),
    ("A direct construction of the Wiener measure on C[0, ∞)", ["C[0, ∞)"]),
    ("Hadamard functions of inverse M-matrices",           ["M"]),
    ("dimension d≥2",                                      ["d≥2"]),
    ("The heat equation in L_q((0, T), Lₚ)-spaces",        ["L_q((0, T), Lₚ)"]),
    ("coefficients in (y,z)",                              ["y,z"]),

    # ── negatives: everything the grammar must refuse ────────────────────
    ("(Almost) Everything you always wanted to know about CDO tranches", []),
    ("Strongly quasiconvex functions, what we know (so far)", []),
    ("Reflected backward SDEs with general jumps (in Russian)", []),
    ("Fast hybrid schemes for fractional Riccati equations "
     "(rough is not so tough)", []),
    ("A semigroup point of view on splitting schemes for stochastic "
     "(partial) differential equations", []),
    ("Optimally deceiving a learning leader in Stackelberg games (NeurIPS)", []),
    ("The Fourier–Malliavin volatility (FMVol) MATLAB library", []),
    ("Laurent Schwartz (1915–2002)", []),
    ("Option pricing using Câma and Heston (2008)'s model", []),
    ("Séminaire Bourbaki, volume 2012:2013, exposés 1059–1073", []),
    ("proceedings of the IFIP-WG 7:1 working conference", []),
    ("Bounds for VIX futures given S&P 500 smiles", []),
    ("A note on a PDE approach to option pricing under XVA", []),
    ("Ending the COVID-19 epidemic in the United Kingdom", []),
    ("solving semilinear parabolic differential equations in 1D and 2D", []),
    ("2017 MATRIX annals", []),
    ("Time-consistent asset allocation for risk measures in a Lévy market", []),
    ("The Itô–Clifford integral", []),
    ("L’économie du principe de précaution", []),
    ("Sobolev regularity for the Monge−Ampère equation", []),
    ("≪ Les précurseurs de la société de statistique de Paris ≫ (1909)", []),
    ("A P.D.E. approach to Asian options", []),
    ("école d'été de probabilités de Saint-Flour XL, 2010", []),
    ("Exercices de mathématiques oraux x–ens, algèbre 1", []),
    ("Naïve Markowitz policies", []),
    ("Quasilinearization methods for nonlocal fully-nonlinear parabolic "
     "systems", []),
    ("Open-loop and closed-loop solvabilities for zero-sum stochastic "
     "linear quadratic differential games", []),
    ("CVT_DG_random_grids_01_12_2025", []),
    ("affine_structure_signature", []),
    ("Rethinking the FIFA world cup(tm) final draw", []),
    ("Theory of function spaces III", []),
    ("Risk-neutral option pricing under GARCH intensity model", []),
    ("Markovian lifting and asymptotic log-Harnack inequality", []),
    ("Direct influences of Ars conjectandi in 18th century Great Britain", []),
    ("Mathématique, nº4 - 28 janvier 1987", []),
    ("From probability to geometry (II), volume in honor of the 60th "
     "birthday of Jean-Michel Bismut", []),
    ("Spatial branching processes, superprocesses and snakes (slides)", []),
    ("The evolutionary game of pressure (or interference), resistance", []),

    # ── grafted from the two runner-up designs, and from a library audit ─
    # Each of these was WRONG in the design this one is built on, and each
    # was fixed by borrowing a rule one of the runner-up designs had.
    ("The equivalence of axiom (*)^+ and axiom (*)^{++}",
     ["(*)^+", "(*)^{++}"]),
    ("Arrêt par régions de {Sₙ:n, n € N²}",       ["Sₙ:n, n € N²"]),
    ("On the expansion 1 = Σq^{−n_i}",             ["1 = Σq^{−n_i}"]),
    ("H₂:H_infty control for continuous-time mean-field stochastic systems",
     ["H₂:H_infty"]),
    ("Evaluation of the multiple ζ values ζ(2, ..., 2, 3, 2, ..., 2)",
     ["ζ", "ζ(2, ..., 2, 3, 2, ..., 2)"]),
    ("A unique method to evaluate the general integral "
     "∫₀^∞ sinᵃ(px)cosᶜ(qx):xᵇdx", ["∫₀^∞ sinᵃ(px)cosᶜ(qx):xᵇdx"]),
    ("BSΔEs and BSDEs with non-Lipschitz drivers, comparison and convergence",
     ["BSΔEs"]),
    ("A direct construction of the Wiener measure on C[0, ∞)", ["C[0, ∞)"]),
    ("Dynamic programming for the stochastic matching model, the case of "
     "the 'N-graph'", ["N"]),
    ("Estimation of volatility functionals, the case of a √n window", ["√n"]),
    ("eps_i and eps_j are the same expression as εᵢ and εⱼ",
     ["eps_i", "eps_j", "εᵢ", "εⱼ"]),
    ("Sur l'indépendance d'un temps d'arrêt T et de la position B_T "
     "d'un mouvement brownien", ["T", "B_T"]),
    # negatives found by reading all 415 distinct region shapes this detector
    # produces over the 25,049 library titles
    ('Remark on the paper "Entropic value-at-risk", J. Opt. Theory and '
     'Appl., 155(3) (2001), 1105-1123', []),
    ("Excess mortality during the 2009–10 Influenza A(H1N1) pandemic", []),
    ("A general solution to Bellman’s lost-in-a-forest problem", []),
    ("Delegated monitoring versus arm’s-length contracting", []),
    ("V-, U-, L-, or W-shaped recovery after COVID? Insights from an "
     "age-structured model", []),
    ("Optimizing S-shaped utility and implications for risk management", []),

    # ── the repairs, one regression case each ────────────────────────────
    # (a) U+002D is a LINK, and must decompose exactly as U+2212 does.
    ("2J_s-R_s",                                   ["2J_s-R_s"]),
    ("2J_s−R_s",                              ["2J_s−R_s"]),
    ("A variant on (2Jₛ-Rₛ, s≥0) for processes",
     ["2Jₛ-Rₛ, s≥0"]),
    ("A variant on (2Jₛ−Rₛ, s≥0) for processes",
     ["2Jₛ−Rₛ, s≥0"]),
    ("The space W^-1 of distributions",             ["W^-1"]),
    ("The space W^−1 of distributions",        ["W^−1"]),
    ("The space W^{-1} of distributions",           ["W^{-1}"]),
    ("Random walks with exact boundaries g(t)=c√(t+b)-a",
     ["g(t)=c√(t+b)-a"]),
    # …and must stay MUTE, or a page range and a compound become mathematics.
    ("Entropic value-at-risk, 155(3) (2001), 1105-1123",            []),
    ("A version of Pitman's 2M-X theorem for geometric Brownian motions", []),
    ("Time-consistent asset allocation for risk measures",          []),
    ("Open-loop and closed-loop solvabilities",                     []),
    # a script index may carry a sign, but the sign may not eat the compound
    ("Limits of certain subhomogeneous C^∗-algebras",          ["C^∗"]),
    ("H_∞-constrained incentive Stackelberg games",            ["H_∞"]),
    ("Absolutely L_exp-summing norms of diagonal operators",        ["L_exp"]),

    # (b) LaTeX is ONE region INCLUDING its delimiters, or it is nothing.
    ("The formula $x + y = z$ is simple",           ["$x + y = z$"]),
    ("$$E = mc^2$$",                                ["$$E = mc^2$$"]),
    (r"\[f(x) = x^2\]",                             [r"\[f(x) = x^2\]"]),
    (r"\(a + b\)",                                  [r"\(a + b\)"]),
    (r"\begin{equation} E = mc^2 \end{equation}",
     [r"\begin{equation} E = mc^2 \end{equation}"]),
    (r"$\alpha \leq \beta$",                        [r"$\alpha \leq \beta$"]),
    (r"A $2 \times 2$ matrix and a $3 \times 3$ matrix",
     [r"$2 \times 2$", r"$3 \times 3$"]),
    # a bare command carries its own scripts, or the span is a partial one
    (r"Solutions in \mathbb{R}^n",                   [r"\mathbb{R}^n"]),
    (r"\alpha_i and \beta^2",                        [r"\alpha_i", r"\beta^2"]),
    # the 90-character formula that an 80-character bound once split in six
    (r"The Black-Scholes PDE $\frac{1}{2}\sigma^2 S^2 \frac{\partial^2 V}"
     r"{\partial S^2} + rS\frac{\partial V}{\partial S} = rV$",
     [r"$\frac{1}{2}\sigma^2 S^2 \frac{\partial^2 V}{\partial S^2} + "
      r"rS\frac{\partial V}{\partial S} = rV$"]),
    # a dollar is money before it is a delimiter
    ("The $5 trillion question and the $100 answer",                []),
    ("A $100 bill and a $50 note",                                  []),
    # the grammar does not look INSIDE a formula, so what is written there is
    # not evidence about anything outside it.  Without the mask the Echo rule
    # read "x" out of the payload and then claimed the bare "x" of the prose.
    ("The $x_i$ of x",                              ["$x_i$"]),
    (r"A note on $X^2$ and on X alone",             [r"$X^2$"]),

    # (c) the short-word escape may not reach across a space, nor be a
    #     relation's operand, nor stand after a hyphen.
    ("Bounds when n ≤ the sample size",                        []),
    ("The set of x ∈ the unit ball",                           []),
    ("A cost of 5€ per unit",                                  []),
    ("Σ + the sum",                                            ["Σ"]),
    ("Σ ⋅ the sum",                                       ["Σ"]),
    ("Probability that n points are in convex position in a regular "
     "κ-gon", ["κ"]),
    # …but the escape still exists, for the two things it was built for
    ("Estimation of volatility functionals, the case of a √n window",
     ["√n"]),
    ("A method of evaluating ∫₀^∞ sin(x):xdx",
     ["∫₀^∞ sin(x):xdx"]),
    ("Sur l'équation de structure d[X, X]ₜ=dt-X⁺ₜ₋dXₜ",
     ["d[X, X]ₜ=dt-X⁺ₜ₋dXₜ"]),

    # (d) an all-lowercase word glued to "(" is English, whatever follows it
    ("The role of the author(s) in peer review",                    []),
    ("A model with several player(s) and state(s)",                 []),
    ("The effect(s) of taxation on savings",                        []),
    # a BRACE has no English reading, so a lowercase head is fine before one
    ("Rough Heston, small time expansion of ksqrt{t}",   ["ksqrt{t}"]),

    # (e) the adjectival tail is a UNICODE letter run: an accent in the first
    #     two characters must not decide the answer.
    ("G-Lévy processes under sublinear expectations",          ["G"]),
    ("G-BSDEs with mean constraints in time-dependent intervals",   ["G"]),
    ("Homologie cyclique et K-théorie",                        ["K"]),

    # (f) NFD input answers as NFC does.  macOS hands back NFD.
    ("A family of weighted Erdo\u030bs–Mordell inequality",    []),
    ("Discrete-time approximations of the Holmstro\u0308m-Milgrom model", []),
    ("Les nouveaux ope\u0301rateurs de Caldero\u0301n–Zygmund", []),
    ("G-Le\u0301vy processes under sublinear expectations",         ["G"]),

    # (g) a relation is the same statement spaced or tight -- but a span
    #     still has to defend a case-bearing character.
    ("excursions of a d-dimensional Bessel process (0<d<2)", ["d", "0<d<2"]),
    ("Where 0 < d < 2 holds",                                ["0 < d < 2"]),
    ("Volume 3 = 4 pages",                                          []),
    ("Is 1 = 2 provable?",                                          []),
    ("x + y is fine",                                               []),
    ("signal + noise",                                              []),
    ("a - b",                                                       []),
    ("P vs NP",                                                     []),

    # (h) inside a bracket that already stands inside a formula, a named
    #     space is an operand.  Outside one it is still a word.
    ("XPDE for X€{BS, FBS, P}, a rough volatility context",
     ["X€{BS, FBS, P}"]),
    ("Autour de la dualité (H¹, BMO)",           ["H¹"]),
    ("α-CIR model with branching processes",          ["α"]),
    ("The time-dependent λ-SABR model",               ["λ"]),

    # (i) a two-digit citation year is not an order
    ("A remark on Meyer(98) and his successors",                    []),
    ("Comments on Heston(93)",                                      []),
    # …and the FOUR-digit guard in _args_ok, on a head that can reach it.
    # The case this rule used to cite could not: the space rule killed it one
    # step earlier, so the guard had no test at all.
    ("Une construction du groupe de Fischer Fi(24)",   ["Fi(24)"]),
    ("Une note sur Fi(2008)",                                       []),

    # (j) a single capital before a full stop is an author's initial
    ("Sur la position B_T, in honour of S. Watanabe and T. Yamada", ["B_T"]),
    ("Studies on S_n, edited by S. Kotani and N. Ikeda",            ["S_n"]),

    # an en dash joins two NOTATIONAL terms -- not only two SYM ones
    ("Diffusion processes with L^q–Lᵖ drift",   ["L^q–Lᵖ"]),
    ("Laurent Schwartz (1915–2002)",                           []),
    ("Chapters (1)–(4) of the book",                           []),

    # (k) U+2212 decomposes as "-" does in the Adjectival production.
    ("G-martingales under sublinear expectation",               ["G"]),
    ("G−martingales under sublinear expectation",          ["G"]),
    ("G–martingales under sublinear expectation",          ["G"]),
    ("A general solution to Bellman's lost−in−a−forest problem",     []),
    # …and the one place they still part company, by the definition and not
    # by oversight: bare alphanumerics carry no evidence, U+2212 does.
    ("A version of Pitman's 2M-X theorem",                          []),
    ("A version of Pitman's 2M−X theorem",             ["2M−X"]),

    # (l) a name GLUED to "++" is notation; a single "+" with an operand
    #     after it is arithmetic.
    ("Le langage C++",                                     ["C++"]),
    ("The Gauss2++ model - a comparison",             ["Gauss2++"]),
    ("the calibrated CIR++ stochastic intensity model", ["CIR++"]),
    ("Freefem++",                                     ["Freefem++"]),
    ("The variance γ++ process and applications",          ["γ++"]),
    ("The 3x+1 problem, an overview",                               []),
    ("Theory of relativistic Brownian motion, the (1+1)-dimensional case",
                                                                    []),
    ("A note on (n k+1) and its bounds",                            []),
    # the "++" of an axiom name still reaches the SymbolBracket production
    ("The equivalence of axiom (*)^+ and axiom (*)^{++}",
     ["(*)^+", "(*)^{++}"]),

    # (m) a span widens to the whole WORD, and "word" is the grammar's
    #     notion, not the Unicode category of the interloper.
    ("BSΔEs and BSDEs with non-Lipschitz drivers",       ["BSΔEs"]),
    ("Convergence of BS∆Es driven by random walks",      ["BS∆Es"]),
    ("Fully coupled nonlinear FBS∆Es, maximum principle", ["FBS∆Es"]),
    # …but never far enough to reach an English word
    ("Martin's maximum⁺⁺ implies Woodin's axiom",           ["⁺⁺"]),
]

if __name__ == "__main__":  # pragma: no cover
    bad = 0
    for title, want in _CASES:
        got = [title[a:b] for a, b in find_math_regions(title)]
        if got != want:
            bad += 1
            print("FAIL", repr(title))
            print("   want", want)
            print("   got ", got)
    # ── contract ─────────────────────────────────────────────────────────
    assert find_math_regions("") == [] and find_math_regions("   ") == []

    # a non-str RAISES, and that is a decision (see find_math_regions)
    for junk in (None, 42, b"L^2", ["L^2"]):
        try:
            find_math_regions(junk)
        except TypeError:
            pass
        else:                                               # pragma: no cover
            bad += 1
            print("FAIL: %r did not raise TypeError" % (junk,))

    # a too-LONG input is refused, and a refusal protects everything
    over = "  " + "x + y " * 400 + "  "
    assert len(over) > MAX_INPUT_CHARS
    assert find_math_regions(over) == [(len(over) - len(over.lstrip()),
                                        len(over.rstrip()))]
    assert find_math_regions("x" * MAX_INPUT_CHARS) == []   # exactly at the cap

    # a too-EXPENSIVE input is refused the same way, and no real title can
    # reach it: the worst of the 25,049 costs 52 of the 1,500 steps.
    hard = "(" + ",".join("a" for _ in range(120)) + ")"
    assert len(hard) <= MAX_INPUT_CHARS
    assert find_math_regions(hard) == [(0, len(hard))]

    # …and the 64-character input that cost 455-620 ms before the memo
    import time as _t
    b1 = "(a(b(c(d(e(" * 4 + ")" * 20
    find_math_regions(b1)
    _t0 = _t.perf_counter()
    for _ in range(20):
        find_math_regions(b1)
    _ms = (_t.perf_counter() - _t0) * 1000 / 20
    assert _ms < 25, "B1 regression: %.1f ms" % _ms

    r = find_math_regions("L^2 and L²")
    assert isinstance(r, list) and all(isinstance(x, tuple) for x in r)
    assert r == sorted(r) and all(r[i][1] <= r[i + 1][0] for i in range(len(r) - 1))
    print("%d/%d cases pass, contract OK (B1 input %.2f ms)"
          % (len(_CASES) - bad, len(_CASES), _ms))
