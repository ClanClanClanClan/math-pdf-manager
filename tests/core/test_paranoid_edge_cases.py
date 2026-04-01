#!/usr/bin/env python3
"""
Paranoid Edge Case Tests

Tests for extreme edge cases that could break the system.
Focuses on boundary conditions, resource limits, and unusual inputs.
"""

import os
import sys
import gc
import time
import threading
import tempfile
import mmap
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import concurrent.futures
from unittest.mock import Mock
import pytest

# Import modules to test
from core.exceptions import (
    ValidationError, ConfigurationError
)
from core.models import (
    Author, PDFMetadata, ValidationSeverity, ValidationIssue
)
from core.dependency_injection import DIContainer
from core.dependency_injection.container import FactorySecurityConfig, TimeoutError
from core.dependency_injection.validation_service import UnifiedValidationService
from utils.security import (
    PathValidator
)
# Only import what's needed from secure credential manager
try:
    from src.secure_credential_manager import SecureCredentialManager, CredentialSource
except ImportError:
    SecureCredentialManager = None
    CredentialSource = None


class TestExceptionEdgeCases:
    """Paranoid tests for exception handling edge cases."""
    
    def test_exception_memory_bomb(self):
        """Test exceptions containing massive data."""
        # Create exception with large message (but not so large it fails)
        large_message = "x" * (1024 * 1024)  # 1MB string
        
        # Should be able to create the exception without crashing
        try:
            exc = ValidationError(large_message)
            # Verify the exception was created
            assert str(exc) == large_message
            assert len(str(exc)) == 1024 * 1024
        except MemoryError:
            # If we do get a memory error, that's acceptable for this test
            pass
    
    def test_exception_circular_reference(self):
        """Test exceptions with circular references."""
        exc1 = ValidationError("Error 1")
        exc2 = ConfigurationError("Error 2")
        
        # Create circular reference
        exc1.__cause__ = exc2
        exc2.__cause__ = exc1
        
        # Should not cause infinite loop when stringified
        str(exc1)
        repr(exc1)
        
        # Cleanup
        exc1.__cause__ = None
        exc2.__cause__ = None
        gc.collect()
    
    def test_exception_deep_nesting(self):
        """Test deeply nested exception chains."""
        current = ValidationError("Base")
        
        # Create deep chain (reduced for CI performance)
        for i in range(100):  # Reduced from 1,000 to 100
            new_exc = ValidationError(f"Level {i}")
            new_exc.__cause__ = current
            current = new_exc
        
        # Should handle deep chains without stack overflow
        str(current)
        
        # Cleanup
        current = None
        gc.collect()
    
    def test_exception_malicious_attributes(self):
        """Test exceptions with malicious attribute access."""
        class EvilException(Exception):
            @property
            def message(self):
                # Malicious property that could cause issues
                os.system("echo 'should not execute'")
                return "evil"
            
            def __str__(self):
                # Could try to access files
                try:
                    with open("/etc/passwd", "r") as f:
                        return f.read()
                except:  # noqa: E722
                    return "failed"
        
        exc = EvilException()
        # Should safely handle without executing malicious code
        try:
            str(exc)
        except:  # noqa: E722
            pass
    
    def test_exception_unicode_edge_cases(self):
        """Test exceptions with problematic Unicode."""
        unicode_nightmares = [
            "\U0001F4A9" * 1000,  # Emoji spam
            "\u200b" * 10000,  # Zero-width spaces
            "\ufeff" * 1000,  # BOMs
            "A" + "\u0301" * 100,  # Combining characters
            "\u202e" + "Hello",  # Right-to-left override
            "\ud800",  # Unpaired surrogate
            "\U00100000",  # Outside BMP
        ]
        
        for nightmare in unicode_nightmares:
            try:
                raise ValidationError(nightmare)
            except ValidationError as e:
                # Should handle without crashing
                str(e)
                repr(e)


class TestModelEdgeCases:
    """Paranoid tests for model edge cases."""
    
    def test_author_name_attacks(self):
        """Test Author model with malicious names."""
        attack_names = [
            "';DROP TABLE authors;--",  # SQL injection
            "<script>alert('xss')</script>",  # XSS
            "\\x00\\x01\\x02",  # Control characters
            "A" * 10000,  # Very long name
            "",  # Empty name
            None,  # None value
            123,  # Wrong type
            ["list", "of", "names"],  # Wrong type
            {"name": "dict"},  # Wrong type
            "name\nwith\nnewlines",  # Newlines
            "name\twith\ttabs",  # Tabs
            "../../etc/passwd",  # Path traversal
            "Robert'); INSERT INTO admins VALUES ('hacker",  # SQL injection variant
        ]
        
        for name in attack_names:
            try:
                if isinstance(name, str):
                    author = Author(name=name)
                    # Should sanitize or handle gracefully
                    assert isinstance(author.name, str)
                else:
                    # Should reject non-string types
                    with pytest.raises((TypeError, ValidationError)):
                        Author(name=name)
            except Exception as e:
                # Should not expose system details
                assert "/etc/passwd" not in str(e)
                assert "DROP TABLE" not in str(e)
    
    def test_pdfmetadata_path_boundaries(self):
        """Test PDFMetadata with boundary path values."""
        boundary_paths = [
            "/" + "a" * 255,  # Max filename length
            "/" + "dir/" * 100 + "file.pdf",  # Deep nesting
            "/file" + ".pdf" * 1000,  # Many extensions
            "/\x00file.pdf",  # Null byte
            "/file\uFEFFname.pdf",  # BOM character
            "//double//slashes//file.pdf",  # Double slashes
            "/file name with spaces.pdf",  # Spaces
            "/file%20name%20encoded.pdf",  # URL encoding
            "/[file]{with}(special)chars.pdf",  # Special chars
            "/😀📄🎉.pdf",  # Emojis
            "C:\\Windows\\Style\\Path.pdf",  # Windows path on Unix
            "\\\\UNC\\Share\\file.pdf",  # UNC path
        ]
        
        for path in boundary_paths:
            try:
                metadata = PDFMetadata(path=path, title="Test")
                # Path should be sanitized
                assert isinstance(metadata.path, str)
                # Should not contain null bytes
                assert "\x00" not in metadata.path
            except Exception:
                # Some paths might be rejected, which is fine
                pass
    
    def test_pdfmetadata_massive_authors(self):
        """Test PDFMetadata with excessive author string."""
        # Create large author string (reduced for CI performance)
        authors_list = []
        for i in range(1000):  # Reduced from 10,000 to 1,000
            authors_list.append(f"Author {i}")
        
        massive_authors = "; ".join(authors_list)
        
        # Should handle large strings
        metadata = PDFMetadata(
            title="Test",
            authors=massive_authors,
            path="/test.pdf"
        )
        assert len(metadata.authors) > 10000  # Large string (reduced with test optimization)
        
        # Test with potential memory issues
        import dataclasses
        metadata_dict = dataclasses.asdict(metadata)
        assert "authors" in metadata_dict
        
        # Cleanup
        authors_list.clear()
        metadata = None
        gc.collect()
    
    def test_validation_issue_severity_edge_cases(self):
        """Test ValidationIssue with edge case severities."""
        # Test enum boundaries
        for severity in ValidationSeverity:
            issue = ValidationIssue(
                severity=severity,
                category="test",
                message="Test message"
            )
            assert issue.severity == severity
        
        # Test invalid severity (dataclasses don't enforce types at runtime)
        issue = ValidationIssue(
            severity="INVALID_SEVERITY",
            category="test", 
            message="Test"
        )
        # Invalid severity is stored as-is (Python doesn't enforce dataclass types)
        assert issue.severity == "INVALID_SEVERITY"
        # But we can detect it's not a valid enum value
        assert not isinstance(issue.severity, ValidationSeverity)
    
    def test_model_property_bombs(self):
        """Test models with property access bombs."""
        class BombModel:
            @property
            def title(self):
                # Property that consumes resources
                time.sleep(0.1)  # Reduced from 10s to 0.1s for CI performance
                return "bomb"
            
            @property
            def authors(self):
                # Property that creates massive data (reduced for CI performance)
                return [Author(name=f"Author {i}") for i in range(10000)]  # Reduced from 1M to 10K
        
        model = BombModel()
        
        # Should timeout or handle gracefully
        with pytest.raises((TimeoutError, concurrent.futures.TimeoutError)):
            with ThreadPoolExecutor() as executor:
                future = executor.submit(lambda: model.title)
                future.result(timeout=0.05)  # Even shorter timeout


class TestDependencyInjectionEdgeCases:
    """Paranoid tests for dependency injection edge cases."""
    
    @pytest.mark.slow
    def test_container_memory_exhaustion(self):
        """Test container behavior under memory pressure."""
        container = DIContainer()
        
        class MemoryHog:
            def __init__(self):
                self.data = bytearray(1 * 1024 * 1024)  # 1MB per instance (reduced for CI)
        
        # Register as transient (new instance each time)
        container.register_transient(MemoryHog, MemoryHog)
        
        # Try to allocate reasonable amount (reduced for CI performance)
        instances = []
        try:
            for _ in range(100):  # Would be 100MB instead of 10GB
                instances.append(container.resolve(MemoryHog))
        except MemoryError:
            # Should handle gracefully
            pass
        
        # Cleanup
        instances.clear()
        gc.collect()
    
    def test_container_circular_dependency_variants(self):
        """Test various circular dependency patterns."""
        container = DIContainer()
        
        # Pattern 1: Direct circular reference
        class ServiceA:
            def __init__(self, b: 'ServiceB'):
                self.b = b
        
        class ServiceB:
            def __init__(self, a: ServiceA):
                self.a = a
        
        container.register_transient(ServiceA, ServiceA)
        container.register_transient(ServiceB, ServiceB)
        
        with pytest.raises(ValueError):  # Circular dependency detection
            container.resolve(ServiceA)
        
        # Pattern 2: Indirect circular reference
        class ServiceX:
            def __init__(self, y: 'ServiceY'):
                self.y = y
        
        class ServiceY:
            def __init__(self, z: 'ServiceZ'):
                self.z = z
        
        class ServiceZ:
            def __init__(self, x: ServiceX):
                self.x = x
        
        container.register_transient(ServiceX, ServiceX)
        container.register_transient(ServiceY, ServiceY)
        container.register_transient(ServiceZ, ServiceZ)
        
        with pytest.raises(ValueError):  # Circular dependency detection
            container.resolve(ServiceX)
    
    @pytest.mark.slow
    def test_container_thread_safety_stress(self):
        """Stress test container thread safety."""
        container = DIContainer()
        results = []
        errors = []
        
        class Counter:
            count = 0
            lock = threading.Lock()
            
            def __init__(self):
                with Counter.lock:
                    Counter.count += 1
                    self.id = Counter.count
        
        container.register_singleton(Counter, Counter)
        
        def resolve_many(n):
            try:
                local_results = []
                for _ in range(n):
                    instance = container.resolve(Counter)
                    local_results.append(instance.id)
                return local_results
            except Exception as e:
                errors.append(e)
                return []
        
        # Test container from multiple threads (reduced for CI performance)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(resolve_many, 20) for _ in range(10)]
            for future in futures:
                results.extend(future.result())
        
        # All results should be 1 (same singleton)
        assert all(r == 1 for r in results)
        assert len(errors) == 0
        assert Counter.count == 1
    
    def test_container_malicious_factories(self):
        """Test container with malicious factory functions."""
        # Configure shorter timeout for testing
        test_security_config = FactorySecurityConfig(
            execution_timeout=2.0,  # 2 second timeout for tests
            enable_circuit_breaker=True,
            enable_execution_logging=False  # Reduce noise in test output
        )
        container = DIContainer(test_security_config)
        
        # Factory that modifies global state
        def evil_factory():
            os.environ['PWNED'] = 'true'
            return Mock()
        
        # Factory that never returns
        def infinite_factory():
            while True:
                time.sleep(0.01)  # Much shorter sleep for testing
        
        # Factory that raises different exceptions
        call_count = 0
        def unstable_factory():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First call")
            elif call_count == 2:
                raise TypeError("Second call")
            else:
                return Mock()
        
        container.register_factory('evil', evil_factory)
        container.register_factory('infinite', infinite_factory)
        container.register_factory('unstable', unstable_factory)
        
        # Should handle malicious factories
        original_env = os.environ.get('PWNED')
        try:
            container.resolve('evil')
            # Should not modify environment
            assert os.environ.get('PWNED') == original_env
        finally:
            if 'PWNED' in os.environ:
                del os.environ['PWNED']
        
        # Should timeout on infinite factories with proper security protection
        with pytest.raises(ValueError, match="Factory execution timed out"):
            container.resolve('infinite')
        
        # Should handle unstable factories
        with pytest.raises(ValueError):
            container.resolve('unstable')
        with pytest.raises(TypeError):
            container.resolve('unstable')
        
        # Circuit breaker should now be active due to repeated failures
        with pytest.raises(ValueError, match="circuit broken"):
            container.resolve('unstable')
        
        # Test manual reset and successful execution
        assert container.reset_factory_circuit_breaker('unstable')
        instance = container.resolve('unstable')  # Third call should work after reset
        assert instance is not None
        
        # Test factory metrics
        metrics = container.get_factory_metrics('infinite')
        assert metrics is not None
        assert metrics.total_timeouts > 0
        
        unstable_metrics = container.get_factory_metrics('unstable')
        assert unstable_metrics is not None
        assert unstable_metrics.total_failures >= 2  # At least two failures before success
        
        # Test infinite factory circuit breaker  
        for _ in range(2):  # Trigger more timeouts
            try:
                container.resolve('infinite')
            except ValueError:
                pass
        
        # Circuit breaker should now be active for infinite factory
        metrics = container.get_factory_metrics('infinite')
        assert metrics.is_circuit_breaker_active()
        
        # Should be blocked by circuit breaker
        with pytest.raises(ValueError, match="circuit broken"):
            container.resolve('infinite')
        
        # Test manual circuit breaker reset
        assert container.reset_factory_circuit_breaker('infinite')
        metrics = container.get_factory_metrics('infinite')
        assert not metrics.is_circuit_breaker_active()
        
        # Test that all security features worked correctly
        all_metrics = container.get_all_factory_metrics()
        assert len(all_metrics) == 3  # evil, infinite, unstable
        assert 'infinite' in all_metrics
        assert 'unstable' in all_metrics
        assert 'evil' in all_metrics
        
        # Verify security protections worked
        assert all_metrics['infinite'].total_timeouts > 0  # DoS protection worked
        assert all_metrics['unstable'].total_failures > 0  # Exception handling worked
        # Environment protection for evil factory was tested above


class TestValidationServiceEdgeCases:
    """Paranoid tests for validation service edge cases."""
    
    def test_validation_recursive_structures(self):
        """Test validation of recursive data structures."""
        from unittest.mock import Mock
        logging_service = Mock()
        service = UnifiedValidationService(logging_service)
        
        # Create recursive dictionary
        recursive_dict = {}
        recursive_dict['self'] = recursive_dict
        
        # Should detect and handle recursion
        with pytest.raises(ValidationError):
            service.validate_dict_structure(recursive_dict)
    
    def test_validation_massive_inputs(self):
        """Test validation with massive inputs."""
        from unittest.mock import Mock
        logging_service = Mock()
        service = UnifiedValidationService(logging_service)
        
        # Massive string
        huge_string = "a" * (1024 * 1024 * 100)  # 100MB
        
        # Should handle or reject efficiently
        start_time = time.time()
        try:
            service.validate_file_content(huge_string.encode(), 'text/plain')
        except:  # noqa: E722
            pass
        elapsed = time.time() - start_time
        
        # Should not take too long (DoS prevention)
        assert elapsed < 1.0
    
    @pytest.mark.slow
    def test_validation_timing_attacks(self):
        """Test validation doesn't leak info through timing."""
        from unittest.mock import Mock
        logging_service = Mock()
        service = UnifiedValidationService(logging_service)
        
        # Test password validation timing
        passwords = [
            "a" * 8,  # Min length
            "a" * 7,  # Too short
            "ValidPass123!",  # Good password
            "ValidPass123",  # Missing special char
            "validpass123!",  # Missing uppercase
            "VALIDPASS123!",  # Missing lowercase
        ]
        
        timings = {}
        for password in passwords:
            times = []
            for _ in range(100):
                start = time.perf_counter()
                try:
                    service.validate_password_strength(password)
                except:  # noqa: E722
                    pass
                times.append(time.perf_counter() - start)
            timings[password] = sum(times) / len(times)
        
        # All timings should be similar
        avg_timing = sum(timings.values()) / len(timings)
        for password, timing in timings.items():
            variance = abs(timing - avg_timing) / avg_timing
            assert variance < 0.3  # Within 30% variance
    
    def test_validation_polyglot_attacks(self):
        """Test validation of polyglot payloads."""
        from unittest.mock import Mock
        logging_service = Mock()
        service = UnifiedValidationService(logging_service)
        
        # Payload that's valid in multiple contexts
        polyglot = '<script>alert(1)</script><!--<?php system($_GET["cmd"]); ?>-->'
        
        # Should be rejected or sanitized
        with pytest.raises(ValidationError):
            service.validate_html_content(polyglot)
        
        # File that looks like multiple types
        magic_bytes = {
            'pdf': b'%PDF-1.4',
            'jpg': b'\xFF\xD8\xFF',
            'png': b'\x89PNG\r\n\x1a\n',
            'zip': b'PK\x03\x04',
        }
        
        # Combine multiple magic bytes
        polyglot_file = magic_bytes['pdf'] + magic_bytes['jpg']
        
        # Should detect confusion
        with pytest.raises(ValidationError):
            service.validate_file_content(polyglot_file, 'application/pdf')


class TestSecurityModuleEdgeCases:
    """Paranoid tests for security module edge cases."""
    
    def test_path_sanitization_advanced(self):
        """Test advanced path sanitization edge cases."""
        advanced_attacks = [
            "test\x00../../etc/passwd",  # Null byte injection
            "test%00../../etc/passwd",  # URL encoded null
            "test\r\n../../etc/passwd",  # CRLF injection
            "test%0d%0a../../etc/passwd",  # URL encoded CRLF
            "....//....//etc/passwd",  # Variation
            "test/../" * 100 + "etc/passwd",  # Deep traversal
            "/test/./././../../../etc/passwd",  # Current dir confusion
            "test/..namedfolder/../../../etc/passwd",  # Fake folder
            "\\test\\..\\..\\..\\windows\\system32",  # Windows style
            "test/..%2f..%2f..%2fetc%2fpasswd",  # Mixed encoding
            "test/..%252f..%252fetc%252fpasswd",  # Double encoding
            "/var/www/html/uploads/../../../etc/passwd",  # Realistic path
        ]
        
        for attack in advanced_attacks:
            try:
                result = PathValidator.validate_path(attack, base_dir=Path("/safe"))
                # Should never allow traversal
                assert ".." not in str(result)
                assert "etc/passwd" not in str(result)
                assert "windows\\system32" not in str(result)
            except Exception:
                # Some attacks should be rejected
                pass
    
    def test_email_validation_edge_cases(self):
        """Test email validation with edge cases."""
        # Get validation service
        from unittest.mock import Mock
        logging_service = Mock()
        service = UnifiedValidationService(logging_service)
        
        edge_emails = [
            "a@b.c",  # Minimal valid
            "test@[127.0.0.1]",  # IP address
            "test@[IPv6:2001:db8::1]",  # IPv6
            '"quoted"@example.com',  # Quoted local
            "user+tag@example.com",  # Plus addressing
            "test@sub.sub.sub.example.com",  # Deep subdomain
            "1234567890" * 6 + "@example.com",  # Long local
            "test@" + "sub." * 50 + "example.com",  # Many subdomains
            "test@example." + "a" * 63,  # Max TLD length
            "tëst@example.com",  # Unicode local
            "test@exämple.com",  # Unicode domain
            "test@example.com\r\nBcc: attacker@evil.com",  # Header injection
        ]
        
        for email in edge_emails:
            try:
                result = service.validate_email(email)
                # Should not contain injection attempts
                assert "\r" not in result
                assert "\n" not in result
            except ValidationError:
                # Some emails should be rejected
                pass
    
    def test_url_validation_attacks(self):
        """Test URL validation against attacks."""
        # Get validation service
        from unittest.mock import Mock
        logging_service = Mock()
        service = UnifiedValidationService(logging_service)
        
        attack_urls = [
            "javascript:alert(1)",  # XSS
            "data:text/html,<script>alert(1)</script>",  # Data URI XSS
            "file:///etc/passwd",  # Local file access
            "ftp://example.com",  # Different protocol
            "//example.com",  # Protocol-relative
            "https://example.com@evil.com",  # Credential confusion
            "https://example.com%2f@evil.com",  # Encoded @
            "https://example.com\\@evil.com",  # Backslash confusion
            "https://exаmple.com",  # Homograph (Cyrillic а)
            "https://example.com/../admin",  # Path traversal
            "https://example.com:99999",  # Invalid port
            "https://[::1]",  # IPv6 localhost
            "https://127.0.0.1",  # IP instead of domain
            "https://0x7f.0x0.0x0.0x1",  # Hex IP
            "https://2130706433",  # Decimal IP
            "https://017700000001",  # Octal IP
        ]
        
        for url in attack_urls:
            try:
                result = service.validate_url(url)
                # Should only allow safe URLs
                assert result.startswith(("http://", "https://"))
                assert "javascript:" not in result
                assert "file://" not in result
                assert "data:" not in result
            except (ValidationError, ValueError):
                # Many attack URLs should be rejected with either exception type
                pass
    
    @pytest.mark.xfail(reason="No real password validation service — inline logic contradicts expected values")
    def test_password_entropy_edge_cases(self):
        """Test password validation entropy edge cases.

        NOTE: This test previously swallowed all assertion failures with
        a bare ``except: pass``.  It is marked xfail until a real password
        validation service is implemented.
        """
        test_cases = [
            ("a" * 100, False),  # Long but low entropy
            ("abcdefgh", False),  # Dictionary word
            ("12345678", False),  # Sequential
            ("qwertyui", False),  # Keyboard pattern
            ("P@ssw0rd", False),  # Common pattern
            ("Tr0ub4dor&3", True),  # Good entropy
            ("correct horse battery staple", True),  # XKCD style
        ]

        for password, should_be_strong in test_cases:
            # Placeholder — real implementation would use a proper service
            is_strong = len(set(password)) > 5 and len(password) >= 8
            if should_be_strong:
                assert is_strong, f"Expected strong: {password!r}"
            else:
                assert not is_strong, f"Expected weak: {password!r}"


class TestMemoryAndResourceEdgeCases:
    """Test memory and resource handling edge cases."""
    
    def test_memory_mapped_file_attacks(self):
        """Test handling of memory-mapped file attacks."""
        with tempfile.NamedTemporaryFile() as tf:
            # Create a sparse file (appears huge but uses little disk)
            tf.seek(1024 * 1024 * 1024 * 100)  # 100GB
            tf.write(b'\x00')
            tf.flush()
            
            # Try to memory map it
            try:
                with open(tf.name, 'r+b') as f:
                    # Should handle huge files gracefully
                    with mmap.mmap(f.fileno(), 0):
                        # Don't actually read it all
                        pass
            except (OSError, OverflowError):
                # System might prevent huge mmaps
                pass
    
    def test_process_limit_awareness(self):
        """Test that we can read the system process limit."""
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)
        assert soft > 0, "Process limit should be positive"
        assert hard >= soft, "Hard limit should be >= soft limit"
    
    def test_recursive_data_structure_limits(self):
        """Test handling of deeply recursive data structures."""
        # Create deeply nested list (reduced for CI performance)
        nested = []
        current = nested
        for _ in range(1000):  # Reduced from 10,000 to 1,000
            new_list = []
            current.append(new_list)
            current = new_list
        
        # Should handle without stack overflow
        try:
            str(nested)
        except RecursionError:
            # This is acceptable
            pass
        
        # Cleanup
        nested = None
        gc.collect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])