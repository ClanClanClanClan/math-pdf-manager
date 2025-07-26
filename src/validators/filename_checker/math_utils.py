"""
Mathematical context detection utilities for filename validation.

This module provides functionality to detect and handle mathematical expressions
and contexts within academic filenames.
"""

import re
from typing import List, Tuple

from .debug import debug_print


# Mathematical operators and symbols
MATHEMATICAL_OPERATORS = {
    # Comparison operators
    "=", "≠", "≡", "≢", "<", ">", "≤", "≥", "≦", "≧", "≨", "≩", "≪", "≫",
    "≺", "≻", "≼", "≽", "≾", "≿", "⊂", "⊃", "⊆", "⊇", "⊈", "⊉", "⊊", "⊋",
    "∈", "∉", "∋", "∌", "∝", "∼", "∽", "≁", "≃", "≄", "≅", "≆", "≇", "≈",
    "≉", "≊", "≋", "≌", "≍", "≎", "≏", "≐", "≑", "≒", "≓", "≔", "≕", "≖",
    "≗", "≘", "≙", "≚", "≛", "≜", "≝", "≞", "≟", "≣", "≬", "≭", "≮", "≯",
    "≰", "≱", "≲", "≳", "≴", "≵", "≶", "≷", "≸", "≹",
    # Arithmetic operators
    "+", "-", "×", "÷", "·", "⋅", "⊕", "⊖", "⊗", "⊘", "⊙", "⊚", "⊛", "⊜",
    "⊝", "⊞", "⊟", "⊠", "⊡", "⊢", "⊣", "⊤", "⊥", "⊦", "⊧", "⊨", "⊩", "⊪",
    "⊫", "⊬", "⊭", "⊮", "⊯", "⊰", "⊱", "⊲", "⊳", "⊴", "⊵", "⊶", "⊷", "⊸",
    "⊹", "⊺", "⊻", "⊼", "⊽", "⊾", "⊿", "⋀", "⋁", "⋂", "⋃", "⋄", "⋅", "⋆",
    "⋇", "⋈", "⋉", "⋊", "⋋", "⋌", "⋍", "⋎", "⋏", "⋐", "⋑", "⋒", "⋓", "⋔",
    "⋕", "⋖", "⋗", "⋘", "⋙", "⋚", "⋛", "⋜", "⋝", "⋞", "⋟", "⋠", "⋡", "⋢",
    "⋣", "⋤", "⋥", "⋦", "⋧", "⋨", "⋩", "⋪", "⋫", "⋬", "⋭", "⋮", "⋯", "⋰",
    "⋱", "⋲", "⋳", "⋴", "⋵", "⋶", "⋷", "⋸", "⋹", "⋺", "⋻", "⋼", "⋽", "⋾", "⋿",
    # Set operations
    "∪", "∩", "∖", "∁", "∂", "∃", "∄", "∅", "∆", "∇", "∏", "∐", "∑", "−",
    "∓", "∔", "∕", "∖", "∗", "∘", "∙", "√", "∛", "∜", "∝", "∞", "∟", "∠",
    "∡", "∢", "∣", "∤", "∥", "∦", "∧", "∨", "∩", "∪", "∫", "∬", "∭", "∮",
    "∯", "∰", "∱", "∲", "∳", "∴", "∵", "∶", "∷", "∸", "∹", "∺", "∻", "∼",
    "∽", "∾", "∿", "≀", "≁", "≂", "≃", "≄", "≅", "≆", "≇", "≈", "≉", "≊",
    "≋", "≌", "≍", "≎", "≏", "≐", "≑", "≒", "≓", "≔", "≕", "≖", "≗", "≘",
    "≙", "≚", "≛", "≜", "≝", "≞", "≟", "≠", "≡", "≢", "≣", "≤", "≥", "≦",
    "≧", "≨", "≩", "≪", "≫", "≬", "≭", "≮", "≯", "≰", "≱", "≲", "≳", "≴",
    "≵", "≶", "≷", "≸", "≹", "≺", "≻", "≼", "≽", "≾", "≿", "⊀", "⊁", "⊂",
    "⊃", "⊄", "⊅", "⊆", "⊇", "⊈", "⊉", "⊊", "⊋", "⊌", "⊍", "⊎", "⊏", "⊐",
    "⊑", "⊒", "⊓", "⊔", "⊕", "⊖", "⊗", "⊘", "⊙", "⊚", "⊛", "⊜", "⊝", "⊞",
    "⊟", "⊠", "⊡", "⊢", "⊣", "⊤", "⊥", "⊦", "⊧", "⊨", "⊩", "⊪", "⊫", "⊬",
    "⊭", "⊮", "⊯", "⊰", "⊱", "⊲", "⊳", "⊴", "⊵", "⊶", "⊷", "⊸", "⊹", "⊺",
    "⊻", "⊼", "⊽", "⊾", "⊿",
    # Logic operators
    "∧", "∨", "¬", "→", "↔", "↑", "↓", "↕", "↖", "↗", "↘", "↙", "↚", "↛",
    "↜", "↝", "↞", "↟", "↠", "↡", "↢", "↣", "↤", "↥", "↦", "↧", "↨", "↩",
    "↪", "↫", "↬", "↭", "↮", "↯", "↰", "↱", "↲", "↳", "↴", "↵", "↶", "↷",
    "↸", "↹", "↺", "↻", "↼", "↽", "↾", "↿", "⇀", "⇁", "⇂", "⇃", "⇄", "⇅",
    "⇆", "⇇", "⇈", "⇉", "⇊", "⇋", "⇌", "⇍", "⇎", "⇏", "⇐", "⇑", "⇒", "⇓",
    "⇔", "⇕", "⇖", "⇗", "⇘", "⇙", "⇚", "⇛", "⇜", "⇝", "⇞", "⇟", "⇠", "⇡",
    "⇢", "⇣", "⇤", "⇥", "⇦", "⇧", "⇨", "⇩", "⇪", "⇫", "⇬", "⇭", "⇮", "⇯",
    "⇰", "⇱", "⇲", "⇳", "⇴", "⇵", "⇶", "⇷", "⇸", "⇹", "⇺", "⇻", "⇼", "⇽",
    "⇾", "⇿"
}

# Mathematical Greek letters
MATHEMATICAL_GREEK_LETTERS = {
    "α", "β", "γ", "δ", "ε", "ζ", "η", "θ", "ι", "κ", "λ", "μ", "ν", "ξ", "ο", "π",
    "ρ", "σ", "τ", "υ", "φ", "χ", "ψ", "ω", "ς", "ϑ", "ϒ", "ϕ", "ϖ", "ϰ", "ϱ", "ϵ",
    "Α", "Β", "Γ", "Δ", "Ε", "Ζ", "Η", "Θ", "Ι", "Κ", "Λ", "Μ", "Ν", "Ξ", "Ο", "Π",
    "Ρ", "Σ", "Τ", "Υ", "Φ", "Χ", "Ψ", "Ω",
    # Mathematical superscript Greek letters
    "ᵅ", "ᵝ", "ᵞ", "ᵟ", "ᵋ", "ᶿ", "ᶥ", "ᶲ", "ᵡ", "ᵠ"
}

# Mathematical variables commonly used
MATHEMATICAL_VARIABLES = {
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p",
    "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P",
    "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"
}

# Try to import constants from existing modules
try:
    from unicode_constants import SUPERSCRIPT_MAP, SUBSCRIPT_MAP
    debug_print("Successfully imported SUPERSCRIPT_MAP and SUBSCRIPT_MAP from unicode_constants")
except ImportError:
    debug_print("Failed to import unicode constants, using fallback")
    SUPERSCRIPT_MAP = {}
    SUBSCRIPT_MAP = {}


def is_mathematical_context(text: str, position: int) -> bool:
    """
    FIXED: Improved mathematical context detection.
    
    Args:
        text: The text to analyze
        position: The position in the text to check
    
    Returns:
        True if the position is in a mathematical context
    """
    if position < 0 or position >= len(text):
        return False

    before = text[position - 1] if position > 0 else " "
    after = text[position + 1] if position < len(text) - 1 else " "

    debug_print(
        f"Checking mathematical context for '{text}' at pos {position} ('{text[position]}')"
    )
    debug_print(f"  Before: '{before}', After: '{after}'")

    # HIGHEST PRIORITY: Version patterns take absolute precedence
    version_pattern = r"\b(?:version|release|rev|ver|v)\s*(\d+(?:\.\d+)*)\b"
    for match in re.finditer(version_pattern, text.lower()):
        version_start = match.start(1)
        version_end = match.end(1)
        if version_start <= position < version_end:
            debug_print("  → DEFINITIVE: Not mathematical context - version number")
            return False

    # SECOND PRIORITY: Time patterns
    if after == ":" and position < len(text) - 2:
        next_chars = text[position + 1 : position + 4]
        if re.match(r":\d{1,2}(?:\s*[APap][Mm])?", next_chars):
            debug_print("  → DEFINITIVE: Not mathematical context - time pattern")
            return False

    # THIRD PRIORITY: Price/decimal patterns
    if before == "$" or (
        before == "."
        and after.isdigit()
        and position >= 2
        and text[position - 2].isdigit()
    ):
        debug_print("  → DEFINITIVE: Not mathematical context - price/decimal pattern")
        return False

    # Check for version-like decimal patterns
    if (before == "." and after.isdigit()) or (before.isdigit() and after == "."):
        start_check = max(0, position - 10)
        end_check = min(len(text), position + 10)
        local_context = text[start_check:end_check]

        if re.search(r"\d+\.\d+\.\d+", local_context):
            debug_print(
                "  → DEFINITIVE: Not mathematical context - version-like decimal pattern"
            )
            return False

    # Check for thin space (mathematical spacing)
    if before == "\u2009" or after == "\u2009":
        debug_print("  → Mathematical context: thin space")
        return True

    # Check for mathematical symbols
    mathematical_symbols = set(MATHEMATICAL_OPERATORS) | set(MATHEMATICAL_GREEK_LETTERS)

    if before in mathematical_symbols or after in mathematical_symbols:
        debug_print("  → Mathematical context: mathematical symbol")
        return True

    # Enhanced variable-operator-digit patterns
    if position >= 2:
        var_before = text[position - 2]
        op_before = text[position - 1]
        if (
            var_before in MATHEMATICAL_VARIABLES
            or var_before in MATHEMATICAL_GREEK_LETTERS
        ) and op_before in MATHEMATICAL_OPERATORS:
            debug_print(
                f"  → Mathematical context: variable-operator pattern ({var_before}{op_before})"
            )
            return True

    # Check for operator followed by variable pattern
    if position <= len(text) - 3:
        op_after = text[position + 1]
        var_after = text[position + 2]
        if op_after in MATHEMATICAL_OPERATORS and (
            var_after in MATHEMATICAL_VARIABLES
            or var_after in MATHEMATICAL_GREEK_LETTERS
        ):
            debug_print(
                f"  → Mathematical context: operator-variable pattern ({op_after}{var_after})"
            )
            return True

    # Check for direct mathematical operators
    if before in MATHEMATICAL_OPERATORS or after in MATHEMATICAL_OPERATORS:
        debug_print("  → Mathematical context: mathematical operator")
        return True

    # Look for mathematical context in wider window
    context_start = max(0, position - 20)
    context_end = min(len(text), position + 20)
    context_window = text[context_start:context_end]

    # Count mathematical symbols in the context window
    math_symbol_count = sum(
        1 for char in context_window if char in mathematical_symbols
    )
    if math_symbol_count >= 2:
        debug_print(
            f"  → Mathematical context: multiple math symbols in context ({math_symbol_count})"
        )
        return True

    # Look for mathematical context indicators in a wider window
    wider_context_start = max(0, position - 50)
    wider_context_end = min(len(text), position + 50)
    wider_context = text[wider_context_start:wider_context_end].lower()

    # Check for mathematical terms that indicate mathematical context
    mathematical_context_words = {
        "equation", "theorem", "proof", "lemma", "integral", "derivative", "limit",
        "convergence", "mathematical", "mathematics", "dimension", "cardinality",
        "degree", "rank", "order", "space", "field", "function", "variable",
        "parameter", "coefficient", "where", "when", "analysis", "study", "series",
        "algebra", "geometry", "domain",
    }

    math_word_count = sum(
        1 for word in mathematical_context_words if word in wider_context
    )
    if math_word_count >= 1:
        debug_print(
            f"  → Mathematical context: mathematical context word(s) in wider context ({math_word_count})"
        )
        return True

    # Check for subscript/superscript indicators
    if SUPERSCRIPT_MAP and SUBSCRIPT_MAP:
        superscript_chars = set(SUPERSCRIPT_MAP.values())
        subscript_chars = set(SUBSCRIPT_MAP.values())
        if (
            before in superscript_chars
            or after in superscript_chars
            or before in subscript_chars
            or after in subscript_chars
        ):
            debug_print("  → Mathematical context: superscript/subscript")
            return True

    # Enhanced check for mathematical delimiters
    if after in "^_${}\\," or before in "${}\\,":
        debug_print("  → Mathematical context: math delimiter")
        return True

    debug_print("  → Not mathematical context")
    return False


def should_preserve_digit(text: str, position: int) -> bool:
    """
    Determine if a digit should be preserved (not converted to words).
    
    Args:
        text: The text to analyze
        position: The position of the digit
    
    Returns:
        True if the digit should be preserved
    """
    if position < 0 or position >= len(text):
        return False

    # First check if it's a mathematical context
    if is_mathematical_context(text, position):
        return True

    # Get surrounding characters
    before = text[position - 1] if position > 0 else " "
    after = text[position + 1] if position < len(text) - 1 else " "

    # Check for version numbers
    version_pattern = re.search(
        r"\b(?:v|version|release|rev|ver)\s*(\d+(?:\.\d+)*)\b", text.lower()
    )
    if version_pattern:
        version_start = version_pattern.start(1)
        version_end = version_pattern.end(1)
        if version_start <= position < version_end:
            debug_print("Preserving digit in version number")
            return True

    # Check for time patterns
    if after == ":" and position < len(text) - 2:
        next_chars = text[position + 1 : position + 4]
        if re.match(r":\d{1,2}(?:\s*[APap][Mm])?", next_chars):
            debug_print("Preserving digit in time pattern")
            return True

    # Check for dates
    if before == "/" or after == "/":
        debug_print("Preserving digit in date pattern")
        return True

    # Check for decimal numbers
    if before == "." or after == ".":
        debug_print("Preserving digit in decimal number")
        return True

    return False


def find_math_regions(text: str) -> List[Tuple[int, int]]:
    """
    Find mathematical regions in text.
    
    Args:
        text: The text to analyze
    
    Returns:
        List of (start, end) tuples for mathematical regions
    """
    regions = []
    
    # Simple implementation - look for mathematical symbols
    i = 0
    while i < len(text):
        if text[i] in MATHEMATICAL_OPERATORS or text[i] in MATHEMATICAL_GREEK_LETTERS:
            start = i
            # Extend the region while we have mathematical content
            while i < len(text) and (
                text[i] in MATHEMATICAL_OPERATORS or
                text[i] in MATHEMATICAL_GREEK_LETTERS or
                text[i] in MATHEMATICAL_VARIABLES or
                text[i].isdigit() or
                text[i] in " \t"
            ):
                i += 1
            regions.append((start, i))
        else:
            i += 1
    
    return regions


def is_filename_math_token(token: str) -> bool:
    """
    Check if a token is a mathematical token.
    
    Args:
        token: The token to check
    
    Returns:
        True if the token is mathematical
    """
    if not token:
        return False
    
    # Check if token contains mathematical symbols
    mathematical_symbols = set(MATHEMATICAL_OPERATORS) | set(MATHEMATICAL_GREEK_LETTERS)
    return any(char in mathematical_symbols for char in token)


def contains_math(text: str) -> bool:
    """
    Check if text contains mathematical content.
    
    Args:
        text: The text to check
    
    Returns:
        True if text contains mathematical content
    """
    mathematical_symbols = set(MATHEMATICAL_OPERATORS) | set(MATHEMATICAL_GREEK_LETTERS)
    return any(char in mathematical_symbols for char in text)


def find_math_segments(text: str) -> List[Tuple[int, int]]:
    """Compatibility wrapper for find_math_regions - RESTORED from original"""
    return find_math_regions(text)


def check_mathematician_names(text: str, lang: str = "en") -> List[str]:
    """Check mathematician names with 8-language support - RESTORED from original"""
    errors = []
    
    # Comprehensive mathematician names database
    mathematician_names = {
        "en": {
            "euler", "gauss", "newton", "leibniz", "fermat", "pascal", "descartes",
            "fibonacci", "pythagoras", "archimedes", "euclid", "diophantus",
            "cauchy", "riemann", "weierstrass", "dedekind", "cantor", "hilbert",
            "gödel", "turing", "von neumann", "erdős", "ramanujan", "hardy",
            "littlewood", "pólya", "hadamard", "landau", "borel", "lebesgue",
            "fourier", "laplace", "legendre", "jacobi", "galois", "abel",
            "noether", "klein", "lie", "cartan", "weil", "grothendieck",
            "serre", "deligne", "tate", "mumford", "atiyah", "singer",
        },
        "fr": {
            "euler", "gauss", "newton", "leibniz", "fermat", "pascal", "descartes",
            "lagrange", "laplace", "legendre", "fourier", "cauchy", "galois",
            "poincaré", "borel", "lebesgue", "hadamard", "weil", "grothendieck",
            "serre", "deligne", "connes", "duflo", "cartier", "schwartz",
        },
        "de": {
            "euler", "gauss", "newton", "leibniz", "fermat", "pascal", "descartes",
            "weierstrass", "dedekind", "cantor", "hilbert", "noether", "klein",
            "riemann", "dirichlet", "jacobi", "kronecker", "kummer", "eisenstein",
            "frobenius", "landau", "hausdorff", "zermelo", "fraenkel",
        },
        "it": {
            "fibonacci", "cardano", "bombelli", "galilei", "torricelli", "viviani",
            "agnesi", "lagrange", "volta", "avogadro", "betti", "beltrami",
            "cremona", "peano", "levi-civita", "volterra", "pincherle",
        },
        "es": {
            "fibonacci", "cardano", "fermat", "pascal", "descartes", "newton",
            "leibniz", "euler", "gauss", "cauchy", "galois", "abel", "jacobi",
            "riemann", "weierstrass", "cantor", "dedekind", "hilbert", "poincaré",
        },
        "pt": {
            "fibonacci", "cardano", "fermat", "pascal", "descartes", "newton",
            "leibniz", "euler", "gauss", "cauchy", "galois", "abel", "jacobi",
            "riemann", "weierstrass", "cantor", "dedekind", "hilbert", "poincaré",
        },
        "ru": {
            "эйлер", "гаусс", "ньютон", "лейбниц", "ферма", "паскаль", "декарт",
            "чебышёв", "марков", "ляпунов", "колмогоров", "соболев", "гельфанд",
            "арнольд", "новиков", "синай", "фоменко", "перельман",
        },
        "zh": {
            "欧拉", "高斯", "牛顿", "莱布尼茨", "费马", "帕斯卡", "笛卡尔",
            "柯西", "黎曼", "魏尔斯特拉斯", "戴德金", "康托尔", "希尔伯特",
            "陈省身", "丘成桐", "张益唐", "田刚", "李政道", "杨振宁",
        },
    }
    
    # Use English as fallback
    names_to_check = mathematician_names.get(lang, mathematician_names["en"])
    
    # Check for misspelled mathematician names
    words = text.lower().split()
    for word in words:
        # Simple fuzzy matching for common misspellings
        for name in names_to_check:
            if len(word) >= 3 and len(name) >= 3:
                # Check if word is a close match (simple edit distance)
                if _simple_edit_distance(word, name) == 1:
                    errors.append(f"Possible misspelling of mathematician name: '{word}' → '{name}'")
    
    return errors


def _simple_edit_distance(s1: str, s2: str) -> int:
    """Simple edit distance calculation"""
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    
    distances = list(range(len(s1) + 1))
    for i2, c2 in enumerate(s2):
        distances_ = [i2 + 1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]