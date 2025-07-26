"""
Author name validation and normalization

This module handles validation and normalization of author names in
academic citations, including handling of initials, suffixes, and particles.
"""
import re
from typing import List, Optional, Set, Tuple
import logging

from .exceptions import AuthorValidationError
from core.models import ValidationResult, ValidationIssue, ValidationSeverity, Author

logger = logging.getLogger(__name__)


class AuthorValidator:
    """Validate and normalize author names"""
    
    # Name particles (von, van, de, etc.)
    NAME_PARTICLES = {
        'von', 'van', 'de', 'der', 'den', 'ter', 'te', 'la', 'le', 
        'du', 'des', 'della', 'degli', 'di', 'da', 'del', 'do', 'dos'
    }
    
    # Common suffixes
    SUFFIXES = {'Jr.', 'Sr.', 'II', 'III', 'IV', 'V', 'Ph.D.', 'M.D.'}
    
    # Author separator pattern
    AUTHOR_SEPARATOR = re.compile(r',(?:\s*(?:and|&)\s*)|;\s*|\s+and\s+|\s*&\s*')
    
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self._known_authors = set()  # Can be loaded from config
    
    def validate_author_string(self, author_string: str) -> ValidationResult:
        """
        Validate a string containing one or more authors.
        
        Args:
            author_string: String with author names
            
        Returns:
            ValidationResult with any issues found
        """
        issues = []
        
        # Split into individual authors
        authors = self._split_authors(author_string)
        
        if not authors:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category='author',
                message='No authors found',
                field='authors',
                current_value=author_string
            ))
            return ValidationResult(is_valid=False, issues=issues)
        
        # Validate each author
        for i, author in enumerate(authors):
            author_issues = self._validate_single_author(author, i)
            issues.extend(author_issues)
        
        # Check for duplicates
        if len(authors) != len(set(authors)):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category='author',
                message='Duplicate authors detected',
                field='authors',
                current_value=author_string
            ))
        
        return ValidationResult(
            is_valid=len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0,
            issues=issues
        )
    
    def _split_authors(self, author_string: str) -> List[str]:
        """Split author string into individual authors"""
        # Handle various separators
        authors = self.AUTHOR_SEPARATOR.split(author_string)
        return [a.strip() for a in authors if a.strip()]
    
    def _validate_single_author(self, author: str, index: int) -> List[ValidationIssue]:
        """Validate a single author name"""
        issues = []
        
        # Check basic format
        if not author:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category='author',
                message=f'Empty author at position {index + 1}',
                field=f'author_{index}',
                current_value=author
            ))
            return issues
        
        # Parse author components
        parsed = self._parse_author(author)
        
        # Validate components
        if not parsed.family_name:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category='author',
                message=f'Missing family name for author {index + 1}',
                field=f'author_{index}',
                current_value=author
            ))
        
        # Check initials format
        if parsed.initials:
            if not re.match(r'^[A-Z](\.[A-Z])*\.$', parsed.initials):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category='author',
                    message=f'Improper initial format for author {index + 1}',
                    field=f'author_{index}_initials',
                    current_value=parsed.initials,
                    suggested_value=self._fix_initials(parsed.initials),
                    fix_available=True
                ))
        
        return issues
    
    def _parse_author(self, author: str) -> Author:
        """Parse author string into components"""
        # This is a simplified version - the full implementation would be more complex
        parts = author.split(',')
        
        if len(parts) == 2:
            # "Last, First" format
            family_name = parts[0].strip()
            given_part = parts[1].strip()
        else:
            # "First Last" format
            words = author.split()
            if not words:
                return Author()
            
            # Simple heuristic: last word is family name
            family_name = words[-1]
            given_part = ' '.join(words[:-1])
        
        # Extract initials
        initials = ''
        given_words = given_part.split()
        for word in given_words:
            if re.match(r'^[A-Z]\.$', word):
                initials += word
        
        return Author(
            full_name=author,
            family_name=family_name,
            given_name=given_part,
            initials=initials
        )
    
    def _fix_initials(self, initials: str) -> str:
        """Fix initial formatting"""
        # Remove spaces, ensure periods after each letter
        cleaned = re.sub(r'[^A-Z]', '', initials.upper())
        return '.'.join(cleaned) + '.' if cleaned else ''
    
    def fix_author_string(self, author_string: str) -> str:
        """Apply automatic fixes to author string"""
        authors = self._split_authors(author_string)
        fixed_authors = []
        
        for author in authors:
            parsed = self._parse_author(author)
            
            # Apply fixes
            if parsed.initials:
                parsed.initials = self._fix_initials(parsed.initials)
            
            # Reconstruct in standard format
            if parsed.given_name and parsed.family_name:
                fixed = f"{parsed.family_name}, {parsed.given_name}"
            else:
                fixed = author  # Keep original if parsing failed
            
            fixed_authors.append(fixed)
        
        # Join with standard separator
        return ', '.join(fixed_authors)
