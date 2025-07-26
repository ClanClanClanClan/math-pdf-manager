#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Validation Service Implementation
Phase 1, Week 2: Consolidates all validation systems into a single DI service

This module consolidates validation logic from:
- validation.py (CLI validation)
- core/security/input_validation.py (comprehensive input validation)
- validators/validation_utils.py (mathematical content validation)
- utils/security.py (security validation)
- filename_checker validation logic
"""

import os
import re
import ipaddress
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .interfaces import IValidationService, ILoggingService
from .container import service


@service(IValidationService, singleton=True)
class UnifiedValidationService:
    """
    Comprehensive validation service that consolidates all validation systems.
    
    Integrates functionality from multiple validation modules:
    - CLI argument validation
    - Path and filename security validation  
    - Input sanitization and format validation
    - Mathematical content detection
    - Configuration validation
    """
    
    def __init__(self, logging_service: ILoggingService):
        self._logger = logging_service
        self._setup_patterns()
        self._setup_mathematical_patterns()
        self._setup_security_patterns()
    
    def _setup_patterns(self):
        """Initialize compiled regex patterns for performance."""
        # Email validation pattern (more permissive for edge cases)
        self.EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{1,}$')
        
        # URL validation pattern
        self.URL_PATTERN = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )
        
        # Filename validation pattern
        self.FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._\-\s]+$')
        
        # SQL injection detection pattern
        self.SQL_INJECTION_PATTERN = re.compile(
            r'(\b(union|select|insert|update|delete|drop|create|alter|exec|execute|script|javascript)\b)',
            re.IGNORECASE
        )
    
    def _setup_mathematical_patterns(self):
        """Initialize mathematical content detection patterns."""
        # Greek letters commonly used in mathematics (lowercase and uppercase)
        self.MATH_GREEK_PATTERN = re.compile(r'[αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ]')
        
        # Mathematical symbols
        self.SUPERSCRIPT_PATTERN = re.compile(r'[⁰¹²³⁴⁵⁶⁷⁸⁹]')
        self.SUBSCRIPT_PATTERN = re.compile(r'[₀₁₂₃₄₅₆₇₈₉]')
        self.MATH_SYMBOLS_PATTERN = re.compile(r'[∀∃∂∇∞∫∮∑∏±×÷≠≤≥≈∈∉⊂⊃∩∪∧∨¬]')
        
        # Language detection keywords
        self.LANGUAGE_INDICATORS = {
            'fr': {'français', 'française', 'initiation', 'théorie', 'algèbre',
                   'géométrie', 'analyse', 'probabilités', 'topologie'},
            'de': {'mathematik', 'algebra', 'geometrie', 'analysis', 'wahrscheinlichkeit',
                   'topologie', 'funktionen', 'einführung', 'grundlagen'},
            'es': {'matemáticas', 'álgebra', 'geometría', 'análisis', 'probabilidad',
                   'topología', 'funciones', 'introducción'}
        }
    
    def _setup_security_patterns(self):
        """Initialize security validation patterns."""
        # Path traversal patterns
        self.SUSPICIOUS_PATTERNS = [
            r'\.\./',           # Parent directory traversal
            r'\.\.\\',          # Windows parent directory
            r'\.\.//',          # Double slash variants
            r'~/',              # Home directory expansion
            r'\$\{.*\}',        # Variable expansion
            r'\$\(.*\)',        # Command substitution
            r'`.*`',            # Backtick command substitution
            r'\|',              # Pipe character
            r'[<>"]',           # Shell metacharacters
            r'[\x00-\x1f]',     # Control characters
        ]
        
        # Unicode normalization attacks
        self.UNICODE_SUSPICIOUS = [
            '\u2025',  # Two dot leader (‥)
            '\u2026',  # Horizontal ellipsis (…)
            '\uff0e',  # Fullwidth full stop (．)
            '\u002e\u002e',  # Could be normalized to ..
        ]
        
        # Safe character sets
        self.SAFE_CHARS = {
            'filename': set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._- '),
            'username': set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-@'),
            'alphanumeric': set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'),
        }
        
        # File type extensions
        self.ALLOWED_EXTENSIONS = {
            'document': {'.pdf', '.txt', '.md', '.tex', '.doc', '.docx'},
            'image': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'},
            'data': {'.json', '.yaml', '.yml', '.csv', '.xml'},
        }
    
    # === Core Path & File Validation ===
    
    def validate_file_path(self, path: Path, base_path: Optional[Path] = None, allow_symlinks: bool = False) -> Path:
        """
        Validate file path for security and accessibility.
        
        Consolidates logic from utils/security.py PathValidator and core/security/input_validation.py
        """
        try:
            # Convert to string for pattern matching
            path_str = str(path)
            
            # Check for suspicious patterns
            for pattern in self.SUSPICIOUS_PATTERNS:
                if re.search(pattern, path_str):
                    from core.exceptions import SecurityError
                    raise SecurityError(
                        f"Suspicious pattern detected in path: {pattern}",
                        threat_type="path_traversal"
                    )
            
            # Check for suspicious Unicode characters
            for char in self.UNICODE_SUSPICIOUS:
                if char in path_str:
                    from core.exceptions import SecurityError
                    raise SecurityError(
                        "Suspicious Unicode character in path",
                        threat_type="unicode_attack"
                    )
            
            # Normalize the path
            normalized = os.path.normpath(os.path.abspath(str(path)))
            path_obj = Path(normalized)
            
            # Always resolve to get the actual path
            resolved_path = path_obj.resolve(strict=False)
            
            # Check if path contains symlinks when not allowed
            if not allow_symlinks and resolved_path != path_obj.absolute():
                from core.exceptions import SecurityError
                raise SecurityError(
                    "Symbolic links not allowed",
                    threat_type="symlink_attack"
                )
            
            # Check if within base directory
            if base_path:
                # Resolve both paths to handle symlinks properly (e.g., /var -> /private/var on macOS)
                base_path_resolved = Path(os.path.normpath(os.path.abspath(str(base_path)))).resolve(strict=False)
                try:
                    resolved_path.relative_to(base_path_resolved)
                except ValueError:
                    from core.exceptions import SecurityError
                    raise SecurityError(
                        f"Path '{path}' is outside allowed directory",
                        threat_type="path_traversal",
                        severity="critical"
                    )
            
            return resolved_path
            
        except Exception as e:
            self._logger.error(f"Path validation failed for {path}: {e}")
            raise
    
    def validate_filename(self, filename: str, allow_paths: bool = False) -> str:
        """
        Validate filename for security.
        
        Consolidates logic from core/security/input_validation.py and utils/security.py
        """
        if not filename:
            raise ValueError("Filename cannot be empty")
        
        # Check for path traversal attempts
        if '..' in filename:
            raise ValueError("Path traversal detected")
        
        # Check for absolute paths
        if os.path.isabs(filename):
            raise ValueError("Absolute paths not allowed")
        
        # If paths not allowed, check for separators
        if not allow_paths and ('/' in filename or '\\' in filename):
            raise ValueError("Path separators not allowed")
        
        # Check for null bytes
        if '\x00' in filename:
            raise ValueError("Null bytes not allowed")
        
        # Validate characters
        if not allow_paths and not self.FILENAME_PATTERN.match(filename):
            raise ValueError("Invalid filename characters")
        
        # Check for reserved names (Windows)
        if os.name == 'nt':
            reserved = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 
                       'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 
                       'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 
                       'LPT7', 'LPT8', 'LPT9'}
            name_upper = filename.upper().split('.')[0]
            if name_upper in reserved:
                raise ValueError(f"Reserved filename: {filename}")
        
        return filename
    
    def validate_html_content(self, content: str) -> str:
        """Validate HTML content for security issues."""
        # Check for script tags and other dangerous content
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',               # JavaScript URLs
            r'on\w+\s*=',                # Event handlers
            r'<iframe[^>]*>',            # Iframes
            r'<object[^>]*>',            # Objects
            r'<embed[^>]*>',             # Embeds
            r'<link[^>]*>',              # External links
        ]
        
        content_lower = content.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE | re.DOTALL):
                from core.exceptions import ValidationError
                raise ValidationError(f"Potentially dangerous HTML content detected: {pattern}")
        
        return content
    
    def validate_file_content(self, content: bytes, content_type: str) -> bytes:
        """Validate file content based on content type."""
        # Basic file content validation
        if not content:
            from core.exceptions import ValidationError
            raise ValidationError("Empty file content")
        
        # Check for very large files (basic DoS protection)
        if len(content) > 100 * 1024 * 1024:  # 100MB limit
            from core.exceptions import ValidationError
            raise ValidationError("File too large")
        
        # Define magic bytes for different file types
        magic_bytes = {
            'pdf': b'%PDF-',
            'jpg': b'\xFF\xD8\xFF',
            'png': b'\x89PNG\r\n\x1a\n',
            'zip': b'PK\x03\x04',
            'gif': b'GIF8',
        }
        
        # Content-type specific validation
        if content_type == 'application/pdf':
            # Check for PDF magic number
            if not content.startswith(magic_bytes['pdf']):
                from core.exceptions import ValidationError
                raise ValidationError("Invalid PDF file format")
            
            # Check for polyglot attacks - look for other file type magic bytes in the content
            for file_type, magic in magic_bytes.items():
                if file_type != 'pdf' and magic in content:
                    from core.exceptions import ValidationError
                    raise ValidationError("Potential polyglot file attack detected")
        
        return content
    
    def validate_template_directory(self, template_dir: str) -> bool:
        """
        Validate template directory exists and is accessible.
        
        From validation.py
        """
        try:
            tmpl_path = Path(template_dir).resolve()
            
            if not tmpl_path.exists():
                self._logger.warning(f"Template directory does not exist: {template_dir}")
                self._logger.info("Reports will use default templates")
                return False
            
            if not tmpl_path.is_dir():
                self._logger.error(f"Template path is not a directory: {template_dir}")
                return False
            
            if not os.access(tmpl_path, os.R_OK):
                self._logger.error(f"Cannot read template directory: {template_dir}")
                return False
            
            self._logger.info(f"Using template directory: {template_dir}")
            return True
            
        except Exception as e:
            self._logger.error(f"Template directory validation failed: {e}")
            return False
    
    # === CLI & Input Validation ===
    
    def validate_cli_arguments(self, args: Any) -> bool:
        """
        Validate command-line arguments for safety.
        
        From validation.py validate_cli_inputs
        """
        if hasattr(args, "root") and args.root:
            try:
                # Check for path traversal BEFORE resolving the path
                raw_path = str(args.root)
                if ".." in raw_path:
                    self._logger.error("Path traversal detected in root argument")
                    return False
                
                # Also check after resolution
                root_path = Path(args.root).expanduser().resolve()
                root_str = str(root_path)
                
                # Additional checks for resolved path
                if ".." in root_str:
                    self._logger.error("Path traversal detected in resolved root argument")
                    return False
                
                # Ensure reasonable path length
                if len(root_str) > 1000:
                    self._logger.error("Root path too long (potential attack)")
                    return False
                    
            except Exception as e:
                self._logger.error(f"Invalid root path: {args.root} ({e})")
                return False
        
        # Validate output file paths
        for output_arg in ["output", "csv_output"]:
            if hasattr(args, output_arg):
                output_path = getattr(args, output_arg, None)
                if output_path:
                    try:
                        # Check raw path first
                        if ".." in str(output_path):
                            self._logger.error(
                                f"Path traversal detected in {output_arg}: {output_path}"
                            )
                            return False
                        
                        out_path = Path(output_path).resolve()
                        out_str = str(out_path)
                        if ".." in out_str or len(out_str) > 500:
                            self._logger.error(f"Invalid output path: {output_path}")
                            return False
                    except Exception:
                        self._logger.error(f"Cannot resolve output path: {output_path}")
                        return False
        
        return True
    
    def validate_string(self, value: str, min_length: int = 0, max_length: int = 1000, 
                       allowed_chars: Optional[set] = None) -> str:
        """
        Validate and sanitize string input.
        
        From core/security/input_validation.py
        """
        if not isinstance(value, str):
            raise ValueError(f"Expected string, got {type(value).__name__}")
        
        # Check length
        if len(value) < min_length:
            raise ValueError(f"String too short (min: {min_length})")
        if len(value) > max_length:
            raise ValueError(f"String too long (max: {max_length})")
        
        # Check allowed characters
        if allowed_chars:
            invalid_chars = set(value) - allowed_chars
            if invalid_chars:
                raise ValueError(f"Invalid characters: {invalid_chars}")
        
        return value
    
    # === Network & Format Validation ===
    
    def validate_email(self, email: str) -> str:
        """Validate email address format."""
        email = email.strip().lower()
        
        # Check for control characters (header injection attacks)
        if any(ord(c) < 32 for c in email if c not in '\t'):
            from core.exceptions import ValidationError
            raise ValidationError("Email contains control characters")
        
        # Handle special cases like IP addresses and quoted strings
        # Basic structure check: has @ and reasonable length
        if '@' not in email or len(email) < 3 or len(email) > 254:
            raise ValueError(f"Invalid email address: {email}")
        
        # Split into local and domain parts
        local, domain = email.rsplit('@', 1)
        
        # Basic validation for local part
        if len(local) == 0 or len(local) > 64:
            raise ValueError(f"Invalid email address: {email}")
        
        # Check for spaces in local part (not allowed in standard email format)
        if ' ' in local and not (local.startswith('"') and local.endswith('"')):
            raise ValueError(f"Invalid email address: {email}")
        
        # Basic validation for domain part
        if len(domain) == 0 or len(domain) > 253:
            raise ValueError(f"Invalid email address: {email}")
        
        # Handle IP addresses in brackets [127.0.0.1] or [IPv6:...]
        if domain.startswith('[') and domain.endswith(']'):
            # IP address literal - basic validation
            ip_part = domain[1:-1]
            if ip_part.startswith('ipv6:'):
                # IPv6 - basic check
                ip_part = ip_part[5:]
            # For this validation service, we'll accept IP literals
            return email
        
        # For regular domains, ensure basic format (allow Unicode)
        if '..' in domain or domain.startswith('.') or domain.endswith('.'):
            raise ValueError(f"Invalid email address: {email}")
        
        # Check that domain has at least one dot (no exceptions)
        if '.' not in domain:
            raise ValueError(f"Invalid email address: {email}")
        
        return email
    
    def validate_url(self, url: str, allowed_schemes: List[str] = None, allow_internal: bool = True) -> str:
        """Validate URL format and scheme."""
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        url = url.strip()
        
        # Check for dangerous schemes first
        dangerous_schemes = ['javascript', 'data', 'vbscript', 'file', 'about']
        if any(url.lower().startswith(scheme + ':') for scheme in dangerous_schemes):
            from core.exceptions import ValidationError
            raise ValidationError(f"Dangerous URL scheme detected: {url}")
        
        # Check for protocol-relative URLs
        if url.startswith('//'):
            from core.exceptions import ValidationError
            raise ValidationError("Protocol-relative URLs not allowed")
        
        # Parse and validate components
        try:
            parsed = urlparse(url)
        except Exception:
            from core.exceptions import ValidationError
            raise ValidationError(f"Invalid URL format: {url}")
        
        # Validate scheme
        if not parsed.scheme:
            from core.exceptions import ValidationError
            raise ValidationError("URL missing scheme")
        
        if parsed.scheme not in allowed_schemes:
            raise ValueError(f"URL scheme not allowed: {parsed.scheme}")
        
        # Validate network location
        if not parsed.netloc:
            from core.exceptions import ValidationError
            raise ValidationError("URL missing network location")
        
        # Check for credential confusion attacks
        if '@' in parsed.netloc:
            # Check if @ is in the userinfo part (before the actual host)
            parts = parsed.netloc.split('@')
            if len(parts) > 2 or '%' in parts[0]:
                from core.exceptions import ValidationError
                raise ValidationError("Potential credential confusion attack")
        
        # Check for invalid ports
        try:
            if parsed.port:
                if parsed.port < 1 or parsed.port > 65535:
                    from core.exceptions import ValidationError
                    raise ValidationError(f"Invalid port number: {parsed.port}")
        except ValueError:
            # urlparse raises ValueError for invalid ports
            from core.exceptions import ValidationError
            raise ValidationError("Invalid port number in URL")
        
        # Check for localhost/internal IPs (if not allowed)
        if not allow_internal:
            netloc_lower = parsed.netloc.lower()
            if any(internal in netloc_lower for internal in ['localhost', '127.0.0.1', '[::1]', '0.0.0.0']):
                from core.exceptions import ValidationError
                raise ValidationError("Internal/localhost URLs not allowed")
        
        # Check for path traversal
        if parsed.path and ('..' in parsed.path or '\\' in parsed.path):
            from core.exceptions import ValidationError
            raise ValidationError("Path traversal detected in URL")
        
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
    
    # === Security Validation ===
    
    def validate_against_sql_injection(self, value: str) -> str:
        """Check for SQL injection patterns."""
        if self.SQL_INJECTION_PATTERN.search(value):
            raise ValueError("Potential SQL injection detected")
        
        # Escape single quotes
        return value.replace("'", "''")
    
    def validate_file_extension(self, filename: str, allowed_extensions: Optional[set] = None,
                               file_type: Optional[str] = None) -> str:
        """Validate file extension against allowed types."""
        if file_type and file_type in self.ALLOWED_EXTENSIONS:
            allowed_extensions = self.ALLOWED_EXTENSIONS[file_type]
        
        if not allowed_extensions:
            return filename
        
        ext = Path(filename).suffix.lower()
        if ext not in allowed_extensions:
            raise ValueError(
                f"File extension {ext} not allowed. "
                f"Allowed: {', '.join(sorted(allowed_extensions))}"
            )
        
        return filename
    
    def validate_file_size(self, size: int, max_size_mb: float = 100) -> int:
        """Validate file size constraints."""
        max_size_bytes = int(max_size_mb * 1024 * 1024)
        
        if size < 0:
            raise ValueError("File size cannot be negative")
        
        if size > max_size_bytes:
            raise ValueError(
                f"File too large: {size / 1024 / 1024:.1f}MB "
                f"(max: {max_size_mb}MB)"
            )
        
        return size
    
    # === Content & Mathematical Validation ===
    
    def detect_language(self, text: str) -> str:
        """
        Detect language of mathematical/academic text.
        
        From validators/validation_utils.py get_language
        """
        text_lower = text.lower()
        
        # Quick language detection based on indicators
        for lang, indicators in self.LANGUAGE_INDICATORS.items():
            if any(indicator in text_lower for indicator in indicators):
                self._logger.debug(f"Language detected as {lang} (keywords)")
                return lang
        
        # Try to use langdetect if available
        try:
            from langdetect import detect
            detected = detect(text)
            self._logger.debug(f"Language detected as: {detected}")
            return detected
        except ImportError:
            self._logger.debug("LangDetect library not available, defaulting to English")
            return "en"
        except Exception:
            self._logger.debug("Language detection failed, defaulting to English")
            return "en"
    
    def has_mathematical_content(self, text: str) -> bool:
        """Check if text contains mathematical notation."""
        return (
            bool(self.MATH_GREEK_PATTERN.search(text)) or
            bool(self.SUPERSCRIPT_PATTERN.search(text)) or
            bool(self.SUBSCRIPT_PATTERN.search(text)) or
            bool(self.MATH_SYMBOLS_PATTERN.search(text))
        )
    
    def validate_mathematician_name(self, name: str) -> bool:
        """
        Validate if name appears to be a mathematician.
        
        From validators/validation_utils.py mathematician validator
        """
        try:
            # Try to use mathematician name validator if available
            from src.validators.mathematician_name_validator import get_global_validator
            validator = get_global_validator()
            if validator:
                return validator.is_mathematician(name)
        except (ImportError, ModuleNotFoundError, AttributeError):
            pass
        
        # Fallback: basic name validation
        return bool(name and len(name.strip()) > 1 and name.replace(' ', '').isalpha())
    
    # === Configuration & Data Validation ===
    
    def validate_config(self, config: Dict[str, Any], schema: Optional[Dict] = None) -> List[str]:
        """Validate configuration against schema, return list of errors."""
        errors = []
        
        if schema is None:
            # Basic validation rules from existing code
            required_keys = ['database', 'logging']
            for key in required_keys:
                if key not in config:
                    errors.append(f"Missing required configuration key: {key}")
        else:
            # Schema-based validation (extensible)
            for key, rules in schema.items():
                if rules.get('required', False) and key not in config:
                    errors.append(f"Missing required key: {key}")
                
                if key in config:
                    value = config[key]
                    expected_type = rules.get('type')
                    if expected_type and not isinstance(value, expected_type):
                        errors.append(f"Key '{key}' should be {expected_type.__name__}, got {type(value).__name__}")
        
        return errors
    
    def validate_dict_structure(self, data: Dict[str, Any], required_keys: Optional[List[str]] = None,
                               optional_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """Validate dictionary structure and keys."""
        if not isinstance(data, dict):
            raise ValueError(f"Expected dictionary, got {type(data).__name__}")
        
        # Check for recursive structures
        self._check_for_recursion(data)
        
        # Check required keys
        if required_keys:
            missing = set(required_keys) - set(data.keys())
            if missing:
                raise ValueError(f"Missing required keys: {missing}")
        
        # Check for unknown keys
        if required_keys is not None or optional_keys is not None:
            allowed_keys = set(required_keys or []) | set(optional_keys or [])
            unknown = set(data.keys()) - allowed_keys
            if unknown:
                raise ValueError(f"Unknown keys: {unknown}")
        
        return data
    
    def _check_for_recursion(self, obj: Any, visited: Optional[set] = None) -> None:
        """Check for recursive structures in object."""
        if visited is None:
            visited = set()
        
        obj_id = id(obj)
        if obj_id in visited:
            from core.exceptions import ValidationError
            raise ValidationError("Recursive data structure detected")
        
        if isinstance(obj, dict):
            visited.add(obj_id)
            try:
                for value in obj.values():
                    if isinstance(value, (dict, list)):
                        self._check_for_recursion(value, visited)
            finally:
                visited.remove(obj_id)
        elif isinstance(obj, list):
            visited.add(obj_id)
            try:
                for item in obj:
                    if isinstance(item, (dict, list)):
                        self._check_for_recursion(item, visited)
            finally:
                visited.remove(obj_id)
    
    # === Numeric Validation ===
    
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