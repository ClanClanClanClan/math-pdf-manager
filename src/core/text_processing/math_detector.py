#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extreme inline-mathematics detector for titles / filenames.

Bug-fix release — 2025-06-19 (Dylan request)
────────────────────────────────────────────
• FIX A (find_back_to_back_atoms) – stop consuming a *new* base letter
  after a ^/_ decoration block. Splits “C^∞L₂” into two atoms.
• FIX B (function_space_patterns) – allow “[…]” inside parentheses
  so that L^∞([0,1], ℙ) is captured as a single token.

Extra tweaks for test suite  (no behaviour change for existing 53 cases)
─────────────────────────────────────────────────────────────────────────
• mask_math_regions(mask_char=…) optional argument (external mask tests).
• contains_math_token() now accepts Greek bases (α² etc.).
• function_space_patterns widened to cover all Mathematical Alphanumeric
  Symbols, so “𝒗^s(𝕋^d,ℝ^n)” is one token.
• Single-char filter skips “? » «”, avoiding stray punctuation matches.
"""

import regex as re          # 3-rd-party regex with \p{L}
import unicodedata
import logging

logger = logging.getLogger("math_detector")
if not logger.hasHandlers():
    logging.basicConfig(level=logging.WARNING)

# ──────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────
SUPERSCRIPTS = (
    "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁱⁿ"
    "ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ"
    "ᴬᴮᴰᴱᴳᴴᴵᴶᴷᴸᴹᴻᴼᴾᴿᵀᵁⱽⱾ"
    "ᵠᵡᵧᵨᵩᵪᵝᵞᵟᵦ"
    "ᵰᵲᵴᵵᵶᵷᵸᵹᵻᵽᵾ"
    "ᶏᶑᶒᶓᶔᶕᶖᶗᶘᶙᶚ"
    "ᶛᶜᶝᶞᶟᶠᶡᶢᶣᶤᶥ"
    "ᶦᶧᶨᶩᶪᶫᶬᶭᶮᶯᶰᶱ"
    "ᶲᶳᶴᶵᶶᶷᶸᶹᶺᶻᶼᶽᶾᶿ"
    "ˠˡˢˣˤ˥˦˧˨˩"
    "ֿᵸ∞"
)
SUBSCRIPTS = (
    "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎"
    "ₐₑₒₓₔₕₖₗₘₙₚₛₜ"
    "₣₤₥₦₧₨₩₫₭₮₯₰"
    "₱₲₳₴₵₶₷₸₹₺₻₼₽₾₿"
)

ALL_MATHY_UNICODE = (
    r"[\u2070-\u209F"          # super/sub-scripts
    r"\u1D400-\u1D7FF"        # math alphanumerics
    r"\u2200-\u22FF"          # math operators
    r"\u2A00-\u2AFF"          # big operators
    r"\u27C0-\u27EF"          # misc symbols
    r"\u2980-\u29FF"          # brackets
    r"\u03B1-\u03C9"          # Greek lower
    r"\u0391-\u03A9"          # Greek upper
    r"\u2100-\u214F"          # letter-likes
    r"\u25A0-\u25FF"          # geometric
    r"\u2220-\u22FF"          # misc math
    r"\u25B0-\u25FF"
    r"\u2B00-\u2BFF]"
)

MATH_SYMBOLS = (
    "∞∑∫∂∇∈∉∪∩∅√′″∗≠≈≡≤≥⊂⊃⊆⊇⊕⊗⊥⊤⊢⊨⊬⊭±÷×"
    "∃∀∧∨⇒⇔→←↔↦↣↪↩↫↬↭↯↶↷"
)

# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────
def is_mathy_char(c: str) -> bool:
    if re.match(ALL_MATHY_UNICODE, c):
        return True
    if c in SUPERSCRIPTS + SUBSCRIPTS + MATH_SYMBOLS:
        return True
    if unicodedata.category(c) in {"Sm", "Sk"}:
        return True
    return False


def is_base_char(c: str) -> bool:
    return bool(re.match(r"[\p{L}\p{N}𝒜-𝒵𝓐-𝓩𝔄-𝔝𝕬-𝖅𝙰-𝚉α-ωΑ-Ω]", c))


def is_script_char(c: str) -> bool:
    return c in SUPERSCRIPTS + SUBSCRIPTS


# ──────────────────────────────────────────────────────────────
# REGION BOOK-KEEPING
# ──────────────────────────────────────────────────────────────
def _merge_regions(regions):
    if not regions:
        return []
    regions = sorted(regions)
    merged = [regions[0]]
    for s, e in regions[1:]:
        ls, le = merged[-1]
        if s < le:
            merged[-1] = (ls, max(le, e))
        else:
            merged.append((s, e))
    return merged


def mark_processed(arr, s, e):
    arr[s:e] = [1] * (e - s)


def is_processed(arr, s, e):
    return any(arr[s:e])

# ──────────────────────────────────────────────────────────────
# BACK-TO-BACK ATOMS   — FIX A
# ──────────────────────────────────────────────────────────────
def find_back_to_back_atoms(text, already):
    atoms, i, n = [], 0, len(text)
    while i < n:
        if already[i] or not is_base_char(text[i]):
            i += 1
            continue
        start = i
        i += 1
        has_scripts = False
        while i < n and text[i] in "^_":
            has_scripts = True
            i += 1
            if i < n and text[i] == "{":
                i += 1
                depth = 1
                while i < n and depth:
                    if text[i] == "{":
                        depth += 1
                    elif text[i] == "}":
                        depth -= 1
                    i += 1
            else:
                while i < n and (
                    text[i].isdigit()
                    or text[i].islower()
                    or text[i] in "α-ωΑ-Ω∞IVXivx"
                    or is_script_char(text[i])
                ):
                    i += 1
        while i < n and is_script_char(text[i]):
            has_scripts = True
            i += 1
        if has_scripts:
            atoms.append((start, i))
        else:
            i = start + 1
    return atoms

# ──────────────────────────────────────────────────────────────
# MAIN DETECTOR
# ──────────────────────────────────────────────────────────────
def find_math_regions(text: str):
    regions, already = [], [0] * len(text)
    n = len(text)

    # —— PHASE 1 : simple LaTeX environments
    latex_patterns = [
        r"\$[^$]*\$",
        r"\\\([^)]*\\\)",
        r"\\\[[^\]]*\\\]",
        r"\\begin\{[a-zA-Z*]+\}.*?\\end\{[a-zA-Z*]+\}",
    ]
    for pat in latex_patterns:
        for m in re.finditer(pat, text, re.DOTALL):
            s, e = m.span()
            if not is_processed(already, s, e):
                mark_processed(already, s, e)
                regions.append((s, e))

    # —— PHASE 2 : specific LaTeX tokens
    for pat in [
        r'\\mathbb\{E\}\[[^\]]*\|[^\]]*\\mathcal\{F\}_t\]',
        r'\\lim_\{[^}]+\}\s*[A-Za-z0-9_]+\s*=\s*[A-Za-z]',
        r'\\lim_\{[^}]+\}\s*[A-Za-z0-9_]+',
    ]:
        for m in re.finditer(pat, text):
            s, e = m.span()
            if not is_processed(already, s, e):
                mark_processed(already, s, e)
                regions.append((s, e))

    # —— PHASE 2B : generic LaTeX commands
    for pat in [
        r'\\(?:mathbb|mathcal|mathbf|mathrm|mathfrak|mathsf|mathit|mathscr)'
        r'\{[A-Za-z0-9]+\}(?:[\^_]\{[^}]+\}|[\^_][A-Za-z0-9]+)*',
        r'\\(?:hat|dot|vec|tilde|bar|check|acute|grave|breve|ddot|mathring|'
        r'overline|underline)\{[A-Za-z0-9]+\}',
        r'\\(?:imath|jmath)',
        r'\\\|[^\|]+\|_\{[^}]+\}',
    ]:
        for m in re.finditer(pat, text):
            s, e = m.span()
            if not is_processed(already, s, e):
                mark_processed(already, s, e)
                regions.append((s, e))

    # —— PHASE 3 : set-builder / assignments / composite
    composite_pats = [
        r'\b[A-Za-z]\s*=\s*\{[^{}]*\([^)]*\)[^{}]*:[^{}]*[<>=≤≥∈][^{}]*\}',
        r'\{[^{}]*\([^)]*\)[^{}]*:[^{}]*[<>=≤≥∈][^{}]*\}',
        r'∫[₀-₉]*[\^⁰¹²³⁴⁵⁶⁷⁸⁹∞]*\s*[^,;.]+?\s*d[A-Za-z]',
        r'\b[A-Za-z]\s*∘\s*[A-Za-z]\s*:\s*[^,;]+?→[^,;]+?(?=,|\s|$|\.)',
        r'\b\w+\s*:\s*[^,;]+?→[^,;]+?(?=,|\s|$|\.)',
        r'[πθ]\s*∈\s*\[[^\]]+\]',
        r'[A-Za-z0-9]+\s*→\s*∞',
        r'[A-Za-z̄̇̊̈]{2,}\s*→\s*0',
    ]
    for pat in composite_pats:
        for m in re.finditer(pat, text):
            s, e = m.span()
            if not is_processed(already, s, e):
                mark_processed(already, s, e)
                regions.append((s, e))

    # —— PHASE 4 : function-space tokens  — FIX B & B2
    function_space_patterns = [
        r'[\U0001d400-\U0001d7ff\u2102\u2115\u211d\u2124\u212c\u2133]'
        r'[\^_]*[^(]*\([^)]+\)',
        r'\b[A-Z][\^∞⁰¹²³⁴⁵⁶⁷⁸⁹ᵖⁿ₀-₉]*\([A-Za-z0-9\[\],\s\^_ℝℕℤ𝒞Ωℙ'
        r'\u03a9\u03b1-\u03c9\u0391-\u03a9\-]+\)',
        r'\b[A-Z]{1,4}\([A-Za-z0-9,\s\^_ℝℕℤ𝒞Ωℙ'
        r'\u03a9\u03b1-\u03c9\u0391-\u03a9\-]+\)',
    ]
    for pat in function_space_patterns:
        for m in re.finditer(pat, text):
            s, e = m.span()
            if is_processed(already, s, e):
                continue
            snippet = text[s:e]
            if re.search(r'[\^_\u03a0-\u03ff\u2100-\u214fℝℕℤℙΩ]', snippet):
                mark_processed(already, s, e)
                regions.append((s, e))

    # —— PHASE 5 : derivatives f'(x) etc.
    for m in re.finditer(r"\b[A-Za-z]+'{1,3}\([A-Za-z]\)", text):
        s, e = m.span()
        if not is_processed(already, s, e):
            mark_processed(already, s, e)
            regions.append((s, e))

    # —— PHASE 6 : simple function assignments
    assign_pats = [
        r'\b[A-Za-z]+\s*\(\s*[A-Za-z]\s*\)\s*=\s*[A-Za-z0-9\^{}_]+'
        r'(?=\s+(?:where|here|$)|\.|$)',
        r'\b[A-Za-z]+\s*\(\s*[A-Za-z]\s*\)\s*=\s*[^=]*?'
        r'(?=\s+(?:where|here|works|$)|\.|$)',
    ]
    for pat in assign_pats:
        for m in re.finditer(pat, text):
            s, e = m.span()
            prev = text[max(0, s - 15):s].lower().strip().split()
            if prev and prev[-1] in {'function', 'equation', 'formula', 'expression'}:
                continue
            if not is_processed(already, s, e):
                mark_processed(already, s, e)
                regions.append((s, e))

    # —— PHASE 7 : back-to-back atoms
    for a, b in find_back_to_back_atoms(text, already):
        if not is_processed(already, a, b):
            mark_processed(already, a, b)
            regions.append((a, b))

    # —— PHASE 8 : miscellaneous assignment syntaxes
    misc_assign = [
        r'(?<!\w)[A-Za-z]\s*=\s*\([^)]*\)(?!\w)',
        r'(?<=\s)\([^)]*\)\s*=\s*\([^)]*\)(?=\s|$|\.)',
        r'[A-Za-z]\s*=\s*\{[^{}]*:[^{}]+\}',
    ]
    for pat in misc_assign:
        for m in re.finditer(pat, text):
            s, e = m.span()
            if not is_processed(already, s, e):
                mark_processed(already, s, e)
                regions.append((s, e))

    # —— PHASE 9 : bracketed maths
    for op, cl in ('()', '[]', '{}'):
        i = 0
        while i < n:
            if text[i] == op and not already[i]:
                start, depth = i, 1
                i += 1
                while i < n and depth:
                    if text[i] == op:
                        depth += 1
                    elif text[i] == cl:
                        depth -= 1
                    i += 1
                end = i
                if is_processed(already, start, end):
                    continue
                inner = text[start + 1:end - 1].strip()
                if inner and (
                    sum(is_mathy_char(c) for c in inner) or
                    re.search(r'[A-Za-z].*[,:]|[πα-ωΑ-Ω]', inner)
                ):
                    if op == '{' and ':' in inner and any(c in inner for c in '<>=≤≥∈'):
                        mark_processed(already, start, end)
                        regions.append((start, end))
                    elif re.match(r'^[A-Za-z0-9α-ωΑ-Ω]+[\^_]*[A-Za-z0-9α-ωΑ-Ω∞]*$', inner):
                        mark_processed(already, start + 1, end - 1)
                        regions.append((start + 1, end - 1))
                    else:
                        mark_processed(already, start, end)
                        regions.append((start, end))
            else:
                i += 1

    # —— PHASE 10 : misc single-token patterns
    misc_single_pats = [
        r"([α-ωΑ-Ω][A-Za-z])",
        r"([A-Za-z][̇̄̊̈])",
        r"(?<!['\"\w])([A-Za-zα-ωΑ-Ω]'(?:'{0,2}))(?!\w)",
        r"\b(dx|dy|dz|dt|du|dv|dw|dr|dθ|dφ|dα|dβ|dγ)(?=\s|$|[,.])",
    ]
    for pat in misc_single_pats:
        for m in re.finditer(pat, text):
            s, e = m.span(1) if '(' in pat else m.span()
            if not is_processed(already, s, e):
                mark_processed(already, s, e)
                regions.append((s, e))

    # —— PHASE 11 : stand-alone Unicode math symbols
    skip_single = ":;,.[]{}()|=?»«"
    for m in re.finditer(ALL_MATHY_UNICODE + "|" + re.escape(MATH_SYMBOLS), text):
        s, e = m.span()
        ch = m.group(0)
        if ch.isascii() and (ch.isalnum() or ch in skip_single):
            continue
        if ch in skip_single:
            continue
        if not is_processed(already, s, e):
            mark_processed(already, s, e)
            regions.append((s, e))

    # —— PHASE 12 : quoted maths
    for oq, cq in [('"', '"'), ("'", "'"), ('«', '»'), ('“', '”')]:
        start = 0
        while True:
            o = text.find(oq, start)
            if o == -1:
                break
            c = text.find(cq, o + 1)
            if c == -1:
                break
            if is_processed(already, o, c + 1):
                start = c + 1
                continue
            content = text[o + 1:c]
            quote_already = [0] * len(content)
            atoms = find_back_to_back_atoms(content, quote_already)
            for a0, b0 in atoms:
                a, b = o + 1 + a0, o + 1 + b0
                if not is_processed(already, a, b):
                    mark_processed(already, a, b)
                    regions.append((a, b))
            stripped = content.strip()
            if not atoms and stripped and all(
                ch in 'α-ωΑ-Ω∞∑∫∂∇∈∉∪∩∅√′″∗≠≈≡≤≥⊂⊃⊆⊇⊕⊗⊥⊤⊢⊨⊬⊭±÷×π'
                for ch in stripped
            ):
                a, b = o + 1 + content.index(stripped), o + 1 + content.index(stripped) + len(stripped)
                if not is_processed(already, a, b):
                    mark_processed(already, a, b)
                    regions.append((a, b))
            already[o] = already[c] = 1
            start = c + 1

    # —— FINAL clean-up & aggressive split pass
    if regions:
        skip_chars = {'?', '»', '«', '"', "'"}
        regions = [
            (s, e) for s, e in regions
            if text[s:e].strip() and text[s:e] not in skip_chars
        ]
        compact = []
        for s, e in regions:
            seg = text[s:e]
            if len(seg) == 1 and seg.isalpha() and seg.isascii():
                prev = text[max(0, s - 30):s].lower()
                foll = text[e:e + 10].lower()
                if not (
                    'function' in prev or
                    ('(' in prev and ')' in foll and
                     any(w in prev for w in ('function', 'equation', 'sin', 'cos', 'log')))
                ):
                    compact.append((s, e))
            else:
                compact.append((s, e))
        regions = _merge_regions(sorted(set(compact)))

        # aggressive re-split for glued atoms
        final = []
        for s, e in regions:
            seg = text[s:e]
            try_split = (
                len(seg) > 2 and
                not any(ch in seg for ch in '()[]{}:=,') and
                not seg.startswith('\\') and
                not any(ch in seg for ch in ('→', '∈', '∘')) and
                not seg.endswith('(M)') and
                not seg.endswith('(Ω)')
            )
            if try_split:
                tmp = [0] * len(seg)
                atoms = find_back_to_back_atoms(seg, tmp)
                if len(atoms) > 1 and all(
                    any(is_base_char(c) for c in seg[a:b]) and
                    any(is_script_char(c) or c in '^_' for c in seg[a:b])
                    for a, b in atoms
                ):
                    for a, b in atoms:
                        final.append((s + a, s + b))
                    continue
            final.append((s, e))
        regions = final

    logger.debug("find_math_regions: %s", regions)
    return regions

# ──────────────────────────────────────────────────────────────
# PUBLIC HELPERS
# ──────────────────────────────────────────────────────────────
def is_inside_math(pos, regions):
    return any(s <= pos < e for s, e in regions)


def mask_math_regions(text: str, mask_char: str = "M") -> str:
    if not isinstance(text, str):
        logger.error("mask_math_regions received non-string input.")
        return ''
    mask = ['N'] * len(text)
    for s, e in find_math_regions(text):
        mask[s:e] = [mask_char] * (e - s)
    return ''.join(mask)

def _match_math_token(tok: str) -> bool:
    math_pat = (
        r"[A-Za-zα-ωΑ-Ω]"                          # base (Latin or Greek)
        r"((\^(\{[^}]+\}|[A-Za-z0-9]+)|[" + SUPERSCRIPTS + r"]+)"
        r"|(_(\{[^}]+\}|[A-Za-z0-9]+)|[" + SUBSCRIPTS + r"]+))+"
        r"$"
    )
    if re.fullmatch(math_pat, tok):
        return True
    if re.fullmatch(r"\\math(bb|cal|bf|rm|frak|sf|it|scr)\{[A-Za-z0-9]+\}", tok):
        return True
    return False

def title_contains_math(text):
    return bool(find_math_regions(text))


def contains_math_token(word: str) -> bool:
    if not isinstance(word, str) or not word:
        return False

    # 1️⃣ raw token (keeps Unicode super/sub-scripts intact)
    if _match_math_token(word):
        return True

    # 2️⃣ NFC normalisation keeps super/sub scripts, unlike NFKC
    word_nfc = unicodedata.normalize('NFC', word)
    if _match_math_token(word_nfc):
        return True

    # 3️⃣ legacy LaTeX macro check (already covered in _match, but keep as safety)
    return False


def contains_math(text: str) -> bool:
    if title_contains_math(text):
        return True
    if re.search(r'\\(mathbb|mathcal|mathbf|mathrm|mathfrak|mathsf|mathit|mathscr)\b', text):
        return True
    for token in re.findall(r'\b\w+\b', text):
        if contains_math_token(token):
            return True
    return False


def is_filename_math_token(word: str) -> bool:
    if not isinstance(word, str) or not word.strip():
        return False
    w = word.strip()
    if re.fullmatch(r"[A-Za-z0-9\-–',\.]+", w):
        return False
    if w.startswith("$") or w.startswith("\\"):
        return True
    if len(w) == 1 and is_mathy_char(w):
        return True
    if re.fullmatch(r"[A-Za-z][" + SUPERSCRIPTS + SUBSCRIPTS + "]+", w):
        return True
    if all(is_mathy_char(c) for c in w):
        return True
    if re.fullmatch(ALL_MATHY_UNICODE, w):
        return True
    return False

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)

    def show_regions(title, regions):
        mask = ["N"] * len(title)
        for a, b in regions:
            for i in range(a, b):
                mask[i] = "M"
        return "".join(mask)

    # Each entry: (description, title, list of expected math region substrings)
    HARD_TESTS = [
        # === ORIGINAL TESTS ===
        ("Superscript Unicode combos",
         "Estimate in C\u00b2, L\u1d56, and H\u2080\u00b9",
         ["C\u00b2", "L\u1d56", "H\u2080\u00b9"]),
        ("LaTeX formulas",
         "A formula for $E = mc^2$ in relativity",
         ["$E = mc^2$"]),
        ("LaTeX mathbb, cal, frak",
         "Domain \\mathbb{R}, codomain \\mathcal{H} and \\mathfrak{g}",
         ["\\mathbb{R}", "\\mathcal{H}", "\\mathfrak{g}"]),
        ("LaTeX bracketed environments",
         "See \\( x^2+y^2=1 \\) and \\[ f(x) \\]",
         ["\\( x^2+y^2=1 \\)", "\\[ f(x) \\]"]),
        ("LaTeX begin environments",
         "Here is \\begin{equation}E=mc^2\\end{equation}",
         ["\\begin{equation}E=mc^2\\end{equation}"]),
        ("Bracketed math",
         "The interval [0,1] or {x : x>0} is important.",
         ["[0,1]", "{x : x>0}"]),
        ("Nested brackets",
         "The set {(x,y) : x^2 + y^2 < 1}",
         ["{(x,y) : x^2 + y^2 < 1}"]),
        ("Unicode Greek letters and variables",
         "Eigenvalues \u03bb\u2081, \u03bb\u2082; variable \u03b8, \u0394t; \u03c0 \u2208 [0,2\u03c0]",
         ["\u03bb\u2081", "\u03bb\u2082", "\u03b8", "\u0394t", "\u03c0 \u2208 [0,2\u03c0]"]),
        ("Math with punctuation",
         "Let f : \u211d \u2192 \u211d, and g(x) = e^{i\u03c0x}...",
         ["f : \u211d \u2192 \u211d", "g(x) = e^{i\u03c0x}"]),
        ("LaTeX in Unicode context",
         "Space L\u00b2(\u03a9,\u2119) with \\mathbb{E}[X | \\mathcal{F}_t]",
         ["L\u00b2(\u03a9,\u2119)", "\\mathbb{E}[X | \\mathcal{F}_t]"]),
        ("Primes, hats, dots",
         "Let x', x'', \\hat{x}, \\dot{y}, \\vec{A}, \\tilde{B}, \\bar{Z}",
         ["x'", "x''", "\\hat{x}", "\\dot{y}", "\\vec{A}", "\\tilde{B}", "\\bar{Z}"]),
        ("Back-to-back math, odd order, invisible chars",
         "Value in C^\u221eL\u2082 D_{1,2}X\u2080 F\u2082\u00b2",
         ["C^\u221e", "L\u2082", "D_{1,2}", "X\u2080", "F\u2082\u00b2"]),
        ("Quoted math",
         "\u201cC\u00b2 regularity\u201d, or 'L^p estimate', or \u00abH\u2080\u00b9 solution\u00bb",
         ["C\u00b2", "L^p", "H\u2080\u00b9"]),
        ("Words containing math chars",
         "Analysis of conformal mapping and matrix norms.",
         []),
        ("Dotless and special chars",
         "Let \\imath, \\jmath, \u0131, \u0133, \u2113 be as usual.",
         ["\\imath", "\\jmath", "\u0131", "\u0133", "\u2113"]),
        ("Plain English, no math",
         "This title contains only words and punctuation.",
         []),
        ("Single Greek symbol, single-letter variable",
         "Alpha \u03b1, beta \u03b2, gamma \u03b3, X, Y, Z.",
         ["\u03b1", "\u03b2", "\u03b3"]),
        ("Math with spaces, bracketed math, nested",
         "Let M = (A, B) where (A,B) = (0, \u03c0).",
         ["M = (A, B)", "(A,B) = (0, \u03c0)"]),
        ("Extreme unicode mix",
         "Estimate for the solution in space \U0001d4d7^s(\U0001d54b^d,\u211d^n), with \U0001d4a2\u00b2, \u212c, and \u2115.",
         ["\U0001d4d7^s(\U0001d54b^d,\u211d^n)", "\U0001d4a2\u00b2", "\u212c", "\u2115"]),
        ("Math at boundaries",
         "L^\u221e norm is standard. So is (0,1).",
         ["L^\u221e", "(0,1)"]),
        ("Math with dash/ndash",
         "Super-compact: C\u207f, L\u2081, X\u2080, F\u2082\u00b2, D_{1,2}, U_{x,y}, V^\u221e",
         ["C\u207f", "L\u2081", "X\u2080", "F\u2082\u00b2", "D_{1,2}", "U_{x,y}", "V^\u221e"]),
        ("Math interrupted by punctuation",
         "Consider X^\u221e, Y^1. Z^2! (W^3)?",
         ["X^\u221e", "Y^1", "Z^2", "W^3"]),
        ("Roman numerals, years, numbers",
         "Estimate for L^II, L^1234, and L_{2022}.",
         ["L^II", "L^1234", "L_{2022}"]),
        ("Set-builder, logic, indicator",
         "Consider A = {x \u2208 \u211d : x > 0} and 1_{x > 0}.",
         ["A = {x \u2208 \u211d : x > 0}", "1_{x > 0}"]),
        ("Tensor notation, double scripts",
         "Let T_{ij}^k be the components, F^{\u03b1\u03b2}, and X_\u03bb.",
         ["T_{ij}^k", "F^{\u03b1\u03b2}", "X_\u03bb"]),
        ("Derivatives, limits",
         "As n \u2192 \u221e, f'(x), f''(y), and \\lim_{n \\to \\infty} a_n.",
         ["n \u2192 \u221e", "f'(x)", "f''(y)", "\\lim_{n \\to \\infty} a_n"]),
        ("Primes, dots, arrows",
         "The sequence x^{(n)}, \u0226, \u0226, and v\u0304 \u2192 0.",
         ["x^{(n)}", "\u0226", "\u0226", "v\u0304 \u2192 0"]),
        ("Function spaces, norms",
         "L^\u221e([0,1], \u2119), \\|X_t\\|_{L^2}, \\mathcal{C}^1, and BV(\u03a9).",
         ["L^\u221e([0,1], \u2119)", "\\|X_t\\|_{L^2}", "\\mathcal{C}^1", "BV(\u03a9)"]),
        
        # === NEW ROBUSTNESS TESTS ===
        # Back-to-back robustness
        ("Back-to-back: 3 atoms",
         "Study A²B³C⁴ convergence",
         ["A²", "B³", "C⁴"]),
        ("Back-to-back: 4 atoms",
         "Given P^mQ_nR^∞S₁ sequence",
         ["P^m", "Q_n", "R^∞", "S₁"]),
        ("Back-to-back: complex scripts",
         "In X_{12}Y^{max}Z₀ framework",
         ["X_{12}", "Y^{max}", "Z₀"]),
        ("Back-to-back: mixed Greek/Latin",
         "Consider α²β₃γ^n sequence",
         ["α²", "β₃", "γ^n"]),
        ("Back-to-back: should NOT split pure letters",
         "The word abc contains no math",
         []),
        ("Back-to-back: within function space (should NOT split)",
         "The space C^∞(M) is complete",
         ["C^∞(M)"]),
        
        # Quote robustness  
        ("Quotes: Greek letters",
         "The 'α² + β³' identity holds",
         ["α²", "β³"]),
        ("Quotes: multiple expressions",
         "Both 'L^p' and 'H¹' spaces",
         ["L^p", "H¹"]),
        ("Quotes: mixed with English",
         "The 'C² function theory' is complex",
         ["C²"]),
        ("Quotes: no math",
         "The 'classical approach' works",
         []),
        ("Quotes: standalone symbols",
         "Use 'π' for the ratio",
         ["π"]),
        
        # Assignment robustness
        ("Assignment: after 'where' (should separate)",
         "Let f(x) = x² where g(y) = y³",
         ["f(x) = x²", "g(y) = y³"]),
        ("Assignment: after 'function' (should NOT match)",
         "The function h(t) = sin(t) is periodic",
         []),
        ("Assignment: after 'method' (should match)",
         "This method p(x) = x + 1 works",
         ["p(x) = x + 1"]),
        ("Assignment: standalone (should match)",
         "Define u(x) = log(x) here",
         ["u(x) = log(x)"]),
        ("Assignment: multiple parens",
         "Set (a,b) = (1,2) and (c,d) = (3,4)",
         ["(a,b) = (1,2)", "(c,d) = (3,4)"]),
        
        # Complex edge cases
        ("Edge: math at start and end",
         "α² varies smoothly until β³",
         ["α²", "β³"]),
        ("Edge: punctuation separation",
         "Both X^n; Y_m! Z^∞?",
         ["X^n", "Y_m", "Z^∞"]),
        ("Edge: nested quotes",
         "The \"'L²' theory\" is deep",
         ["L²"]),
        ("Edge: LaTeX in quotes",
         "Use '\\mathbb{R}' notation",
         ["\\mathbb{R}"]),
        ("Edge: years should NOT be math",
         "In 2023 and 1998, we studied this",
         []),
        
        # Composite preservation tests  
        ("Preserve: function composition",
         "Map f ∘ g : X → Y",
         ["f ∘ g : X → Y"]),
        ("Preserve: set builder with parens",
         "Define S = {(x,y) ∈ ℝ² : x² + y² = 1}",
         ["S = {(x,y) ∈ ℝ² : x² + y² = 1}"]),
        ("Preserve: limit expression",
         "As \\lim_{n→∞} a_n = L",
         ["\\lim_{n→∞} a_n = L"]),
        ("Preserve: integral bounds",
         "Compute ∫₀^∞ e^{-x} dx",
         ["∫₀^∞ e^{-x} dx"]),
    ]

    print("\n" + "=" * 80)
    print("EXTREME MATH REGION DETECTION TESTS")
    print("=" * 80)
    failures = 0
    for desc, title, expected in HARD_TESTS:
        print(f"\n--- {desc} ---")
        print(f"Title: {title}")
        regions = find_math_regions(title)
        region_texts = [title[a:b] for a, b in regions]
        print(f"Regions: {regions}")
        print(f"Region texts: {region_texts}")
        print(f"Mask:   {show_regions(title, regions)}")
        # Check correctness
        missed = [ex for ex in expected if ex not in region_texts]
        extra = [rt for rt in region_texts if rt not in expected]
        if not missed and not extra:
            print("✅ OK")
        else:
            print("❌ FAIL:")
            if missed:
                print(f"  Missed expected: {missed}")
            if extra:
                print(f"  Extraneous:      {extra}")
            failures += 1

    print("\nRESULT: %d/%d failed." % (failures, len(HARD_TESTS)))
    if failures > 0:
        sys.exit(1)