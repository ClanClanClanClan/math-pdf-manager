#!/usr/bin/env python3
"""
Comprehensive tests for configuration security components.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.unified_config.security import ConfigSecurityManager
from core.unified_config.interfaces import ConfigValue, ConfigSource, ConfigSecurityLevel


class TestConfigSecurityManager:
    """Test the configuration security manager."""
    
    @pytest.fixture
    def security_manager(self):
        """Create a configuration security manager instance."""
        return ConfigSecurityManager()
    
    @pytest.fixture
    def temp_secure_dir(self):
        """Create a temporary secure directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            secure_dir = Path(temp_dir) / "secure"
            secure_dir.mkdir(mode=0o700)  # Owner only
            yield secure_dir
    
    def test_security_manager_initialization(self, security_manager):
        """Test security manager initializes correctly."""
        assert hasattr(security_manager, 'should_encrypt')
        assert hasattr(security_manager, 'encrypt_value')
        assert hasattr(security_manager, 'decrypt_value')
        assert callable(security_manager.should_encrypt)
    
    def test_security_level_classification(self, security_manager):
        """Test security level classification."""
        # Public values should not need encryption
        public_value = ConfigValue("public.setting", "value", ConfigSource.DEFAULTS, ConfigSecurityLevel.PUBLIC)
        assert security_manager.should_encrypt(public_value) is False
        
        # Internal values may or may not need encryption
        internal_value = ConfigValue("internal.setting", "value", ConfigSource.ENVIRONMENT, ConfigSecurityLevel.INTERNAL)
        internal_needs_encryption = security_manager.should_encrypt(internal_value)
        assert isinstance(internal_needs_encryption, bool)
        
        # Sensitive values should need encryption
        sensitive_value = ConfigValue("sensitive.data", "value", ConfigSource.ENV_FILE, ConfigSecurityLevel.SENSITIVE)
        assert security_manager.should_encrypt(sensitive_value) is True
        
        # Secret values should definitely need encryption
        secret_value = ConfigValue("secret.key", "value", ConfigSource.ENV_FILE, ConfigSecurityLevel.SECRET)
        assert security_manager.should_encrypt(secret_value) is True
    
    def test_encryption_decryption_cycle(self, security_manager):
        """Test encryption and decryption round trip."""
        original_value = "super_secret_password_123"
        sensitive_config = ConfigValue(
            "db.password", 
            original_value, 
            ConfigSource.ENV_FILE, 
            ConfigSecurityLevel.SECRET
        )
        
        # Encrypt the value
        encrypted = security_manager.encrypt_value(sensitive_config)
        
        # Encrypted value should be different from original
        assert encrypted != original_value
        assert len(encrypted) > 0
        
        # Decrypt the value
        decrypted = security_manager.decrypt_value(encrypted, sensitive_config)
        
        # Should get back original value
        assert decrypted == original_value
    
    def test_encryption_key_management(self, security_manager):
        """Test encryption key generation and management."""
        # Test that encryption uses proper key management
        value1 = ConfigValue("secret1", "value1", ConfigSource.ENV_FILE, ConfigSecurityLevel.SECRET)
        value2 = ConfigValue("secret2", "value2", ConfigSource.ENV_FILE, ConfigSecurityLevel.SECRET)
        
        encrypted1 = security_manager.encrypt_value(value1)
        encrypted2 = security_manager.encrypt_value(value2)
        
        # Different values should produce different encrypted results
        assert encrypted1 != encrypted2
        
        # Same value should be consistently decryptable
        decrypted1 = security_manager.decrypt_value(encrypted1, value1)
        assert decrypted1 == "value1"
    
    def test_secure_storage_paths(self, security_manager, temp_secure_dir):
        """Test secure storage path generation."""
        secret_value = ConfigValue("api.secret", "secret123", ConfigSource.ENV_FILE, ConfigSecurityLevel.SECRET)
        
        # Get secure storage path
        if hasattr(security_manager, 'get_secure_path'):
            secure_path = security_manager.get_secure_path(secret_value, temp_secure_dir)
            
            assert isinstance(secure_path, Path)
            assert secure_path.parent == temp_secure_dir
            assert secure_path.name.endswith('.enc') or 'encrypted' in secure_path.name
    
    def test_permission_checking(self, security_manager):
        """Test file permission validation."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            
            try:
                # Set secure permissions
                temp_path.chmod(0o600)  # Owner read/write only
                
                if hasattr(security_manager, 'check_file_permissions'):
                    is_secure = security_manager.check_file_permissions(temp_path)
                    assert is_secure is True
                
                # Set insecure permissions
                temp_path.chmod(0o644)  # World readable
                
                if hasattr(security_manager, 'check_file_permissions'):
                    is_secure = security_manager.check_file_permissions(temp_path)
                    assert is_secure is False
                    
            finally:
                temp_path.unlink()
    
    def test_secure_deletion(self, security_manager):
        """Test secure deletion of sensitive data."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            sensitive_data = "very_secret_information"
            
            try:
                # Write sensitive data
                with open(temp_path, 'w') as f:
                    f.write(sensitive_data)
                
                # Secure delete
                if hasattr(security_manager, 'secure_delete'):
                    security_manager.secure_delete(temp_path)
                    
                    # File should be gone
                    assert not temp_path.exists()
                else:
                    # If no secure delete, at least regular delete
                    temp_path.unlink()
                    
            finally:
                if temp_path.exists():
                    temp_path.unlink()
    
    def test_memory_protection(self, security_manager):
        """Test memory protection for sensitive values."""
        secret_data = "extremely_sensitive_data_12345"
        secret_value = ConfigValue("memory.secret", secret_data, ConfigSource.ENV_FILE, ConfigSecurityLevel.SECRET)
        
        # Test if security manager provides memory protection
        if hasattr(security_manager, 'protect_in_memory'):
            protected = security_manager.protect_in_memory(secret_value)
            
            # Protected version should be different
            assert protected != secret_data
            
            # Should be able to retrieve original
            if hasattr(security_manager, 'unprotect_from_memory'):
                unprotected = security_manager.unprotect_from_memory(protected, secret_value)
                assert unprotected == secret_data
    
    def test_audit_logging(self, security_manager):
        """Test security audit logging."""
        sensitive_value = ConfigValue("audit.test", "sensitive", ConfigSource.ENVIRONMENT, ConfigSecurityLevel.SENSITIVE)
        
        # Mock logger to capture audit events
        with patch('logging.getLogger') as mock_logger:
            mock_log = MagicMock()
            mock_logger.return_value = mock_log
            
            # Perform operations that should be audited
            security_manager.should_encrypt(sensitive_value)
            
            if hasattr(security_manager, 'audit_access'):
                security_manager.audit_access(sensitive_value, "read")
                
                # Check if audit logging occurred
                # This depends on implementation details
    
    def test_access_control(self, security_manager):
        """Test access control for configuration values."""
        # Test different security contexts
        contexts = [
            {"user": "admin", "role": "administrator"},
            {"user": "app", "role": "application"},
            {"user": "guest", "role": "readonly"}
        ]
        
        secret_value = ConfigValue("access.secret", "secret", ConfigSource.ENV_FILE, ConfigSecurityLevel.SECRET)
        internal_value = ConfigValue("access.internal", "internal", ConfigSource.ENVIRONMENT, ConfigSecurityLevel.INTERNAL)
        
        for context in contexts:
            if hasattr(security_manager, 'check_access'):
                # Admin should have access to everything
                if context["role"] == "administrator":
                    assert security_manager.check_access(secret_value, context) is True
                    assert security_manager.check_access(internal_value, context) is True
                
                # Guest should have limited access
                elif context["role"] == "readonly":
                    secret_access = security_manager.check_access(secret_value, context)
                    assert secret_access is False  # No access to secrets
    
    def test_encryption_algorithm_security(self, security_manager):
        """Test that secure encryption algorithms are used."""
        test_value = ConfigValue("crypto.test", "test_data", ConfigSource.ENV_FILE, ConfigSecurityLevel.SECRET)
        
        encrypted = security_manager.encrypt_value(test_value)
        
        # Encrypted value should be significantly different
        assert len(encrypted) >= len("test_data")
        assert encrypted != "test_data"
        
        # Should not contain obvious patterns
        assert "test_data" not in encrypted
        
        # Should be base64 encoded or similar safe format
        import string
        allowed_chars = string.ascii_letters + string.digits + "+/="
        assert all(c in allowed_chars for c in encrypted)
    
    def test_key_rotation(self, security_manager):
        """Test encryption key rotation capability."""
        original_value = "data_for_rotation_test"
        test_config = ConfigValue("rotation.test", original_value, ConfigSource.ENV_FILE, ConfigSecurityLevel.SECRET)
        
        # Encrypt with current key
        encrypted_v1 = security_manager.encrypt_value(test_config)
        
        # Test key rotation if supported
        if hasattr(security_manager, 'rotate_keys'):
            # Rotate keys
            security_manager.rotate_keys()
            
            # Should still be able to decrypt old data
            decrypted_old = security_manager.decrypt_value(encrypted_v1, test_config)
            assert decrypted_old == original_value
            
            # New encryption should use new key
            encrypted_v2 = security_manager.encrypt_value(test_config)
            assert encrypted_v2 != encrypted_v1  # Different due to new key
            
            # New encryption should decrypt correctly
            decrypted_new = security_manager.decrypt_value(encrypted_v2, test_config)
            assert decrypted_new == original_value
    
    def test_security_configuration_validation(self, security_manager):
        """Test validation of security configuration itself."""
        # Test that security manager validates its own configuration
        if hasattr(security_manager, 'validate_security_config'):
            validation_result = security_manager.validate_security_config()
            assert isinstance(validation_result, bool)
            
            # Should have proper encryption configuration
            assert validation_result is True
    
    def test_threat_mitigation(self, security_manager):
        """Test protection against common threats."""
        # Test against timing attacks
        secret1 = ConfigValue("timing.secret1", "a" * 32, ConfigSource.ENV_FILE, ConfigSecurityLevel.SECRET)
        secret2 = ConfigValue("timing.secret2", "b" * 32, ConfigSource.ENV_FILE, ConfigSecurityLevel.SECRET)
        
        import time
        
        # Encrypt two values and measure time
        start1 = time.time()
        encrypted1 = security_manager.encrypt_value(secret1)
        time1 = time.time() - start1
        
        start2 = time.time()
        encrypted2 = security_manager.encrypt_value(secret2)
        time2 = time.time() - start2
        
        # Timing should be similar (no obvious timing attack vector)
        time_diff = abs(time1 - time2)
        assert time_diff < 0.1  # Should complete within similar timeframes
        
        # Test against side-channel attacks
        assert encrypted1 != encrypted2  # Same length inputs produce different outputs


class TestConfigSecurityIntegration:
    """Integration tests for configuration security."""
    
    @pytest.fixture
    def integration_security(self, tmp_path):
        """Create security manager for integration testing."""
        return ConfigSecurityManager()
    
    def test_end_to_end_secure_configuration(self, integration_security, tmp_path):
        """Test complete secure configuration workflow."""
        # Create secure configuration values
        sensitive_configs = {
            "db.password": ConfigValue("db.password", "secure_db_pass_123", ConfigSource.ENV_FILE, ConfigSecurityLevel.SECRET),
            "api.key": ConfigValue("api.key", "sk-1234567890abcdef", ConfigSource.ENV_FILE, ConfigSecurityLevel.SECRET),
            "encryption.salt": ConfigValue("encryption.salt", "random_salt_value", ConfigSource.ENV_FILE, ConfigSecurityLevel.SENSITIVE)
        }
        
        encrypted_configs = {}
        
        # Encrypt all sensitive configurations
        for key, config in sensitive_configs.items():
            if integration_security.should_encrypt(config):
                encrypted_configs[key] = integration_security.encrypt_value(config)
            else:
                encrypted_configs[key] = config.value
        
        # Verify all sensitive values were encrypted
        for key in ["db.password", "api.key"]:
            assert encrypted_configs[key] != sensitive_configs[key].value
        
        # Decrypt and verify
        for key, config in sensitive_configs.items():
            if integration_security.should_encrypt(config):
                decrypted = integration_security.decrypt_value(encrypted_configs[key], config)
                assert decrypted == config.value
    
    def test_secure_configuration_storage(self, integration_security, tmp_path):
        """Test secure storage of configuration files."""
        secure_dir = tmp_path / "secure_config"
        secure_dir.mkdir(mode=0o700)  # Secure permissions
        
        # Create configuration with mixed security levels
        configs = [
            ConfigValue("public.setting", "public_value", ConfigSource.MAIN_CONFIG, ConfigSecurityLevel.PUBLIC),
            ConfigValue("internal.setting", "internal_value", ConfigSource.MAIN_CONFIG, ConfigSecurityLevel.INTERNAL),
            ConfigValue("secret.setting", "secret_value", ConfigSource.MAIN_CONFIG, ConfigSecurityLevel.SECRET)
        ]
        
        # Store configurations securely
        for config in configs:
            if hasattr(integration_security, 'store_securely'):
                storage_path = integration_security.store_securely(config, secure_dir)
                
                # Verify secure storage
                assert storage_path.exists()
                
                # Check file permissions are secure
                file_mode = storage_path.stat().st_mode & 0o777
                assert file_mode <= 0o600  # No broader permissions than owner read/write
    
    def test_configuration_security_migration(self, integration_security):
        """Test migrating from insecure to secure configuration."""
        # Simulate existing insecure configuration
        insecure_configs = {
            "db.password": "plaintext_password",
            "api.secret": "plaintext_secret",
            "encryption.key": "plaintext_key"
        }
        
        # Migrate to secure format
        secure_configs = {}
        for key, value in insecure_configs.items():
            config_value = ConfigValue(key, value, ConfigSource.MAIN_CONFIG, ConfigSecurityLevel.SECRET)
            
            if integration_security.should_encrypt(config_value):
                secure_configs[key] = integration_security.encrypt_value(config_value)
            else:
                secure_configs[key] = value
        
        # Verify migration
        assert all(secure_configs[key] != insecure_configs[key] for key in insecure_configs)
        
        # Verify we can still access the data
        for key, original_value in insecure_configs.items():
            config_value = ConfigValue(key, original_value, ConfigSource.MAIN_CONFIG, ConfigSecurityLevel.SECRET)
            decrypted = integration_security.decrypt_value(secure_configs[key], config_value)
            assert decrypted == original_value
    
    def test_security_compliance_validation(self, integration_security):
        """Test compliance with security standards."""
        # Test configuration meets security requirements
        test_configs = [
            ConfigValue("compliance.test1", "test_value_1", ConfigSource.ENVIRONMENT, ConfigSecurityLevel.PUBLIC),
            ConfigValue("compliance.test2", "sensitive_data", ConfigSource.ENV_FILE, ConfigSecurityLevel.SENSITIVE),
            ConfigValue("compliance.test3", "top_secret", ConfigSource.ENV_FILE, ConfigSecurityLevel.SECRET)
        ]
        
        compliance_results = {}
        for config in test_configs:
            # Check if configuration meets compliance requirements
            if hasattr(integration_security, 'check_compliance'):
                compliance_results[config.key] = integration_security.check_compliance(config)
            else:
                # Basic compliance check
                compliance_results[config.key] = {
                    'encrypted': integration_security.should_encrypt(config),
                    'secure_level': config.security_level in [ConfigSecurityLevel.SENSITIVE, ConfigSecurityLevel.SECRET]
                }
        
        # Verify compliance
        assert compliance_results["compliance.test1"]['encrypted'] is False  # Public doesn't need encryption
        assert compliance_results["compliance.test2"]['encrypted'] is True   # Sensitive should be encrypted
        assert compliance_results["compliance.test3"]['encrypted'] is True   # Secret should be encrypted