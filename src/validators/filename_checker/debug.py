"""
Debug utilities for filename validation.

This module provides debug functionality for the filename validation system.
"""

from typing import Any

# Global debug state
_DEBUG_ENABLED = False


def enable_debug():
    """Enable comprehensive debugging output."""
    global _DEBUG_ENABLED
    _DEBUG_ENABLED = True
    print("🔍 DEBUG: Comprehensive debugging ENABLED")


def disable_debug():
    """Disable debugging output."""
    global _DEBUG_ENABLED
    _DEBUG_ENABLED = False


def debug_print(*args, **kwargs):
    """Print debug message only if debugging is enabled."""
    if _DEBUG_ENABLED:
        print("🔍 DEBUG:", *args, **kwargs)


def debug_unicode_info(text: str) -> None:
    """Print detailed Unicode information about text."""
    if not _DEBUG_ENABLED:
        return
    
    print("🔍 DEBUG: Unicode analysis for:", repr(text))
    for i, char in enumerate(text):
        import unicodedata
        print(f"  [{i}] {repr(char)} - {unicodedata.name(char, 'UNKNOWN')} - Category: {unicodedata.category(char)}")


def debug_tokenization(tokens: list) -> None:
    """Print detailed tokenization information."""
    if not _DEBUG_ENABLED:
        return
    
    print("🔍 DEBUG: Tokenization results:")
    for i, token in enumerate(tokens):
        print(f"  [{i}] {token.kind}: '{token.value}' ({token.start}-{token.end})")


def debug_validation_step(step_name: str, input_data: Any, result: Any) -> None:
    """Print validation step information."""
    if not _DEBUG_ENABLED:
        return
    
    print(f"🔍 DEBUG: {step_name}")
    print(f"  Input: {repr(input_data)}")
    print(f"  Result: {repr(result)}")


def is_debug_enabled() -> bool:
    """Check if debugging is enabled."""
    return _DEBUG_ENABLED


def debug_fixer_chain(text: str, fixers: list, regions: list, spans: list) -> str:
    """Debug helper for fixer chain processing - RESTORED from original"""
    result = text
    for fixer in fixers:
        old_result = result
        try:
            result = fixer(result, regions, None, spans)
            if result != old_result:
                debug_print(f"Fixer {fixer.__name__}: '{old_result}' -> '{result}'")
        except Exception as e:
            debug_print(f"Fixer {fixer.__name__} failed: {e}")
    return result