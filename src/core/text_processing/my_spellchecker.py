"""
my_spellchecker.py  ―  project-local spell-checking helper (FIXED VERSION)
===========================================================================

• Provides :func:`canonicalize`, :func:`load_known_words`, :func:`check_spelling`
• Exports :class:`SpellChecker`, a thin wrapper around *pyspellchecker*
  that also honours project-specific word-lists and LanguageTool.

This file is **stand-alone** – just drop it into *Scripts/* and run the test-suite.
"""

from __future__ import annotations

import atexit
import logging
import re
import threading
import unicodedata
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable, Optional, Union
from weakref import WeakSet

# Import consolidated text processing utilities
try:
    # Check if consolidated text processing is available
    import importlib.util
    _text_processing_spec = importlib.util.find_spec('core.text_processing')
    USE_CONSOLIDATED_TEXT_PROCESSING = _text_processing_spec is not None
except ImportError:
    USE_CONSOLIDATED_TEXT_PROCESSING = False

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

DEFAULT_LANGUAGE = "en_GB"
MORFOLOGIK_RULE_PREFIX = "MORFOLOGIK_RULE"
MAX_TEXT_LENGTH = 1_000_000  # 1MB text limit
MAX_WORD_LENGTH = 50
MAX_FILE_SIZE = 10_485_760  # 10MB file limit
CACHE_SIZE = 10_000

# Pre-compiled regex patterns
# Pattern that matches words including Unicode letters, digits, and apostrophes
# \w in Python includes Unicode letters and digits by default
WORD_PATTERN = re.compile(r"\b\w+(?:'\w+)?(?:[-–—]\w+(?:'\w+)?)*\b", flags=re.UNICODE)
ZERO_WIDTH_PATTERN = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f]", flags=re.UNICODE)
DASH_PATTERN = re.compile(r"[–—−]", flags=re.UNICODE)
HYPHEN_TRIM_PATTERN = re.compile(r"^-+|-+$", flags=re.UNICODE)

# --------------------------------------------------------------------------- #
# 3rd-party libraries (fail gracefully)
# --------------------------------------------------------------------------- #

try:
    from spellchecker import SpellChecker as _BaseSpellChecker
    ExternalSpellChecker = _BaseSpellChecker
except ImportError:
    ExternalSpellChecker = None  # type: ignore[assignment]

try:
    import language_tool_python
    LT_AVAILABLE = True
except ImportError:
    language_tool_python = None  # type: ignore[assignment]
    LT_AVAILABLE = False

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

logger = logging.getLogger("my_spellchecker")

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

@dataclass
class SpellCheckerConfig:
    """Configuration for SpellChecker."""
    language: str = DEFAULT_LANGUAGE
    known_words: Optional[Iterable[str]] = None
    capitalization_whitelist: Optional[Iterable[str]] = None
    name_dash_whitelist: Optional[Iterable[str]] = None
    use_languagetool: bool = False
    lt_server: Optional[str] = None
    cache_size: int = CACHE_SIZE
    max_text_length: int = MAX_TEXT_LENGTH
    thread_safe: bool = False

# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #

class SpellCheckerError(Exception):
    """Base exception for spell checker errors."""
    pass

class ConfigurationError(SpellCheckerError):
    """Raised when configuration is invalid."""
    pass

class ResourceError(SpellCheckerError):
    """Raised when external resources fail."""
    pass

# --------------------------------------------------------------------------- #
# Resource Management
# --------------------------------------------------------------------------- #

_active_languagetools: WeakSet = WeakSet()

def _cleanup_languagetools():
    """Clean up any remaining LanguageTool instances."""
    for lt in list(_active_languagetools):
        try:
            if hasattr(lt, 'close'):
                lt.close()
        except Exception:
            pass

atexit.register(_cleanup_languagetools)

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=CACHE_SIZE)
def canonicalize(s: str) -> str:
    """
    Canonical form used throughout the project:
    
    NOTE: This function is now available in consolidated form at:
    core.text_processing.canonicalize() - consider migrating to use that version.

    1. strip BOM / zero-width & directional controls
    2. normalise dashes to hyphen
    3. strip accents & combining marks
    4. ``lower().strip()`` and remove leading/trailing hyphens
    
    Args:
        s: String to canonicalize
        
    Returns:
        Canonicalized string
        
    Raises:
        TypeError: If input is not a string
        
    Examples:
        >>> canonicalize("Café")
        'cafe'
        >>> canonicalize("  --test--  ")
        'test'
    """
    if not isinstance(s, str):
        raise TypeError(f"Expected str, got {type(s).__name__}")
    
    if len(s) > MAX_WORD_LENGTH:
        logger.warning("Word exceeds maximum length: %d chars", len(s))
        s = s[:MAX_WORD_LENGTH]

    # Remove BOM
    s = s.replace("\ufeff", "")
    
    # Normalize dashes
    s = DASH_PATTERN.sub("-", s)
    
    # Remove zero-width and directional characters
    s = ZERO_WIDTH_PATTERN.sub("", s)
    
    # CRITICAL FIX: Remove problematic characters BEFORE NFKD normalization
    # NFKD converts ™→TM, ®→(R), ©→(C), etc. so we MUST remove them first!
    # Also remove any multi-character results from NFKD like "TM", "(R)", etc.
    s = s.replace('™', '').replace('®', '').replace('©', '')
    s = s.replace('°', '').replace('±', '').replace('×', '').replace('÷', '')
    s = s.replace('²', '').replace('³', '').replace('¹', '').replace('º', '')
    
    # NOW use NFKD to decompose accented characters
    s = unicodedata.normalize("NFKD", s)
    
    # Remove any TM, (R), (C) that might have been created by NFKD from other Unicode variants
    # Use case-insensitive replacement since we lowercase later anyway
    s = re.sub(r'\bTM\b', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\(R\)', '', s, flags=re.IGNORECASE) 
    s = re.sub(r'\(C\)', '', s, flags=re.IGNORECASE)
    
    # Remove combining characters (removes accents)
    s = "".join(c for c in s if not unicodedata.combining(c))
    
    # Filter to keep only ASCII alphanumeric and basic punctuation
    # This removes any remaining non-ASCII characters (emoji, Chinese, etc.)
    s = ''.join(c for c in s if ord(c) < 128 and (c.isalnum() or c in " -_'.,;:!?()"))
    
    # Remove "TM" if it appears as a separate word after all processing
    s = re.sub(r'\btm\b', '', s, flags=re.IGNORECASE)
    
    # Lowercase and strip
    s = s.lower().strip()
    
    # Remove leading/trailing hyphens
    s = HYPHEN_TRIM_PATTERN.sub("", s)
    
    # Clean up any multiple spaces that might have been created
    s = ' '.join(s.split())
    
    return s


def validate_path(path: Union[str, Path]) -> Path:
    """
    Validate and resolve a file path safely.
    
    Raises:
        ValueError: If path is invalid or outside allowed directories
    """
    try:
        resolved = Path(path).expanduser().resolve()
        
        # Check if path exists
        if not resolved.exists():
            raise ValueError(f"Path does not exist: {path}")
            
        if not resolved.is_file():
            raise ValueError(f"Path is not a file: {path}")
            
        # Check file size
        if resolved.stat().st_size > MAX_FILE_SIZE:
            raise ValueError(f"File too large: {resolved.stat().st_size} bytes")
            
        return resolved
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Invalid path: {path}") from e


def load_known_words(
    path: Union[str, Path, None] = None,
    *,
    normalize: Optional[str] = "NFC",
    validate: bool = True,
) -> frozenset[str]:
    """
    Load *known_words.txt* (or another file) and return **immutable** `frozenset`.

    • Comments begin with "#".
    • Blank lines are skipped.
    • `normalize` chooses a Unicode normal-form (``None`` ⇒ no normalisation).
    
    Args:
        path: Path to word file (default: known_words.txt in script directory)
        normalize: Unicode normalization form
        validate: Whether to validate the path
        
    Returns:
        Immutable set of known words
        
    Raises:
        ValueError: If path validation fails
        IOError: If file cannot be read
    """
    if path is None:
        path = Path(__file__).with_name("known_words.txt")
    
    if validate:
        path = validate_path(path)
    else:
        path = Path(path).expanduser()

    out: set[str] = set()
    
    try:
        with path.open(encoding="utf-8-sig", errors="strict") as fh:
            for line_num, line in enumerate(fh, 1):
                if line_num > 1_000_000:  # Prevent DoS
                    logger.warning("Word file too large, stopping at line %d", line_num)
                    break
                    
                w = line.split("#", 1)[0].strip()
                if not w:
                    continue
                    
                if len(w) > MAX_WORD_LENGTH:
                    logger.warning("Word too long on line %d: %s", line_num, w[:50])
                    continue
                    
                if normalize:
                    w = unicodedata.normalize(normalize, w)
                out.add(w)
    except UnicodeDecodeError as e:
        logger.error("Unicode decode error in %s: %s", path, e)
        raise IOError(f"Failed to decode file {path}: {e}") from e
    except IOError as e:
        logger.error("Failed to load words from %s: %s", path, e)
        raise

    return frozenset(out)


@lru_cache(maxsize=CACHE_SIZE)
def extract_words(text: str) -> tuple[str, ...]:
    """
    Return word-like tokens (handles contractions and hyphenated compounds).
    
    Returns tuple for hashability (enables caching).
    
    NOTE: This function is now available in consolidated form at:
    core.text_processing.extract_words() - consider migrating to use that version.
    
    Examples:
        >>> extract_words("Don't forget the re-test!")
        ("Don't", 'forget', 'the', 're-test')
        >>> extract_words("café naïve résumé")
        ('café', 'naïve', 'résumé')
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str, got {type(text).__name__}")
        
    if not text.strip():
        return ()
        
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(f"Text too long: {len(text)} chars (max: {MAX_TEXT_LENGTH})")
    
    words = WORD_PATTERN.findall(text)
    return tuple(words)  # Tuple for caching


def load_word_file(path: Union[str, Path, None]) -> set[str]:
    """
    Utility: read a simple 1-word-per-line file (ignore blanks & comments).
    
    Safely handles missing files and I/O errors.
    """
    if not path:
        return set()
        
    words: set[str] = set()
    
    try:
        validated_path = validate_path(path)
        with validated_path.open("r", encoding="utf-8-sig") as fh:
            for line_num, line in enumerate(fh, 1):
                if line_num > 1_000_000:
                    logger.warning("File too large, stopping at line %d", line_num)
                    break
                    
                t = line.strip()
                if t and not t.startswith("#"):
                    words.add(t)
    except (ValueError, IOError) as e:
        logger.warning("Failed to load word file %s: %s", path, e)
        
    return words


# --------------------------------------------------------------------------- #
# Main Spell-checker class
# --------------------------------------------------------------------------- #

class SpellChecker:
    """
    Thread-safe, resource-managed spell-checker.

    • honours *known_words*, *capitalization_whitelist*, *name_dash_whitelist*
    • optional LanguageTool support  (``use_languagetool=True``)
    • falls back to *pyspellchecker* if available
    • implements context manager protocol for resource cleanup
    """

    def __init__(self, config: Optional[SpellCheckerConfig] = None) -> None:
        """Initialize spell checker with configuration."""
        self.config = config or SpellCheckerConfig()
        self._lock = threading.RLock() if self.config.thread_safe else None
        self._closed = False
        
        # Validate configuration
        self._validate_config()
        
        # Initialize caches
        self._spell_cache: OrderedDict[str, bool] = OrderedDict()
        self._cache_size = self.config.cache_size
        
        # Initialize word sets
        self._init_word_sets()
        
        # Initialize external tools
        self._init_external_tools()

    def _validate_config(self) -> None:
        """Validate configuration parameters."""
        if not self.config.language:
            raise ConfigurationError("Language cannot be empty")
            
        if self.config.cache_size < 0:
            raise ConfigurationError("Cache size must be non-negative")
            
        if self.config.max_text_length < 0:
            raise ConfigurationError("Max text length must be non-negative")

    def _init_word_sets(self) -> None:
        """Initialize canonicalized word sets."""
        # Canonicalized known words
        self._known_canon = {
            canonicalize(w) for w in (self.config.known_words or [])
        }

        # Canonicalized whitelists
        self._canon_whitelist: dict[str, set[str]] = {}
        
        for whitelist in (self.config.capitalization_whitelist, 
                         self.config.name_dash_whitelist):
            if whitelist:
                for w in whitelist:
                    canon = canonicalize(w)
                    self._canon_whitelist.setdefault(canon, set()).add(w)

    def _init_external_tools(self) -> None:
        """Initialize LanguageTool and pyspellchecker."""
        # LanguageTool
        self.lt = None
        if self.config.use_languagetool and LT_AVAILABLE:
            self._init_languagetool()
            
        # pyspellchecker
        self.spell = None
        if ExternalSpellChecker is not None:
            self._init_pyspellchecker()

    def _init_languagetool(self) -> None:
        """Initialize LanguageTool with error handling."""
        lt_lang = "en-GB" if self.config.language.lower().startswith("en") else self.config.language
        
        try:
            if self.config.lt_server:
                self.lt = language_tool_python.LanguageToolPublicAPI(
                    lt_lang, host=self.config.lt_server
                )
            else:
                self.lt = language_tool_python.LanguageTool(lt_lang)
            
            _active_languagetools.add(self.lt)
            
        except Exception as exc:
            logger.error("LanguageTool initialization failed: %s", exc)
            self.config.use_languagetool = False
            self.lt = None

    def _init_pyspellchecker(self) -> None:
        """Initialize pyspellchecker with error handling."""
        try:
            # Map language codes
            spell_lang = "en" if self.config.language.lower().startswith("en") else self.config.language
            self.spell = ExternalSpellChecker(language=spell_lang)
            
            if self.config.known_words:
                self.spell.word_frequency.load_words(self.config.known_words)
                
        except Exception as exc:
            logger.error("pyspellchecker initialization failed: %s", exc)
            self.spell = None

    def _with_lock(func):
        """Decorator for thread-safe methods."""
        def wrapper(self, *args, **kwargs):
            if self._lock:
                with self._lock:
                    return func(self, *args, **kwargs)
            return func(self, *args, **kwargs)
        return wrapper

    @_with_lock
    def _cache_lookup(self, word: str) -> Optional[bool]:
        """Thread-safe cache lookup with LRU eviction."""
        if word in self._spell_cache:
            # Move to end (most recently used)
            self._spell_cache.move_to_end(word)
            return self._spell_cache[word]
        return None

    @_with_lock
    def _cache_store(self, word: str, result: bool) -> None:
        """Thread-safe cache storage with LRU eviction."""
        self._spell_cache[word] = result
        if len(self._spell_cache) > self._cache_size:
            # Remove least recently used
            self._spell_cache.popitem(last=False)

    def _exact_whitelist(self, word: str) -> bool:
        """Check if word matches exact whitelist entry."""
        canon = canonicalize(word)
        allowed = self._canon_whitelist.get(canon)
        return bool(allowed and word in allowed)

    def _should_be_exact(self, word: str) -> Optional[str]:
        """Return suggested spelling if word is almost in whitelist."""
        canon = canonicalize(word)
        allowed = self._canon_whitelist.get(canon)
        if allowed and word not in allowed:
            return sorted(allowed)[0]
        return None

    def _in_known(self, word: str) -> bool:
        """Check if word is in known words (case-insensitive)."""
        return canonicalize(word) in self._known_canon

    def _check_with_languagetool(self, word: str) -> Optional[bool]:
        """Check word with LanguageTool."""
        if not self.lt:
            return None
            
        try:
            matches = self.lt.check(word)
            morfologik_errors = [
                m for m in matches 
                if m.ruleId.startswith(MORFOLOGIK_RULE_PREFIX)
            ]
            return len(morfologik_errors) == 0
        except Exception as exc:
            logger.debug("LanguageTool check failed for '%s': %s", word, exc)
            return None

    def _check_with_pyspellchecker(self, word: str) -> Optional[bool]:
        """Check word with pyspellchecker."""
        if not self.spell:
            return None
            
        try:
            # Single letters should be rejected unless explicitly in dictionary
            if len(word) == 1:
                # Only accept if it's explicitly in the spell checker
                return word.lower() in self.spell
                
            lower = word.lower()
            if lower in self.spell or word in self.spell:
                return True
            if word.istitle() and lower in self.spell:
                return True
            return False
        except Exception as exc:
            logger.debug("pyspellchecker check failed for '%s': %s", word, exc)
            return None

    def _misspelled_by_fallback(self, word: str) -> bool:
        """Check if word is misspelled according to all available checkers."""
        # Check cache first
        cached = self._cache_lookup(word)
        if cached is not None:
            return cached
            
        # Check with available spell checkers
        results = []
        
        # LanguageTool
        lt_result = self._check_with_languagetool(word)
        if lt_result is not None:
            results.append(lt_result)
            
        # pyspellchecker
        spell_result = self._check_with_pyspellchecker(word)
        if spell_result is not None:
            results.append(spell_result)
            
        # Determine result
        if not results:
            # No checkers available - for single letters, default to misspelled
            # For longer words, default to not misspelled
            result = len(word) == 1
        else:
            # Word is correct if ANY checker accepts it
            # For single letters, be more strict - ALL checkers must accept it
            if len(word) == 1:
                result = not all(results)  # Misspelled if ANY checker rejects it
            else:
                result = not any(results)  # Misspelled if ALL checkers reject it
            
        # Cache result
        self._cache_store(word, result)
        return result

    @_with_lock
    def is_misspelled(self, word: str) -> bool:
        """
        Public 1-word check (thread-safe).
        
        Args:
            word: Single word to check
            
        Returns:
            True if word is misspelled
            
        Raises:
            TypeError: If word is not a string
            ValueError: If closed
        """
        if self._closed:
            raise ValueError("SpellChecker is closed")
            
        if not isinstance(word, str):
            raise TypeError(f"Expected str, got {type(word).__name__}")
            
        return self._misspelled_by_fallback(word)

    @_with_lock
    def check_spelling(
        self,
        text: str,
        *,
        contains_math_func: Optional[Callable[[str], bool]] = None,
        unique_only: bool = True,
        debug: bool = False,
    ) -> list[str]:
        """
        Scan text and return list of problematic tokens.
        
        Args:
            text: Text to check
            contains_math_func: Optional function to identify math expressions
            unique_only: Whether to return only unique problems
            
        Returns:
            List of spelling problems (unique by default)
            
        Raises:
            TypeError: If text is not a string
            ValueError: If text is too long or checker is closed
        """
        if self._closed:
            raise ValueError("SpellChecker is closed")
            
        if not isinstance(text, str):
            raise TypeError(f"Expected str, got {type(text).__name__}")
            
        if len(text) > self.config.max_text_length:
            raise ValueError(
                f"Text too long: {len(text)} chars "
                f"(max: {self.config.max_text_length})"
            )
            
        problems: list[str] = []
        
        try:
            words = extract_words(text)
        except ValueError as e:
            logger.error("Failed to extract words: %s", e)
            return []

        for word in words:
            if debug:
                logger.debug(f"Checking word: '{word}'")
                
            # Skip math expressions
            if contains_math_func and contains_math_func(word):
                if debug:
                    logger.debug(f"  Skipping '{word}' (math expression)")
                continue

            # Check known words (takes precedence over whitelist)
            if self._in_known(word):
                if debug:
                    logger.debug(f"  ✓ '{word}' found in known words")
                continue
            
            # Check exact whitelist
            if self._exact_whitelist(word):
                if debug:
                    logger.debug(f"  ✓ '{word}' found in exact whitelist")
                continue

            # Check for case mismatch in whitelist
            suggestion = self._should_be_exact(word)
            if suggestion:
                if debug:
                    logger.debug(f"  ! '{word}' should be '{suggestion}' (case mismatch)")
                problems.append(f"'{word}' should appear as '{suggestion}'")
                continue

            # Single letters need special handling
            if len(word) == 1:
                # Only accept single letters if they're explicitly in known words
                # We already checked _in_known above, so this is an error
                if debug:
                    logger.debug(f"  ✗ '{word}' single letter not in known words")
                problems.append(word)
                continue

            # Check with dictionaries
            if self._misspelled_by_fallback(word):
                if debug:
                    logger.debug(f"  ✗ '{word}' flagged as misspelled by fallback checker")
                problems.append(word)
            elif debug:
                logger.debug(f"  ✓ '{word}' accepted by fallback checker")

        # Return unique problems if requested
        if unique_only:
            # Preserve order while removing duplicates
            return list(OrderedDict.fromkeys(problems))
        return problems

    def clear_cache(self) -> None:
        """Clear the spell check cache."""
        with self._lock if self._lock else threading.RLock():
            self._spell_cache.clear()

    def close(self) -> None:
        """Close and cleanup resources."""
        with self._lock if self._lock else threading.RLock():
            if self._closed:
                return
                
            self._closed = True
            
            # Close LanguageTool
            if self.lt:
                try:
                    if hasattr(self.lt, 'close'):
                        self.lt.close()
                    _active_languagetools.discard(self.lt)
                except Exception as exc:
                    logger.error("Failed to close LanguageTool: %s", exc)
                finally:
                    self.lt = None
                    
            # Clear caches
            self._spell_cache.clear()
            
            # Clear other resources
            self.spell = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.close()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Convenience wrapper (legacy API)
# --------------------------------------------------------------------------- #

def check_spelling(
    text: str,
    known_words: Optional[Iterable[str]],
    *,
    contains_math_func: Optional[Callable[[str], bool]] = None,
    capitalization_whitelist: Optional[Iterable[str]] = None,
    name_dash_whitelist: Optional[Iterable[str]] = None,
    use_languagetool: bool = False,
    debug: bool = False,
) -> list[str]:
    """Legacy API for backward compatibility."""
    config = SpellCheckerConfig(
        known_words=known_words,
        capitalization_whitelist=capitalization_whitelist,
        name_dash_whitelist=name_dash_whitelist,
        use_languagetool=use_languagetool,
    )
    
    with SpellChecker(config) as sc:
        return sc.check_spelling(text, contains_math_func=contains_math_func, debug=debug)


# --------------------------------------------------------------------------- #
# CLI interface
# --------------------------------------------------------------------------- #

def main():
    """Command-line interface."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description="Spell-check text using multiple backends",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --text "Check this text"
  %(prog)s --file document.txt --known project_words.txt
  %(prog)s --text "colour" --language en_US
  %(prog)s --text "Test" --use-lt --lt-server http://localhost:8081
        """
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--text", help="Text to check")
    input_group.add_argument("--file", help="File to check", type=Path)
    
    # Configuration options
    parser.add_argument("--known", help="Path to known_words.txt", type=Path)
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, 
                       help=f"Language code (default: {DEFAULT_LANGUAGE})")
    parser.add_argument("--use-lt", action="store_true", 
                       help="Use LanguageTool")
    parser.add_argument("--lt-server", help="LanguageTool server URL")
    parser.add_argument("--json", action="store_true", 
                       help="Output results as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Verbose output")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format='%(levelname)s: %(message)s'
    )
    
    # Load text
    if args.text:
        text = args.text
    else:
        try:
            text = args.file.read_text(encoding='utf-8-sig')
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            return sys.exit(1)  # Return the exit to ensure function stops
    
    # Load known words
    known_words = None
    if args.known:
        try:
            known_words = load_known_words(args.known)
        except Exception as e:
            print(f"Error loading known words: {e}", file=sys.stderr)
            return sys.exit(1)
    
    # Configure and run spell checker
    config = SpellCheckerConfig(
        language=args.language,
        known_words=known_words,
        use_languagetool=args.use_lt,
        lt_server=args.lt_server,
    )
    
    try:
        with SpellChecker(config) as sc:
            errors = sc.check_spelling(text)
            
        if args.json:
            import json
            print(json.dumps({
                "errors": errors,
                "count": len(errors),
                "text_length": len(text),
            }, indent=2))
        else:
            if errors:
                print(f"❌ Found {len(errors)} problem(s):")
                for error in errors:
                    print(f"  • {error}")
            else:
                print("✅ No spelling issues detected.")
                
        sys.exit(1 if errors else 0)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
