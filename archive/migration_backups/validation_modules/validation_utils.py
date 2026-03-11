"""
Validation Utilities

Common utilities and debugging functions extracted from src.validators.filename_checker.py
"""

import threading
from functools import lru_cache
from typing import Optional

# Global debug state
_DEBUG_ENABLED = False

# Thread-local storage
_thread_local = threading.local()


def enable_debug():
    """Enable comprehensive debugging output"""
    global _DEBUG_ENABLED
    _DEBUG_ENABLED = True
    print("🔍 DEBUG: Comprehensive debugging ENABLED")


def disable_debug():
    """Disable debugging output"""
    global _DEBUG_ENABLED
    _DEBUG_ENABLED = False


def debug_print(*args, **kwargs):
    """Print debug message only if debugging is enabled"""
    if _DEBUG_ENABLED:
        print("🔍 DEBUG:", *args, **kwargs)


def is_debug_enabled() -> bool:
    """Check if debugging is enabled"""
    return _DEBUG_ENABLED


# Language detection support
try:
    from langdetect import DetectorFactory
    LANGDETECT_AVAILABLE = True
    debug_print("✅ Language detection available")
except ImportError:
    LANGDETECT_AVAILABLE = False
    debug_print("⚠️ Language detection not available")


def _ensure_detector_seed():
    """Ensure language detector is seeded for consistent results"""
    if LANGDETECT_AVAILABLE and not hasattr(_thread_local, "seeded"):
        DetectorFactory.seed = 0
        _thread_local.seeded = True


@lru_cache(maxsize=1_000)
def get_language(text: str) -> str:
    """Enhanced language detection for academic/mathematical texts"""
    if not LANGDETECT_AVAILABLE:
        return "en"  # Default to English
        
    _ensure_detector_seed()
    text_lower = text.lower()

    debug_print(f"Detecting language for: '{text}'")

    # French indicators
    french_indicators = {
        "français", "française", "initiation", "théorie", "algèbre",
        "géométrie", "analyse", "probabilités", "topologie"
    }
    
    # German indicators  
    german_indicators = {
        "mathematik", "algebra", "geometrie", "analysis", "wahrscheinlichkeit",
        "topologie", "funktionen", "einführung", "grundlagen"
    }
    
    # Spanish indicators
    spanish_indicators = {
        "matemáticas", "álgebra", "geometría", "análisis", "probabilidad",
        "topología", "funciones", "introducción"
    }

    # Quick language detection based on indicators
    if any(indicator in text_lower for indicator in french_indicators):
        debug_print("Language detected as French (keywords)")
        return "fr"
    elif any(indicator in text_lower for indicator in german_indicators):
        debug_print("Language detected as German (keywords)")
        return "de"
    elif any(indicator in text_lower for indicator in spanish_indicators):
        debug_print("Language detected as Spanish (keywords)")
        return "es"

    # Fallback to langdetect library
    try:
        from langdetect import detect, LangDetectException
        detected = detect(text)
        debug_print(f"Language detected as: {detected}")
        return detected
    except (LangDetectException, ImportError):
        debug_print("Language detection failed, defaulting to English")
        return "en"


# Mathematician name validator integration
try:
    from src.validators.mathematician_name_validator import (
        MathematicianNameValidator,
        get_global_validator,
    )
    MATHEMATICIAN_VALIDATOR_AVAILABLE = True
    debug_print("✅ Mathematician name validator available for enhanced name checking")
except (ImportError, ModuleNotFoundError):
    MATHEMATICIAN_VALIDATOR_AVAILABLE = False
    debug_print("⚠️ Mathematician name validator not available")


def get_mathematician_validator() -> Optional[object]:
    """Get mathematician name validator if available"""
    if MATHEMATICIAN_VALIDATOR_AVAILABLE:
        try:
            return get_global_validator()
        except Exception:
            return None
    return None


# Timeout decorator support
import signal
from contextlib import contextmanager
from typing import Generator


@contextmanager
def timeout(seconds: int) -> Generator[None, None, None]:
    """Context manager for timeout protection"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Set up signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # Restore old handler and cancel alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


# Common validation patterns
import re

# Mathematical patterns
MATH_GREEK_PATTERN = re.compile(r'[αβγδεζηθικλμνξοπρστυφχψω]')
SUPERSCRIPT_PATTERN = re.compile(r'[⁰¹²³⁴⁵⁶⁷⁸⁹]')
SUBSCRIPT_PATTERN = re.compile(r'[₀₁₂₃₄₅₆₇₈₉]')

def has_mathematical_greek(text: str) -> bool:
    """Check if text contains mathematical Greek letters"""
    return bool(MATH_GREEK_PATTERN.search(text))


def has_superscripts(text: str) -> bool:
    """Check if text contains superscript characters"""
    return bool(SUPERSCRIPT_PATTERN.search(text))


def has_subscripts(text: str) -> bool:
    """Check if text contains subscript characters"""
    return bool(SUBSCRIPT_PATTERN.search(text))