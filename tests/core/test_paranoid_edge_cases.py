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
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import concurrent.futures
from unittest.mock import Mock
import pytest

# Import modules to test
from core.exceptions import (
    ValidationError, ConfigurationError, SecurityError
)
from core.models import (
    Author, PDFMetadata, ValidationSeverity, ValidationIssue
)
from core.dependency_injection import DIContainer
from core.dependency_injection.container import FactorySecurityConfig
from core.dependency_injection.validation_service import UnifiedValidationService
from utils.security import (
    PathValidator
)
# Only import what's needed from secure credential manager
try:
    from secure_credential_manager import SecureCredentialManager, CredentialSource
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
        """A circular ``__cause__`` chain must not change what an
        exception says about itself.

        Previously this called ``str()``/``repr()`` and asserted nothing,
        so it could only ever have caught a hang.  The property that
        actually matters is that our rendering is LOCAL: an exception
        reports its own message and its own details, and does not walk
        the cause chain (walking it here would recurse forever).
        """
        exc1 = ValidationError("Error 1")
        exc2 = ConfigurationError("Error 2")

        # Create circular reference
        exc1.__cause__ = exc2
        exc2.__cause__ = exc1

        assert str(exc1) == "Error 1"
        assert str(exc2) == "Error 2"
        # The cause must NOT bleed into the rendering \u2014 if it did, the
        # cycle would make this call non-terminating.
        assert "Error 2" not in str(exc1)
        assert "Error 1" not in str(exc2)
        assert "Error 1" in repr(exc1)
        # ValidationError builds its own details dict; it must describe
        # this exception, not the one it was caused by.
        assert exc1.details["message"] == "Error 1"

        # Cleanup
        exc1.__cause__ = None
        exc2.__cause__ = None
        gc.collect()

    def test_exception_deep_nesting(self):
        """A 100-deep cause chain must not truncate or merge messages."""
        current = ValidationError("Base")

        # Create deep chain (reduced for CI performance)
        for i in range(100):  # Reduced from 1,000 to 100
            new_exc = ValidationError(f"Level {i}")
            new_exc.__cause__ = current
            current = new_exc

        # The outermost exception renders as itself, not as the chain.
        assert str(current) == "Level 99"
        assert current.details["message"] == "Level 99"
        assert "Base" not in str(current)

        # The chain is intact and walkable to the original base \u2014 a
        # dropped link would lose the real cause of a failure.
        depth = 0
        node = current
        while node.__cause__ is not None:
            node = node.__cause__
            depth += 1
        assert depth == 100, f"cause chain lost links: depth {depth}"
        assert str(node) == "Base"

        # Cleanup
        current = None
        node = None
        gc.collect()

    # NOTE: ``test_exception_malicious_attributes`` used to live here.  It
    # defined an ``EvilException`` class INSIDE the test, called ``str()``
    # on it inside ``try: ... except: pass``, and asserted nothing.  No
    # code from src/ was involved at any point \u2014 it exercised CPython's
    # ``str()``, and could not have failed even if every module in this
    # project were deleted.  There is no error-rendering helper in this
    # codebase for it to have been testing.  Removed rather than
    # rewritten: inventing a subject for it would be fiction too.

    def test_exception_unicode_edge_cases(self):
        """A hostile Unicode message must survive verbatim.

        Not "must not crash" \u2014 that was the old, unassertable version.
        The message is what a human reads when a paper fails to file, so
        silent truncation, escaping or re-normalisation of it is a defect
        even though nothing raises.
        """
        unicode_nightmares = [
            "\U0001F4A9" * 1000,  # Emoji spam
            "\u200b" * 10000,  # Zero-width spaces
            "\ufeff" * 1000,  # BOMs
            "A" + "\u0301" * 100,  # Combining characters
            "\u202e" + "Hello",  # Right-to-left override
            "\ud800",  # Unpaired surrogate (not UTF-8 encodable)
            "\U00100000",  # Outside BMP
        ]

        for nightmare in unicode_nightmares:
            try:
                raise ValidationError(nightmare)
            except ValidationError as e:
                assert str(e) == nightmare, (
                    f"message altered: {len(str(e))} chars out of "
                    f"{len(nightmare)} in"
                )
                assert e.args == (nightmare,)
                assert e.details["message"] == nightmare
                # repr must be produceable and must not be empty.
                assert repr(e)


class TestModelEdgeCases:
    """Paranoid tests for model edge cases."""
    
    def test_author_name_attacks(self):
        """Hostile text in an author name must be stored, not interpreted.

        The previous version of this test called ``Author(name=...)``.
        ``Author`` has no ``name`` field, so EVERY iteration raised
        ``TypeError`` before touching the model; the ``except Exception``
        below it then asserted only that the TypeError text did not
        mention /etc/passwd, which it never could.  It tested nothing.

        Rewritten against the real fields.  ``Author`` is a container:
        the contract is that what goes in comes out unchanged, and that
        the derived fields it computes are derived from exactly that.
        """
        attack_names = [
            "';DROP TABLE authors;--",  # SQL injection
            "<script>alert('xss')</script>",  # XSS
            "\x00\x01\x02",  # Control characters
            "A" * 10000,  # Very long name
            "name\nwith\nnewlines",  # Newlines
            "name\twith\ttabs",  # Tabs
            "../../etc/passwd",  # Path traversal
            "Robert'); INSERT INTO admins VALUES ('hacker",  # SQL variant
            "Кабанов",  # Cyrillic
        ]

        for given in attack_names:
            author = Author(given_name=given, family_name="Smith")

            # Stored verbatim: no escaping, no truncation, no stripping.
            assert author.given_name == given
            assert author.family_name == "Smith"

            # full_name is exactly the documented composition.
            assert author.full_name == f"{given} Smith", repr(author.full_name)

            # initials are one "X." per whitespace-separated part of the
            # given name, upper-cased, in order.
            parts = given.split()
            assert author.initials == "".join(p[0].upper() + "." for p in parts), (
                f"{given!r} -> {author.initials!r}"
            )
            # …and they are a function of given_name ALONE: changing the
            # family name must not move them.
            other = Author(given_name=given, family_name="Zzz")
            assert other.initials == author.initials

        # An explicit full_name must win over the computed one.
        pinned = Author(given_name="Jean", family_name="Jacod",
                        full_name="Jacod, J.")
        assert pinned.full_name == "Jacod, J."

    def test_pdfmetadata_path_boundaries(self):
        """A boundary path is stored byte-identical or rejected loudly.

        The old version asserted ``"\\x00" not in metadata.path`` inside a
        ``try`` whose ``except Exception: pass`` swallowed the resulting
        AssertionError — so it green-lit a sanitisation guarantee the
        model does not provide and never did.

        The guarantee that matters for a 29k-file library is the opposite
        one: metadata must never silently ALTER the owner's path, because
        a silently altered path is a file nobody can find again.  If a
        path is unacceptable, the model must raise; quietly rewriting it
        is the failure mode.
        """
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
            except (ValidationError, ValueError, TypeError):
                # An explicit refusal is an acceptable answer.
                continue
            # Acceptance means byte-identical round-trip.
            assert metadata.path == path, (
                f"path silently rewritten: {path!r} -> {metadata.path!r}"
            )
            assert str(metadata.path) == path
            assert metadata.title == "Test"


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
    def test_container_does_not_retain_transient_instances(self):
        """A transient must be fresh AND must not be kept alive.

        The old ``test_container_memory_exhaustion`` resolved 100 1MB
        objects, caught MemoryError, and asserted nothing — so a
        container that cached every transient forever (the actual memory
        exhaustion bug it was named after) passed it.  Assert the two
        postconditions instead: distinct objects out, and no strong
        reference left behind.
        """
        container = DIContainer()

        class MemoryHog:
            def __init__(self):
                self.data = bytearray(1 * 1024 * 1024)  # 1MB per instance

        # Register as transient (new instance each time)
        container.register_transient(MemoryHog, MemoryHog)

        instances = [container.resolve(MemoryHog) for _ in range(100)]

        assert len(instances) == 100
        assert all(isinstance(i, MemoryHog) for i in instances)
        # "Transient" means a NEW instance every time — not a cached one.
        assert len({id(i) for i in instances}) == 100, (
            "transient registration handed back a shared instance"
        )

        # And the container must hold no strong reference to any of them,
        # or 100 resolutions is a 100MB leak.
        import weakref
        refs = [weakref.ref(i) for i in instances]
        instances.clear()
        del instances
        gc.collect()
        leaked = sum(1 for r in refs if r() is not None)
        assert leaked == 0, (
            f"{leaked}/100 transient instances still reachable from the "
            f"container after the caller dropped them"
        )


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
        
        import statistics
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
            # Use the MEDIAN, not the mean: these are microsecond-scale
            # ops, so a single GC pause or scheduler preemption (common
            # under parallel test load) skews the mean and makes the test
            # flaky.  The median reflects the typical code-path cost and
            # is robust to such outliers; a real timing side-channel would
            # show a large, *consistent* difference that the median still
            # catches.
            timings[password] = statistics.median(times)

        # All timings should be similar (no early-exit side channel).
        median_timing = statistics.median(timings.values())
        for password, timing in timings.items():
            variance = abs(timing - median_timing) / median_timing
            assert variance < 0.5, f"{password!r}: {variance:.0%} from median"
    
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
    
    def test_path_sanitization_advanced(self, tmp_path):
        """Every traversal attempt is refused, or lands inside base_dir.

        The three assertions here used to sit inside ``try: ... except
        Exception: pass``.  ``AssertionError`` IS an ``Exception``, so
        the handler ate the test's own verdict: this path-traversal guard
        had a test that could not fail.  Two changes: only the documented
        refusal type is caught, and acceptance is checked against
        containment in base_dir rather than against substring spelling.

        A positive control is included on purpose — without it, a
        ``validate_path`` mutated to reject *everything* would pass a
        suite made only of attacks.
        """
        base = tmp_path / "safe"
        base.mkdir()
        base_resolved = base.resolve()

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
            str(base_resolved) + "/../../etc/passwd",  # escape from inside
        ]

        refused = 0
        for attack in advanced_attacks:
            try:
                result = PathValidator.validate_path(attack, base_dir=base)
            except SecurityError:
                # A refusal is the documented, correct answer.
                refused += 1
                continue
            # If it was ACCEPTED, the result must genuinely be contained.
            resolved = Path(result).resolve()
            assert resolved.is_relative_to(base_resolved), (
                f"{attack!r} escaped base_dir: accepted as {resolved}"
            )
            assert ".." not in resolved.parts, f"{attack!r} -> {resolved}"

        # Today every one of the above is refused outright.  This line
        # exists to catch a validator that SILENTLY REDIRECTS instead of
        # refusing (returning base_dir for anything it dislikes would
        # satisfy the containment assertion above while losing the
        # caller's path).  If a future validator legitimately normalises
        # one of these into base_dir, relax this line deliberately —
        # never the containment assertion above it.
        assert refused == len(advanced_attacks), (
            f"only {refused}/{len(advanced_attacks)} traversal attempts "
            f"were refused; the rest were silently redirected"
        )

        # Every attack above is also caught by the suspicious-pattern
        # screen, so none of them witnesses the base_dir containment
        # check.  This one does: an ordinary, innocently spelled path
        # that simply lives outside base_dir.  Delete the containment
        # check and only this assertion notices.
        outside = tmp_path / "outside" / "notes.pdf"
        outside.parent.mkdir()
        outside.write_bytes(b"%PDF-1.4\n")
        with pytest.raises(SecurityError):
            PathValidator.validate_path(outside, base_dir=base)

        # POSITIVE CONTROL: a legitimate path inside base_dir must be
        # accepted, and returned pointing at the same place.
        good = base / "papers" / "Ito, K. - Stochastic integral.pdf"
        good.parent.mkdir(parents=True)
        good.write_bytes(b"%PDF-1.4\n")
        accepted = PathValidator.validate_path(good, base_dir=base)
        assert Path(accepted).resolve() == good.resolve(), (
            "a legitimate in-base path was rewritten or rejected"
        )
        assert Path(accepted).is_relative_to(base_resolved)


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
    
    # NOTE: a password-entropy test used to live here.  It tested a
    # password-validation *service* that does not exist in this
    # PDF-management codebase — it only ever exercised a contradictory
    # inline placeholder heuristic against hard-coded expectations, so it
    # was a permanent xfail asserting nothing real.  Removed (audit
    # green-up).  If a real credential-strength check is ever added, test
    # it against that implementation, not a placeholder.


class TestMemoryAndResourceEdgeCases:
    """Test memory and resource handling edge cases."""
    
    # NOTE: ``test_memory_mapped_file_attacks`` used to live here.  It
    # created a 100GB sparse file, called ``mmap.mmap`` on it inside
    # ``try: ... except (OSError, OverflowError): pass``, and asserted
    # nothing.  No function from src/ appeared anywhere in it: it was a
    # test of CPython's ``mmap`` module, with both outcomes declared
    # acceptable.  Nothing in this codebase mmaps a file, so there is no
    # subject to point it at.  Removed.  (It also wrote a 100GB sparse
    # file on every run, on a machine whose Dropbox holds the library.)

    def test_process_limit_awareness(self):
        """Test that we can read the system process limit."""
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)
        assert soft > 0, "Process limit should be positive"
        assert hard >= soft, "Hard limit should be >= soft limit"
    
    # NOTE: ``test_recursive_data_structure_limits`` used to live here.
    # It built a 1000-deep nested list and called ``str()`` on it inside
    # ``try: ... except RecursionError: pass``, asserting nothing — both
    # outcomes passed, and no project code was involved.  The real
    # recursion guarantee this project needs is the one asserted by
    # ``TestValidationServiceEdgeCases.test_validation_recursive_structures``
    # above, which puts a self-referential dict through
    # ``UnifiedValidationService`` and requires a ValidationError.
    # Removed as a duplicate-in-intent test of CPython's ``str()``.


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])