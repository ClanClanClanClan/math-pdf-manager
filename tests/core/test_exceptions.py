#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive tests for core.exceptions module
"""

import pytest
from pathlib import Path
from core.exceptions import (
    MathPDFError,
    ValidationError,
    FileOperationError,
    APIError,
    ConfigurationError,
    ResourceError,
    ParseError,
    DuplicateError,
    SecurityError
)


class TestMathPDFError:
    """Test base MathPDFError exception"""
    
    def test_basic_creation(self):
        """Test basic exception creation"""
        error = MathPDFError("Test error message")
        assert str(error) == "Test error message"
        assert error.details == {}
    
    def test_with_details(self):
        """Test exception with details"""
        details = {"code": 123, "context": "testing"}
        error = MathPDFError("Test error", details)
        assert str(error) == "Test error"
        assert error.details == details
    
    def test_inheritance(self):
        """Test that it inherits from Exception"""
        error = MathPDFError("Test")
        assert isinstance(error, Exception)
        assert isinstance(error, MathPDFError)


class TestValidationError:
    """Test ValidationError exception"""
    
    def test_basic_creation(self):
        """Test basic validation error"""
        error = ValidationError("Invalid field")
        assert str(error) == "Invalid field"
        assert error.field is None
        assert error.value is None
        assert error.suggestion is None
    
    def test_with_field_and_value(self):
        """Test with field and value"""
        error = ValidationError("Invalid email", field="email", value="invalid@")
        assert str(error) == "Invalid email"
        assert error.field == "email"
        assert error.value == "invalid@"
        assert error.suggestion is None
        
        expected_details = {
            'field': 'email',
            'value': 'invalid@',
            'message': 'Invalid email',
            'suggestion': None
        }
        assert error.details == expected_details
    
    def test_with_suggestion(self):
        """Test with suggestion"""
        error = ValidationError(
            "Invalid format", 
            field="title", 
            value="bad title",
            suggestion="Use sentence case"
        )
        assert error.suggestion == "Use sentence case"
        assert error.details['suggestion'] == "Use sentence case"
    
    def test_none_value_handling(self):
        """Test None value is handled correctly"""
        error = ValidationError("Empty field", field="name", value=None)
        assert error.details['value'] is None
    
    def test_inheritance(self):
        """Test inheritance from MathPDFError"""
        error = ValidationError("Test")
        assert isinstance(error, MathPDFError)
        assert isinstance(error, ValidationError)


class TestFileOperationError:
    """Test FileOperationError exception"""
    
    def test_basic_creation(self):
        """Test basic file operation error"""
        path = Path("/test/file.pdf")
        error = FileOperationError("Cannot read file", path, "read")
        
        assert str(error) == "Cannot read file"
        assert error.path == path
        assert error.operation == "read"
        assert error.error_code is None
        
        expected_details = {
            'path': '/test/file.pdf',
            'operation': 'read',
            'error_code': None,
            'message': 'Cannot read file'
        }
        assert error.details == expected_details
    
    def test_with_error_code(self):
        """Test with error code"""
        path = Path("/test/file.pdf")
        error = FileOperationError("Permission denied", path, "write", error_code=13)
        
        assert error.error_code == 13
        assert error.details['error_code'] == 13
    
    def test_inheritance(self):
        """Test inheritance from MathPDFError"""
        error = FileOperationError("Test", Path("/test"), "test")
        assert isinstance(error, MathPDFError)
        assert isinstance(error, FileOperationError)


class TestAPIError:
    """Test APIError exception"""
    
    def test_basic_creation(self):
        """Test basic API error"""
        error = APIError("API call failed", "CrossRef")
        
        assert str(error) == "API call failed"
        assert error.api_name == "CrossRef"
        assert error.status_code is None
        assert error.response_body is None
        assert error.request_id is None
        
        expected_details = {
            'api': 'CrossRef',
            'status_code': None,
            'response': None,
            'request_id': None,
            'message': 'API call failed'
        }
        assert error.details == expected_details
    
    def test_with_all_fields(self):
        """Test with all optional fields"""
        error = APIError(
            "Server error",
            api_name="ArXiv",
            status_code=500,
            response_body='{"error": "Internal server error"}',
            request_id="req-123"
        )
        
        assert error.status_code == 500
        assert error.response_body == '{"error": "Internal server error"}'
        assert error.request_id == "req-123"
        assert error.details['status_code'] == 500
        assert error.details['request_id'] == "req-123"
    
    def test_inheritance(self):
        """Test inheritance from MathPDFError"""
        error = APIError("Test", "TestAPI")
        assert isinstance(error, MathPDFError)
        assert isinstance(error, APIError)


class TestConfigurationError:
    """Test ConfigurationError exception"""
    
    def test_basic_creation(self):
        """Test basic configuration error"""
        error = ConfigurationError("Invalid configuration")
        
        assert str(error) == "Invalid configuration"
        assert error.config_key is None
        assert error.config_file is None
        
        expected_details = {
            'config_key': None,
            'config_file': None,
            'message': 'Invalid configuration'
        }
        assert error.details == expected_details
    
    def test_with_key_and_file(self):
        """Test with config key and file"""
        error = ConfigurationError(
            "Missing required setting",
            config_key="database.url",
            config_file="config.yaml"
        )
        
        assert error.config_key == "database.url"
        assert error.config_file == "config.yaml"
        assert error.details['config_key'] == "database.url"
        assert error.details['config_file'] == "config.yaml"
    
    def test_inheritance(self):
        """Test inheritance from MathPDFError"""
        error = ConfigurationError("Test")
        assert isinstance(error, MathPDFError)
        assert isinstance(error, ConfigurationError)


class TestResourceError:
    """Test ResourceError exception"""
    
    def test_basic_creation(self):
        """Test basic resource error"""
        error = ResourceError("Resource not available", "database")
        
        assert str(error) == "Resource not available"
        assert error.resource_type == "database"
        assert error.resource_id is None
        
        expected_details = {
            'resource_type': 'database',
            'resource_id': None,
            'message': 'Resource not available'
        }
        assert error.details == expected_details
    
    def test_with_resource_id(self):
        """Test with resource ID"""
        error = ResourceError(
            "Connection failed",
            resource_type="cache",
            resource_id="redis-001"
        )
        
        assert error.resource_id == "redis-001"
        assert error.details['resource_id'] == "redis-001"
    
    def test_inheritance(self):
        """Test inheritance from MathPDFError"""
        error = ResourceError("Test", "test")
        assert isinstance(error, MathPDFError)
        assert isinstance(error, ResourceError)


class TestParseError:
    """Test ParseError exception"""
    
    def test_basic_creation(self):
        """Test basic parse error"""
        error = ParseError("Syntax error")
        
        assert str(error) == "Syntax error"
        assert error.line_number is None
        assert error.column is None
        assert error.context is None
        
        expected_details = {
            'line': None,
            'column': None,
            'context': None,
            'message': 'Syntax error'
        }
        assert error.details == expected_details
    
    def test_with_location_info(self):
        """Test with location information"""
        error = ParseError(
            "Unexpected token",
            line_number=42,
            column=15,
            context="author: 'John Doe"
        )
        
        assert error.line_number == 42
        assert error.column == 15
        assert error.context == "author: 'John Doe"
        assert error.details['line'] == 42
        assert error.details['column'] == 15
        assert error.details['context'] == "author: 'John Doe"
    
    def test_inheritance(self):
        """Test inheritance from MathPDFError"""
        error = ParseError("Test")
        assert isinstance(error, MathPDFError)
        assert isinstance(error, ParseError)


class TestDuplicateError:
    """Test DuplicateError exception"""
    
    def test_creation(self):
        """Test duplicate error creation"""
        original = Path("/docs/paper1.pdf")
        duplicate = Path("/docs/paper1_copy.pdf")
        similarity = 0.95
        
        error = DuplicateError(
            "Duplicate detected",
            original_path=original,
            duplicate_path=duplicate,
            similarity=similarity
        )
        
        assert str(error) == "Duplicate detected"
        assert error.original_path == original
        assert error.duplicate_path == duplicate
        assert error.similarity == similarity
        
        expected_details = {
            'original': '/docs/paper1.pdf',
            'duplicate': '/docs/paper1_copy.pdf',
            'similarity': 0.95,
            'message': 'Duplicate detected'
        }
        assert error.details == expected_details
    
    def test_inheritance(self):
        """Test inheritance from MathPDFError"""
        error = DuplicateError("Test", Path("/a"), Path("/b"), 0.8)
        assert isinstance(error, MathPDFError)
        assert isinstance(error, DuplicateError)


class TestSecurityError:
    """Test SecurityError exception"""
    
    def test_basic_creation(self):
        """Test basic security error"""
        error = SecurityError("Potential security threat", "path_traversal")
        
        assert str(error) == "Potential security threat"
        assert error.threat_type == "path_traversal"
        assert error.severity == "high"  # default
        
        expected_details = {
            'threat_type': 'path_traversal',
            'severity': 'high',
            'message': 'Potential security threat'
        }
        assert error.details == expected_details
    
    def test_with_custom_severity(self):
        """Test with custom severity level"""
        error = SecurityError(
            "Suspicious activity",
            threat_type="injection",
            severity="medium"
        )
        
        assert error.severity == "medium"
        assert error.details['severity'] == "medium"
    
    def test_inheritance(self):
        """Test inheritance from MathPDFError"""
        error = SecurityError("Test", "test")
        assert isinstance(error, MathPDFError)
        assert isinstance(error, SecurityError)


class TestExceptionHierarchy:
    """Test exception hierarchy and relationships"""
    
    def test_all_inherit_from_base(self):
        """Test that all exceptions inherit from MathPDFError"""
        exceptions = [
            ValidationError("test"),
            FileOperationError("test", Path("/test"), "test"),
            APIError("test", "test"),
            ConfigurationError("test"),
            ResourceError("test", "test"),
            ParseError("test"),
            DuplicateError("test", Path("/a"), Path("/b"), 0.5),
            SecurityError("test", "test")
        ]
        
        for exc in exceptions:
            assert isinstance(exc, MathPDFError)
            assert isinstance(exc, Exception)
    
    def test_exception_catching(self):
        """Test that specific exceptions can be caught as base type"""
        try:
            raise ValidationError("Test validation error")
        except MathPDFError as e:
            assert isinstance(e, ValidationError)
            assert str(e) == "Test validation error"
        
        try:
            raise FileOperationError("Test file error", Path("/test"), "read")
        except MathPDFError as e:
            assert isinstance(e, FileOperationError)
            assert str(e) == "Test file error"
    
    def test_details_attribute_consistency(self):
        """Test that all exceptions have consistent details attribute"""
        # Base exception doesn't auto-add message, but subclasses do
        base_exc = MathPDFError("test")
        assert hasattr(base_exc, 'details')
        assert isinstance(base_exc.details, dict)
        
        # All specific exceptions should have message in details
        specific_exceptions = [
            ValidationError("test", field="field"),
            FileOperationError("test", Path("/test"), "test"),
            APIError("test", "test"),
            ConfigurationError("test"),
            ResourceError("test", "test"),
            ParseError("test"),
            DuplicateError("test", Path("/a"), Path("/b"), 0.5),
            SecurityError("test", "test")
        ]
        
        for exc in specific_exceptions:
            assert hasattr(exc, 'details')
            assert isinstance(exc.details, dict)
            assert 'message' in exc.details
            assert exc.details['message'] == "test"


class TestEdgeCases:
    """Test edge cases and special scenarios"""
    
    def test_empty_message(self):
        """Test with empty message"""
        error = MathPDFError("")
        assert str(error) == ""
        assert error.details == {}
    
    def test_unicode_message(self):
        """Test with Unicode characters in message"""
        message = "Error with Unicode: αβγ 数学 🚀"
        error = MathPDFError(message)
        assert str(error) == message
    
    def test_long_message(self):
        """Test with very long message"""
        long_message = "x" * 10000
        error = MathPDFError(long_message)
        assert str(error) == long_message
    
    def test_special_characters_in_paths(self):
        """Test file operations with special characters in paths"""
        special_path = Path("/test/file with spaces & symbols!@#.pdf")
        error = FileOperationError("Test error", special_path, "read")
        assert error.details['path'] == str(special_path)
    
    def test_none_details_handling(self):
        """Test None details handling in base exception"""
        error = MathPDFError("Test", None)
        assert error.details == {}
    
    def test_numeric_values_in_validation_error(self):
        """Test numeric values in validation error"""
        error = ValidationError("Invalid number", field="age", value=42)
        assert error.details['value'] == "42"  # Should be converted to string
        
        error2 = ValidationError("Invalid float", field="rate", value=3.14)
        assert error2.details['value'] == "3.14"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])