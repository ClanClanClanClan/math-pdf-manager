"""The house convention for mathematics in a title.

Two forms are correct, and which one applies is decided by what Unicode
can actually render:

  * **Unicode when it exists** — ``L^2`` is ``L²``, ``L^p`` is ``Lᵖ``,
    ``X_n`` is ``Xₙ``, ``\\mathbb{R}`` is ``ℝ``.  The library already
    votes this way: 305 filenames use Unicode scripts against 64 still
    carrying a caret, and no filename anywhere uses a LaTeX command.
  * **LaTeX-like when it doesn't** — ``L^∞`` stays, because there is no
    superscript infinity; ``C^{1,α}`` stays, because neither a comma nor
    an alpha has a superscript form.  Braces for a multi-character
    script, bare ``^``/``_`` for a single one, and no spaces inside the
    braces: the space belongs to the prose, not to the expression.

**The rule that matters is all-or-nothing.** An expression converts only
if EVERY character of EVERY one of its scripts has a Unicode form.  The
previous (never-called) converter did it character by character and
produced ``C^{0, α}`` → ``C⁰, α``, where only the digit rises and the
comma and alpha stay on the baseline — which does not mean ``C^{0,α}``,
it means something else entirely.  A partial conversion is worse than
either endpoint, so a single unrepresentable character keeps the whole
expression in LaTeX form.

This module owns typography only.  Deciding WHICH SPANS are mathematics
belongs to ``core.text_processing.math_detector``; prose rules consult
it to keep out, and this module is what may go in.
"""
from __future__ import annotations

import re
import unicodedata

# Explicit, not derived.  Deriving these from Unicode's <super>/<sub>
# decompositions looks clever and is wrong: it maps "a" to "ª" FEMININE
# ORDINAL INDICATOR and "o" to "º" MASCULINE ORDINAL INDICATOR, which are
# not superscript letters at all.  ``verify_maps()`` below asserts every
# glyph really is a superscript/subscript form, so a typo cannot ship.
_SUP = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    "+": "⁺", "-": "⁻", "−": "⁻", "=": "⁼", "(": "⁽", ")": "⁾",
    "a": "ᵃ", "b": "ᵇ", "c": "ᶜ", "d": "ᵈ", "e": "ᵉ", "f": "ᶠ",
    "g": "ᵍ", "h": "ʰ", "i": "ⁱ", "j": "ʲ", "k": "ᵏ", "l": "ˡ",
    "m": "ᵐ", "n": "ⁿ", "o": "ᵒ", "p": "ᵖ", "r": "ʳ", "s": "ˢ",
    "t": "ᵗ", "u": "ᵘ", "v": "ᵛ", "w": "ʷ", "x": "ˣ", "y": "ʸ",
    "z": "ᶻ",
    # "q" has NO superscript form in Unicode.  Neither has any capital
    # beyond a partial set, nor "∞", "α", "λ" — those keep LaTeX form.
    "β": "ᵝ", "γ": "ᵞ", "δ": "ᵟ", "θ": "ᶿ", "χ": "ᵡ",
}
_SUB = {
    "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
    "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
    "+": "₊", "-": "₋", "−": "₋", "=": "₌", "(": "₍", ")": "₎",
    "a": "ₐ", "e": "ₑ", "h": "ₕ", "i": "ᵢ", "j": "ⱼ", "k": "ₖ",
    "l": "ₗ", "m": "ₘ", "n": "ₙ", "o": "ₒ", "p": "ₚ", "r": "ᵣ",
    "s": "ₛ", "t": "ₜ", "u": "ᵤ", "v": "ᵥ", "x": "ₓ",
    # missing on purpose: b c d f g q w y z
    "β": "ᵦ", "γ": "ᵧ", "ρ": "ᵨ", "φ": "ᵩ", "χ": "ᵪ",
}
_MATHBB = {
    "R": "ℝ", "N": "ℕ", "Z": "ℤ", "Q": "ℚ", "C": "ℂ",
    "E": "𝔼", "F": "𝔽", "P": "ℙ", "H": "ℍ", "D": "𝔻",
    "S": "𝕊", "T": "𝕋", "A": "𝔸", "B": "𝔹", "K": "𝕂",
}

#: Operators that may stand immediately before a base without being part
#: of a word: "Σq^{-n}" has base q, but "Il_2" has base l inside a word.
_OPERATORS = "ΣΠ∑∏∫∮∇∂√"

#: base letter, then one or more ``^x`` / ``^{xyz}`` / ``_x`` / ``_{xyz}``.
#:
#: The base is any Unicode letter, not just ASCII: ``\mathbb{R}^d`` is
#: rewritten to ``ℝ^d`` before this runs, and ℝ (like every double-struck
#: capital) must still count as a base or the exponent is stranded.
#:
#: A BARE script is one character that is not followed by more word
#: characters.  Without that guard "H_infty" became "Hᵢnfty" and the raw
#: download "HAL-A_stochastic_maximum_principle" became "HAL-Aₛtochastic"
#: — the underscore there is a word separator, not a subscript.  "(" is
#: excluded too: "e^(|x|²)" opens a group, it is not a one-character
#: exponent, and treating it as one produced "e⁽|x|²)".
#: A bare script is ONE character: anything but whitespace, a bracket, a
#: script mark, or trailing punctuation.  It must include symbols like
#: "∞" that have no Unicode script form.  Excluding them looked harmless
#: — "L^∞" came back unchanged — but only because nothing matched at
#: all, and that accident broke the moment a sibling script DID match:
#: "Σ_{i=1}^∞" became "Σᵢ₌₁^∞", the half-raised form this module exists
#: to prevent.  Matching it and then REFUSING is what makes the
#: all-or-nothing rule real rather than incidental.
#: "(" stays out: it opens a group, so "e^(|x|²)" is not a one-character
#: exponent and treating it as one produced "e⁽|x|²)".
_BARE = r"[^\s{}\[\]\^_,;:()]"

#: A brace group that itself contains a script mark: "2^{-n_k}",
#: "‖X‖_{L^2}", "ℝ^{n_i}".  Nothing inside one may be rewritten.  Without
#: this the INNER expression was converted whenever the OUTER carrier was
#: not matched — a digit or a symbol base — giving "2^{-nₖ}", which is the
#: half-raised form in a different disguise.
_PROTECTED_RE = re.compile(r"\{[^{}]*[\^_][^{}]*\}")
#: ONE pass, not two.  Running an operator-aware second pass afterwards
#: was too late: with "Σq^{−n_i}" the first pass had already refused the
#: outer expression (q sits behind Σ) and eaten the INNER "n_i", giving
#: "Σq^{−nᵢ}" — a half-converted form.  Both lookbehinds are width 1, so
#: they alternate cleanly in a single expression.
#: The trailing (?![\^_]) refuses an expression followed by a DANGLING
#: script mark. "a^1^" was converting to "a¹^", putting a script
#: character hard against a caret — indistinguishable from the
#: half-raised output this module exists to prevent, and unreadable
#: either way. A dangling mark means the notation is corrupt, which is
#: the same class as a nested script or an unbalanced brace, so it gets
#: the same answer: leave it exactly alone and report it.
#: Found by fuzzing, not by the library — no real filename contains it.
_EXPR_RE = re.compile(
    rf"(?:(?<![^\W\d_])|(?<=[{_OPERATORS}]))(?<![0-9])"
    rf"([^\W\d_])"
    rf"((?:[\^_](?:\{{[^{{}}]*\}}|(?:{_BARE})(?![^\W_])))+)"
    rf"(?![\^_])",
    re.UNICODE,
)
_SCRIPT_RE = re.compile(
    rf"([\^_])(?:\{{([^{{}}]*)\}}|((?:{_BARE})))")
_MATHBB_RE = re.compile(r"\\mathbb\s*\{\s*([A-Z])\s*\}")


def verify_maps() -> list:
    """Return the entries whose glyph is not really a script form.

    Cheap enough to run as a test; the point is that a mistyped glyph
    would otherwise be invisible until it reached a filename.
    """
    bad = []
    for src, got in _SUP.items():
        name = unicodedata.name(got, "")
        if not ("SUPERSCRIPT" in name or "MODIFIER LETTER" in name):
            bad.append(("sup", src, got, name))
    for src, got in _SUB.items():
        name = unicodedata.name(got, "")
        if not ("SUBSCRIPT" in name or "MODIFIER LETTER" in name):
            bad.append(("sub", src, got, name))
    return bad


def _as_script(text: str, table: dict) -> str | None:
    """Unicode rendering of ``text``, or None if ANY character lacks one."""
    out = []
    for ch in text:
        got = table.get(ch)
        if got is None:
            return None
        out.append(got)
    return "".join(out)


def _latex(kind: str, content: str) -> str:
    """Braces for a multi-character script, bare mark for a single one."""
    return f"{kind}{{{content}}}" if len(content) > 1 else f"{kind}{content}"


def _rewrite(m: re.Match) -> str:
    base, raw = m.group(1), m.group(2)
    scripts = []
    for sm in _SCRIPT_RE.finditer(raw):
        kind = sm.group(1)
        content = sm.group(2) if sm.group(2) is not None else sm.group(3)
        # An EMPTY script is not "fully representable" — _as_script("")
        # returns "" rather than None, so "L^{}" rendered as "L" and
        # silently deleted characters from the owner's title.
        if not content.strip():
            return m.group(0)
        # " - " inside a script is the author/title separator wandering
        # into a formula ("X_{Doob - Meyer}").  Stripping spaces there
        # welded it shut, which is the one edit that makes a file
        # invisible to every rule downstream.
        if " - " in content:
            return m.group(0)
        # NESTED scripts ("L_{exp_q}", "q^{-n_i}") are beyond this
        # module's grammar.  Guessing produced half-converted output like
        # "q^{−nᵢ}", which is neither form.  Leave the expression exactly
        # as written — ``problems()`` reports it for a human instead.
        if "^" in content or "_" in content:
            return m.group(0)
        # A space inside braces is prose leaking into the expression.
        scripts.append((kind, re.sub(r"\s+", "", content)))
    if not scripts:
        return m.group(0)

    # All-or-nothing across the WHOLE expression, not per script: a base
    # carrying both a sub and a super must not end up half raised, which
    # is how "Σ_{i=1}^∞" would have become "Σᵢ₌₁^∞".
    rendered = []
    for kind, content in scripts:
        got = _as_script(content, _SUP if kind == "^" else _SUB)
        if got is None:
            return base + "".join(_latex(k, c) for k, c in scripts)
        rendered.append(got)
    return base + "".join(rendered)


def _balanced(text: str) -> bool:
    """Braces and parens pair up — otherwise the expression is corrupt."""
    for open_c, close_c in (("{", "}"), ("(", ")"), ("[", "]")):
        if text.count(open_c) != text.count(close_c):
            return False
    return True


def canonicalise(title: str) -> str:
    """Apply the house convention to every expression in ``title``.

    Refuses rather than guesses: a title whose brackets do not pair up is
    returned untouched, because the notation is already corrupt
    ("q^(−n_i}") and any edit would only add a second error on top.
    """
    text = unicodedata.normalize("NFC", title)
    if not _balanced(text):
        return text
    text = _MATHBB_RE.sub(lambda m: _MATHBB.get(m.group(1), m.group(0)), text)
    guarded = [(g.start(), g.end()) for g in _PROTECTED_RE.finditer(text)]

    def _outer_only(m: re.Match) -> str:
        # Never rewrite an expression sitting INSIDE a brace group that
        # already carries a script mark: the outer carrier owns it, and
        # if the outer carrier was not matched (a digit or symbol base)
        # the right answer is to leave the whole thing alone.
        if any(a <= m.start() < b for a, b in guarded):
            return m.group(0)
        return _rewrite(m)

    return _EXPR_RE.sub(_outer_only, text)


def problems(title: str) -> list:
    """Expressions this module deliberately would not touch.

    The point of the standing check is to distinguish "handled" from
    "nobody looked"; a title in here is the second kind and needs a human.
    """
    text = unicodedata.normalize("NFC", title)
    out = []
    if ("^" in text or "_" in text or "\\math" in text) and not _balanced(text):
        out.append("brackets do not pair up")
    # Report on the SAME text canonicalise works on.  Scanning the raw
    # string made problems('\\mathbb{R}^{n_i}') empty while
    # problems('ℝ^{n_i}') was not — the report disagreed with itself
    # depending on how the owner had spelled the same thing.
    scanned = _MATHBB_RE.sub(lambda m: _MATHBB.get(m.group(1), m.group(0)), text)
    for g in _PROTECTED_RE.finditer(scanned):
        out.append(f"nested script in {g.group(0)!r}")
    for m in _EXPR_RE.finditer(scanned):
        for sm in _SCRIPT_RE.finditer(m.group(2)):
            content = sm.group(2) if sm.group(2) is not None else sm.group(3)
            if not content.strip():
                out.append(f"empty script in {m.group(0)!r}")
            elif " - " in content:
                out.append(f"author/title separator inside {m.group(0)!r}")
    return sorted(set(out))


def describe(before: str, after: str) -> str:
    """One-line reason, for a review sheet."""
    if before == after:
        return ""
    if "^" in before or "_" in before:
        return ("converted to Unicode" if "^" not in after and "_" not in after
                else "normalised LaTeX form")
    return "changed"
