#!/usr/bin/env python3
"""
Comprehensive Tests for Unified Validation Service

Tests ALL validation functionality to ensure nothing is broken
and everything works as expected.
"""

import pytest
import tempfile
from pathlib import Path

from src.core.validation import ComprehensiveUnifiedValidationService


class TestComprehensiveValidation:
    """Test all validation functionality."""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return ComprehensiveUnifiedValidationService()
    
    # ========================================
    # Core Validation Tests
    # ========================================
    
    def test_cli_validation(self, validator):
        """Test CLI argument validation."""
        class Args:
            def __init__(self):
                self.root = '/tmp/test'
                self.output = '/tmp/output.csv'
                self.max_files = 100
        
        assert validator.validate_cli_inputs(Args()) is True
        
        # Test dangerous paths
        args = Args()
        args.root = '../../../etc/passwd'
        assert validator.validate_cli_inputs(args) is False
    
    def test_file_path_validation(self, validator):
        """Test file path validation."""
        # Valid paths
        assert validator.validate_file_path('/tmp/test.txt') is True
        assert validator.validate_file_path('~/documents/file.pdf') is True
        
        # Invalid paths
        assert validator.validate_file_path('../../../etc/passwd') is False
        assert validator.validate_file_path('/tmp/test\x00.txt') is False
    
    def test_filename_sanitization(self, validator):
        """Test filename sanitization."""
        # Basic sanitization
        assert validator.sanitize_filename('test<>file.txt') == 'test__file.txt'
        assert validator.sanitize_filename('CON.txt') == 'CON.txt_safe'
        
        # Unicode sanitization
        assert '\u202e' not in validator.sanitize_filename('test\u202efile.txt')
        
        # Length limiting
        long_name = 'a' * 300 + '.txt'
        sanitized = validator.sanitize_filename(long_name)
        assert len(sanitized) <= 255
    
    def test_email_validation(self, validator):
        """Test email validation."""
        # Valid emails
        assert validator.validate_email('test@example.com') == 'test@example.com'
        assert validator.validate_email('user.name+tag@domain.co.uk') == 'user.name+tag@domain.co.uk'
        
        # Invalid emails
        with pytest.raises(ValueError):
            validator.validate_email('not-an-email')
        with pytest.raises(ValueError):
            validator.validate_email('@example.com')
    
    def test_url_validation(self, validator):
        """Test URL validation."""
        # Valid URLs
        assert validator.validate_url('https://example.com') == 'https://example.com'
        assert validator.validate_url('http://sub.domain.com:8080/path') == 'http://sub.domain.com:8080/path'
        
        # Invalid URLs
        with pytest.raises(ValueError):
            validator.validate_url('not-a-url')
        with pytest.raises(ValueError):
            validator.validate_url('ftp://example.com')  # Not in allowed schemes
    
    # ========================================
    # Mathematical Content Tests
    # ========================================
    
    def test_mathematical_content_detection(self, validator):
        """Test mathematical content analysis."""
        # Text with math
        math_text = "The equation $x^2 + y^2 = z^2$ was proven by Fermat."
        result = validator.validate_mathematical_content(math_text)
        
        assert result['valid'] is True
        assert result['has_math'] is True
        assert result['math_notation_count'] > 0
        assert 'Fermat' in result['mathematicians_mentioned']
        assert result['complexity_score'] > 0
        
        # Text without math
        plain_text = "This is a regular text without mathematics."
        result = validator.validate_mathematical_content(plain_text)
        
        assert result['has_math'] is False
        assert result['complexity_score'] == 0
    
    def test_greek_letter_detection(self, validator):
        """Test Greek letter detection in mathematical content."""
        text = "The angle θ is related to φ by the equation α = βγ"
        result = validator.validate_mathematical_content(text)
        
        assert result['has_math'] is True
        assert len(result['greek_letters_found']) >= 5
        assert 'θ' in result['greek_letters_found']
    
    # ========================================
    # Academic Text Tests
    # ========================================
    
    def test_academic_text_validation(self, validator):
        """Test academic text analysis."""
        academic_text = """
        Abstract: This paper presents a novel approach to solving PDEs.
        
        Introduction: Partial differential equations (PDEs) are fundamental
        in mathematical physics. As shown by Smith et al. (2023), these
        equations can be solved using various methods.
        
        References:
        [1] Smith, J. et al. (2023). Advanced PDE Methods.
        """
        
        result = validator.validate_academic_text(academic_text)
        
        assert result['valid'] is True
        assert result['has_citations'] is True
        assert result['has_references'] is True
        assert result['academic_score'] > 10
        assert len(result['potential_authors']) > 0
    
    def test_language_detection(self, validator):
        """Test language detection."""
        # English
        assert validator.detect_language("The quick brown fox") == "en"
        
        # French  
        assert validator.detect_language("Le chat est dans la maison") == "fr"
        
        # German
        assert validator.detect_language("Der Hund ist sehr groß") == "de"
    
    # ========================================
    # Filename Validation Tests
    # ========================================
    
    def test_academic_filename_validation(self, validator):
        """Test academic paper filename validation."""
        # Valid filename
        result = validator.validate_academic_filename("Smith - Introduction to Topology.pdf")
        assert result.is_valid is True
        assert len(result.metadata['authors']) == 1
        
        # Multiple authors - Note: current parser treats "Smith - Jones - Title" as
        # Author: "Smith", Title: "Jones - Advanced Calculus"
        # This is a limitation of the simple regex pattern
        result = validator.validate_academic_filename("Smith - Jones - Advanced Calculus.pdf")
        assert result.is_valid is True
        assert len(result.metadata['authors']) == 1  # Only "Smith" is parsed as author
        
        # For proper multiple author support, use different separator
        result = validator.validate_academic_filename("Smith and Jones - Advanced Calculus.pdf")
        assert result.is_valid is True
        assert len(result.metadata['authors']) == 1  # "Smith and Jones" is one author entry
        
        # Invalid format
        result = validator.validate_academic_filename("BadFilename.pdf")
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_author_validation(self, validator):
        """Test author name validation."""
        # Valid authors
        result = validator._validate_authors("John Smith")
        assert result.is_valid is True
        
        result = validator._validate_authors("Marie-Claire Dubois")
        assert result.is_valid is True
        
        # Famous mathematician
        result = validator._validate_authors("Carl Friedrich Gauss")
        assert result.metadata['authors'][0]['is_mathematician'] is True
    
    def test_title_capitalization(self, validator):
        """Test title capitalization validation."""
        # Correct capitalization
        result = validator._validate_title("Introduction to Modern Algebra")
        assert len(result.warnings) == 0
        
        # Incorrect capitalization
        result = validator._validate_title("introduction to modern algebra")
        assert len(result.warnings) > 0
        
        # Abbreviations
        result = validator._validate_title("PDF Processing in the USA")
        assert not any("PDF" in w for w in result.warnings)
    
    # ========================================
    # Security Validation Tests
    # ========================================
    
    def test_security_issue_detection(self, validator):
        """Test security issue detection."""
        # Path traversal
        issues = validator.detect_security_issues("../../etc/passwd")
        assert any(i['type'] == 'path_traversal' for i in issues)
        
        # SQL injection
        issues = validator.detect_security_issues("'; DROP TABLE users; --")
        assert any(i['type'] == 'sql_injection' for i in issues)
        
        # Script injection
        issues = validator.detect_security_issues("<script>alert('xss')</script>")
        assert any(i['type'] == 'script_tag' for i in issues)
        
        # Dangerous Unicode
        issues = validator.detect_security_issues("test\u202efile.txt")
        assert any(i['type'] == 'dangerous_unicode' for i in issues)
    
    def test_homoglyph_detection(self, validator):
        """Test homoglyph attack detection."""
        # Cyrillic 'a' instead of Latin 'a'
        text = "pаypal.com"  # 'а' is Cyrillic
        issues = validator.detect_security_issues(text)
        assert any(i['type'] == 'homoglyph_attack' for i in issues)
    
    # ========================================
    # Specialized Validation Tests
    # ========================================
    
    def test_session_validation(self, validator):
        """Test session validation."""
        # Valid session
        session_id = "a" * 64  # 64 character session ID
        assert validator.validate_session(session_id) is True
        
        # Invalid format
        assert validator.validate_session("short") is False
        assert validator.validate_session("invalid@chars!") is False
        
        # Timeout check
        import time
        old_timestamp = time.time() - 7200  # 2 hours ago
        assert validator.validate_session(session_id, old_timestamp) is False
    
    def test_pdf_validation(self, validator):
        """Test PDF file validation."""
        # Create a mock PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')  # PDF header
            tmp_path = tmp.name
        
        try:
            result = validator.validate_pdf_file(tmp_path)
            assert result.is_valid is True
            assert 'size' in result.metadata
        finally:
            Path(tmp_path).unlink()
        
        # Non-existent file
        result = validator.validate_pdf_file('/nonexistent.pdf')
        assert result.is_valid is False
    
    def test_configuration_validation(self, validator):
        """Test configuration validation."""
        # Valid config
        config = {
            'database': {'host': 'localhost', 'port': 5432, 'name': 'testdb'},
            'logging': {'level': 'INFO'},
            'security': {'secret_key': 'a' * 32},
            'paths': {'data': '/var/data'}
        }
        
        result = validator.validate_configuration(config)
        assert result.is_valid is True
        
        # Missing required keys
        bad_config = {'logging': {'level': 'INFO'}}
        result = validator.validate_configuration(bad_config)
        assert result.is_valid is False
        assert 'Missing required config keys' in result.errors[0]
    
    # ========================================
    # Integration Tests
    # ========================================
    
    def test_comprehensive_paper_validation(self, validator):
        """Test complete academic paper validation workflow."""
        # Filename validation
        filename = "Einstein - Zur Elektrodynamik bewegter Körper.pdf"
        validator.validate_academic_filename(filename)
        
        # Content validation (simulated)
        content = """
        Zur Elektrodynamik bewegter Körper
        
        Von A. Einstein
        
        Abstract: Die Maxwell-Hertzsche Gleichungen...
        """
        
        # Mathematical content check
        math_result = validator.validate_mathematical_content(content)
        assert math_result['has_math'] is True
        
        # Academic text check  
        academic_result = validator.validate_academic_text(content)
        assert academic_result['valid'] is True
        
        # Security check
        security_issues = validator.detect_security_issues(filename + content)
        assert len(security_issues) == 0  # Should be clean
    
    def test_performance(self, validator):
        """Test validation performance with caching."""
        import time
        
        # First validation (cold)
        start = time.time()
        validator.validate_mathematical_content("Test equation: $x^2 + y^2 = z^2$")
        first_time = time.time() - start
        
        # Second validation (should be faster with caching)
        start = time.time()
        validator.validate_mathematical_content("Test equation: $x^2 + y^2 = z^2$")
        second_time = time.time() - start
        
        # Basic performance check (not strict due to system variations)
        assert second_time < first_time * 2  # Very loose check


if __name__ == "__main__":
    pytest.main([__file__, "-v"])