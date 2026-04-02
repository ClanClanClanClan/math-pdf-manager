"""
Filename Validator Module

Core filename validation logic extracted from validators.filename_checker.py
"""

import time
from typing import Set, List, Tuple, Any
from .validation_result import FilenameCheckResult
from .author_parser import (
    fix_author_block, 
    author_string_is_normalized,
    parse_authors_and_title
)
from .title_normalizer import (
    check_title_capitalization,
    check_title_dashes
)
from .unicode_handler import (
    nfc,
    is_nfc,
    sanitize_unicode_security
)
from .pattern_matcher import (
    PatternMatcher,
    find_bad_dash_patterns
)


class FilenameValidator:
    """Core filename validation functionality"""
    
    def __init__(self):
        self.pattern_matcher = PatternMatcher()
        self.max_filename_length = 5000  # DoS protection
        
    def check_filename(
        self,
        filename: str,
        known_words: Set[str],
        whitelist_pairs: List[str],
        exceptions: Set[str],
        compound_terms: Set[str],
        *,
        spellchecker: Any = None,
        language_tool: Any = None,
        sentence_case: bool = True,
        lowercase_exceptions: Set[str] = None,
        capitalization_whitelist: Set[str] = None,
        debug: bool = False,
        multiword_surnames: Set[str] = None,
        name_dash_whitelist: Set[str] = None,
        auto_fix_nfc: bool = False,
        auto_fix_authors: bool = False,
    ) -> FilenameCheckResult:
        """Main filename validation function"""
        
        # Performance protection
        if len(filename) > self.max_filename_length:
            result = FilenameCheckResult(filename=filename, messages=[])
            result.add_error("MAX_LENGTH", "Filename too long (max 5000 characters)")
            return result
        
        time.time()
        
        # Initialize result
        result = FilenameCheckResult(filename=filename, messages=[], fixed_filename=filename)
        
        # Unicode validation
        unicode_errors = self._check_unicode(filename)
        for error in unicode_errors:
            result.add_error("UNICODE", error)
        
        # Parse authors and title
        author_part, title_part = parse_authors_and_title(filename)
        if not author_part or not title_part:
            result.add_error("FORMAT", "Invalid filename format (expected 'Authors - Title.pdf')")
            return result
        
        # Check authors
        author_errors, fixed_authors = self._check_authors(
            author_part, 
            auto_fix=auto_fix_authors,
            name_dash_whitelist=name_dash_whitelist
        )
        for error in author_errors:
            result.add_warning("AUTHOR", error)
        
        # Check title
        title_errors = self._check_title(
            title_part,
            known_words=known_words,
            exceptions=exceptions,
            capitalization_whitelist=capitalization_whitelist,
            sentence_case=sentence_case
        )
        for error in title_errors:
            result.add_warning("TITLE", error)
        
        # Apply fixes if requested
        if auto_fix_nfc or auto_fix_authors:
            fixed_filename = self._apply_fixes(
                filename, 
                fixed_authors if auto_fix_authors else author_part,
                title_part,
                auto_fix_nfc=auto_fix_nfc
            )
            result.fixed_filename = fixed_filename
        
        # Store fixed author for compatibility
        if auto_fix_authors:
            result.fixed_author = fixed_authors
        
        return result
    
    def _check_unicode(self, filename: str) -> List[str]:
        """Check for Unicode issues"""
        errors = []
        
        # Check NFC normalization
        if not is_nfc(filename):
            errors.append("ERROR: Filename is not NFC normalized")
        
        # Security check
        sanitized, removed_chars, mixed_scripts = sanitize_unicode_security(filename)
        if removed_chars:
            errors.append(f"ERROR: Contains dangerous Unicode characters: {', '.join(removed_chars)}")
        if len(mixed_scripts) > 1:
            errors.append(f"WARNING: Mixed scripts detected: {', '.join(mixed_scripts)}")
        
        return errors
    
    def _check_authors(self, author_part: str, auto_fix: bool = False, 
                      name_dash_whitelist: Set[str] = None) -> Tuple[List[str], str]:
        """Check author formatting"""
        errors = []
        
        # Normalize authors
        is_normalized, normalized = author_string_is_normalized(author_part)
        if not is_normalized:
            errors.append(f"Author formatting: '{author_part}' → '{normalized}'")
        
        # Check for multiple dashes between authors
        dash_patterns = find_bad_dash_patterns(author_part)
        for start, end, pattern_type in dash_patterns:
            if pattern_type == 'multiple-hyphens':
                errors.append(f"Multiple hyphens in author names at position {start}")
        
        # Apply fixes if requested
        fixed_authors = fix_author_block(author_part) if auto_fix else author_part
        
        return errors, fixed_authors
    
    def _check_title(self, title: str, known_words: Set[str], exceptions: Set[str],
                    capitalization_whitelist: Set[str] = None, 
                    sentence_case: bool = True) -> List[str]:
        """Check title formatting"""
        errors = []
        
        # Check capitalization
        cap_errors = check_title_capitalization(
            title, known_words, exceptions, 
            capitalization_whitelist=capitalization_whitelist
        )
        errors.extend(cap_errors)
        
        # Check dashes
        dash_errors = check_title_dashes(
            title, known_words, exceptions,
            capitalization_whitelist=capitalization_whitelist
        )
        errors.extend(dash_errors)
        
        # Check parentheses balance
        paren_errors = self._check_parentheses_balance(title)
        errors.extend(paren_errors)
        
        return errors
    
    def _check_parentheses_balance(self, text: str) -> List[str]:
        """Check for balanced parentheses and brackets"""
        errors = []
        
        # Simple stack-based checking
        stack = []
        pairs = {'(': ')', '[': ']', '{': '}'}
        
        for i, char in enumerate(text):
            if char in pairs:
                stack.append((char, i))
            elif char in pairs.values():
                if not stack:
                    errors.append(f"Unmatched closing '{char}' at position {i}")
                else:
                    opening, _ = stack.pop()
                    if pairs[opening] != char:
                        errors.append(f"Mismatched brackets: '{opening}' and '{char}'")
        
        # Check for unclosed brackets
        for char, pos in stack:
            errors.append(f"Unclosed '{char}' at position {pos}")
        
        return errors
    
    def _apply_fixes(self, filename: str, fixed_authors: str, title: str,
                    auto_fix_nfc: bool = False) -> str:
        """Apply automatic fixes to filename"""
        # Apply NFC normalization if requested
        if auto_fix_nfc:
            filename = nfc(filename)
            fixed_authors = nfc(fixed_authors)
            title = nfc(title)
        
        # Reconstruct filename
        extension = '.pdf' if filename.endswith('.pdf') else ''
        fixed_filename = f"{fixed_authors} - {title}{extension}"
        
        return fixed_filename
    
    def _generate_suggestions(self, filename: str, author_part: str, 
                            title_part: str, errors: List[str]) -> List[str]:
        """Generate fix suggestions based on errors"""
        suggestions = []
        
        # Author suggestions
        if any("Author formatting" in e for e in errors):
            fixed_authors = fix_author_block(author_part)
            suggestions.append(f"Fix authors: {author_part} → {fixed_authors}")
        
        # Title suggestions
        if any("Capitalization" in e for e in errors):
            # Get known words from somewhere (would need to be passed in)
            suggestions.append("Fix title capitalization")
        
        # Unicode suggestions
        if any("NFC" in e for e in errors):
            suggestions.append("Normalize Unicode to NFC form")
        
        return suggestions


# Module-level functions for backward compatibility
_default_validator = FilenameValidator()

def check_filename(
    filename: str,
    known_words: set[str],
    whitelist_pairs: list[str],
    exceptions: set[str],
    compound_terms: set[str],
    **kwargs
) -> FilenameCheckResult:
    """Check filename - main entry point"""
    return _default_validator.check_filename(
        filename,
        known_words,
        whitelist_pairs,
        exceptions,
        compound_terms,
        **kwargs
    )


def batch_check_filenames(
    filenames: List[str],
    known_words: Set[str],
    whitelist_pairs: List[str],
    exceptions: Set[str],
    compound_terms: Set[str],
    **kwargs
) -> List[FilenameCheckResult]:
    """Check multiple filenames"""
    results = []
    for filename in filenames:
        result = check_filename(
            filename,
            known_words,
            whitelist_pairs,
            exceptions,
            compound_terms,
            **kwargs
        )
        results.append(result)
    return results