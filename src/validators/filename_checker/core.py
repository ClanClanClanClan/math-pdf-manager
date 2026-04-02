"""
Core filename validation functionality.

This module provides the main check_filename function and associated
validation logic.
"""

from typing import List, Optional, Any, Set
import re

from .data_structures import FilenameCheckResult, Message
from .debug import debug_print, enable_debug
from .unicode_utils import sanitize_unicode_security, nfc, find_all_exception_spans, add_spaces_after_commas
from .tokenization import enforce_ndash_between_authors
from .math_utils import find_math_regions
from .text_processing import (
    fix_ellipsis, fix_ligatures, fix_ligature_words, spell_out_small_numbers,
    fix_and_flag_quotes
)
from .author_processing import (
    parse_authors_and_title, author_string_is_normalized, normalize_for_comparison,
    is_nfc
)

# Try to import required functions from existing modules
try:
    from src.core.text_processing.my_spellchecker import SpellChecker
    from langdetect import detect, LangDetectException
    debug_print("Successfully imported SpellChecker and language detection")
except ImportError:
    debug_print("Failed to import SpellChecker, using fallback")
    class LangDetectException(Exception):
        pass
    
    class MockSpellChecker:
        def __init__(self):
            self.known_words = set()
            
        def is_misspelled(self, word):
            return False
            
        def candidates(self, word):
            return []
    
    SpellChecker = MockSpellChecker
    
    def detect(text):
        return "en"

# Global debug flag
_DEBUG_ENABLED = False


def check_filename(
    filename: str,
    known_words: Set[str] = None,
    whitelist_pairs: List[str] = None,
    exceptions: Set[str] = None,
    compound_terms: Set[str] = None,
    *,
    spellchecker: Optional[SpellChecker] = None,
    language_tool: Optional[Any] = None,
    sentence_case: bool = True,
    lowercase_exceptions: Optional[Set[str]] = None,
    capitalization_whitelist: Optional[Set[str]] = None,
    debug: bool = False,
    multiword_surnames: Optional[Set[str]] = None,
    name_dash_whitelist: Optional[Set[str]] = None,
    auto_fix_nfc: bool = False,
    auto_fix_authors: bool = False,
    **kwargs
) -> FilenameCheckResult:
    """
    Main filename validation function.
    
    Args:
        filename: The filename to validate
        known_words: Set of known valid words
        whitelist_pairs: List of whitelisted word pairs
        exceptions: Set of exception words
        compound_terms: Set of compound terms
        spellchecker: Optional SpellChecker instance
        language_tool: Optional language tool instance
        sentence_case: Whether to apply sentence case
        lowercase_exceptions: Set of words that should remain lowercase
        capitalization_whitelist: Set of words with special capitalization
        debug: Enable debug mode
        multiword_surnames: Set of multiword surnames
        name_dash_whitelist: Set of names with dashes
        auto_fix_nfc: Automatically fix NFC normalization
        auto_fix_authors: Automatically fix author formatting
        **kwargs: Additional arguments
    
    Returns:
        FilenameCheckResult containing validation results
    """
    # Use defaults if None provided
    if known_words is None:
        known_words = set()
    if whitelist_pairs is None:
        whitelist_pairs = []
    if exceptions is None:
        exceptions = set()
    if compound_terms is None:
        compound_terms = set()
    if capitalization_whitelist is None:
        capitalization_whitelist = set()
    if name_dash_whitelist is None:
        name_dash_whitelist = set()
    if multiword_surnames is None:
        multiword_surnames = set()
    if lowercase_exceptions is None:
        lowercase_exceptions = set()

    # Performance protection: limit input length to prevent ReDoS attacks
    if len(filename) > 5000:  # Reasonable limit for academic filenames
        return FilenameCheckResult(
            is_valid=False,
            original_filename=filename,
            messages=[
                Message(
                    "error",
                    "Filename too long for processing (security protection)",
                    None,
                )
            ],
        )

    # Enable debug mode for all checks
    if debug or _DEBUG_ENABLED:
        enable_debug()

    spellchecker = spellchecker or SpellChecker()
    raw = filename

    debug_print(f"=== CHECKING FILENAME: '{filename}' ===")

    # Log the input word lists
    debug_print("Input word lists:")
    debug_print(f"  Known words: {len(known_words)}")
    debug_print(f"  Capitalization whitelist: {len(capitalization_whitelist)}")
    debug_print(f"  Dash whitelist: {len(name_dash_whitelist)}")
    debug_print(f"  Exceptions: {len(exceptions)}")
    debug_print(f"  Compound terms: {len(compound_terms)}")

    # Create result object early so we can use add_message
    result = FilenameCheckResult(
        is_valid=True,
        original_filename=raw,
        corrected_filename=filename
    )
    
    # Unicode security check
    filename_clean, removed, scripts = sanitize_unicode_security(filename)
    if removed:
        result.add_message(
            "error",
            f"Removed dangerous char(s): {', '.join(removed)}"
        )
    if len(scripts) > 1 and "LATIN" in scripts:
        result.add_message(
            "error",
            f"Mixed scripts detected: {', '.join(sorted(scripts))}"
        )
    if any(x in filename_clean for x in ("..", "/", "\\", "\x00")):
        result.add_message(
            "error",
            "Filename contains path-traversal or control chars"
        )

    # Use cleaned filename for further processing
    filename = filename_clean

    # NFC normalization check
    if not is_nfc(filename):
        result.add_message("warning", "Filename not NFC-normalised")
        if auto_fix_nfc:
            filename = nfc(filename)

    # Enhanced separator detection
    if " - " not in filename:
        if " -" in filename or "- " in filename or re.search(r"\w\.\s+[A-Z]", filename):
            result.add_message("error", "Missing ' - ' between authors and title")
        else:
            result.add_message("error", "Missing ' - ' between authors and title")
        
        # Set as invalid and return early
        result.is_valid = False
        return result

    # Parse authors and title
    authors_raw, title_raw = parse_authors_and_title(filename, multiword_surnames)

    # Normalize both authors and title to NFC immediately after parsing
    authors_raw = nfc(authors_raw) if authors_raw else authors_raw
    title_raw = nfc(title_raw) if title_raw else title_raw

    # Extract file extension
    ext_match = re.search(r"\.(?P<ext>[A-Za-z0-9]{1,4})$", title_raw)
    ext = ext_match.group("ext").lower() if ext_match else None
    title_wo_ext = title_raw[: ext_match.start()] if ext_match else title_raw

    debug_print(f"Title without extension: '{title_wo_ext}'")

    # Find mathematical regions
    math_regions = find_math_regions(title_wo_ext)

    # Get language from the full filename for better context
    try:
        lang = detect(filename)
    except (LangDetectException, ValueError):
        lang = "en"
    debug_print(f"Detected language from full filename: {lang}")

    # Find phrase spans for exceptions
    phrase_spans = find_all_exception_spans(
        title_wo_ext,
        capitalization_whitelist | name_dash_whitelist | exceptions | compound_terms,
    )

    debug_print(f"Math regions: {math_regions}")

    # Enhanced quote processing that excludes contractions
    title_wo_ext_processed, quote_flags = fix_and_flag_quotes(
        title_wo_ext, lang, math_regions, phrase_spans, debug=debug
    )
    for flag in quote_flags:
        result.add_message("error", flag)

    # Apply text fixers with math regions
    fixers = [
        fix_ellipsis,
        fix_ligatures,
        fix_ligature_words,
        spell_out_small_numbers,
        # Note: Some fixers from original are not implemented yet
    ]
    current = title_wo_ext_processed

    debug_print(f"Applying fixers to: '{current}'")

    for fn in fixers:
        try:
            math_regions_current = find_math_regions(current)
            new = fn(current, math_regions_current, exceptions, phrase_spans)
            if new != current:
                debug_print(f"Fixer {fn.__name__}: '{current}' → '{new}'")
                result.add_message("info", f"{fn.__name__}: '{current}' → '{new}'")
                current = new
        except Exception as e:
            debug_print(f"Fixer {fn.__name__} failed: {e}")
            # Continue with other fixers

    title_after = current
    debug_print(f"After fixers: '{title_after}'")

    # ── Empty title check ──────────────────────────────────────────────
    if not title_after or not title_after.strip():
        result.add_message("error", "Title is empty or whitespace-only")

    # ── Dash pattern validation ────────────────────────────────────────
    # Check for bad dash patterns: space-hyphen-space, double hyphens, etc.
    _bad_dash_re = re.compile(
        r'(?P<shs>\s+-\s+)'        # space-hyphen-space (should be em-dash)
        r'|(?P<multi>-{2,})'       # multiple consecutive hyphens
    )
    for m in _bad_dash_re.finditer(title_after):
        if m.group('shs'):
            result.add_message(
                "warning",
                f"Dash pattern: space-hyphen-space at position {m.start()} "
                "(consider em-dash or en-dash)"
            )
        elif m.group('multi'):
            result.add_message(
                "warning",
                f"Dash pattern: multiple consecutive hyphens at position {m.start()}"
            )

    # Enhanced author normalization check
    ok, authors_fixed = author_string_is_normalized(authors_raw)
    if not ok:
        if auto_fix_authors:
            result.add_message("info", f"Author fix: {authors_raw} → {authors_fixed}")
            authors_clean = authors_fixed
        else:
            result.add_message("warning", f"Author format suggestion: {authors_fixed}")
            authors_clean = authors_raw
    else:
        authors_clean = authors_raw

    # Apply final author processing
    authors_clean = add_spaces_after_commas(
        enforce_ndash_between_authors(authors_clean, whitelist_pairs)
    )

    # Sentence case processing
    if sentence_case:
        try:
            from core.sentence_case import to_sentence_case_academic
            sent_case, sent_changed = to_sentence_case_academic(
                title_after,
                capitalization_whitelist=capitalization_whitelist,
                name_dash_whitelist=name_dash_whitelist,
                known_words=known_words,
            )
            if sent_changed:
                result.add_message(
                    "warning",
                    f"Sentence case: '{title_after}' → '{sent_case}'"
                )
        except ImportError:
            sent_case = title_after  # Fallback if core module unavailable
    else:
        sent_case = title_after

    # Determine if we need to fix the filename
    fixed_name = None
    new_fn = f"{authors_clean} - {sent_case}"
    if ext:
        new_fn += f".{ext}"

    # Check if the reconstructed filename differs from the original.
    # This catches ALL corrections: sentence case, author formatting,
    # NFC normalization, dash whitelist, etc.
    original_normalized = normalize_for_comparison(nfc(raw))
    new_normalized = normalize_for_comparison(nfc(new_fn))

    if original_normalized != new_normalized:
        fixed_name = new_fn
        debug_print(f"Filename fix needed: '{raw}' → '{new_fn}'")
    else:
        debug_print(f"No filename fix needed after comparison: '{raw}'")

    # Update result with final information
    result.corrected_filename = fixed_name
    result.is_valid = len(result.errors) == 0

    debug_print(
        f"Final result: errors={len(result.errors)}, suggestions={len(result.messages) - len(result.errors)}"
    )
    debug_print("=== END CHECKING FILENAME ===")

    return result


# Backward compatibility functions
def check_filename_spelling_and_format(*args, **kwargs):
    """Placeholder for backward compatibility."""
    return check_filename(*args, **kwargs)


def check_filename_basic(*args, **kwargs):
    """Placeholder for backward compatibility."""
    return check_filename(*args, **kwargs)


def check_filename_advanced(*args, **kwargs):
    """Placeholder for backward compatibility."""
    return check_filename(*args, **kwargs)


def process_filename(filename: str, **kwargs) -> dict:
    """Process filename compatibility function - RESTORED from original"""
    result = check_filename(filename, set(), [], set(), set(), **kwargs)
    return {
        "filename": result.filename,
        "errors": result.errors,
        "suggestions": result.suggestions,
        "fixed": result.fixed_filename,
    }


def process_files(files: list, **kwargs) -> list:
    """Batch file processing compatibility - RESTORED from original"""
    from .batch_processing import batch_check_filenames
    return batch_check_filenames(files, set(), [], set(), set(), **kwargs)


def validate_filename_format(filename: str) -> bool:
    """Validate filename format compatibility - RESTORED from original"""
    return (
        " - " in filename
        and not filename.startswith(" - ")
        and not filename.endswith(" - ")
    )


def format_error_message(error: str, context: str = "") -> str:
    """Format error message compatibility - RESTORED from original"""
    return f"{error}" + (f" ({context})" if context else "")


def load_config_file(config_path: str) -> dict:
    """Load YAML configuration file - RESTORED from original"""
    import yaml
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config file {config_path}: {e}")
        return {}


def load_word_list(word_list_path: str) -> set:
    """Load word list from file - RESTORED from original"""
    try:
        with open(word_list_path, 'r', encoding='utf-8') as f:
            return set(line.strip().lower() for line in f if line.strip())
    except Exception as e:
        print(f"Error loading word list {word_list_path}: {e}")
        return set()


def check_capitalization(text: str, whitelist: set, dash_whitelist: set) -> list:
    """Check title capitalization - RESTORED from original"""
    # Import here to avoid circular imports
    try:
        from ..validators.title_normalizer import check_title_capitalization
        return check_title_capitalization(text, whitelist, dash_whitelist)
    except ImportError:
        # Fallback implementation
        errors = []
        words = text.split()
        if words and not words[0][0].isupper():
            errors.append("First word should be capitalized")
        return errors


def check_spelling(text: str, known_words: set, whitelist: set, exceptions: set, dash_whitelist: set, speller) -> list:
    """Check spelling and format errors - RESTORED from original"""
    # Import here to avoid circular imports
    try:
        from ..validators.title_normalizer import spelling_and_format_errors
        return spelling_and_format_errors(text, known_words, whitelist, exceptions, dash_whitelist, speller)
    except ImportError:
        # Fallback implementation
        errors = []
        words = text.split()
        for word in words:
            if word.lower() not in known_words and word.lower() not in whitelist:
                if speller and speller.unknown([word]):
                    errors.append(f"Unknown word: {word}")
        return errors