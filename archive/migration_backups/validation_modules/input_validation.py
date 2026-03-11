#!/usr/bin/env python3
"""
Input Validation and Security Module
Provides comprehensive input validation and sanitization
"""

import re
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Pattern, TypeVar
from urllib.parse import urlparse
import ipaddress
import mimetypes

T = TypeVar('T')


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class InputValidator:
    """Comprehensive input validation utilities."""
    
    # Compiled regex patterns for performance
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._\-\s]+$')
    SQL_INJECTION_PATTERN = re.compile(
        r'(\b(union|select|insert|update|delete|drop|create|alter|exec|execute|script|javascript)\b)',
        re.IGNORECASE
    )
    
    # Safe characters for different contexts
    SAFE_CHARS = {
        'filename': set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._- '),
        'username': set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-@'),
        'alphanumeric': set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'),
    }
    
    @classmethod
    def validate_string(
        cls, 
        value: Any, 
        min_length: int = 0, 
        max_length: int = 1000,
        allowed_chars: Optional[set] = None,
        pattern: Optional[Pattern] = None
    ) -> str:
        """
        Validate and sanitize string input.
        
        Args:
            value: Input value
            min_length: Minimum allowed length
            max_length: Maximum allowed length
            allowed_chars: Set of allowed characters
            pattern: Regex pattern to match
            
        Returns:
            Validated string
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, str):
            raise ValidationError(f"Expected string, got {type(value).__name__}")
        
        # Check length
        if len(value) < min_length:
            raise ValidationError(f"String too short (min: {min_length})")
        if len(value) > max_length:
            raise ValidationError(f"String too long (max: {max_length})")
        
        # Check allowed characters
        if allowed_chars:
            invalid_chars = set(value) - allowed_chars
            if invalid_chars:
                raise ValidationError(f"Invalid characters: {invalid_chars}")
        
        # Check pattern
        if pattern and not pattern.match(value):
            raise ValidationError("String does not match required pattern")
        
        return value
    
    @classmethod
    def validate_email(cls, email: str) -> str:
        """Validate email address."""
        email = email.strip().lower()
        if not cls.EMAIL_PATTERN.match(email):
            raise ValidationError(f"Invalid email address: {email}")
        return email
    
    @classmethod
    def validate_url(cls, url: str, allowed_schemes: List[str] = ['http', 'https']) -> str:
        """
        Validate URL.
        
        Args:
            url: URL to validate
            allowed_schemes: Allowed URL schemes
            
        Returns:
            Validated URL
        """
        url = url.strip()
        
        # Basic pattern check
        if not cls.URL_PATTERN.match(url):
            raise ValidationError(f"Invalid URL format: {url}")
        
        # Parse and validate components
        parsed = urlparse(url)
        
        if parsed.scheme not in allowed_schemes:
            raise ValidationError(f"URL scheme not allowed: {parsed.scheme}")
        
        if not parsed.netloc:
            raise ValidationError("URL missing network location")
        
        return url
    
    @classmethod
    def validate_filename(cls, filename: str, allow_paths: bool = False) -> str:
        """
        Validate filename for security.
        
        Args:
            filename: Filename to validate
            allow_paths: Whether to allow path separators
            
        Returns:
            Validated filename
        """
        if not filename:
            raise ValidationError("Filename cannot be empty")
        
        # Check for path traversal attempts
        if '..' in filename:
            raise ValidationError("Path traversal detected")
        
        # Check for absolute paths
        if os.path.isabs(filename):
            raise ValidationError("Absolute paths not allowed")
        
        # If paths not allowed, check for separators
        if not allow_paths and ('/' in filename or '\\' in filename):
            raise ValidationError("Path separators not allowed")
        
        # Validate characters
        if not allow_paths and not cls.FILENAME_PATTERN.match(filename):
            raise ValidationError("Invalid filename characters")
        
        return filename
    
    @classmethod
    def validate_path(cls, path: Union[str, Path], base_path: Optional[Path] = None) -> Path:
        """
        Validate file path for security.
        
        Args:
            path: Path to validate
            base_path: Base path for relative validation
            
        Returns:
            Validated Path object
        """
        path = Path(path)
        
        # Resolve to absolute path
        try:
            resolved_path = path.resolve()
        except (OSError, RuntimeError):
            raise ValidationError(f"Invalid path: {path}")
        
        # Check if within base path
        if base_path:
            base_path = Path(base_path).resolve()
            try:
                resolved_path.relative_to(base_path)
            except ValueError:
                raise ValidationError(f"Path outside allowed directory: {path}")
        
        return resolved_path
    
    @classmethod
    def validate_integer(
        cls, 
        value: Any, 
        min_value: Optional[int] = None, 
        max_value: Optional[int] = None
    ) -> int:
        """Validate integer input."""
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid integer: {value}")
        
        if min_value is not None and int_value < min_value:
            raise ValidationError(f"Value too small (min: {min_value})")
        
        if max_value is not None and int_value > max_value:
            raise ValidationError(f"Value too large (max: {max_value})")
        
        return int_value
    
    @classmethod
    def validate_ip_address(cls, ip: str, version: Optional[int] = None) -> str:
        """
        Validate IP address.
        
        Args:
            ip: IP address to validate
            version: IP version (4 or 6), None for both
        """
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            if version == 4 and not isinstance(ip_obj, ipaddress.IPv4Address):
                raise ValidationError(f"Expected IPv4 address, got IPv6")
            elif version == 6 and not isinstance(ip_obj, ipaddress.IPv6Address):
                raise ValidationError(f"Expected IPv6 address, got IPv4")
            
            return str(ip_obj)
        except ValueError:
            raise ValidationError(f"Invalid IP address: {ip}")
    
    @classmethod
    def sanitize_for_sql(cls, value: str) -> str:
        """
        Sanitize string for SQL queries.
        
        Note: This is a basic sanitization. Use parameterized queries instead!
        """
        # Check for SQL injection patterns
        if cls.SQL_INJECTION_PATTERN.search(value):
            raise ValidationError("Potential SQL injection detected")
        
        # Escape single quotes
        return value.replace("'", "''")
    
    @classmethod
    def validate_mime_type(cls, mime_type: str, allowed_types: Optional[List[str]] = None) -> str:
        """Validate MIME type."""
        mime_type = mime_type.strip().lower()
        
        # Check if it's a valid MIME type format
        if '/' not in mime_type:
            raise ValidationError(f"Invalid MIME type format: {mime_type}")
        
        # Check against allowed types
        if allowed_types and mime_type not in allowed_types:
            raise ValidationError(f"MIME type not allowed: {mime_type}")
        
        return mime_type
    
    @classmethod
    def validate_dict(
        cls, 
        data: Any, 
        required_keys: Optional[List[str]] = None,
        optional_keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate dictionary structure.
        
        Args:
            data: Dictionary to validate
            required_keys: Keys that must be present
            optional_keys: Keys that are allowed but not required
            
        Returns:
            Validated dictionary
        """
        if not isinstance(data, dict):
            raise ValidationError(f"Expected dictionary, got {type(data).__name__}")
        
        # Check required keys
        if required_keys:
            missing = set(required_keys) - set(data.keys())
            if missing:
                raise ValidationError(f"Missing required keys: {missing}")
        
        # Check for unknown keys
        if required_keys is not None or optional_keys is not None:
            allowed_keys = set(required_keys or []) | set(optional_keys or [])
            unknown = set(data.keys()) - allowed_keys
            if unknown:
                raise ValidationError(f"Unknown keys: {unknown}")
        
        return data


class SecureFileHandler:
    """Secure file operations with validation."""
    
    ALLOWED_EXTENSIONS = {
        'document': {'.pdf', '.txt', '.md', '.tex', '.doc', '.docx'},
        'image': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'},
        'data': {'.json', '.yaml', '.yml', '.csv', '.xml'},
    }
    
    @classmethod
    def validate_file_extension(
        cls, 
        filename: str, 
        allowed_extensions: Optional[set] = None,
        file_type: Optional[str] = None
    ) -> str:
        """
        Validate file extension.
        
        Args:
            filename: Filename to check
            allowed_extensions: Set of allowed extensions
            file_type: Type category from ALLOWED_EXTENSIONS
        """
        if file_type and file_type in cls.ALLOWED_EXTENSIONS:
            allowed_extensions = cls.ALLOWED_EXTENSIONS[file_type]
        
        if not allowed_extensions:
            return filename
        
        ext = Path(filename).suffix.lower()
        if ext not in allowed_extensions:
            raise ValidationError(
                f"File extension {ext} not allowed. "
                f"Allowed: {', '.join(sorted(allowed_extensions))}"
            )
        
        return filename
    
    @classmethod
    def validate_file_size(cls, size: int, max_size_mb: float = 100) -> int:
        """Validate file size."""
        max_size_bytes = int(max_size_mb * 1024 * 1024)
        
        if size < 0:
            raise ValidationError("File size cannot be negative")
        
        if size > max_size_bytes:
            raise ValidationError(
                f"File too large: {size / 1024 / 1024:.1f}MB "
                f"(max: {max_size_mb}MB)"
            )
        
        return size