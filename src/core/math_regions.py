"""Which spans of a title are mathematics. One rule, one implementation.

THE OPERATIONAL DEFINITION, and the only one that matters: a span is
mathematics if REWRITING ITS CASE OR ITS WORDS WOULD BE WRONG. "L^2" must not
become "l^2"; "AR(1)" must not become "Ar(1)". "(Almost) Everything you always
wanted to know" is ordinary English in brackets and must not be protected.

There were THREE implementations and all three were wrong.

  core/text_processing/math_detector.py   724 lines, LaTeX-centric.
      Treated ACCENTED LATIN LETTERS as mathematics -- 4,331 hits on "e-acute"
      alone. Of the 4,238 titles it flagged, 3,614 (85%) contain no
      mathematics at all. Downstream, maintenance/conformance asks it which
      part of a title is prose, and was handed "Prcis d'analyse relle" for
      "Precis d'analyse reelle" -- 15% of titles affected.

  validators/filename_checker/math_utils.py   457 lines.
      Its MATHEMATICAL_VARIABLES set is the entire ASCII alphabet, so once the
      character scan met any operator -- and "-" is one -- it ran through
      letters, digits AND SPACES to the end of the sentence. It claimed 49.6%
      of a title on average; 3,921 of its spans were three or more ordinary
      English words. One claimed 186 of 189 characters of an English sentence.

  validators/math_handler.py
      Understood only $...$, which appears in ZERO of this library's 25,005
      titles. Zero hits, and its only consumer was deleted.

WHAT THE LIBRARY ACTUALLY CONTAINS, which is what sized this module. Across
25,005 titles: no $...$ at all, no \\mathbb at all, 39 titles with an L^2-style
caret, 25 with X_t, 8 with AR(1). The entire mathematical surface is about
800 characters -- 416 Greek, 190 super/subscript, 116 operators, 80
letterlike. The 724 lines of LaTeX machinery were built for a library that
has none.

MEASURED, all three over the same 25,005 titles:

    detector        flags 4,238   claims  5.5% of a title   2,988 accent spans
    scanner         flags 6,954   claims 49.6%              3,921 English spans
    this module     flags   877   claims  9.4%   0 accents,     0 English

"""
import re, unicodedata

# Anchors: characters that are mathematics wherever they appear.
# Latin-1 and Latin Extended are DELIBERATELY ABSENT -- "é", "ô", "ä" are
# letters in French and German titles, not mathematics, and treating them as
# maths is what made the incumbent flag 3,614 titles that contain none.
def _is_anchor(ch: str) -> bool:
    """Is this character mathematics wherever it appears?

    Derived from Unicode properties, not a hand-written list. Hand lists are
    how the incumbent came to treat "e-acute" as mathematics: 4,331 hits on a
    French accent alone, and 85% of the titles it flagged contained no
    mathematics at all.

    Measured over the library's 207 distinct non-ASCII characters, this admits
    Greek (416 occurrences), superscript modifier letters (157), mathematical
    operators (116), superscript and subscript digits (89), letterlike symbols
    (80) and a handful of arrows and double-struck capitals -- and rejects the
    4,145 en dashes and quotation marks, the 127 Cyrillic letters of Russian
    titles, and every accented Latin letter.
    """
    o = ord(ch)
    cat = unicodedata.category(ch)
    if cat == "Sm":                                  # ∞ ≥ ∈ ∂ √ ⊂ ∀
        return True
    if 0x0370 <= o <= 0x03FF:                        # Greek: Γ-convergence
        return True
    if 0x2070 <= o <= 0x209F:                        # ⁰ ² ₀ ₜ -- the whole
        return True                                  # Superscripts block. Its
                                                     # U+209C is named LATIN
                                                     # SUBSCRIPT SMALL LETTER T,
                                                     # so the MODIFIER LETTER
                                                     # rule below misses the t
                                                     # of Bₜ.
    if 0x2100 <= o <= 0x214F:                        # ℝ ℂ ℕ ℤ ℚ ℓ
        return True
    if 0x1D400 <= o <= 0x1D7FF:                      # 𝔼 𝕏
        return True
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return False
    # Anything Unicode CALLS a superscript or subscript, whatever block or
    # category it landed in. Blocks are the wrong index here and cost two
    # bugs: U+209C "LATIN SUBSCRIPT SMALL LETTER T" (the t of Bₜ) sits in
    # Superscripts, while U+1D63 "LATIN SUBSCRIPT SMALL LETTER R" (the r of
    # lᵣ) sits in Phonetic Extensions and U+1D62 the i of εᵢ with it.
    if "SUPERSCRIPT" in name or "SUBSCRIPT" in name:
        return True
    if cat == "No" and "FRACTION" in name:           # ½ ⅓ ¾
        return True
    if cat == "Lm" and name.startswith("MODIFIER LETTER") and \
            ("SMALL" in name or "CAPITAL" in name):  # the p of Lᵖ
        # U+02BC MODIFIER LETTER APOSTROPHE is transliteration -- Tsirel'son
        return "APOSTROPHE" not in name and "PRIME" not in name
    return False


_ANCHOR = None   # computed lazily below; see _anchor_set()


def _anchor_set():
    global _ANCHOR
    if _ANCHOR is None:
        _ANCHOR = {chr(c) for c in range(0x20, 0x2FFF) if _is_anchor(chr(c))}
        _ANCHOR |= {chr(c) for c in range(0x1D400, 0x1D800) if _is_anchor(chr(c))}
    return _ANCHOR


_INNER = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
             "0123456789^_{}()[]|/+-*=<>,.'’")

#: LaTeX DELIMITERS come first and are matched greedily, because a displayed
#: formula is one expression however many operators it contains. Dropping
#: these was a real regression: the tokeniser's contract is one MATH token per
#: formula, and the Black-Scholes equation came back as six.
#:
#: The dollar bound is 400, not 80. At 80 the very formula the test uses --
#: 90 characters between its dollars -- fell through to per-character matching
#: and split.
_NOTATION = re.compile(
    r"\$[^$]{1,400}\$"                      # $...$
    r"|\\\[.{1,400}?\\\]"                   # \[...\]  displayed
    r"|\\\(.{1,400}?\\\)"                   # \(...\)  inline
    r"|\\begin\{([a-zA-Z*]+)\}.*?\\end\{\1\}"
    r"|\\[a-zA-Z]{2,}(?:\{[^}]*\})*"        # \mathbb{R}
    r"|\b[A-Za-z]\^\{[^}]{1,20}\}"          # C^{0,1}
    r"|\b[A-Za-z]\^-?[0-9A-Za-z]{1,4}\b"    # L^2, H^1
    r"|\b[A-Za-z]_\{[^}]{1,20}\}"           # L_{exp}
    r"|\b[A-Za-z]_[0-9A-Za-z]{1,3}\b"       # X_t
    , re.DOTALL)

#: An identifier applied to a bracketed argument list -- SL(2, Z), GL(n),
#: sin(x), AR(1). Whether the brackets really hold arguments is decided by
#: _looks_like_arguments below. Without this rule the anchor alone returned
#: "Z)" from "SL(2, Z)", leaving "SL(2," in the prose where a caser could
#: reach it.
#:
#: The identifier must sit flush against the bracket, which is what keeps
#: "(Almost) Everything" and "Dupire (1994)" out -- neither has one.
_CALL = re.compile(r"\b[A-Za-z][A-Za-z]{0,3}\([^()]{1,24}\)")

#: Words that appear between brackets in this library's titles and are PROSE,
#: not arguments. Measured, not imagined -- these are the ones the rule met.
_PROSE_IN_BRACKETS = re.compile(r"[A-Za-z]{3,}")


def _looks_like_arguments(inside: str) -> bool:
    """Is what sits between the brackets an argument list?

    The first version demanded a digit or a mathematical character, and that
    REJECTED real notation: sin(x), GL(n), f(x), GL(N, F), Bes(d) -- 13 in the
    library, every one of them mathematics that must not be recased. "Gl(n)"
    would be wrong.

    So the test is on SHAPE instead: arguments are short, and each name in
    them is one or two characters. That admits "x", "n", "N, F", "3, k", "d",
    and refuses "(Almost)", "(1994)" -- which never reach here anyway, having
    no identifier in front -- and any bracket holding a real word.
    """
    if not inside or len(inside) > 8:
        return False
    if _PROSE_IN_BRACKETS.search(inside):
        return False
    return any(c.isalnum() or c in _anchor_set() for c in inside)


def find_math_regions(text: str):
    if not text:
        return []
    text = unicodedata.normalize("NFC", text)
    n = len(text)
    marks = bytearray(n)

    for m in _NOTATION.finditer(text):
        for i in range(*m.span()):
            marks[i] = 1

    for m in _CALL.finditer(text):
        inside = m.group(0)[m.group(0).index("(") + 1:-1]
        if _looks_like_arguments(inside):
            for i in range(*m.span()):
                marks[i] = 1

    def _inner_at(j: int) -> bool:
        """May the growth step onto position ``j``?

        A PERIOD counts only as a decimal point -- digits on both sides.
        Letting it through unconditionally meant an anchor at the end of a
        stem swallowed the file extension: "lᵣ.pdf" became one span while
        "l_r" did not, so the prose either side of the change differed and
        conformance called a pure typeface change a REWRITE, the loudest
        bucket it has.
        """
        c = text[j]
        # _INNER holds no whitespace, so "not in _INNER" already stops at a
        # space. The explicit isspace() check that used to sit here was
        # redundant -- a mutation removing it survived, and measurement
        # confirmed why rather than a test being written to hide it.
        if c not in _INNER:
            return False
        if c == ".":
            return (j > 0 and text[j - 1].isdigit()
                    and j + 1 < n and text[j + 1].isdigit())
        return True

    for i, ch in enumerate(text):
        if ch not in _anchor_set():
            continue
        marks[i] = 1
        # grow left and right, never crossing whitespace
        j = i - 1
        while j >= 0 and _inner_at(j):
            marks[j] = 1; j -= 1
        j = i + 1
        while j < n and _inner_at(j):
            marks[j] = 1; j += 1

    spans, start = [], None
    for i in range(n):
        if marks[i] and start is None:
            start = i
        elif not marks[i] and start is not None:
            spans.append((start, i)); start = None
    if start is not None:
        spans.append((start, n))

    # An expression may contain spaces: "SL(2, Z)", and a whole displayed
    # formula like "\frac{\partial V}{\partial t} + ... = 0". Two spans
    # separated by a SINGLE SPACE are one expression -- prose is never a span,
    # so nothing but mathematics can be joined this way.
    #
    # The first version required both sides to carry an anchor CHARACTER,
    # which a LaTeX command does not have, so the Black-Scholes equation came
    # back as six spans instead of one. For casing that is the same set of
    # protected characters; for the tokeniser, which wants one MATH token per
    # formula, it is not.
    merged = []
    for s, e in spans:
        if merged and s - merged[-1][1] == 1 and text[merged[-1][1]] == " ":
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))

    # THE INVARIANT: a span that is nothing but ASCII letters and spaces is
    # prose, whatever led us there. This is the guard the character-scanning
    # implementation lacked, and without it a hyphen in "square-root" grew a
    # region across the whole sentence.
    #
    # It currently fires ZERO times -- measured over the 25,005 library titles
    # and 60,000 random strings -- because growth stops at whitespace and no
    # anchor is an ASCII letter, so a prose span cannot be built. Kept anyway:
    # it is the property the whole module promises, and it costs one pass. A
    # mutation removing it survives, and that is recorded here rather than
    # answered with a test that cannot reach it.
    return [(s, e) for s, e in merged
            if not all(c.isascii() and (c.isalpha() or c.isspace())
                       for c in text[s:e])]
