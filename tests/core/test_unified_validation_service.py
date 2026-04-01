#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive tests for UnifiedValidationService

Tests the consolidation of all validation systems:
- CLI argument validation (from validators.core_validation.py)
- Security validation (from utils/security.py and core/security/input_validation.py)
- Mathematical content validation (from validators/validation_utils.py)
- Filename and path validation
"""

import pytest
import os
import tempfile
from pathlib import Path
from argparse import Namespace

from core.dependency_injection.validation_service import UnifiedValidationService


class MockLoggingService:
    """Mock logging service for testing"""
    
    def __init__(self):
        self.logs = []
    
    def debug(self, message: str, **kwargs) -> None:
        self.logs.append(('debug', message, kwargs))
    
    def info(self, message: str, **kwargs) -> None:
        self.logs.append(('info', message, kwargs))
    
    def warning(self, message: str, **kwargs) -> None:
        self.logs.append(('warning', message, kwargs))
    
    def error(self, message: str, **kwargs) -> None:
        self.logs.append(('error', message, kwargs))


class TestUnifiedValidationService:
    """Test unified validation service functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.mock_logger = MockLoggingService()
        self.validator = UnifiedValidationService(self.mock_logger)
        self.temp_dir = Path(tempfile.mkdtemp())
        self.base_dir = self.temp_dir / "base"
        self.base_dir.mkdir(exist_ok=True)
        
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestPathAndFileValidation(TestUnifiedValidationService):
    """Test path and file validation consolidation"""
    
    def test_validate_file_path_success(self):
        """Test successful path validation"""
        # Create a file within the base directory
        test_file = self.base_dir / "test.txt"
        test_file.touch()
        
        # Use absolute path within base directory, allowing symlinks for macOS filesystem
        result = self.validator.validate_file_path(test_file, self.base_dir, allow_symlinks=True)
        assert isinstance(result, Path)
        # Should resolve to an absolute path
        assert result.is_absolute()
        # Should be within base directory (accounting for symlinks)
        try:
            result.resolve().relative_to(self.base_dir.resolve())
            # If this succeeds, the path is within base directory
            assert True
        except ValueError:
            # If relative_to fails, check if paths share common root
            assert str(self.base_dir.resolve()) in str(result.resolve()) or str(result.resolve()) in str(self.base_dir.resolve())
    
    def test_validate_file_path_traversal_attack(self):
        """Test path traversal detection"""
        from core.exceptions import SecurityError
        
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "subdir/../../../etc/passwd"
        ]
        
        for malicious_path in malicious_paths:
            with pytest.raises(SecurityError):
                self.validator.validate_file_path(malicious_path, self.base_dir)
    
    def test_validate_file_path_unicode_attack(self):
        """Test Unicode normalization attack detection"""
        from core.exceptions import SecurityError
        
        unicode_attacks = [
            "file\u2025txt",  # Two dot leader
            "file\u2026txt",  # Horizontal ellipsis
            "file\uff0etxt",  # Fullwidth full stop
        ]
        
        for attack_path in unicode_attacks:
            with pytest.raises(SecurityError):
                self.validator.validate_file_path(attack_path, self.base_dir)
    
    def test_validate_file_path_symlink_rejection(self):
        """Test symlink rejection when not allowed"""
        if os.name != 'nt':  # Skip on Windows
            target_file = self.base_dir / "target.txt"
            target_file.touch()
            
            symlink_path = self.base_dir / "symlink.txt"
            symlink_path.symlink_to("target.txt")
            
            from core.exceptions import SecurityError
            with pytest.raises(SecurityError):
                self.validator.validate_file_path(symlink_path, self.base_dir, allow_symlinks=False)
    
    def test_validate_filename_safe(self):
        """Test safe filename validation"""
        safe_filenames = [
            "document.pdf",
            "file_with_underscores.txt",
            "123-numbers.doc"
        ]
        
        for filename in safe_filenames:
            result = self.validator.validate_filename(filename)
            assert result == filename
    
    def test_validate_filename_dangerous(self):
        """Test dangerous filename rejection"""
        dangerous_filenames = [
            "../parent.txt",
            "subdir/file.txt",
            "file\\windows.txt",
            "file\x00null.txt"
        ]
        
        for filename in dangerous_filenames:
            with pytest.raises(ValueError):
                self.validator.validate_filename(filename)
    
    def test_validate_template_directory_success(self):
        """Test template directory validation"""
        template_dir = self.temp_dir / "templates"
        template_dir.mkdir()
        
        result = self.validator.validate_template_directory(str(template_dir))
        assert result is True
    
    def test_validate_template_directory_missing(self):
        """Test template directory validation with missing directory"""
        missing_dir = self.temp_dir / "nonexistent"
        
        result = self.validator.validate_template_directory(str(missing_dir))
        assert result is False


class TestCLIValidation(TestUnifiedValidationService):
    """Test CLI argument validation consolidation"""
    
    def test_validate_cli_arguments_success(self):
        """Test successful CLI argument validation"""
        args = Namespace()
        args.root = str(self.base_dir)
        args.output = "output.txt"
        
        result = self.validator.validate_cli_arguments(args)
        assert result is True
    
    def test_validate_cli_arguments_path_traversal(self):
        """Test CLI argument validation with path traversal"""
        args = Namespace()
        args.root = "../../../etc/passwd"
        
        result = self.validator.validate_cli_arguments(args)
        assert result is False
    
    def test_validate_cli_arguments_long_path(self):
        """Test CLI argument validation with excessively long path"""
        args = Namespace()
        args.root = "a" * 1001  # Exceeds 1000 character limit
        
        result = self.validator.validate_cli_arguments(args)
        assert result is False
    
    def test_validate_string_success(self):
        """Test string validation"""
        result = self.validator.validate_string("valid string", min_length=5, max_length=20)
        assert result == "valid string"
    
    def test_validate_string_length_constraints(self):
        """Test string validation with length constraints"""
        # Too short
        with pytest.raises(ValueError):
            self.validator.validate_string("hi", min_length=5)
        
        # Too long
        with pytest.raises(ValueError):
            self.validator.validate_string("a" * 1001, max_length=1000)
    
    def test_validate_string_allowed_chars(self):
        """Test string validation with character constraints"""
        allowed_chars = set('abcdefghijklmnopqrstuvwxyz ')
        
        # Valid
        result = self.validator.validate_string("hello world", allowed_chars=allowed_chars)
        assert result == "hello world"
        
        # Invalid characters
        with pytest.raises(ValueError):
            self.validator.validate_string("hello@world", allowed_chars=allowed_chars)


class TestNetworkFormatValidation(TestUnifiedValidationService):
    """Test network and format validation consolidation"""
    
    def test_validate_email_success(self):
        """Test email validation"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org"
        ]
        
        for email in valid_emails:
            result = self.validator.validate_email(email)
            assert result == email.strip().lower()
    
    def test_validate_email_invalid(self):
        """Test email validation with invalid emails"""
        invalid_emails = [
            "invalid",
            "@domain.com",
            "user@",
            "user@domain",  # Missing TLD
            "user@.com",    # Missing domain
            "user space@domain.com"  # Space in local part
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValueError):
                self.validator.validate_email(email)
    
    def test_validate_url_success(self):
        """Test URL validation"""
        valid_urls = [
            "https://example.com",
            "http://localhost:8080",
            "https://sub.domain.com/path?param=value"
        ]
        
        for url in valid_urls:
            result = self.validator.validate_url(url)
            assert result == url.strip()
    
    def test_validate_url_invalid_scheme(self):
        """Test URL validation with invalid schemes"""
        with pytest.raises(ValueError):
            self.validator.validate_url("ftp://example.com", allowed_schemes=['http', 'https'])
    
    def test_validate_ip_address_success(self):
        """Test IP address validation"""
        valid_ips = [
            ("192.168.1.1", None),
            ("127.0.0.1", 4),
            ("::1", 6),
            ("2001:db8::1", 6)
        ]
        
        for ip, version in valid_ips:
            result = self.validator.validate_ip_address(ip, version)
            assert result == ip
    
    def test_validate_ip_address_invalid(self):
        """Test IP address validation with invalid addresses"""
        invalid_ips = [
            "256.256.256.256",
            "not.an.ip.address",
            "192.168.1",
            "::1::2"
        ]
        
        for ip in invalid_ips:
            with pytest.raises(ValueError):
                self.validator.validate_ip_address(ip)


class TestSecurityValidation(TestUnifiedValidationService):
    """Test security validation consolidation"""
    
    def test_validate_against_sql_injection_safe(self):
        """Test SQL injection validation with safe strings"""
        safe_strings = [
            "normal text",
            "user input with numbers 123",
            "text with apostrophe's"
        ]
        
        for safe_string in safe_strings:
            result = self.validator.validate_against_sql_injection(safe_string)
            # Should escape single quotes
            assert result == safe_string.replace("'", "''")
    
    def test_validate_against_sql_injection_dangerous(self):
        """Test SQL injection validation with dangerous patterns"""
        dangerous_strings = [
            "'; DROP TABLE users; --",
            "1 OR 1=1; DELETE FROM users",
            "UNION SELECT * FROM passwords"
        ]
        
        for dangerous_string in dangerous_strings:
            with pytest.raises(ValueError):
                self.validator.validate_against_sql_injection(dangerous_string)
    
    def test_validate_file_extension_success(self):
        """Test file extension validation"""
        result = self.validator.validate_file_extension("document.pdf", file_type="document")
        assert result == "document.pdf"
    
    def test_validate_file_extension_invalid(self):
        """Test file extension validation with invalid extensions"""
        with pytest.raises(ValueError):
            self.validator.validate_file_extension("malicious.exe", file_type="document")
    
    def test_validate_file_size_success(self):
        """Test file size validation"""
        result = self.validator.validate_file_size(1024 * 1024, max_size_mb=2)  # 1MB
        assert result == 1024 * 1024
    
    def test_validate_file_size_too_large(self):
        """Test file size validation with oversized file"""
        with pytest.raises(ValueError):
            self.validator.validate_file_size(200 * 1024 * 1024, max_size_mb=100)  # 200MB > 100MB limit


class TestMathematicalContentValidation(TestUnifiedValidationService):
    """Test mathematical content validation consolidation"""
    
    def test_detect_language_keywords(self):
        """Test language detection using mathematical keywords"""
        test_cases = [
            ("théorie des nombres", "fr"),
            ("einführung in die mathematik", "de"),
            ("introducción a las matemáticas", "es")
        ]
        
        for text, expected_lang in test_cases:
            result = self.validator.detect_language(text)
            assert result == expected_lang
    
    def test_detect_language_fallback(self):
        """Test language detection fallback"""
        # Test with text that has no specific language indicators
        # Should fallback to langdetect, and if that fails, to English
        result = self.validator.detect_language("unknown random text xyz")
        # Should either detect a language or fallback to English
        assert result in ["en", "de", "fr", "es"] or len(result) == 2  # Valid language codes
    
    def test_has_mathematical_content_greek(self):
        """Test mathematical content detection with Greek letters"""
        math_texts = [
            "Let α be a real number",
            "The function θ(x) = sin(x)",
            "Probability Ω space"
        ]
        
        for text in math_texts:
            assert self.validator.has_mathematical_content(text)
    
    def test_has_mathematical_content_symbols(self):
        """Test mathematical content detection with symbols"""
        math_texts = [
            "x² + y² = r²",  # Superscripts
            "H₂O molecule",   # Subscripts
            "∀x ∈ ℝ",        # Mathematical symbols
            "∫f(x)dx = F(x)" # Integral symbol
        ]
        
        for text in math_texts:
            assert self.validator.has_mathematical_content(text)
    
    def test_has_mathematical_content_regular_text(self):
        """Test mathematical content detection with regular text"""
        regular_texts = [
            "This is normal text",
            "No mathematical content here",
            "Just regular English words"
        ]
        
        for text in regular_texts:
            assert not self.validator.has_mathematical_content(text)
    
    def test_validate_mathematician_name_basic(self):
        """Test mathematician name validation"""
        valid_names = [
            "Albert Einstein",
            "Isaac Newton",
            "Marie Curie"
        ]
        
        for name in valid_names:
            assert self.validator.validate_mathematician_name(name)
    
    def test_validate_mathematician_name_invalid(self):
        """Test mathematician name validation with invalid names"""
        invalid_names = [
            "",
            "123",
            "a",
            "user@domain.com"
        ]
        
        for name in invalid_names:
            assert not self.validator.validate_mathematician_name(name)


class TestConfigurationValidation(TestUnifiedValidationService):
    """Test configuration and data validation consolidation"""
    
    def test_validate_config_basic(self):
        """Test basic configuration validation"""
        valid_config = {
            "database": {"host": "localhost"},
            "logging": {"level": "INFO"}
        }
        
        errors = self.validator.validate_config(valid_config)
        assert len(errors) == 0
    
    def test_validate_config_missing_keys(self):
        """Test configuration validation with missing keys"""
        invalid_config = {
            "database": {"host": "localhost"}
            # Missing 'logging' key
        }
        
        errors = self.validator.validate_config(invalid_config)
        assert len(errors) > 0
        assert any("logging" in error for error in errors)
    
    def test_validate_config_with_schema(self):
        """Test configuration validation with schema"""
        config = {
            "database": {"host": "localhost"},
            "port": 8080
        }
        
        schema = {
            "database": {"required": True, "type": dict},
            "port": {"required": True, "type": int},
            "optional_field": {"required": False, "type": str}
        }
        
        errors = self.validator.validate_config(config, schema)
        assert len(errors) == 0
    
    def test_validate_config_schema_type_mismatch(self):
        """Test configuration validation with type mismatches"""
        config = {
            "database": "not_a_dict",  # Should be dict
            "port": "not_an_int"       # Should be int
        }
        
        schema = {
            "database": {"required": True, "type": dict},
            "port": {"required": True, "type": int}
        }
        
        errors = self.validator.validate_config(config, schema)
        assert len(errors) >= 2  # Should have type errors
    
    def test_validate_dict_structure_success(self):
        """Test dictionary structure validation"""
        data = {
            "required_key": "value",
            "optional_key": "value"
        }
        
        result = self.validator.validate_dict_structure(
            data,
            required_keys=["required_key"],
            optional_keys=["optional_key", "another_optional"]
        )
        assert result == data
    
    def test_validate_dict_structure_missing_required(self):
        """Test dictionary structure validation with missing required keys"""
        data = {
            "optional_key": "value"
        }
        
        with pytest.raises(ValueError):
            self.validator.validate_dict_structure(
                data,
                required_keys=["required_key"]
            )
    
    def test_validate_dict_structure_unknown_keys(self):
        """Test dictionary structure validation with unknown keys"""
        data = {
            "required_key": "value",
            "unknown_key": "value"
        }
        
        with pytest.raises(ValueError):
            self.validator.validate_dict_structure(
                data,
                required_keys=["required_key"],
                optional_keys=[]
            )


class TestNumericValidation(TestUnifiedValidationService):
    """Test numeric validation consolidation"""
    
    def test_validate_integer_success(self):
        """Test integer validation"""
        test_cases = [
            ("123", 123),
            (456, 456),
            ("0", 0),
            ("-42", -42)
        ]
        
        for input_value, expected in test_cases:
            result = self.validator.validate_integer(input_value)
            assert result == expected
    
    def test_validate_integer_with_bounds(self):
        """Test integer validation with bounds"""
        result = self.validator.validate_integer(50, min_value=0, max_value=100)
        assert result == 50
    
    def test_validate_integer_invalid_type(self):
        """Test integer validation with invalid types"""
        invalid_values = [
            "not_a_number",
            "12.34",
            None,
            []
        ]
        
        for invalid_value in invalid_values:
            with pytest.raises(ValueError):
                self.validator.validate_integer(invalid_value)
    
    def test_validate_integer_out_of_bounds(self):
        """Test integer validation with out-of-bounds values"""
        # Too small
        with pytest.raises(ValueError):
            self.validator.validate_integer(-5, min_value=0)
        
        # Too large
        with pytest.raises(ValueError):
            self.validator.validate_integer(150, max_value=100)


class TestValidationServiceIntegration(TestUnifiedValidationService):
    """Test validation service integration with DI framework"""
    
    def test_service_registration(self):
        """Test that the service registers correctly with DI container"""
        from core.dependency_injection import get_container
        from core.dependency_injection.interfaces import IValidationService
        
        container = get_container()
        
        # Should be able to resolve the validation service
        service = container.resolve(IValidationService)
        assert service is not None
        assert isinstance(service, UnifiedValidationService)
    
    def test_service_singleton_behavior(self):
        """Test that the validation service is a singleton"""
        from core.dependency_injection import get_container
        from core.dependency_injection.interfaces import IValidationService
        
        container = get_container()
        
        service1 = container.resolve(IValidationService)
        service2 = container.resolve(IValidationService)
        
        assert service1 is service2  # Should be the same instance
    
    def test_dependency_injection_logging(self):
        """Test that logging service is properly injected"""
        # The service should have a logger
        assert hasattr(self.validator, '_logger')
        assert self.validator._logger is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])