"""
Title Normalizer Module

Title normalization, capitalization checking, and dash handling
extracted from src.validators.filename_checker.py
"""

import re
from typing import List, Set, Tuple, Optional, Any
from .pattern_matcher import robust_tokenize_with_math
from .validation_result import Message


class TitleNormalizer:
    """Advanced title normalization and validation"""
    
    def __init__(self):
        # Common words that should be lowercase in titles (unless first word)
        self.lowercase_words = {
            'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'from',
            'in', 'into', 'nor', 'of', 'on', 'or', 'the', 'to', 'with'
        }
        
        # Common abbreviations that should stay uppercase
        self.uppercase_abbrevs = {
            'USA', 'UK', 'EU', 'UN', 'NATO', 'IEEE', 'ACM', 'PDF',
            'HTML', 'XML', 'JSON', 'API', 'URL', 'URI', 'HTTP', 'HTTPS'
        }
        
        # Mathematical terms that might have special capitalization
        self.math_terms = {
            'LaTeX', 'TeX', 'MATLAB', 'NumPy', 'SciPy', 'PyTorch',
            'TensorFlow', 'GitHub', 'JavaScript', 'TypeScript'
        }
    
    def normalize_title(self, title: str) -> str:
        """Normalize title formatting"""
        if not title:
            return title
        
        # Normalize whitespace
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Fix spacing around punctuation
        title = re.sub(r'\s*([,;:])\s*', r'\1 ', title)
        title = re.sub(r'\s*([.!?])\s*', r'\1 ', title)
        
        # Fix spacing around parentheses
        title = re.sub(r'\s*\(\s*', ' (', title)
        title = re.sub(r'\s*\)\s*', ') ', title)
        
        # Remove trailing spaces
        title = title.strip()
        
        return title
    
    def check_title_capitalization(self, title: str, known_words: Set[str],
                                 exceptions: Set[str], capitalization_whitelist: Set[str] = None,
                                 math_regions: List[Tuple[int, int]] = None) -> List[Message]:
        """Check title capitalization and return list of issues"""
        messages = []
        caps_wl = capitalization_whitelist or set()
        
        # Combine all word lists
        all_allowed_words = known_words | exceptions | caps_wl
        
        # Tokenize the title
        tokens = robust_tokenize_with_math(title, all_allowed_words, math_regions)
        
        # Check each word token
        for i, token in enumerate(tokens):
            if token.type != "WORD":
                continue
            
            word = token.text
            is_first = i == 0 or all(t.type != "WORD" for t in tokens[:i])
            
            # Check capitalization rules
            error = self._check_word_capitalization(word, is_first, all_allowed_words)
            if error:
                messages.append(Message(
                    level="warning",
                    code="TITLE_CAP",
                    text=f"Capitalization: {error}",
                    pos=token.start
                ))
        
        return messages
    
    def _check_word_capitalization(self, word: str, is_first: bool, 
                                  allowed_words: Set[str]) -> Optional[str]:
        """Check if a word is properly capitalized"""
        # Special cases in allowed words
        if word in allowed_words:
            return None
        
        # Check case-insensitive match in allowed words
        word_lower = word.lower()
        for allowed in allowed_words:
            if allowed.lower() == word_lower:
                if word != allowed:
                    return f"{word} should be '{allowed}'"
                return None
        
        # First word should be capitalized
        if is_first:
            if not word[0].isupper():
                return f"{word} (first word should be capitalized)"
            return None
        
        # Check if it's a lowercase word that should stay lowercase
        if word_lower in self.lowercase_words and word != word_lower:
            return f"{word} should be '{word_lower}'"
        
        # Check if it's an abbreviation that should be uppercase
        if word.upper() in self.uppercase_abbrevs and word != word.upper():
            return f"{word} should be '{word.upper()}'"
        
        # Check if it's a known special term
        for special_term in self.math_terms:
            if word_lower == special_term.lower() and word != special_term:
                return f"{word} should be '{special_term}'"
        
        # General rule: content words should be capitalized
        if len(word) > 3 and word[0].islower() and word_lower not in self.lowercase_words:
            return f"{word} should be '{word[0].upper() + word[1:]}'"
        
        return None
    
    def fix_title_capitalization(self, title: str, known_words: Set[str] = None,
                               exceptions: Set[str] = None) -> str:
        """Fix title capitalization according to standard rules"""
        if not title:
            return title
        
        known_words = known_words or set()
        exceptions = exceptions or set()
        all_allowed = known_words | exceptions
        
        # Tokenize
        tokens = robust_tokenize_with_math(title, all_allowed)
        
        # Fix each word
        result_parts = []
        last_end = 0
        
        for i, token in enumerate(tokens):
            # Add any text before this token
            if token.start > last_end:
                result_parts.append(title[last_end:token.start])
            
            if token.type == "WORD":
                is_first = i == 0 or all(t.type != "WORD" for t in tokens[:i])
                fixed_word = self._fix_word_capitalization(token.text, is_first, all_allowed)
                result_parts.append(fixed_word)
            else:
                result_parts.append(token.text)
            
            last_end = token.end
        
        # Add any remaining text
        if last_end < len(title):
            result_parts.append(title[last_end:])
        
        return ''.join(result_parts)
    
    def _fix_word_capitalization(self, word: str, is_first: bool, 
                                allowed_words: Set[str]) -> str:
        """Fix capitalization of a single word"""
        # Check if word has exact match in allowed words
        if word in allowed_words:
            return word
        
        # Check case-insensitive match
        word_lower = word.lower()
        for allowed in allowed_words:
            if allowed.lower() == word_lower:
                return allowed
        
        # First word is always capitalized
        if is_first:
            return word[0].upper() + word[1:] if len(word) > 1 else word.upper()
        
        # Lowercase words
        if word_lower in self.lowercase_words:
            return word_lower
        
        # Abbreviations
        if word.upper() in self.uppercase_abbrevs:
            return word.upper()
        
        # Special terms
        for special_term in self.math_terms:
            if word_lower == special_term.lower():
                return special_term
        
        # General rule: capitalize if longer than 3 characters
        if len(word) > 3:
            return word[0].upper() + word[1:]
        
        return word
    
    def check_title_dashes(self, title: str, known_words: Set[str]) -> List[Message]:
        """Check for dash-related issues in title"""
        messages = []
        
        # Check for bad dash patterns
        bad_patterns = [
            (r'\s+-\s+', 'space-hyphen-space should be em dash'),
            (r'-{2,}', 'multiple consecutive hyphens'),
            (r'[–—−‐-]{2,}', 'mixed dash types'),
        ]
        
        for pattern, description in bad_patterns:
            for match in re.finditer(pattern, title):
                messages.append(Message(
                    level="warning",
                    code="DASH_ISSUE",
                    text=f"Dash issue: {description} at position {match.start()}",
                    pos=match.start()
                ))
        
        # Check hyphenated words
        hyphenated_words = re.findall(r'\b\w+-\w+\b', title)
        for word in hyphenated_words:
            if word.lower() not in known_words:
                messages.append(Message(
                    level="info",
                    code="HYPHEN_CHECK",
                    text=f"Check hyphenated word: {word}",
                    pos=title.find(word)
                ))
        
        return messages


# Module-level functions for backward compatibility
_default_normalizer = TitleNormalizer()

def normalize_title(title: str) -> str:
    """Normalize title formatting"""
    return _default_normalizer.normalize_title(title)

def check_title_capitalization(title: str, known_words: Set[str], exceptions: Set[str],
                             ext: str = None, capitalization_whitelist: Set[str] = None,
                             dash_whitelist: Set[str] = None, spellchecker: Any = None,
                             contains_math_func: Any = None, debug: bool = False) -> List[str]:
    """Check title capitalization - backward compatibility wrapper"""
    messages = _default_normalizer.check_title_capitalization(
        title, known_words, exceptions, capitalization_whitelist
    )
    return [msg.text for msg in messages]

def fix_title_capitalization(title: str, known_words: Set[str] = None,
                           exceptions: Set[str] = None) -> str:
    """Fix title capitalization"""
    return _default_normalizer.fix_title_capitalization(title, known_words, exceptions)

def check_title_dashes(title: str, known_words: Set[str], exceptions: Set[str],
                      capitalization_whitelist: Set[str] = None,
                      dash_whitelist: Set[str] = None) -> List[str]:
    """Check title dashes - backward compatibility wrapper"""
    messages = _default_normalizer.check_title_dashes(title, known_words)
    return [msg.text for msg in messages]


def spelling_and_format_errors(
    title: str,
    known_words: Set[str],
    capitalization_whitelist: Set[str],
    exceptions: Set[str],
    dash_whitelist: Set[str],
    speller: Any,
    contains_math_func: Any = None,
) -> List[str]:
    """FIXED: Enhanced spelling checker with proper phrase detection - RESTORED from original filename_checker"""
    import unicodedata
    
    # Import required functions
    from ..validators.filename_checker.debug import debug_print
    from ..validators.filename_checker.math_utils import find_math_regions, is_filename_math_token
    from ..validators.filename_checker.tokenization import robust_tokenize_with_math
    from ..validators.filename_checker.unicode_utils import nfc
    try:
        from utils import canonicalize
    except ImportError:
        from ..core.text_processing.my_spellchecker import canonicalize
    
    errs = []
    
    # FIXED: Ensure all sets are properly initialized
    known_words = known_words or set()
    capitalization_whitelist = capitalization_whitelist or set()
    exceptions = exceptions or set()
    dash_whitelist = dash_whitelist or set()
    
    # FIXED: Combine ALL whitelists for comprehensive checking
    all_allowed_words = (
        known_words | capitalization_whitelist | exceptions | dash_whitelist
    )
    
    debug_print(f"=== spelling_and_format_errors for: '{title}' ===")
    debug_print(f"Known words: {len(known_words)}")
    debug_print(f"Capitalization whitelist: {len(capitalization_whitelist)}")
    debug_print(f"Dash whitelist: {len(dash_whitelist)}")
    debug_print(f"Exceptions: {len(exceptions)}")
    debug_print(f"Combined allowed words: {len(all_allowed_words)}")
    
    # Debug: Show sample compound terms
    compound_terms = [w for w in all_allowed_words if "-" in w]
    debug_print(f"Sample compound terms: {compound_terms[:10]}")
    
    math_regions = find_math_regions(title)
    debug_print(f"Math regions: {math_regions}")
    
    # FIXED: Use the corrected tokenization
    tokens = robust_tokenize_with_math(title, all_allowed_words, math_regions)
    debug_print(
        f"Tokens: {[(tok.kind, tok.value, tok.start, tok.end) for tok in tokens]}"
    )
    
    def is_word(tok_value: str) -> bool:
        if not tok_value or tok_value.isspace():
            return False
        if all(c in ",.;:!?-–—'\"()[]{}" for c in tok_value):
            return False
        if is_filename_math_token(tok_value):
            return False
        return any(unicodedata.category(c)[0] == "L" for c in tok_value)
    
    for idx, token in enumerate(tokens):
        debug_print(
            f"Processing token {idx}: '{token.value}' (kind: {token.kind}, pos: {token.start}-{token.end})"
        )
        
        # FIXED: Skip if already identified as a phrase - this is the key fix!
        if token.kind == "PHRASE":
            debug_print(f"  → Skipping phrase token: '{token.value}'")
            continue
        
        if not is_word(token.value):
            debug_print("  → Not a word, skipping")
            continue
        
        if any(a <= token.start < b or a < token.end <= b for a, b in math_regions):
            debug_print("  → In math region, skipping")
            continue
        
        base = (
            token.value[:-2]
            if token.value.lower().endswith(("'s", "'s"))
            else token.value
        )
        debug_print(f"  → Base word: '{base}'")
        
        # Normalize Unicode for comparison
        base_normalized = nfc(base)
        
        if base.isdigit() or base.lower() in {"", "s"}:
            debug_print("  → Digit or empty, skipping")
            continue
        
        # Check for mathematical variables
        if len(base) == 1 and base.isalpha():
            next_token_idx = idx + 1
            if next_token_idx < len(tokens):
                next_token = tokens[next_token_idx]
                if (
                    next_token.value.startswith("^")
                    or next_token.value.startswith("_")
                    or re.match(
                        r"^[\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089]",
                        next_token.value,
                    )
                ):
                    debug_print("  → Math variable, skipping")
                    continue
        
        # FIXED: Check against combined whitelist first (with Unicode normalization)
        all_allowed_words_normalized = {nfc(w) for w in all_allowed_words}
        if base_normalized in all_allowed_words_normalized:
            debug_print(f"  → '{base}' found in all_allowed_words, skipping")
            continue
        
        # Check if this is a mathematical variable in context
        if is_mathematical_variable_in_context(title, base, token.start, token.end):
            debug_print("  → Mathematical variable in context, skipping")
            continue
        
        # NEW: Check if this is a compound term where the first part is in a whitelist
        # e.g., "Itô-formula" is OK if "Itô" is in the whitelist
        if "-" in base_normalized or "–" in base_normalized:
            # Prepare case-sensitive words for checking
            case_sensitive_words = (
                capitalization_whitelist | exceptions | dash_whitelist
            )
            case_sensitive_words_normalized = {nfc(w) for w in case_sensitive_words}
            canon_known_temp = {canonicalize(nfc(w)) for w in known_words}
            
            # Try both dash types
            for dash in ["-", "–"]:
                if dash in base_normalized:
                    parts = base_normalized.split(dash, 1)
                    if len(parts) == 2:
                        first_part = parts[0]
                        # Check if first part is in any whitelist
                        if (
                            first_part in all_allowed_words_normalized
                            or first_part in case_sensitive_words_normalized
                            or canonicalize(first_part) in canon_known_temp
                        ):
                            debug_print(
                                f"  → '{base}' is compound term with whitelisted first part '{first_part}', skipping"
                            )
                            continue
        
        # FIXED: Handle case-sensitive vs case-insensitive matching separately (with normalization)
        
        # First check exact match against case-sensitive lists
        case_sensitive_words = capitalization_whitelist | exceptions | dash_whitelist
        case_sensitive_words_normalized = {nfc(w) for w in case_sensitive_words}
        if base_normalized in case_sensitive_words_normalized:
            debug_print(
                f"  → '{base}' found in case-sensitive lists (exact match), skipping"
            )
            continue
        
        # Then check canonicalized match against case-insensitive known_words only
        cbase = canonicalize(base_normalized)
        canon_known = {canonicalize(nfc(w)) for w in known_words}
        
        if cbase in canon_known:
            debug_print(
                f"  → '{base}' (canonicalized: '{cbase}') found in known_words, skipping"
            )
            continue
        
        if base.isupper() and cbase not in canon_known:
            error = f"Not in any allowed list: '{token.value}'"
            debug_print(f"  → UPPERCASE ERROR: {error}")
            errs.append(error)
            continue
        
        if not speller.is_misspelled(base_normalized):
            debug_print(f"  → Speller says '{base}' is OK, skipping")
            continue
        
        error = f"Not in any allowed list: '{token.value}'"
        debug_print(f"  → FINAL ERROR: {error}")
        errs.append(error)
    
    debug_print(f"=== END spelling_and_format_errors, {len(errs)} errors ===")
    return errs


def is_mathematical_variable_in_context(text: str, word: str, word_start: int, word_end: int) -> bool:
    """FIXED: Check if a word is a mathematical variable in a mathematical context - RESTORED from original"""
    MATHEMATICAL_OPERATORS = {'+', '-', '*', '/', '=', '<', '>', '≤', '≥', '≠', '≈', '∈', '∉', '⊂', '⊆', '∪', '∩', '∅', '∞', '∂', '∇', '∫', '∑', '∏', '√', '∼', '≡', '⊕', '⊗', '∧', '∨', '¬', '→', '↔', '∀', '∃', '∝', '∴', '∵', '°', '±', '∓', '×', '÷', '·', '∘', '∆', '∇', '∂', '∫', '∮', '∑', '∏', '∐', '∪', '∩', '∁', '∖', '∆', '∇', '∂', '∫', '∮', '∑', '∏', '∐', '∪', '∩', '∁', '∖'}
    
    # Only consider single-letter words as potential mathematical variables
    if len(word) != 1 or not word.isalpha():
        return False
    
    # Check if immediately followed by mathematical operator
    if word_end < len(text):
        next_char = text[word_end]
        if next_char in MATHEMATICAL_OPERATORS:
            return True
    
    # Check if immediately preceded by mathematical operator
    if word_start > 0:
        prev_char = text[word_start - 1]
        if prev_char in MATHEMATICAL_OPERATORS:
            return True
    
    # FIXED: Check for "set X" pattern which is mathematical
    if word_start >= 5:
        before_context = text[word_start - 5 : word_start].lower()
        if before_context.endswith("set "):
            return True
    
    # Check for mathematical context words nearby
    context_start = max(0, word_start - 50)
    context_end = min(len(text), word_end + 50)
    context = text[context_start:context_end].lower()
    
    mathematical_context_words = {
        "dimension", "cardinality", "degree", "rank", "order", "space", "field",
        "group", "ring", "module", "algebra", "manifold", "topology", "metric",
        "norm", "measure", "probability", "distribution", "function", "operator",
        "transformation", "matrix", "vector", "tensor", "equation", "inequality",
        "theorem", "lemma", "proof", "conjecture", "hypothesis", "corollary",
        "proposition", "definition", "axiom", "postulate", "algorithm", "formula",
        "expression", "variable", "constant", "parameter", "coefficient", "exponent",
        "logarithm", "exponential", "polynomial", "rational", "irrational", "real",
        "complex", "imaginary", "integer", "natural", "prime", "composite", "even",
        "odd", "finite", "infinite", "continuous", "discrete", "differentiable",
        "integrable", "convergent", "divergent", "limit", "derivative", "integral",
        "series", "sequence", "sum", "product", "quotient", "remainder", "modulo",
        "congruent", "equivalent", "isomorphic", "homeomorphic", "bijective",
        "injective", "surjective", "invertible", "determinant", "eigenvalue",
        "eigenvector", "trace", "characteristic", "minimal", "maximal", "supremum",
        "infimum", "bounded", "unbounded", "compact", "connected", "simply",
        "multiply", "path", "component", "homotopy", "homology", "cohomology",
        "fundamental", "universal", "covering", "fiber", "bundle", "sheaf",
        "scheme", "variety", "affine", "projective", "elliptic", "parabolic",
        "hyperbolic", "euclidean", "non-euclidean", "riemannian", "lorentzian",
        "minkowski", "hilbert", "banach", "sobolev", "hardy", "bergman", "fock",
        "schwartz", "tempered", "distribution", "generalized", "classical",
        "quantum", "statistical", "thermodynamic", "mechanical", "dynamical",
        "stochastic", "deterministic", "chaotic", "periodic", "aperiodic",
        "stable", "unstable", "attracting", "repelling", "fixed", "critical",
        "saddle", "node", "focus", "center", "spiral", "limit", "cycle",
        "bifurcation", "catastrophe", "singularity", "regularity", "smoothness",
        "analyticity", "holomorphic", "meromorphic", "entire", "rational"
    }
    
    # Check if any mathematical context words are present
    for ctx_word in mathematical_context_words:
        if ctx_word in context:
            return True
    
    return False