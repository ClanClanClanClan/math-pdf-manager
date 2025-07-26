"""
Custom exceptions for Math-PDF Manager

This module provides a hierarchy of exceptions for better error handling
and debugging throughout the application.
"""
from typing import Any, Optional, Dict
from pathlib import Path


class MathPDFError(Exception):
    """Base exception for Math-PDF Manager"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class ValidationError(MathPDFError):
    """Validation error with field-specific details"""
    
    def __init__(self, message: str, field: Optional[str] = None, 
                 value: Optional[Any] = None, suggestion: Optional[str] = None):
        super().__init__(message)
        self.field = field
        self.value = value
        self.suggestion = suggestion
        self.details = {
            'field': field,
            'value': str(value) if value is not None else None,
            'message': message,
            'suggestion': suggestion
        }


class FileOperationError(MathPDFError):
    """File operation error with context"""
    
    def __init__(self, message: str, path: Path, operation: str, 
                 error_code: Optional[int] = None):
        super().__init__(message)
        self.path = path
        self.operation = operation
        self.error_code = error_code
        self.details = {
            'path': str(path),
            'operation': operation,
            'error_code': error_code,
            'message': message
        }


class APIError(MathPDFError):
    """API error with response details"""
    
    def __init__(self, message: str, api_name: str, 
                 status_code: Optional[int] = None, 
                 response_body: Optional[str] = None,
                 request_id: Optional[str] = None):
        super().__init__(message)
        self.api_name = api_name
        self.status_code = status_code
        self.response_body = response_body
        self.request_id = request_id
        self.details = {
            'api': api_name,
            'status_code': status_code,
            'response': response_body,
            'request_id': request_id,
            'message': message
        }


class ConfigurationError(MathPDFError):
    """Configuration error"""
    
    def __init__(self, message: str, config_key: Optional[str] = None,
                 config_file: Optional[str] = None):
        super().__init__(message)
        self.config_key = config_key
        self.config_file = config_file
        self.details = {
            'config_key': config_key,
            'config_file': config_file,
            'message': message
        }


class ResourceError(MathPDFError):
    """Resource management error"""
    
    def __init__(self, message: str, resource_type: str,
                 resource_id: Optional[str] = None):
        super().__init__(message)
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.details = {
            'resource_type': resource_type,
            'resource_id': resource_id,
            'message': message
        }


class ParseError(MathPDFError):
    """Parsing error with location info"""
    
    def __init__(self, message: str, line_number: Optional[int] = None,
                 column: Optional[int] = None, context: Optional[str] = None):
        super().__init__(message)
        self.line_number = line_number
        self.column = column
        self.context = context
        self.details = {
            'line': line_number,
            'column': column,
            'context': context,
            'message': message
        }


class DuplicateError(MathPDFError):
    """Duplicate detection error"""
    
    def __init__(self, message: str, original_path: Path, 
                 duplicate_path: Path, similarity: float):
        super().__init__(message)
        self.original_path = original_path
        self.duplicate_path = duplicate_path
        self.similarity = similarity
        self.details = {
            'original': str(original_path),
            'duplicate': str(duplicate_path),
            'similarity': similarity,
            'message': message
        }


class SecurityError(MathPDFError):
    """Security-related error"""
    
    def __init__(self, message: str, threat_type: str,
                 severity: str = "high"):
        super().__init__(message)
        self.threat_type = threat_type
        self.severity = severity
        self.details = {
            'threat_type': threat_type,
            'severity': severity,
            'message': message
        }