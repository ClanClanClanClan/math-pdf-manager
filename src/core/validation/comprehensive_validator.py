#!/usr/bin/env python3
"""
COMPREHENSIVE Unified Validation Service

This is the REAL unified validation service that consolidates ALL validation
functionality from across the entire project. Not just 4-5 systems, but ALL
validation logic in one coherent service.

Consolidates:
- CLI and configuration validation
- File path and security validation
- Filename validation (academic papers)
- Author and title normalization
- Unicode handling and security
- Mathematical content detection
- Pattern matching and tokenization
- Mathematician name validation
- Paper/PDF validation
- Spell checking
- Session validation
And more...
"""

import os
import re
import time
import ipaddress
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Set
from urllib.parse import urlparse
from dataclasses import dataclass
from enum import Enum

from .interfaces import IValidationService


@dataclass
class ValidationResult:
    """Unified validation result."""
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    fixed_value: Optional[Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    CRITICAL = "critical"


class ComprehensiveUnifiedValidationService(IValidationService):
    """
    The REAL comprehensive validation service that actually consolidates
    ALL validation systems in the project.
    """
    
    def __init__(self):
        """Initialize the comprehensive validation service."""
        # Initialize all validation subsystems
        self._init_core_validation()
        self._init_security_validation()
        self._init_filename_validation()
        self._init_text_validation()
        self._init_math_validation()
        self._init_unicode_validation()
        self._init_pattern_validation()
        self._init_specialized_validation()
        
        # Performance tracking
        self._validation_cache = {}
        self._performance_metrics = {}
    
    # ========================================
    # INITIALIZATION METHODS
    # ========================================
    
    def _init_core_validation(self):
        """Initialize core validation patterns and rules."""
        # Email validation
        self.EMAIL_PATTERN = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        # URL validation
        self.URL_PATTERN = re.compile(
            r'^https?://[^\s/$.?#].[^\s]*$', 
            re.IGNORECASE
        )
        
        # Path traversal detection
        self.PATH_TRAVERSAL_PATTERN = re.compile(r'\.\.([\\/]|$)')
        
        # SQL injection patterns
        self.SQL_INJECTION_PATTERN = re.compile(
            r'(\b(union|select|insert|update|delete|drop|create|'
            r'alter|exec|execute|script|javascript)\b)',
            re.IGNORECASE
        )
    
    def _init_security_validation(self):
        """Initialize security validation rules."""
        self.MAX_PATH_LENGTH = 1000
        self.MAX_FILENAME_LENGTH = 255
        self.MAX_TEXT_LENGTH = 1_000_000
        
        # Dangerous characters and patterns
        self.DANGEROUS_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
        
        # Blocked path components (Windows reserved names)
        self.BLOCKED_PATH_COMPONENTS = {
            '..', '.', 'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 
            'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5',
            'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        
        # Dangerous Unicode characters
        self.DANGEROUS_UNICODE = {
            '\u202e', '\u202d', '\u202a', '\u202b', '\u202c',  # Direction override
            '\u200b', '\u200c', '\u200d', '\u200e', '\u200f',  # Zero-width
            '\ufeff', '\u2060', '\u2061', '\u2062', '\u2063',  # Invisible
            '\u2064', '\u202f'
        }
        
        # Homoglyph detection patterns
        self.HOMOGLYPH_MAPPINGS = {
            'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c',
            'у': 'y', 'х': 'x', 'А': 'A', 'В': 'B', 'Е': 'E',
            'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O', 'Р': 'P',
            'С': 'C', 'Т': 'T', 'У': 'Y', 'Х': 'X'
        }
    
    def _init_filename_validation(self):
        """Initialize academic filename validation patterns."""
        # Author name patterns
        self.AUTHOR_NAME_PATTERN = re.compile(
            r'^[A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-z]+)+$'
        )
        
        # Title word patterns
        self.TITLE_WORD_PATTERN = re.compile(r'\b\w+\b')
        
        # Academic filename format
        self.ACADEMIC_FILENAME_PATTERN = re.compile(
            r'^([^-]+)\s*-\s*(.+)\.pdf$'
        )
        
        # Common abbreviations that should stay uppercase
        self.UPPERCASE_ABBREVIATIONS = {
            'USA', 'UK', 'EU', 'UN', 'NATO', 'ISBN', 'DOI',
            'PDF', 'HTML', 'XML', 'JSON', 'API', 'URL', 'URI',
            'CPU', 'GPU', 'RAM', 'SSD', 'HDD', 'OS', 'UI', 'UX'
        }
        
        # Words that should stay lowercase in titles
        self.LOWERCASE_WORDS = {
            'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for',
            'from', 'in', 'into', 'like', 'of', 'on', 'or',
            'over', 'the', 'to', 'with', 'via'
        }
    
    def _init_text_validation(self):
        """Initialize text processing validation."""
        # Spell checking patterns
        self.MISSPELLING_PATTERNS = [
            (r'\b(teh)\b', 'the'),
            (r'\b(recieve)\b', 'receive'),
            (r'\b(occured)\b', 'occurred'),
            (r'\b(seperate)\b', 'separate'),
            (r'\b(definately)\b', 'definitely')
        ]
        
        # Language detection keywords
        self.LANGUAGE_INDICATORS = {
            'en': {'the', 'and', 'of', 'to', 'in', 'is', 'that'},
            'fr': {'le', 'la', 'de', 'et', 'est', 'dans', 'que'},
            'de': {'der', 'die', 'das', 'und', 'ist', 'von', 'mit'},
            'es': {'el', 'la', 'de', 'y', 'es', 'en', 'que'}
        }
    
    def _init_math_validation(self):
        """Initialize mathematical content validation."""
        # Mathematical notation patterns
        self.MATH_PATTERNS = [
            re.compile(r'\$[^$]+\$'),           # Inline math
            re.compile(r'\$\$[^$]+\$\$'),       # Display math
            re.compile(r'\\begin\{[^}]+\}'),    # LaTeX environments
            re.compile(r'\\[a-zA-Z]+\{[^}]*\}'), # LaTeX commands
        ]
        
        # Greek letters
        self.GREEK_LETTERS = set('αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ')
        
        # Mathematical symbols
        self.MATH_SYMBOLS = set('∞∑∏∫∂∇∆≤≥≠≈∝±×÷√∛∜⊕⊖⊗⊘∈∉⊂⊃∩∪∧∨¬∀∃')
        
        # Mathematical terms (multilingual)
        self.MATH_TERMS = {
            # English
            'theorem', 'lemma', 'proof', 'corollary', 'proposition',
            'equation', 'formula', 'algorithm', 'matrix', 'vector',
            'derivative', 'integral', 'limit', 'convergence',
            'topology', 'algebra', 'geometry', 'analysis',
            # German
            'gleichungen', 'gleichung', 'theorem', 'beweis', 'formel',
            'mathematik', 'algebra', 'geometrie', 'analysis',
            # French  
            'équation', 'théorème', 'preuve', 'formule', 'mathématiques',
            # Common academic terms
            'pdf', 'pde', 'ode', 'differential', 'calculus', 'statistics'
        }
        
        # Famous mathematicians
        self.FAMOUS_MATHEMATICIANS = {
            'Gauss', 'Euler', 'Newton', 'Leibniz', 'Riemann',
            'Cauchy', 'Fermat', 'Descartes', 'Hilbert', 'Poincaré',
            'Ramanujan', 'Turing', 'Gödel', 'Cantor', 'Nash',
            'Einstein', 'Maxwell', 'Hertz', 'Laplace', 'Fourier'
        }
    
    def _init_unicode_validation(self):
        """Initialize Unicode validation and normalization."""
        # Unicode categories to check
        self.UNICODE_CATEGORIES = {
            'Cc': 'Control',
            'Cf': 'Format',
            'Co': 'Private Use',
            'Cn': 'Unassigned'
        }
        
        # Normalization forms
        self.NORMALIZATION_FORMS = ['NFC', 'NFD', 'NFKC', 'NFKD']
    
    def _init_pattern_validation(self):
        """Initialize pattern matching validation."""
        # Token patterns
        self.TOKEN_PATTERNS = {
            'word': re.compile(r'\b[\w\'-]+\b'),
            'number': re.compile(r'\b\d+(?:\.\d+)?\b'),
            'punctuation': re.compile(r'[.,;:!?\-]'),
            'whitespace': re.compile(r'\s+')
        }
        
        # Dash patterns
        self.DASH_PATTERNS = {
            'hyphen': re.compile(r'-'),
            'endash': re.compile(r'–'),
            'emdash': re.compile(r'—'),
            'minus': re.compile(r'−')
        }
    
    def _init_specialized_validation(self):
        """Initialize specialized validation rules."""
        # Session validation
        self.SESSION_TIMEOUT = 3600  # 1 hour
        self.SESSION_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{32,128}$')
        
        # PDF validation
        self.PDF_MAGIC_BYTES = b'%PDF'
        self.MAX_PDF_SIZE = 100 * 1024 * 1024  # 100 MB
        
        # Configuration keys
        self.REQUIRED_CONFIG_KEYS = {
            'database', 'logging', 'security', 'paths'
        }
    
    # ========================================
    # CORE VALIDATION METHODS (IValidationService)
    # ========================================
    
    def validate_cli_inputs(self, args: Any) -> bool:
        """Validate command-line arguments for safety and correctness."""
        try:
            # Validate root path
            if hasattr(args, 'root') and args.root:
                if not self._validate_safe_path(args.root):
                    return False
            
            # Validate output paths
            for output_attr in ['output', 'csv_output', 'report_output']:
                if hasattr(args, output_attr):
                    output_path = getattr(args, output_attr, None)
                    if output_path and not self._validate_safe_path(output_path):
                        return False
            
            # Validate numeric arguments
            for numeric_attr in ['max_files', 'timeout', 'threads']:
                if hasattr(args, numeric_attr):
                    value = getattr(args, numeric_attr, None)
                    if value is not None:
                        try:
                            num_val = int(value)
                            if num_val < 0:
                                return False
                        except (ValueError, TypeError):
                            return False
            
            return True
            
        except Exception:
            return False
    
    def validate_file_path(self, path: Union[str, Path]) -> bool:
        """Validate file path for security and accessibility."""
        return self._validate_safe_path(path, check_exists=False)
    
    def validate_directory_path(self, path: Union[str, Path]) -> bool:
        """Validate directory path for security and accessibility."""
        if not self._validate_safe_path(path, check_exists=False):
            return False
        
        try:
            path_obj = Path(path).expanduser().resolve()
            if path_obj.exists() and not path_obj.is_dir():
                return False
            return True
        except Exception:
            return False
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe filesystem usage."""
        if not filename:
            return 'untitled'
        
        # Remove dangerous Unicode
        filename = self._remove_dangerous_unicode(filename)
        
        # Replace dangerous characters
        filename = self.DANGEROUS_FILENAME_CHARS.sub('_', filename)
        
        # Handle reserved names
        name_upper = filename.upper().split('.')[0]
        if name_upper in self.BLOCKED_PATH_COMPONENTS:
            filename = f'{filename}_safe'
        
        # Ensure reasonable length
        if len(filename) > self.MAX_FILENAME_LENGTH:
            name, ext = os.path.splitext(filename)
            max_name_len = self.MAX_FILENAME_LENGTH - len(ext)
            filename = name[:max_name_len] + ext
        
        # Ensure not empty
        filename = filename.strip('. ')
        if not filename:
            filename = 'untitled'
        
        return filename
    
    def validate_mathematical_content(self, text: str) -> Dict[str, Any]:
        """Validate and analyze mathematical content in text."""
        if not text or len(text) > self.MAX_TEXT_LENGTH:
            return {
                'valid': False,
                'reason': 'Invalid text input',
                'has_math': False
            }
        
        results = {
            'valid': True,
            'has_math': False,
            'math_notation_count': 0,
            'math_terms_found': [],
            'math_symbols_found': [],
            'greek_letters_found': [],
            'mathematicians_mentioned': [],
            'complexity_score': 0,
            'math_regions': []
        }
        
        text_lower = text.lower()
        
        # Check for mathematical terms
        for term in self.MATH_TERMS:
            if term in text_lower:
                results['math_terms_found'].append(term)
        
        # Check for mathematical symbols
        for char in text:
            if char in self.MATH_SYMBOLS:
                results['math_symbols_found'].append(char)
            if char in self.GREEK_LETTERS:
                results['greek_letters_found'].append(char)
        
        # Check for LaTeX math notation
        for pattern in self.MATH_PATTERNS:
            matches = pattern.findall(text)
            results['math_notation_count'] += len(matches)
            for match in matches:
                start = text.find(match)
                results['math_regions'].append((start, start + len(match)))
        
        # Check for mathematician names
        for mathematician in self.FAMOUS_MATHEMATICIANS:
            if mathematician.lower() in text_lower:
                results['mathematicians_mentioned'].append(mathematician)
        
        # Determine if text has mathematical content
        results['has_math'] = (
            len(results['math_terms_found']) > 0 or
            len(results['math_symbols_found']) > 0 or
            len(results['greek_letters_found']) > 0 or
            results['math_notation_count'] > 0 or
            len(results['mathematicians_mentioned']) > 0
        )
        
        # Calculate complexity score
        results['complexity_score'] = (
            len(results['math_terms_found']) * 2 +
            len(results['math_symbols_found']) +
            len(results['greek_letters_found']) +
            results['math_notation_count'] * 3 +
            len(results['mathematicians_mentioned']) * 2
        )
        
        return results
    
    def validate_academic_text(self, text: str) -> Dict[str, Any]:
        """Validate and analyze academic text content."""
        if not text or len(text) > self.MAX_TEXT_LENGTH:
            return {'valid': False, 'reason': 'Invalid text input'}
        
        results = {
            'valid': True,
            'word_count': 0,
            'sentence_count': 0,
            'paragraph_count': 0,
            'potential_authors': [],
            'has_citations': False,
            'has_references': False,
            'academic_score': 0,
            'language': 'en',
            'spelling_errors': []
        }
        
        # Basic text statistics
        words = text.split()
        results['word_count'] = len(words)
        results['sentence_count'] = len(re.findall(r'[.!?]+', text))
        results['paragraph_count'] = len([p for p in text.split('\n\n') if p.strip()])
        
        # Find potential author names - improved pattern
        author_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-z]+)+)\b',  # Full names like "John Smith"
            r'\b([A-Z][a-z]+,?\s+[A-Z]\.?(?:\s+[A-Z]\.?)*)\b',        # "Smith, J." or "Smith J."
            r'\b([A-Z][a-z]+(?:\s+et\s+al\.?)?)\b',                   # "Smith et al."
        ]
        
        author_matches = []
        for pattern in author_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            author_matches.extend(matches)
        
        # Clean up author names
        cleaned_authors = []
        for author in author_matches:
            # Remove "et al." suffix and clean up
            author = re.sub(r'\s+et\s+al\.?', '', author, flags=re.IGNORECASE)
            author = author.strip(' ,.')
            if len(author) > 2 and author.lower() not in ['the', 'and', 'or', 'as', 'by']:
                cleaned_authors.append(author)
        
        results['potential_authors'] = list(set(cleaned_authors))
        
        # Check for citations
        citation_patterns = [
            r'\[[0-9, -]+\]',          # [1], [1-3], [1, 2, 3]
            r'\([^)]*[0-9]{4}[^)]*\)',  # (Author, 2023)
            r'\bet al\.\b',             # et al.
        ]
        
        for pattern in citation_patterns:
            if re.search(pattern, text):
                results['has_citations'] = True
                break
        
        # Check for references section
        if re.search(r'\b(References|Bibliography|Works Cited)\b', text, re.IGNORECASE):
            results['has_references'] = True
        
        # Detect language
        results['language'] = self._detect_language(text)
        
        # Basic spell checking
        results['spelling_errors'] = self._check_spelling(text)
        
        # Calculate academic score
        academic_indicators = [
            'abstract', 'introduction', 'methodology', 'results',
            'discussion', 'conclusion', 'references', 'figure', 'table'
        ]
        
        text_lower = text.lower()
        academic_word_count = sum(1 for word in academic_indicators if word in text_lower)
        
        results['academic_score'] = (
            min(results['word_count'] / 100, 10) +  # Length factor
            len(results['potential_authors']) * 2 +   # Author mentions
            (5 if results['has_citations'] else 0) +  # Citations
            (5 if results['has_references'] else 0) + # References
            academic_word_count                       # Academic vocabulary
        )
        
        return results
    
    def detect_security_issues(self, content: str) -> List[Dict[str, Any]]:
        """Detect potential security issues in content."""
        issues = []
        
        if not content:
            return issues
        
        # Check for dangerous Unicode characters
        for char in self.DANGEROUS_UNICODE:
            if char in content:
                issues.append({
                    'type': 'dangerous_unicode',
                    'severity': ValidationSeverity.CRITICAL,
                    'description': f'Dangerous Unicode character detected: {repr(char)}',
                    'position': content.find(char)
                })
        
        # Check for homoglyphs
        homoglyphs_found = self._detect_homoglyphs(content)
        if homoglyphs_found:
            issues.append({
                'type': 'homoglyph_attack',
                'severity': ValidationSeverity.WARNING,
                'description': f'Potential homoglyph attack: {homoglyphs_found}',
                'characters': homoglyphs_found
            })
        
        # Check for path traversal
        if self.PATH_TRAVERSAL_PATTERN.search(content):
            issues.append({
                'type': 'path_traversal',
                'severity': ValidationSeverity.CRITICAL,
                'description': 'Path traversal pattern detected'
            })
        
        # Check for SQL injection
        sql_match = self.SQL_INJECTION_PATTERN.search(content)
        if sql_match:
            issues.append({
                'type': 'sql_injection',
                'severity': ValidationSeverity.CRITICAL,
                'description': f'Potential SQL injection: {sql_match.group()}'
            })
        
        # Check for script injection
        script_patterns = [
            (r'<script[^>]*>', 'script_tag'),
            (r'javascript:', 'javascript_protocol'),
            (r'on\w+\s*=', 'event_handler'),
            (r'eval\s*\(', 'eval_call'),
            (r'exec\s*\(', 'exec_call'),
        ]
        
        for pattern, issue_type in script_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append({
                    'type': issue_type,
                    'severity': ValidationSeverity.ERROR,
                    'description': f'Suspicious pattern detected: {issue_type}'
                })
        
        return issues
    
    # ========================================
    # FILENAME VALIDATION (Academic Papers)
    # ========================================
    
    def validate_academic_filename(self, filename: str) -> ValidationResult:
        """
        Validate academic paper filename format.
        Expected format: "Author(s) - Title.pdf"
        """
        result = ValidationResult(is_valid=True)
        
        # Check basic format
        match = self.ACADEMIC_FILENAME_PATTERN.match(filename)
        if not match:
            result.is_valid = False
            result.errors.append("Invalid filename format. Expected: 'Author(s) - Title.pdf'")
            return result
        
        authors_part, title_part = match.groups()
        
        # Validate authors
        author_result = self._validate_authors(authors_part)
        if not author_result.is_valid:
            result.is_valid = False
            result.errors.extend(author_result.errors)
        else:
            result.metadata['authors'] = author_result.metadata.get('authors', [])
        
        # Validate title
        title_result = self._validate_title(title_part)
        if not title_result.is_valid:
            result.is_valid = False
            result.errors.extend(title_result.errors)
        
        # Check Unicode normalization
        if not self._is_nfc_normalized(filename):
            result.warnings.append("Filename is not NFC normalized")
            result.fixed_value = unicodedata.normalize('NFC', filename)
        
        # Check for dangerous characters
        security_issues = self.detect_security_issues(filename)
        for issue in security_issues:
            if issue['severity'] == ValidationSeverity.CRITICAL:
                result.is_valid = False
                result.errors.append(issue['description'])
            else:
                result.warnings.append(issue['description'])
        
        return result
    
    def _validate_authors(self, authors_str: str) -> ValidationResult:
        """Validate author names in filename."""
        result = ValidationResult(is_valid=True)
        
        # Split multiple authors
        if ' - ' in authors_str:
            authors = authors_str.split(' - ')
        elif ' — ' in authors_str:  # em-dash
            authors = authors_str.split(' — ')
        elif ' – ' in authors_str:  # en-dash
            authors = authors_str.split(' – ')
        else:
            authors = [authors_str]
        
        validated_authors = []
        for author in authors:
            author = author.strip()
            
            # Check author name format
            if not self.AUTHOR_NAME_PATTERN.match(author):
                result.warnings.append(f"Unusual author name format: '{author}'")
            
            # Check for known mathematicians
            is_mathematician = any(
                math_name in author 
                for math_name in self.FAMOUS_MATHEMATICIANS
            )
            
            validated_authors.append({
                'name': author,
                'is_mathematician': is_mathematician
            })
        
        result.metadata['authors'] = validated_authors
        return result
    
    def _validate_title(self, title: str) -> ValidationResult:
        """Validate paper title format and capitalization."""
        result = ValidationResult(is_valid=True)
        
        words = self.TITLE_WORD_PATTERN.findall(title)
        if not words:
            result.is_valid = False
            result.errors.append("Title contains no words")
            return result
        
        # Check capitalization
        for i, word in enumerate(words):
            # First word should be capitalized
            if i == 0 and not word[0].isupper():
                result.warnings.append(f"First word '{word}' should be capitalized")
            
            # Check other words
            elif i > 0:
                if word.upper() in self.UPPERCASE_ABBREVIATIONS:
                    if word != word.upper():
                        result.warnings.append(f"'{word}' should be uppercase")
                elif word.lower() in self.LOWERCASE_WORDS:
                    if word != word.lower():
                        result.warnings.append(f"'{word}' should be lowercase")
                elif not word[0].isupper() and len(word) > 3:
                    result.warnings.append(f"'{word}' might need capitalization")
        
        # Check for mathematical content
        math_check = self.validate_mathematical_content(title)
        if math_check['has_math']:
            result.metadata['has_math'] = True
            result.metadata['math_complexity'] = math_check['complexity_score']
        
        return result
    
    # ========================================
    # SPECIALIZED VALIDATION METHODS
    # ========================================
    
    def validate_session(self, session_id: str, timestamp: Optional[float] = None) -> bool:
        """Validate session ID and check for timeout."""
        # Check session ID format
        if not self.SESSION_ID_PATTERN.match(session_id):
            return False
        
        # Check session timeout if timestamp provided
        if timestamp is not None:
            current_time = time.time()
            if current_time - timestamp > self.SESSION_TIMEOUT:
                return False
        
        return True
    
    def validate_pdf_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """Validate PDF file format and metadata."""
        result = ValidationResult(is_valid=True)
        
        try:
            file_path = Path(file_path)
            
            # Check file exists
            if not file_path.exists():
                result.is_valid = False
                result.errors.append("File does not exist")
                return result
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.MAX_PDF_SIZE:
                result.is_valid = False
                result.errors.append(f"File too large: {file_size / 1024 / 1024:.1f}MB")
                return result
            
            # Check magic bytes
            with open(file_path, 'rb') as f:
                magic = f.read(4)
                if magic != self.PDF_MAGIC_BYTES:
                    result.is_valid = False
                    result.errors.append("Not a valid PDF file")
                    return result
            
            result.metadata['size'] = file_size
            result.metadata['path'] = str(file_path)
            
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Error validating PDF: {str(e)}")
        
        return result
    
    def validate_configuration(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration dictionary."""
        result = ValidationResult(is_valid=True)
        
        # Check required keys
        missing_keys = self.REQUIRED_CONFIG_KEYS - set(config.keys())
        if missing_keys:
            result.is_valid = False
            result.errors.append(f"Missing required config keys: {missing_keys}")
        
        # Validate specific sections
        if 'database' in config:
            db_result = self._validate_database_config(config['database'])
            if not db_result.is_valid:
                result.is_valid = False
                result.errors.extend(db_result.errors)
        
        if 'security' in config:
            sec_result = self._validate_security_config(config['security'])
            if not sec_result.is_valid:
                result.is_valid = False
                result.errors.extend(sec_result.errors)
        
        return result
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def _validate_safe_path(self, path: Union[str, Path], check_exists: bool = False) -> bool:
        """Validate path for security issues."""
        try:
            path_str = str(path)
            
            # Check length
            if len(path_str) > self.MAX_PATH_LENGTH:
                return False
            
            # Check for path traversal
            if '..' in path_str or self.PATH_TRAVERSAL_PATTERN.search(path_str):
                return False
            
            # Check for dangerous Unicode
            if any(char in path_str for char in self.DANGEROUS_UNICODE):
                return False
            
            # Resolve path
            resolved_path = Path(path).expanduser().resolve()
            
            # Check resolved path doesn't contain traversal
            if '..' in str(resolved_path):
                return False
            
            # Check path components
            for component in resolved_path.parts:
                if component.upper() in self.BLOCKED_PATH_COMPONENTS:
                    return False
            
            # Check existence if requested
            if check_exists and not resolved_path.exists():
                return False
            
            return True
            
        except Exception:
            return False
    
    def _remove_dangerous_unicode(self, text: str) -> str:
        """Remove dangerous Unicode characters from text."""
        return ''.join(char for char in text if char not in self.DANGEROUS_UNICODE)
    
    def _is_nfc_normalized(self, text: str) -> bool:
        """Check if text is NFC normalized."""
        return text == unicodedata.normalize('NFC', text)
    
    def _detect_homoglyphs(self, text: str) -> List[str]:
        """Detect potential homoglyph characters."""
        found = []
        for char in text:
            if char in self.HOMOGLYPH_MAPPINGS:
                found.append(char)
        return found
    
    def _detect_language(self, text: str) -> str:
        """Detect language of text."""
        text_lower = text.lower()
        text_words = set(text_lower.split())
        
        # Count indicator words for each language
        scores = {}
        for lang, indicators in self.LANGUAGE_INDICATORS.items():
            score = len(text_words.intersection(indicators))
            scores[lang] = score
        
        # Return language with highest score
        if scores:
            return max(scores, key=scores.get)
        
        return 'en'  # Default to English
    
    def _check_spelling(self, text: str) -> List[str]:
        """Basic spell checking."""
        errors = []
        
        for pattern, correction in self.MISSPELLING_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                errors.append(f"{match.group()} -> {correction}")
        
        return errors
    
    def _validate_database_config(self, db_config: Dict[str, Any]) -> ValidationResult:
        """Validate database configuration."""
        result = ValidationResult(is_valid=True)
        
        required = ['host', 'port', 'name']
        missing = [key for key in required if key not in db_config]
        
        if missing:
            result.is_valid = False
            result.errors.append(f"Missing database config: {missing}")
        
        return result
    
    def _validate_security_config(self, sec_config: Dict[str, Any]) -> ValidationResult:
        """Validate security configuration."""
        result = ValidationResult(is_valid=True)
        
        if 'secret_key' in sec_config:
            key = sec_config['secret_key']
            if len(key) < 32:
                result.warnings.append("Secret key should be at least 32 characters")
        
        return result
    
    # ========================================
    # INTERFACE COMPLIANCE METHODS
    # ========================================
    
    def validate_string(self, value: str, min_length: int = 0, 
                       max_length: int = 1000, allowed_chars: Optional[Set[str]] = None) -> str:
        """Validate and sanitize string input."""
        if not isinstance(value, str):
            raise ValueError(f"Expected string, got {type(value).__name__}")
        
        if len(value) < min_length:
            raise ValueError(f"String too short (min: {min_length})")
        
        if len(value) > max_length:
            raise ValueError(f"String too long (max: {max_length})")
        
        if allowed_chars:
            invalid_chars = set(value) - allowed_chars
            if invalid_chars:
                raise ValueError(f"Invalid characters: {invalid_chars}")
        
        return value
    
    def validate_email(self, email: str) -> str:
        """Validate email address format."""
        email = email.strip().lower()
        if not self.EMAIL_PATTERN.match(email):
            raise ValueError(f"Invalid email address: {email}")
        return email
    
    def validate_url(self, url: str, allowed_schemes: List[str] = None) -> str:
        """Validate URL format and scheme."""
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        url = url.strip()
        
        if not self.URL_PATTERN.match(url):
            raise ValueError(f"Invalid URL format: {url}")
        
        parsed = urlparse(url)
        
        if parsed.scheme not in allowed_schemes:
            raise ValueError(f"URL scheme not allowed: {parsed.scheme}")
        
        if not parsed.netloc:
            raise ValueError("URL missing network location")
        
        return url
    
    def validate_ip_address(self, ip: str, version: Optional[int] = None) -> str:
        """Validate IP address."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            if version == 4 and not isinstance(ip_obj, ipaddress.IPv4Address):
                raise ValueError("Expected IPv4 address, got IPv6")
            elif version == 6 and not isinstance(ip_obj, ipaddress.IPv6Address):
                raise ValueError("Expected IPv6 address, got IPv4")
            
            return str(ip_obj)
        except ValueError:
            raise ValueError(f"Invalid IP address: {ip}")
    
    def validate_file_extension(self, filename: str, allowed_extensions: Optional[Set[str]] = None,
                               file_type: Optional[str] = None) -> str:
        """Validate file extension against allowed types."""
        default_extensions = {
            'document': {'.pdf', '.txt', '.md', '.tex', '.doc', '.docx'},
            'image': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'},
            'data': {'.json', '.yaml', '.yml', '.csv', '.xml'},
        }
        
        if file_type and file_type in default_extensions:
            allowed_extensions = default_extensions[file_type]
        
        if not allowed_extensions:
            return filename
        
        ext = Path(filename).suffix.lower()
        if ext not in allowed_extensions:
            raise ValueError(
                f"File extension {ext} not allowed. "
                f"Allowed: {', '.join(sorted(allowed_extensions))}"
            )
        
        return filename
    
    def validate_integer(self, value: Any, min_value: Optional[int] = None, 
                        max_value: Optional[int] = None) -> int:
        """Validate integer input with optional bounds."""
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid integer: {value}")
        
        if min_value is not None and int_value < min_value:
            raise ValueError(f"Value too small (min: {min_value})")
        
        if max_value is not None and int_value > max_value:
            raise ValueError(f"Value too large (max: {max_value})")
        
        return int_value
    
    def detect_language(self, text: str) -> str:
        """Detect language of academic/mathematical text."""
        return self._detect_language(text)


# Alias for backward compatibility
UnifiedValidationService = ComprehensiveUnifiedValidationService
