"""
Batch processing functionality for filename validation.

This module provides batch processing capabilities for validating multiple
filenames at once.
"""

from typing import Iterable, Dict, Any, Set, List

from .core import check_filename

try:
    from core.text_processing.my_spellchecker import SpellChecker
except ImportError:
    class MockSpellChecker:
        def __init__(self, *args, **kwargs):
            pass
    SpellChecker = MockSpellChecker


def batch_check_filenames(
    file_infos: Iterable[Dict[str, str]],
    known_words: Set[str] = None,
    whitelist_pairs: List[str] = None,
    exceptions: Set[str] = None,
    compound_terms: Set[str] = None,
    **kwargs,
) -> List[Dict[str, Any]]:
    """
    Process all files and return results for files with issues.
    This is by design - it only returns files that have errors or suggestions.
    
    Args:
        file_infos: Iterable of file info dictionaries
        known_words: Set of known valid words
        whitelist_pairs: List of whitelisted word pairs
        exceptions: Set of exception words
        compound_terms: Set of compound terms
        **kwargs: Additional validation options
    
    Returns:
        List of dictionaries containing validation results for problematic files
    """
    # Use empty sets/lists if None provided
    if known_words is None:
        known_words = set()
    if whitelist_pairs is None:
        whitelist_pairs = []
    if exceptions is None:
        exceptions = set()
    if compound_terms is None:
        compound_terms = set()
    
    results = []
    for info in file_infos:
        # Ensure we have the expected keys
        filename = info.get("filename") or info.get("name", "UNKNOWN")

        # Pass all parameters to check_filename for consistent validation
        res = check_filename(
            filename,
            known_words=known_words,
            whitelist_pairs=whitelist_pairs, 
            exceptions=exceptions,
            compound_terms=compound_terms,
            **kwargs
        )
        
        if res.messages or res.errors or res.warnings:
            # Determine if this is an author fix by checking if we have a corrected filename
            # and if the fix involved author formatting
            fixed_author = None
            if res.corrected_filename and res.corrected_filename != res.original_filename:
                # Extract author parts from original and fixed filenames
                original_parts = res.original_filename.split(" - ", 1)
                fixed_parts = res.corrected_filename.split(" - ", 1)
                
                if len(original_parts) == 2 and len(fixed_parts) == 2:
                    original_author = original_parts[0]
                    fixed_author_part = fixed_parts[0]
                    
                    # Check if the author part actually changed
                    if original_author != fixed_author_part:
                        fixed_author = fixed_author_part
            
            results.append(
                {
                    "filename": res.original_filename,
                    "messages": [{"type": m.type, "message": m.message} for m in res.messages],
                    "errors": res.errors,
                    "suggestions": res.suggestions,
                    "fixed_filename": res.corrected_filename,
                    "fixed_author": fixed_author,
                    "path": info.get("path", ""),
                    "folder": info.get("folder", ""),
                }
            )
    return results


def batch_check_filenames_new(
    file_infos: Iterable[Dict[str, str]],
    checker: "SpellChecker" = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    New interface for batch_check_filenames that accepts a SpellChecker object.
    
    Args:
        file_infos: Iterable of file info dictionaries
        checker: SpellChecker object containing validation data
        **kwargs: Additional validation options
    
    Returns:
        List of dictionaries containing validation results
    """
    if checker is None:
        # Use empty sets if no checker provided
        return batch_check_filenames(file_infos, set(), [], set(), set(), **kwargs)
    
    # Extract data from the SpellChecker object
    # Handle both old and new SpellChecker interfaces
    if hasattr(checker, 'config'):
        # New interface with config object
        config = checker.config
        known_words = getattr(config, 'known_words', set())
        multiword_surnames = getattr(config, 'multiword_surnames', set())
        exceptions = getattr(config, 'exceptions', set())
        compound_terms = getattr(config, 'compound_terms', set())
    else:
        # Old interface with direct attributes
        known_words = getattr(checker, 'known_words', set())
        multiword_surnames = getattr(checker, 'multiword_surnames', set())
        exceptions = getattr(checker, 'exceptions', set())
        compound_terms = getattr(checker, 'compound_terms', set())
    
    whitelist_pairs = list(multiword_surnames)  # Convert to list
    
    # Merge compound_terms into known_words as expected by check_filename
    all_known_words = known_words | compound_terms
    
    # Filter out parameters that are not recognized by check_filename
    # These are interface parameters that should not be passed to the underlying function
    filtered_kwargs = {}
    unrecognized_params = {
        'check_unicode_normalization', 'check_author_format', 'verbose'
    }
    
    for key, value in kwargs.items():
        if key not in unrecognized_params:
            filtered_kwargs[key] = value
    
    return batch_check_filenames(
        file_infos, 
        all_known_words,
        whitelist_pairs,
        exceptions,
        compound_terms,
        **filtered_kwargs
    )


def _batch_check_worker(args):
    """Worker function for batch processing - RESTORED from original"""
    file_info, known_words, whitelist_pairs, exceptions, compound_terms, kwargs = args
    return batch_check_filenames([file_info], known_words, whitelist_pairs, exceptions, compound_terms, **kwargs)