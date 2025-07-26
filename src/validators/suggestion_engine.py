"""
Suggestion Engine Module

Auto-fix suggestions and correction generation
extracted from src.validators.filename_checker.py
"""

import re
from typing import List, Set, Optional, Dict, Any
from .author_parser import fix_author_block
from .title_normalizer import fix_title_capitalization
from .unicode_handler import nfc


class SuggestionEngine:
    """Generate intelligent suggestions for filename fixes"""
    
    def __init__(self):
        self.max_suggestions = 5
        
    def generate_suggestions(
        self, 
        filename: str,
        errors: List[str],
        author_part: Optional[str] = None,
        title_part: Optional[str] = None,
        known_words: Set[str] = None,
        exceptions: Set[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Generate fix suggestions based on errors"""
        suggestions = []
        
        # Process each error and generate suggestions
        for error in errors:
            if "Author formatting" in error:
                suggestion = self._suggest_author_fix(error, author_part)
                if suggestion:
                    suggestions.append(suggestion)
                    
            elif "Capitalization" in error:
                suggestion = self._suggest_capitalization_fix(
                    error, title_part, known_words, exceptions
                )
                if suggestion:
                    suggestions.append(suggestion)
                    
            elif "NFC" in error or "Unicode" in error:
                suggestion = self._suggest_unicode_fix(error, filename)
                if suggestion:
                    suggestions.append(suggestion)
                    
            elif "dash" in error.lower() or "hyphen" in error:
                suggestion = self._suggest_dash_fix(error, filename)
                if suggestion:
                    suggestions.append(suggestion)
                    
            elif "parenthes" in error or "bracket" in error:
                suggestion = self._suggest_bracket_fix(error, filename)
                if suggestion:
                    suggestions.append(suggestion)
        
        # Limit suggestions
        return suggestions[:self.max_suggestions]
    
    def _suggest_author_fix(self, error: str, author_part: str) -> Optional[Dict[str, Any]]:
        """Suggest author formatting fixes"""
        if not author_part:
            return None
            
        # Extract the suggested fix from error message
        match = re.search(r"'([^']+)' → '([^']+)'", error)
        if match:
            original, suggested = match.groups()
            return {
                'type': 'author_fix',
                'description': "Fix author formatting",
                'original': original,
                'suggested': suggested,
                'confidence': 0.95
            }
        
        # Fallback: generate fix
        fixed = fix_author_block(author_part)
        if fixed != author_part:
            return {
                'type': 'author_fix',
                'description': "Fix author formatting",
                'original': author_part,
                'suggested': fixed,
                'confidence': 0.9
            }
        
        return None
    
    def _suggest_capitalization_fix(
        self, 
        error: str, 
        title_part: str,
        known_words: Set[str],
        exceptions: Set[str]
    ) -> Optional[Dict[str, Any]]:
        """Suggest title capitalization fixes"""
        if not title_part:
            return None
        
        # Extract specific word if mentioned
        match = re.search(r"Capitalization: (\w+)", error)
        if match:
            word = match.group(1)
            # Try to determine correct capitalization
            if word.lower() in known_words or word.lower() in exceptions:
                # Find the correct form
                for known in known_words | exceptions:
                    if known.lower() == word.lower():
                        return {
                            'type': 'capitalization_fix',
                            'description': f"Fix capitalization of '{word}'",
                            'original': word,
                            'suggested': known,
                            'confidence': 0.95
                        }
        
        # Fallback: fix entire title
        fixed = fix_title_capitalization(title_part, known_words, exceptions)
        if fixed != title_part:
            return {
                'type': 'title_capitalization_fix',
                'description': "Fix title capitalization",
                'original': title_part,
                'suggested': fixed,
                'confidence': 0.85
            }
        
        return None
    
    def _suggest_unicode_fix(self, error: str, filename: str) -> Optional[Dict[str, Any]]:
        """Suggest Unicode normalization fixes"""
        if "NFC" in error:
            normalized = nfc(filename)
            if normalized != filename:
                return {
                    'type': 'unicode_normalization',
                    'description': "Normalize to NFC Unicode form",
                    'original': filename,
                    'suggested': normalized,
                    'confidence': 1.0
                }
        
        if "dangerous Unicode" in error:
            # Extract characters mentioned
            match = re.search(r"characters: (.+)", error)
            if match:
                chars = match.group(1)
                return {
                    'type': 'unicode_security',
                    'description': f"Remove dangerous Unicode characters: {chars}",
                    'original': filename,
                    'suggested': None,  # Would need actual removal logic
                    'confidence': 1.0
                }
        
        return None
    
    def _suggest_dash_fix(self, error: str, text: str) -> Optional[Dict[str, Any]]:
        """Suggest dash-related fixes"""
        if "space-hyphen-space" in error:
            # Replace " - " with proper em dash
            fixed = text.replace(" - ", " — ")
            return {
                'type': 'dash_fix',
                'description': "Replace space-hyphen-space with em dash",
                'original': text,
                'suggested': fixed,
                'confidence': 0.9
            }
        
        if "multiple" in error and "hyphen" in error:
            # Replace multiple hyphens with single
            fixed = re.sub(r'-{2,}', '-', text)
            return {
                'type': 'dash_fix',
                'description': "Fix multiple consecutive hyphens",
                'original': text,
                'suggested': fixed,
                'confidence': 0.85
            }
        
        return None
    
    def _suggest_bracket_fix(self, error: str, text: str) -> Optional[Dict[str, Any]]:
        """Suggest bracket/parenthesis fixes"""
        # This would require more complex logic to fix mismatched brackets
        # For now, just identify the issue
        if "Unmatched" in error or "Unclosed" in error:
            return {
                'type': 'bracket_fix',
                'description': error,
                'original': text,
                'suggested': None,  # Manual fix required
                'confidence': 0.5
            }
        
        return None
    
    def apply_suggestion(self, filename: str, suggestion: Dict[str, Any]) -> str:
        """Apply a single suggestion to the filename"""
        if suggestion['suggested'] is None:
            # Can't auto-apply
            return filename
        
        if suggestion['type'] in ['author_fix', 'title_capitalization_fix']:
            # Replace the specific part
            return filename.replace(suggestion['original'], suggestion['suggested'])
        
        if suggestion['type'] == 'unicode_normalization':
            return suggestion['suggested']
        
        if suggestion['type'] == 'dash_fix':
            return suggestion['suggested']
        
        return filename
    
    def apply_all_suggestions(
        self, 
        filename: str, 
        suggestions: List[Dict[str, Any]]
    ) -> str:
        """Apply all suggestions to generate fixed filename"""
        fixed = filename
        
        # Apply suggestions in order of confidence
        sorted_suggestions = sorted(
            suggestions, 
            key=lambda s: s.get('confidence', 0), 
            reverse=True
        )
        
        for suggestion in sorted_suggestions:
            if suggestion.get('suggested') is not None:
                fixed = self.apply_suggestion(fixed, suggestion)
        
        return fixed
    
    def get_quick_fixes(self, filename: str, errors: List[str]) -> List[str]:
        """Get simple text-based fix suggestions (backward compatibility)"""
        quick_fixes = []
        
        for error in errors:
            if "→" in error:
                # Extract the suggestion from arrow notation
                quick_fixes.append(error)
            elif "should be" in error:
                # Extract from "X should be Y" format
                quick_fixes.append(error)
            else:
                # Generic suggestion
                if "NFC" in error:
                    quick_fixes.append("Normalize Unicode to NFC form")
                elif "Author" in error:
                    quick_fixes.append("Fix author formatting")
                elif "Capitalization" in error:
                    quick_fixes.append("Fix title capitalization")
                elif "dash" in error.lower():
                    quick_fixes.append("Fix dash formatting")
        
        return quick_fixes[:self.max_suggestions]


# Module-level functions for backward compatibility
_default_engine = SuggestionEngine()

def generate_suggestions(
    filename: str,
    errors: List[str],
    **kwargs
) -> List[Dict[str, Any]]:
    """Generate suggestions for fixing errors"""
    return _default_engine.generate_suggestions(filename, errors, **kwargs)


def get_quick_fixes(filename: str, errors: List[str]) -> List[str]:
    """Get simple text suggestions"""
    return _default_engine.get_quick_fixes(filename, errors)


def apply_suggestion(filename: str, suggestion: Dict[str, Any]) -> str:
    """Apply a single suggestion"""
    return _default_engine.apply_suggestion(filename, suggestion)


def apply_all_suggestions(
    filename: str, 
    suggestions: List[Dict[str, Any]]
) -> str:
    """Apply all suggestions"""
    return _default_engine.apply_all_suggestions(filename, suggestions)