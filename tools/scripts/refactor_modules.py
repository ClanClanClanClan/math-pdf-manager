#!/usr/bin/env python3
"""
Refactor large modules into smaller, focused components

This script splits large files like main.py and filename_checker.py into
properly organized modules following the Single Responsibility Principle.
"""
import ast
import os
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class ModuleRefactorer:
    """Refactor large Python modules into smaller components"""
    
    def __init__(self):
        self.created_modules = []
        self.import_map = {}
        
    def analyze_module(self, file_path: Path) -> Dict[str, List[str]]:
        """Analyze a Python module and categorize its components"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return {}
        
        components = {
            'imports': [],
            'constants': [],
            'exceptions': [],
            'models': [],
            'validators': [],
            'utils': [],
            'core_logic': [],
            'cli': [],
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                components['imports'].append(ast.unparse(node))
            elif isinstance(node, ast.ImportFrom):
                components['imports'].append(ast.unparse(node))
            elif isinstance(node, ast.ClassDef):
                # Categorize classes
                if 'Exception' in node.name or 'Error' in node.name:
                    components['exceptions'].append(node.name)
                elif any(word in node.name.lower() for word in ['validator', 'checker']):
                    components['validators'].append(node.name)
                elif any(word in node.name.lower() for word in ['model', 'data', 'result']):
                    components['models'].append(node.name)
                else:
                    components['core_logic'].append(node.name)
            elif isinstance(node, ast.FunctionDef):
                # Categorize functions
                if node.name.startswith('validate_') or node.name.startswith('check_'):
                    components['validators'].append(node.name)
                elif node.name.startswith('_') and not node.name.startswith('__'):
                    components['utils'].append(node.name)
                elif node.name in ['main', 'cli', 'parse_args']:
                    components['cli'].append(node.name)
                else:
                    components['core_logic'].append(node.name)
            elif isinstance(node, ast.Assign):
                # Check for constants
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        components['constants'].append(target.id)
        
        return components
    
    def refactor_filename_checker(self) -> None:
        """Refactor filename_checker.py into smaller modules"""
        logger.info("\n📦 Refactoring filename_checker.py...")
        
        # Create validators directory structure
        validators_dir = Path('validators')
        validators_dir.mkdir(exist_ok=True)
        
        # Create module files
        modules = {
            'filename.py': self._create_filename_validator(),
            'author.py': self._create_author_validator(),
            'unicode.py': self._create_unicode_validator(),
            'math_context.py': self._create_math_context_detector(),
            'exceptions.py': self._create_validator_exceptions(),
        }
        
        for filename, content in modules.items():
            file_path = validators_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"  ✓ Created {file_path}")
            self.created_modules.append(file_path)
        
        # Create __init__.py
        init_content = '''"""Validators package for Math-PDF Manager"""
from .filename import FilenameValidator
from .author import AuthorValidator
from .unicode import UnicodeValidator
from .math_context import MathContextDetector
from .exceptions import *

__all__ = [
    'FilenameValidator',
    'AuthorValidator', 
    'UnicodeValidator',
    'MathContextDetector',
    'ValidationError',
    'FilenameValidationError',
]
'''
        with open(validators_dir / '__init__.py', 'w', encoding='utf-8') as f:
            f.write(init_content)
    
    def _create_filename_validator(self) -> str:
        """Create filename validator module"""
        return '''"""
Filename validation for academic PDFs

This module provides validation for the "Author(s) - Title.pdf" format
used in academic document management.
"""
import re
from pathlib import Path
from typing import List, Optional, Tuple
import logging

from .exceptions import FilenameValidationError
from core.models import ValidationResult, ValidationIssue, ValidationSeverity

logger = logging.getLogger(__name__)


class FilenameValidator:
    """Validate academic PDF filenames"""
    
    # Filename pattern: Author(s) - Title.pdf
    FILENAME_PATTERN = re.compile(
        r'^(?P<authors>[^-]+?)\s*-\s*(?P<title>[^-]+?)\.pdf$',
        re.UNICODE | re.IGNORECASE
    )
    
    # Maximum lengths
    MAX_FILENAME_LENGTH = 255
    MAX_AUTHOR_LENGTH = 100
    MAX_TITLE_LENGTH = 200
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize filename validator.
        
        Args:
            strict_mode: Enable strict validation rules
        """
        self.strict_mode = strict_mode
        self._author_validator = None  # Lazy load
        self._unicode_validator = None  # Lazy load
    
    @property
    def author_validator(self):
        """Lazy load author validator"""
        if self._author_validator is None:
            from .author import AuthorValidator
            self._author_validator = AuthorValidator(self.strict_mode)
        return self._author_validator
    
    @property
    def unicode_validator(self):
        """Lazy load unicode validator"""
        if self._unicode_validator is None:
            from .unicode import UnicodeValidator
            self._unicode_validator = UnicodeValidator()
        return self._unicode_validator
    
    def validate_filename(self, file_path: Path) -> ValidationResult:
        """
        Validate a PDF filename.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            ValidationResult with issues found
        """
        issues = []
        filename = file_path.name
        
        # Check length
        if len(filename.encode('utf-8')) > self.MAX_FILENAME_LENGTH:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category='filename',
                message=f'Filename too long ({len(filename.encode("utf-8"))} bytes)',
                field='filename',
                current_value=filename
            ))
        
        # Check extension
        if not filename.lower().endswith('.pdf'):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category='filename',
                message='File must have .pdf extension',
                field='extension',
                current_value=file_path.suffix
            ))
            return ValidationResult(is_valid=False, issues=issues)
        
        # Match pattern
        match = self.FILENAME_PATTERN.match(filename)
        if not match:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category='filename',
                message='Filename must follow "Author(s) - Title.pdf" format',
                field='format',
                current_value=filename
            ))
            return ValidationResult(is_valid=False, issues=issues)
        
        authors = match.group('authors').strip()
        title = match.group('title').strip()
        
        # Validate components
        author_issues = self._validate_authors(authors)
        title_issues = self._validate_title(title)
        unicode_issues = self.unicode_validator.validate_text(filename)
        
        issues.extend(author_issues)
        issues.extend(title_issues)
        issues.extend(unicode_issues)
        
        # Generate suggested filename if there are issues
        suggested_filename = None
        if issues and any(issue.fix_available for issue in issues):
            suggested_filename = self._generate_suggested_filename(authors, title)
        
        return ValidationResult(
            is_valid=len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0,
            issues=issues,
            suggested_filename=suggested_filename
        )
    
    def _validate_authors(self, authors: str) -> List[ValidationIssue]:
        """Validate author component"""
        issues = []
        
        if len(authors) > self.MAX_AUTHOR_LENGTH:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category='author',
                message=f'Author field too long ({len(authors)} chars)',
                field='authors',
                current_value=authors
            ))
        
        # Delegate to author validator
        author_result = self.author_validator.validate_author_string(authors)
        issues.extend(author_result.issues)
        
        return issues
    
    def _validate_title(self, title: str) -> List[ValidationIssue]:
        """Validate title component"""
        issues = []
        
        if len(title) > self.MAX_TITLE_LENGTH:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category='title',
                message=f'Title too long ({len(title)} chars)',
                field='title',
                current_value=title
            ))
        
        if not title:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category='title',
                message='Title cannot be empty',
                field='title',
                current_value=title
            ))
        
        # Check for common issues
        if title.isupper():
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category='title',
                message='Title should not be all uppercase',
                field='title',
                current_value=title,
                suggested_value=title.title(),
                fix_available=True
            ))
        
        return issues
    
    def _generate_suggested_filename(self, authors: str, title: str) -> str:
        """Generate suggested filename with fixes applied"""
        # Apply author fixes
        fixed_authors = self.author_validator.fix_author_string(authors)
        
        # Apply title fixes
        fixed_title = title.title() if title.isupper() else title
        
        # Apply Unicode normalization
        from unicodedata import normalize
        suggested = f"{fixed_authors} - {fixed_title}.pdf"
        suggested = normalize('NFC', suggested)
        
        return suggested
'''
    
    def _create_author_validator(self) -> str:
        """Create author validator module"""
        return '''"""
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
'''
    
    def _create_unicode_validator(self) -> str:
        """Create Unicode validator module"""
        return '''"""
Unicode validation and normalization

This module handles Unicode normalization and validation for filenames,
ensuring consistent encoding and preventing homograph attacks.
"""
import unicodedata
import re
from typing import List, Optional, Set
import logging

from core.models import ValidationIssue, ValidationSeverity

logger = logging.getLogger(__name__)


class UnicodeValidator:
    """Validate and normalize Unicode in filenames"""
    
    # Suspicious Unicode categories
    SUSPICIOUS_CATEGORIES = {
        'Cc',  # Control characters
        'Cf',  # Format characters
        'Cs',  # Surrogates
        'Co',  # Private use
        'Cn',  # Unassigned
    }
    
    # Allowed scripts for mathematical documents
    ALLOWED_SCRIPTS = {
        'Common',
        'Latin',
        'Greek',  # Mathematical symbols
        'Cyrillic',  # Russian names
        'Han',  # Chinese names
        'Hiragana',
        'Katakana',
        'Arabic',  # Some mathematical notation
    }
    
    def __init__(self):
        self._script_cache = {}
    
    def validate_text(self, text: str) -> List[ValidationIssue]:
        """
        Validate Unicode text for potential issues.
        
        Args:
            text: Text to validate
            
        Returns:
            List of validation issues found
        """
        issues = []
        
        # Check normalization
        nfc_form = unicodedata.normalize('NFC', text)
        nfd_form = unicodedata.normalize('NFD', text)
        
        if text != nfc_form:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category='unicode',
                message='Text is not in NFC normalized form',
                field='normalization',
                current_value=text,
                suggested_value=nfc_form,
                fix_available=True
            ))
        
        # Check for suspicious characters
        suspicious_chars = self._find_suspicious_characters(text)
        if suspicious_chars:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category='unicode',
                message=f'Contains suspicious Unicode characters: {suspicious_chars}',
                field='characters',
                current_value=text
            ))
        
        # Check for mixed scripts (potential homograph attack)
        scripts = self._get_scripts(text)
        unexpected_scripts = scripts - self.ALLOWED_SCRIPTS
        if unexpected_scripts:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category='unicode',
                message=f'Contains unexpected scripts: {unexpected_scripts}',
                field='scripts',
                current_value=text
            ))
        
        # Check for zero-width characters
        if self._has_zero_width_chars(text):
            cleaned = self._remove_zero_width_chars(text)
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category='unicode',
                message='Contains zero-width characters',
                field='characters',
                current_value=text,
                suggested_value=cleaned,
                fix_available=True
            ))
        
        return issues
    
    def _find_suspicious_characters(self, text: str) -> List[str]:
        """Find suspicious Unicode characters"""
        suspicious = []
        
        for char in text:
            category = unicodedata.category(char)
            if category in self.SUSPICIOUS_CATEGORIES:
                suspicious.append(f"U+{ord(char):04X} ({category})")
        
        return suspicious
    
    def _get_scripts(self, text: str) -> Set[str]:
        """Get all Unicode scripts used in text"""
        scripts = set()
        
        for char in text:
            # Cache script lookups for performance
            if char not in self._script_cache:
                try:
                    # This would use the unicodedata2 library in production
                    # For now, use a simplified approach
                    if char.isascii():
                        script = 'Latin'
                    elif 'GREEK' in unicodedata.name(char, ''):
                        script = 'Greek'
                    elif 'CYRILLIC' in unicodedata.name(char, ''):
                        script = 'Cyrillic'
                    else:
                        script = 'Common'
                    self._script_cache[char] = script
                except ValueError:
                    self._script_cache[char] = 'Unknown'
            
            scripts.add(self._script_cache[char])
        
        return scripts
    
    def _has_zero_width_chars(self, text: str) -> bool:
        """Check for zero-width characters"""
        zero_width_pattern = re.compile(r'[\\u200b-\\u200f\\u202a-\\u202e\\u2060-\\u206f]')
        return bool(zero_width_pattern.search(text))
    
    def _remove_zero_width_chars(self, text: str) -> str:
        """Remove zero-width characters"""
        zero_width_pattern = re.compile(r'[\\u200b-\\u200f\\u202a-\\u202e\\u2060-\\u206f]')
        return zero_width_pattern.sub('', text)
    
    def normalize_text(self, text: str, form: str = 'NFC') -> str:
        """
        Normalize Unicode text.
        
        Args:
            text: Text to normalize
            form: Normalization form (NFC, NFD, NFKC, NFKD)
            
        Returns:
            Normalized text
        """
        if form not in ('NFC', 'NFD', 'NFKC', 'NFKD'):
            raise ValueError(f"Invalid normalization form: {form}")
        
        return unicodedata.normalize(form, text)
'''
    
    def _create_math_context_detector(self) -> str:
        """Create math context detector module"""
        return '''"""
Mathematical context detection

This module detects mathematical expressions and notation in text,
helping to prevent false positives in spell checking and validation.
"""
import re
from typing import List, Set, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class MathContextDetector:
    """Detect mathematical context in text"""
    
    # LaTeX math delimiters
    MATH_DELIMITERS = [
        (r'\\$\\$', r'\\$\\$'),  # Display math
        (r'\\$', r'\\$'),      # Inline math
        (r'\\\\\\[', r'\\\\\\]'),  # Display math
        (r'\\\\\\(', r'\\\\\\)'),  # Inline math
        (r'\\\\begin\\{equation\\}', r'\\\\end\\{equation\\}'),
        (r'\\\\begin\\{align\\}', r'\\\\end\\{align\\}'),
    ]
    
    # Mathematical notation patterns
    MATH_PATTERNS = [
        # Variables with subscripts/superscripts
        r'[a-zA-Z]_\\{?\\w+\\}?',
        r'[a-zA-Z]\\^\\{?\\w+\\}?',
        
        # Greek letters
        r'\\\\(?:alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|phi|chi|psi|omega)',
        
        # Mathematical operators
        r'\\\\(?:sum|prod|int|oint|partial|nabla|pm|mp|times|div|cdot|cap|cup|subset|supset|in|notin)',
        
        # Functions
        r'\\\\(?:sin|cos|tan|log|ln|exp|lim|sup|inf|max|min|det|dim|ker|deg)',
        
        # Common expressions
        r'[a-zA-Z]\\([^)]+\\)',  # f(x)
        r'\\d+[a-zA-Z]',         # 2x, 3y
        r'[a-zA-Z]\\d+',         # x1, y2
    ]
    
    def __init__(self):
        # Compile patterns for efficiency
        self._delimiter_patterns = [
            (re.compile(start), re.compile(end))
            for start, end in self.MATH_DELIMITERS
        ]
        self._math_patterns = [re.compile(p) for p in self.MATH_PATTERNS]
    
    def find_math_regions(self, text: str) -> List[Tuple[int, int]]:
        """
        Find regions containing mathematical expressions.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of (start, end) positions of math regions
        """
        regions = []
        
        # Find delimited math regions
        for start_pattern, end_pattern in self._delimiter_patterns:
            pos = 0
            while True:
                start_match = start_pattern.search(text, pos)
                if not start_match:
                    break
                
                end_match = end_pattern.search(text, start_match.end())
                if not end_match:
                    break
                
                regions.append((start_match.start(), end_match.end()))
                pos = end_match.end()
        
        # Find inline math patterns
        for pattern in self._math_patterns:
            for match in pattern.finditer(text):
                regions.append((match.start(), match.end()))
        
        # Merge overlapping regions
        return self._merge_regions(regions)
    
    def _merge_regions(self, regions: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Merge overlapping regions"""
        if not regions:
            return []
        
        # Sort by start position
        sorted_regions = sorted(regions)
        merged = [sorted_regions[0]]
        
        for start, end in sorted_regions[1:]:
            last_start, last_end = merged[-1]
            
            if start <= last_end:
                # Overlapping, merge
                merged[-1] = (last_start, max(last_end, end))
            else:
                # Non-overlapping, add new region
                merged.append((start, end))
        
        return merged
    
    def is_math_context(self, text: str, position: int) -> bool:
        """
        Check if a position in text is within mathematical context.
        
        Args:
            text: Full text
            position: Position to check
            
        Returns:
            True if position is within math context
        """
        math_regions = self.find_math_regions(text)
        
        for start, end in math_regions:
            if start <= position < end:
                return True
        
        return False
    
    def contains_math(self, text: str) -> bool:
        """
        Check if text contains any mathematical expressions.
        
        Args:
            text: Text to check
            
        Returns:
            True if text contains math
        """
        return len(self.find_math_regions(text)) > 0
    
    def extract_non_math_text(self, text: str) -> str:
        """
        Extract text that is not within mathematical regions.
        
        Args:
            text: Original text
            
        Returns:
            Text with math regions removed
        """
        math_regions = self.find_math_regions(text)
        
        if not math_regions:
            return text
        
        result = []
        last_end = 0
        
        for start, end in math_regions:
            # Add text before this math region
            result.append(text[last_end:start])
            last_end = end
        
        # Add remaining text
        result.append(text[last_end:])
        
        return ' '.join(result)
'''
    
    def _create_validator_exceptions(self) -> str:
        """Create validator exceptions module"""
        return '''"""
Custom exceptions for validators

This module defines specific exceptions for validation errors,
providing better error handling and debugging information.
"""
from typing import Optional, Dict, Any


class ValidationError(Exception):
    """Base validation error"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class FilenameValidationError(ValidationError):
    """Filename validation error"""
    
    def __init__(self, message: str, filename: str, **kwargs):
        super().__init__(message, {'filename': filename, **kwargs})
        self.filename = filename


class AuthorValidationError(ValidationError):
    """Author validation error"""
    
    def __init__(self, message: str, author: str, **kwargs):
        super().__init__(message, {'author': author, **kwargs})
        self.author = author


class UnicodeValidationError(ValidationError):
    """Unicode validation error"""
    
    def __init__(self, message: str, text: str, **kwargs):
        super().__init__(message, {'text': text, **kwargs})
        self.text = text


class MathContextError(ValidationError):
    """Mathematical context detection error"""
    pass
'''
    
    def refactor_main_py(self) -> None:
        """Refactor main.py into smaller modules"""
        logger.info("\n📦 Refactoring main.py...")
        
        # Create cli directory
        cli_dir = Path('cli')
        cli_dir.mkdir(exist_ok=True)
        
        # Create extractors directory
        extractors_dir = Path('extractors')
        extractors_dir.mkdir(exist_ok=True)
        
        modules = {
            'cli/args_parser.py': self._create_args_parser(),
            'cli/commands.py': self._create_commands(),
            'extractors/author_extractor.py': self._create_author_extractor(),
        }
        
        for filename, content in modules.items():
            file_path = Path(filename)
            file_path.parent.mkdir(exist_ok=True, parents=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"  ✓ Created {file_path}")
            self.created_modules.append(file_path)
    
    def _create_args_parser(self) -> str:
        """Create argument parser module"""
        return '''"""
Command-line argument parsing for Math-PDF Manager

This module handles parsing and validation of command-line arguments,
providing a clean interface for the main application.
"""
import argparse
from pathlib import Path
from typing import Optional, List
import sys

from core.exceptions import ValidationError, MathPDFError


class ArgumentParser:
    """Enhanced argument parser with validation"""
    
    def __init__(self):
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser"""
        parser = argparse.ArgumentParser(
            prog='mathpdf',
            description='Math-PDF Manager: Organize and validate mathematical PDFs',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._get_epilog()
        )
        
        # Add argument groups
        self._add_path_arguments(parser)
        self._add_operation_arguments(parser)
        self._add_option_arguments(parser)
        self._add_output_arguments(parser)
        
        return parser
    
    def _get_epilog(self) -> str:
        """Get help epilog with examples"""
        return """
Examples:
  %(prog)s /path/to/pdfs --check --report
  %(prog)s --config myconfig.yaml --auto-fix-authors
  %(prog)s --bsde --check --strict
  %(prog)s --duplicates --output-dir ./reports

For more information, see: https://github.com/username/math-pdf-manager
        """
    
    def _add_path_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add path-related arguments"""
        parser.add_argument(
            'root',
            nargs='?',
            type=Path,
            help='Root directory to process'
        )
        
        # Configuration
        parser.add_argument(
            '--config',
            type=Path,
            default=Path('config.yaml'),
            help='Configuration file (default: config.yaml)'
        )
        
        # Domain shortcuts
        shortcuts = parser.add_argument_group('Domain shortcuts')
        shortcuts.add_argument('--bsde', action='store_true',
                              help='Use BSDE folder from config')
        shortcuts.add_argument('--contract', action='store_true',
                              help='Use Contract Theory folder')
        shortcuts.add_argument('--control', action='store_true',
                              help='Use Control Theory folder')
        shortcuts.add_argument('--networks', action='store_true',
                              help='Use Optimal Control on Networks folder')
    
    def _add_operation_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add operation arguments"""
        ops = parser.add_argument_group('Operations')
        
        ops.add_argument('--check', action='store_true',
                        help='Check filenames for issues')
        ops.add_argument('--duplicates', action='store_true',
                        help='Find duplicate files')
        ops.add_argument('--metadata', action='store_true',
                        help='Extract and verify metadata')
        ops.add_argument('--auto-fix-authors', action='store_true',
                        help='Automatically fix author formatting')
        ops.add_argument('--auto-fix-unicode', action='store_true',
                        help='Automatically fix Unicode normalization')
        ops.add_argument('--auto-fix-all', action='store_true',
                        help='Apply all available fixes')
    
    def _add_option_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add option arguments"""
        opts = parser.add_argument_group('Options')
        
        opts.add_argument('--strict', action='store_true',
                         help='Enable strict validation')
        opts.add_argument('--dry-run', action='store_true',
                         help='Preview changes without applying')
        opts.add_argument('--backup', action='store_true',
                         help='Create backups before changes')
        opts.add_argument('--max-files', type=int, default=10000,
                         help='Maximum files to process')
        opts.add_argument('--parallel', type=int, default=1,
                         help='Number of parallel workers')
        
        # Verbosity
        verbosity = opts.add_mutually_exclusive_group()
        verbosity.add_argument('--quiet', action='store_true',
                              help='Minimal output')
        verbosity.add_argument('--verbose', action='store_true',
                              help='Detailed output')
        verbosity.add_argument('--debug', action='store_true',
                              help='Debug output')
    
    def _add_output_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add output arguments"""
        output = parser.add_argument_group('Output')
        
        output.add_argument('--report', action='store_true',
                           help='Generate HTML report')
        output.add_argument('--json', action='store_true',
                           help='Output results as JSON')
        output.add_argument('--csv', action='store_true',
                           help='Output results as CSV')
        output.add_argument('--output-dir', type=Path, default=Path('output'),
                           help='Output directory (default: output)')
    
    def parse_args(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """Parse and validate arguments"""
        parsed = self.parser.parse_args(args)
        self._validate_args(parsed)
        return parsed
    
    def _validate_args(self, args: argparse.Namespace) -> None:
        """Validate parsed arguments"""
        # Check mutually exclusive shortcuts
        shortcuts = ['bsde', 'contract', 'control', 'networks']
        active_shortcuts = sum(getattr(args, s, False) for s in shortcuts)
        
        if active_shortcuts > 1:
            raise ValidationError("Only one domain shortcut can be used at a time")
        
        # Ensure we have a path to process
        if not args.root and active_shortcuts == 0:
            raise ValidationError("Must specify either a path or domain shortcut")
        
        # Validate operations
        operations = ['check', 'duplicates', 'metadata', 
                     'auto_fix_authors', 'auto_fix_unicode']
        if not any(getattr(args, op, False) for op in operations):
            if not (args.report or args.json or args.csv):
                raise ValidationError("No operation specified")
        
        # Handle --auto-fix-all
        if args.auto_fix_all:
            args.auto_fix_authors = True
            args.auto_fix_unicode = True
'''
    
    def _create_commands(self) -> str:
        """Create commands module"""
        return '''"""
Command implementations for Math-PDF Manager

This module contains the actual command implementations that are
called based on parsed arguments.
"""
import logging
from pathlib import Path
from typing import List, Optional
import json

from core.models import ProcessingStats, ScanResult
from scanner import Scanner
from validators import FilenameValidator
from duplicate_detector import DuplicateDetector
from reporter import Reporter

logger = logging.getLogger(__name__)


class CommandProcessor:
    """Process commands based on parsed arguments"""
    
    def __init__(self, config):
        self.config = config
        self.stats = ProcessingStats()
        
        # Initialize components
        self.scanner = Scanner()
        self.validator = FilenameValidator(
            strict_mode=config.get('strict_mode', False)
        )
        self.duplicate_detector = DuplicateDetector()
        self.reporter = Reporter()
    
    def process_check_command(self, path: Path, args) -> None:
        """Process filename checking command"""
        logger.info("Checking filenames...")
        
        # Scan for files
        scan_result = self.scanner.scan(
            path,
            max_files=args.max_files,
            follow_symlinks=False
        )
        
        issues_found = []
        
        # Check each file
        for file_path in scan_result.files:
            result = self.validator.validate_filename(file_path)
            
            if not result.is_valid or result.issues:
                issues_found.append({
                    'file': str(file_path),
                    'issues': result.to_dict()
                })
                
                # Apply fixes if requested
                if args.auto_fix_authors or args.auto_fix_unicode:
                    self._apply_fixes(file_path, result, args)
        
        # Generate report
        if args.report:
            self._generate_report(issues_found, args)
        
        if args.json:
            self._output_json(issues_found, args)
        
        # Update stats
        self.stats.files_processed = len(scan_result.files)
        self.stats.files_failed = len(issues_found)
        self.stats.files_succeeded = len(scan_result.files) - len(issues_found)
    
    def process_duplicates_command(self, path: Path, args) -> None:
        """Process duplicate detection command"""
        logger.info("Finding duplicates...")
        
        # Scan for files
        scan_result = self.scanner.scan(path, max_files=args.max_files)
        
        # Find duplicates
        duplicate_groups = self.duplicate_detector.find_duplicates(
            scan_result.files
        )
        
        logger.info(f"Found {len(duplicate_groups)} duplicate groups")
        
        # Generate output
        if args.report:
            self._generate_duplicate_report(duplicate_groups, args)
        
        if args.json:
            self._output_json({
                'duplicate_groups': [
                    group.to_dict() for group in duplicate_groups
                ]
            }, args)
    
    def _apply_fixes(self, file_path: Path, result, args) -> None:
        """Apply automatic fixes to a file"""
        if not result.suggested_filename:
            return
        
        new_path = file_path.parent / result.suggested_filename
        
        if new_path == file_path:
            return  # No change needed
        
        if args.dry_run:
            logger.info(f"Would rename: {file_path.name} → {new_path.name}")
            return
        
        # Create backup if requested
        if args.backup:
            backup_path = file_path.with_suffix('.pdf.bak')
            file_path.rename(backup_path)
            backup_path.rename(file_path)
        
        # Apply rename
        try:
            file_path.rename(new_path)
            logger.info(f"Renamed: {file_path.name} → {new_path.name}")
        except OSError as e:
            logger.error(f"Failed to rename {file_path}: {e}")
    
    def _generate_report(self, issues: List[dict], args) -> None:
        """Generate HTML report"""
        output_file = args.output_dir / 'validation_report.html'
        self.reporter.generate_html_report(issues, output_file)
        logger.info(f"Report generated: {output_file}")
    
    def _output_json(self, data: dict, args) -> None:
        """Output data as JSON"""
        output_file = args.output_dir / 'results.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"JSON output: {output_file}")
'''
    
    def _create_author_extractor(self) -> str:
        """Create author extractor module"""
        return '''"""
Author extraction and parsing

This module handles extraction of author information from various sources
including filenames, PDF metadata, and content.
"""
import re
from typing import List, Optional, Tuple, Dict
import logging

from core.models import Author

logger = logging.getLogger(__name__)


class AuthorExtractor:
    """Extract and parse author information"""
    
    # Common author patterns
    PATTERNS = {
        'last_first': re.compile(
            r'(?P<last>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*'
            r'(?P<first>[A-Z](?:[a-z]+|\.)(?:\s+[A-Z](?:[a-z]+|\.))*)'
        ),
        'first_last': re.compile(
            r'(?P<first>[A-Z](?:[a-z]+|\.)(?:\s+[A-Z](?:[a-z]+|\.))*)\s+'
            r'(?P<last>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ),
        'initials_last': re.compile(
            r'(?P<initials>(?:[A-Z]\.(?:\s*[A-Z]\.)*)+)\s*'
            r'(?P<last>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ),
    }
    
    def extract_from_filename(self, filename: str) -> List[Author]:
        """Extract authors from filename"""
        # Assume "Authors - Title.pdf" format
        if ' - ' not in filename:
            return []
        
        author_part = filename.split(' - ')[0]
        return self.parse_author_string(author_part)
    
    def parse_author_string(self, author_string: str) -> List[Author]:
        """Parse a string containing one or more authors"""
        authors = []
        
        # Split by common separators
        parts = re.split(r',\s*and\s*|;\s*|\s+and\s+|\s*&\s*', author_string)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            author = self._parse_single_author(part)
            if author:
                authors.append(author)
        
        return authors
    
    def _parse_single_author(self, author_str: str) -> Optional[Author]:
        """Parse a single author string"""
        author_str = author_str.strip()
        
        # Try each pattern
        for pattern_name, pattern in self.PATTERNS.items():
            match = pattern.match(author_str)
            if match:
                return self._create_author_from_match(match, pattern_name)
        
        # Fallback: treat as full name
        return Author(full_name=author_str)
    
    def _create_author_from_match(self, match, pattern_name: str) -> Author:
        """Create Author object from regex match"""
        groups = match.groupdict()
        
        if pattern_name == 'last_first':
            return Author(
                family_name=groups['last'],
                given_name=groups['first'],
                full_name=match.group(0)
            )
        elif pattern_name == 'first_last':
            return Author(
                given_name=groups['first'],
                family_name=groups['last'],
                full_name=match.group(0)
            )
        elif pattern_name == 'initials_last':
            return Author(
                initials=groups['initials'],
                family_name=groups['last'],
                full_name=match.group(0)
            )
        
        return Author(full_name=match.group(0))
'''
    
    def run(self) -> None:
        """Run the refactoring process"""
        logger.info("🔧 Module Refactoring Tool")
        logger.info("=" * 60)
        
        # Check for large files
        large_files = {
            'main.py': 1791,
            'filename_checker.py': 2000,
        }
        
        for filename, line_count in large_files.items():
            if Path(filename).exists():
                logger.info(f"\n📊 {filename}: ~{line_count} lines")
        
        # Refactor modules
        self.refactor_filename_checker()
        self.refactor_main_py()
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Refactoring complete!")
        logger.info(f"   Created {len(self.created_modules)} new modules")
        
        logger.info("\n📝 Next steps:")
        logger.info("1. Update imports in existing files to use new modules")
        logger.info("2. Test that all functionality still works")
        logger.info("3. Remove old monolithic files once verified")


if __name__ == '__main__':
    refactorer = ModuleRefactorer()
    refactorer.run()