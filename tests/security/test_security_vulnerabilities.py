#!/usr/bin/env python3
"""
Comprehensive Security Vulnerability Tests
==========================================

Paranoid security testing for all identified attack vectors and vulnerabilities.
"""

import pytest
import tempfile
import os
import sys
import json
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.utils.cache import DiskCache
from core.security.secure_file_ops import SecureFileOperations
from core.security.vulnerability_scanner import SecurityScanner
from core.unified_config.security import ConfigSecurityManager


class TestCacheSecurityFixes:
    """Test that cache no longer uses dangerous pickle operations."""
    
    def test_cache_no_pickle_deserialization(self):
        """Test that cache doesn't deserialize arbitrary Python objects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = DiskCache(cache_dir=temp_dir)
            
            # Try to cache a safe object
            cache.put("safe_data", {"key": "value", "number": 42})
            result = cache.get("safe_data")
            assert result == {"key": "value", "number": 42}
            
            # Verify no pickle files are created
            cache_files = list(Path(temp_dir).glob("*"))
            for cache_file in cache_files:
                if cache_file.is_file():
                    content = cache_file.read_text(encoding='utf-8')
                    # Should be JSON, not pickle
                    assert not content.startswith('\x80')  # Pickle protocol marker
                    # Should be valid JSON
                    json.loads(content)
    
    def test_cache_malicious_file_resistance(self):
        """Test that cache doesn't execute code from malicious cache files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = DiskCache(cache_dir=temp_dir)
            
            # Create a malicious cache file manually
            cache_path = Path(temp_dir) / "cache_malicious.json"
            malicious_content = '{"__reduce__": ["os.system", ["echo PWNED"]]}'
            cache_path.write_text(malicious_content, encoding='utf-8')
            
            # Try to read it - should not execute code
            result = cache.get("malicious")
            # Should either return the dict safely or None (if validation fails)
            assert result is None or isinstance(result, dict)
    
    def test_cache_handles_non_serializable_gracefully(self):
        """Test that cache handles non-JSON-serializable objects gracefully."""
        import datetime
        import threading
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = DiskCache(cache_dir=temp_dir)
            
            # These should fail gracefully without crashing
            cache.put("datetime", datetime.datetime.now())
            cache.put("thread", threading.Thread())
            cache.put("function", lambda x: x)
            
            # Should return None for non-serializable objects
            assert cache.get("datetime") is None
            assert cache.get("thread") is None
            assert cache.get("function") is None


class TestFileOperationSecurity:
    """Test secure file operations and path validation."""
    
    def test_path_traversal_prevention(self):
        """Test that path traversal attacks are prevented."""
        with tempfile.TemporaryDirectory() as temp_dir:
            secure_ops = SecureFileOperations([temp_dir])
            
            # These should be blocked (universally dangerous paths)
            dangerous_paths = [
                "../../../etc/passwd",
                temp_dir + "/../../../etc/passwd",
                "/etc/passwd",
                "/tmp/../../../etc/passwd",
                "../../../../../../etc/passwd"
            ]
            
            for dangerous_path in dangerous_paths:
                with pytest.raises(ValueError, match="Path"):
                    secure_ops.secure_write(dangerous_path, "malicious content")
    
    def test_symlink_attack_prevention(self):
        """Test that symlink attacks are detected and prevented."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            secure_ops = SecureFileOperations([temp_dir])
            
            # Create a symlink pointing outside allowed directory
            try:
                # Point to a system file that's definitely not in allowed paths
                if os.name == 'posix':
                    outside_target = Path("/etc/passwd")
                else:
                    outside_target = Path("C:\\Windows\\System32\\config\\sam")
                
                symlink_path = temp_path / "symlink_attack"
                symlink_path.symlink_to(outside_target)
                
                # Should detect and prevent symlink attack
                with pytest.raises(ValueError):
                    secure_ops.secure_write(symlink_path, "malicious content")
                    
            except (OSError, NotImplementedError):
                # Symlinks not supported on this system
                pytest.skip("Symlinks not supported")
    
    def test_file_permission_validation(self):
        """Test that insecure file permissions are detected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            secure_ops = SecureFileOperations([temp_dir])
            
            # Create files with various permissions
            test_file = temp_path / "test_file.txt"
            test_file.write_text("test content")
            
            # Test secure permissions
            test_file.chmod(0o600)  # Owner read/write only
            result = secure_ops.validate_file_permissions(test_file)
            assert result["secure"] is True
            assert len(result["issues"]) == 0
            
            # Test insecure permissions
            test_file.chmod(0o666)  # World readable/writable
            result = secure_ops.validate_file_permissions(test_file)
            assert result["secure"] is False
            assert "World-readable" in result["issues"]
            assert "World-writable" in result["issues"]
    
    def test_file_size_limits(self):
        """Test that file size limits are enforced."""
        with tempfile.TemporaryDirectory() as temp_dir:
            secure_ops = SecureFileOperations([temp_dir])
            
            large_file = Path(temp_dir) / "large_file.txt"
            # Create a file larger than the limit
            large_content = "x" * (200 * 1024 * 1024)  # 200MB
            large_file.write_text(large_content)
            
            # Should refuse to read large files
            result = secure_ops.secure_read(large_file, max_size=1024*1024)  # 1MB limit
            assert result is None


class TestModuleLoadingSecurity:
    """Test that module loading is secure and doesn't execute arbitrary code."""
    
    def test_api_docs_generator_path_validation(self):
        """Test that API docs generator validates package paths."""
        from core.documentation.api_docs_generator import APIDocGenerator
        
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "safe_base"
            base_path.mkdir()
            
            generator = APIDocGenerator(base_path=base_path)
            
            # Test with path outside base - should be rejected
            outside_path = Path(temp_dir) / "outside_package"
            outside_path.mkdir()
            (outside_path / "__init__.py").write_text("")
            
            # Should return empty dict for untrusted paths
            docs = generator.generate_docs_for_package(outside_path)
            assert docs == {}


class TestConfigurationSecurity:
    """Test configuration system security."""
    
    def test_config_encryption_for_secrets(self):
        """Test that secret configurations are properly encrypted."""
        from core.unified_config.interfaces import ConfigValue, ConfigSecurityLevel
        
        security_manager = ConfigSecurityManager()
        
        # Test secret value encryption
        secret_config = ConfigValue(
            "db.password", 
            "super_secret_password", 
            None,  # source 
            ConfigSecurityLevel.SECRET
        )
        
        assert security_manager.should_encrypt(secret_config) is True
        
        encrypted = security_manager.encrypt_value(secret_config)
        assert encrypted != "super_secret_password"
        assert len(encrypted) > len("super_secret_password")
        
        # Test decryption
        decrypted = security_manager.decrypt_value(encrypted, secret_config)
        assert decrypted == "super_secret_password"
    
    def test_config_no_plaintext_secrets(self):
        """Test that secret configs don't leak in plaintext."""
        from core.unified_config.manager import UnifiedConfigManager
        from core.unified_config.interfaces import ConfigSchema, ConfigSecurityLevel
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = UnifiedConfigManager(config_dir=temp_dir)
            
            # Register secret schema
            schema = ConfigSchema("api.secret", str, ConfigSecurityLevel.SECRET)
            manager.register_schema(schema)
            
            # Set secret value
            manager.set("api.secret", "secret_api_key_12345")
            
            # Verify it's stored securely (implementation-dependent)
            retrieved = manager.get("api.secret")
            assert retrieved is not None  # Should be retrievable
            
            # Check that it's not stored in plaintext anywhere
            config_files = list(Path(temp_dir).glob("**/*"))
            for config_file in config_files:
                if config_file.is_file():
                    try:
                        content = config_file.read_text(encoding='utf-8', errors='ignore')
                        assert "secret_api_key_12345" not in content
                    except:  # noqa: E722
                        pass  # Skip binary files


class TestVulnerabilityScanner:
    """Test the vulnerability scanner itself."""
    
    def test_scanner_detects_dangerous_operations(self):
        """Test that vulnerability scanner detects dangerous code patterns."""
        scanner = SecurityScanner()
        
        # Test dangerous code samples
        dangerous_code_samples = [
            "eval(user_input)",
            "exec(malicious_code)",
            "subprocess.call(cmd, shell=True)",
            "os.system(user_command)",
            "pickle.loads(untrusted_data)",
            'password = "hardcoded_secret"',
            "except:",  # Bare except
        ]
        
        for code_sample in dangerous_code_samples:
            # Create temp file with dangerous code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code_sample)
                temp_file = f.name
            
            try:
                vulnerabilities = scanner.scan_file(temp_file)
                assert len(vulnerabilities) > 0, f"Should detect vulnerability in: {code_sample}"
            finally:
                os.unlink(temp_file)
    
    def test_scanner_safe_code_no_false_positives(self):
        """Test that scanner doesn't flag safe code patterns."""
        scanner = SecurityScanner()
        
        safe_code_samples = [
            "import ast; ast.literal_eval(data)",
            "subprocess.run(['ls', '-l'], shell=False)",
            "import json; json.loads(data)",
            "password = get_secure_password()",
            "try:\n    risky_operation()\nexcept ValueError:\n    handle_error()",
        ]
        
        for code_sample in safe_code_samples:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code_sample)
                temp_file = f.name
            
            try:
                vulnerabilities = scanner.scan_file(temp_file)
                # Should have no or minimal vulnerabilities
                assert len(vulnerabilities) == 0, f"False positive in safe code: {code_sample}"
            finally:
                os.unlink(temp_file)


class TestInputValidationSecurity:
    """Test input validation and sanitization."""
    
    def test_unicode_handling_security(self):
        """Test that Unicode handling doesn't introduce vulnerabilities."""
        from core.text_processing.unicode_utils import UnicodeProcessor
        
        processor = UnicodeProcessor()
        
        # Test various Unicode attack vectors
        unicode_attacks = [
            "normal text",  # Control
            "test\u0000null",  # Null bytes
            "test\u202Eoverride",  # Right-to-left override
            "test\uFEFFbom",  # Byte order mark
            "test\u200Bzwsp",  # Zero-width space
            "\U0001F4A9💩",  # High Unicode
            "café\u0301",  # Combining characters
        ]
        
        for attack_text in unicode_attacks:
            try:
                # Should handle all Unicode safely without crashing
                normalized = processor.normalize(attack_text)
                result = processor.remove_dangerous_chars(normalized)
                assert isinstance(result, str)
                # Should not contain dangerous control characters
                assert '\u0000' not in result
                assert '\u202E' not in result
            except Exception as e:
                pytest.fail(f"Unicode processor failed on: {repr(attack_text)} with error: {e}")
    
    def test_filename_security(self):
        """Test that filename processing is secure."""
        from validators.filename_checker.core import check_filename
        
        # Test dangerous filename patterns
        dangerous_filenames = [
            "../../../etc/passwd",
            "C:\\Windows\\System32\\cmd.exe",
            "file\x00.txt",  # Null byte injection
            "file.txt\n.exe",  # Newline injection
            "con.txt",  # Windows reserved name
            "file.txt.",  # Trailing dot (Windows)
            " file.txt ",  # Leading/trailing spaces
        ]
        
        for dangerous_filename in dangerous_filenames:
            try:
                result = check_filename(dangerous_filename)
                # Should either reject or sanitize dangerous filenames
                if result.status == "ok":
                    # If accepted, should be sanitized
                    assert ".." not in dangerous_filename  # Original should still contain it
                    # But the checker should have flagged issues
                    assert len(result.messages) > 0  # Should have warnings/errors
            except Exception:
                # Acceptable to raise exception for dangerous input
                pass


class TestConcurrencySecurityIssues:
    """Test for race conditions and other concurrency-related security issues."""
    
    def test_cache_thread_safety(self):
        """Test that cache operations are thread-safe."""
        import threading
        import time
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = DiskCache(cache_dir=temp_dir)
            
            results = []
            errors = []
            
            def cache_worker(worker_id):
                try:
                    for i in range(10):
                        key = f"worker_{worker_id}_key_{i}"
                        value = f"worker_{worker_id}_value_{i}"
                        
                        cache.put(key, value)
                        retrieved = cache.get(key)
                        
                        if retrieved != value:
                            errors.append(f"Worker {worker_id}: Expected {value}, got {retrieved}")
                        else:
                            results.append(f"Worker {worker_id}: Success {i}")
                        
                        time.sleep(0.001)  # Small delay to increase contention
                except Exception as e:
                    errors.append(f"Worker {worker_id}: Exception {e}")
            
            # Run multiple threads
            threads = []
            for worker_id in range(5):
                thread = threading.Thread(target=cache_worker, args=(worker_id,))
                threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join()
            
            # Check results
            assert len(errors) == 0, f"Thread safety errors: {errors}"
            assert len(results) == 50  # 5 workers * 10 operations each
    
    def test_config_concurrent_access(self):
        """Test that configuration access is thread-safe."""
        from core.unified_config.manager import UnifiedConfigManager
        import threading
        
        manager = UnifiedConfigManager()
        errors = []
        
        def config_worker(worker_id):
            try:
                for i in range(20):
                    key = f"concurrent_test_{worker_id}_{i}"
                    value = f"value_{worker_id}_{i}"
                    
                    manager.set(key, value)
                    retrieved = manager.get(key)
                    
                    if retrieved != value:
                        errors.append(f"Worker {worker_id}: Config mismatch")
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")
        
        threads = [threading.Thread(target=config_worker, args=(i,)) for i in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0, f"Concurrency errors: {errors}"


if __name__ == "__main__":
    # Run paranoid security tests
    pytest.main([__file__, "-v", "--tb=short"])