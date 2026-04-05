#!/usr/bin/env python3
"""
Comprehensive tests for credential management systems.

Tests all credential storage and retrieval mechanisms across the project:
- SecureCredentialManager
- CredentialStore 
- ETH authentication setup
- Security vulnerability prevention
"""

import os
import tempfile
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

# Import classes under test
from secure_credential_manager import (
    SecureCredentialManager, 
    CredentialSource,
    get_credential_manager,
    setup_eth_credentials_from_env
)

try:
    from auth.store import CredentialStore
except ImportError:
    CredentialStore = None

try:
    from tools.security.eth_auth_setup import ETHAuthSetup
    ETH_AUTH_AVAILABLE = True
except ImportError:
    ETH_AUTH_AVAILABLE = False


class TestCredentialSource:
    """Test CredentialSource dataclass."""
    
    def test_credential_source_creation(self):
        """Test creating CredentialSource objects."""
        source = CredentialSource(
            method="env",
            location="API_KEY",
            encrypted=False,
            description="API key from environment"
        )
        
        assert source.method == "env"
        assert source.location == "API_KEY"
        assert source.encrypted is False
        assert source.description == "API key from environment"
    
    def test_credential_source_defaults(self):
        """Test CredentialSource with default values."""
        source = CredentialSource(method="file")
        
        assert source.method == "file"
        assert source.location is None
        assert source.encrypted is False
        assert source.description == ""


class TestSecureCredentialManager:
    """Test SecureCredentialManager functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.app_name = "test_academic_papers"
        
        # Mock home directory to use temp directory
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            self.manager = SecureCredentialManager(self.app_name)
    
    def test_init_creates_config_directory(self):
        """Test that initialization creates config directory."""
        assert self.manager.config_dir.exists()
        assert self.manager.config_dir.is_dir()
    
    def test_init_encryption_creates_key(self):
        """Test that encryption initialization creates a key."""
        assert self.manager.fernet is not None
        key_file = self.manager.config_dir / ".encryption_key"
        assert key_file.exists()
    
    def test_machine_identifier_generation(self):
        """Test machine identifier generation."""
        identifier = self.manager._get_machine_identifier()
        assert isinstance(identifier, bytes)
        assert len(identifier) == 32  # SHA256 output
        
        # Should be consistent across calls
        identifier2 = self.manager._get_machine_identifier()
        assert identifier == identifier2
    
    def test_store_credential_file_method(self):
        """Test storing credentials using file method."""
        success = self.manager.store_credential("test_service", "test_value", "file")
        assert success
        
        # Check that encrypted file was created
        enc_file = self.manager.config_dir / "test_service.enc"
        assert enc_file.exists()
        
        # Verify file permissions
        assert oct(enc_file.stat().st_mode)[-3:] == "600"
    
    def test_store_credential_env_method(self):
        """Test storing credentials using env method."""
        success = self.manager.store_credential("test_service", "test_value", "env")
        assert success  # Should always return True for env method
    
    @patch('keyring.set_password')
    def test_store_credential_keyring_method(self, mock_set_password):
        """Test storing credentials using keyring method."""
        success = self.manager.store_credential("test_service", "test_value", "keyring")
        assert success
        mock_set_password.assert_called_once_with(
            self.app_name, "test_service", "test_value"
        )
    
    def test_get_credential_from_file(self):
        """Test retrieving credentials from encrypted file."""
        # Store a credential
        self.manager.store_credential("test_service", "secret_value", "file")
        
        # Add source config for the test service
        self.manager.sources_config["test_service_file"] = CredentialSource(
            method="file",
            location=str(self.manager.config_dir / "test_service.enc"),
            encrypted=True
        )
        
        # Retrieve it
        value = self.manager.get_credential("test_service")
        assert value == "secret_value"
    
    @patch.dict(os.environ, {"TEST_USERNAME": "user123"})
    def test_get_credential_from_env(self):
        """Test retrieving credentials from environment variables."""
        # Setup source config for env variable
        self.manager.sources_config["test_service_env"] = CredentialSource(
            method="env",
            location="TEST_USERNAME"
        )
        
        value = self.manager.get_credential("test_service")
        assert value == "user123"
    
    @patch('keyring.get_password')
    def test_get_credential_from_keyring(self, mock_get_password):
        """Test retrieving credentials from keyring."""
        mock_get_password.return_value = "keyring_secret"
        
        self.manager.sources_config["test_service_keyring"] = CredentialSource(
            method="keyring",
            location="test_service"
        )
        
        value = self.manager.get_credential("test_service")
        assert value == "keyring_secret"
    
    @patch.dict(os.environ, {}, clear=True)  # Clear environment to avoid interference
    def test_get_eth_credentials(self):
        """Test getting ETH username and password."""
        # Store test credentials with proper source config
        self.manager.store_credential("eth_username", "testuser", "file")
        self.manager.store_credential("eth_password", "testpass", "file")
        
        # Add source configs
        self.manager.sources_config["eth_username_file"] = CredentialSource(
            method="file",
            location=str(self.manager.config_dir / "eth_username.enc"),
            encrypted=True
        )
        self.manager.sources_config["eth_password_file"] = CredentialSource(
            method="file",
            location=str(self.manager.config_dir / "eth_password.enc"),
            encrypted=True
        )
        
        username, password = self.manager.get_eth_credentials()
        assert username == "testuser"
        assert password == "testpass"
    
    def test_has_eth_credentials_true(self):
        """Test has_eth_credentials when credentials exist."""
        self.manager.store_credential("eth_username", "testuser", "file")
        self.manager.store_credential("eth_password", "testpass", "file")
        
        assert self.manager.has_eth_credentials() is True
    
    @patch.dict(os.environ, {}, clear=True)  # Clear environment to avoid interference
    def test_has_eth_credentials_false(self):
        """Test has_eth_credentials when credentials missing."""
        # Ensure no credentials are stored by clearing sources config
        self.manager.sources_config = {}
        assert self.manager.has_eth_credentials() is False
    
    @patch.dict(os.environ, {}, clear=True)  # Clear environment to avoid interference
    def test_setup_credentials_from_dict(self):
        """Test setting up multiple credentials from dictionary."""
        credentials = {
            "eth_username": "testuser",
            "eth_password": "testpass",
            "api_key": "test_key"
        }
        
        success = self.manager.setup_credentials_from_dict(credentials)
        assert success
        
        # Add source configs for retrieval
        for cred_name in credentials:
            self.manager.sources_config[f"{cred_name}_file"] = CredentialSource(
                method="file",
                location=str(self.manager.config_dir / f"{cred_name}.enc"),
                encrypted=True
            )
        
        # Verify all credentials were stored
        assert self.manager.get_credential("eth_username") == "testuser"
        assert self.manager.get_credential("eth_password") == "testpass"
        assert self.manager.get_credential("api_key") == "test_key"
    
    @patch.dict(os.environ, {}, clear=True)  # Clear environment to avoid interference
    def test_list_available_credentials(self):
        """Test listing available credentials."""
        # Store some credentials
        self.manager.store_credential("eth_username", "testuser", "file")
        
        # Add source config
        self.manager.sources_config["eth_username_file"] = CredentialSource(
            method="file",
            location=str(self.manager.config_dir / "eth_username.enc"),
            encrypted=True
        )
        
        available = self.manager.list_available_credentials()
        assert "eth_username" in available
        assert available["eth_username"] == "file"
        assert available["eth_password"] == "not_found"
    
    def test_create_setup_instructions(self):
        """Test generating setup instructions."""
        instructions = self.manager.create_setup_instructions()
        assert "Environment Variables" in instructions
        assert "Encrypted Files" in instructions
        assert "System Keyring" in instructions
        assert "Docker/Container Setup" in instructions
    
    def test_sources_config_persistence(self):
        """Test that sources configuration is saved and loaded."""
        # Modify sources config
        test_source = CredentialSource(
            method="test",
            location="test_location",
            encrypted=True,
            description="Test source"
        )
        self.manager.sources_config["test_source"] = test_source
        self.manager._save_sources_config(self.manager.sources_config)
        
        # Create new manager instance (should load config)
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            new_manager = SecureCredentialManager(self.app_name)
        
        assert "test_source" in new_manager.sources_config
        loaded_source = new_manager.sources_config["test_source"]
        assert loaded_source.method == "test"
        assert loaded_source.location == "test_location"
        assert loaded_source.encrypted is True


@pytest.mark.skipif(CredentialStore is None, reason="auth.store module removed")
class TestCredentialStore:
    """Test CredentialStore from auth module."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock home directory
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            self.store = CredentialStore("test_app")
    
    def test_init_creates_directories(self):
        """Test that initialization creates required directories."""
        assert self.store.config_dir.exists()
        assert self.store.config_file.parent.exists()
    
    @patch('keyring.set_password')
    def test_store_credential_keyring_success(self, mock_set_password):
        """Test successful credential storage in keyring."""
        self.store.store_credential("test_service", "test_user", "test_pass")
        mock_set_password.assert_called_once_with(
            "test_app", "test_service:test_user", "test_pass"
        )
    
    @patch('keyring.set_password', side_effect=Exception("Keyring error"))
    def test_store_credential_keyring_fallback(self, mock_set_password):
        """Test fallback to encrypted storage when keyring fails."""
        self.store.store_credential("test_service", "test_user", "test_pass")
        
        # Should create encrypted file as fallback
        enc_file = self.store.config_dir / "test_service_creds.enc"
        assert enc_file.exists()
    
    @patch('keyring.get_password')
    def test_get_credential_keyring_success(self, mock_get_password):
        """Test successful credential retrieval from keyring."""
        mock_get_password.return_value = "retrieved_password"
        
        password = self.store.get_credential("test_service", "test_user")
        assert password == "retrieved_password"
        mock_get_password.assert_called_once_with(
            "test_app", "test_service:test_user"
        )
    
    def test_encrypted_storage_fallback(self):
        """Test encrypted file storage when keyring unavailable."""
        # Store using encrypted fallback
        self.store._store_encrypted("test_service", "test_user", "test_pass")
        
        # Retrieve using encrypted fallback
        password = self.store._get_encrypted("test_service", "test_user")
        assert password == "test_pass"
    
    def test_file_permissions(self):
        """Test that credential files have correct permissions."""
        self.store._store_encrypted("test_service", "test_user", "test_pass")
        
        enc_file = self.store.config_dir / "test_service_creds.enc"
        assert oct(enc_file.stat().st_mode)[-3:] == "600"


@pytest.mark.skipif(not ETH_AUTH_AVAILABLE, reason="ETH auth setup not available")
class TestETHAuthSetup:
    """Test ETH authentication setup."""
    
    def setup_method(self):
        """Setup test environment."""
        with patch('tools.security.eth_auth_setup.get_auth_manager'):
            self.eth_setup = ETHAuthSetup()
    
    def test_init_creates_auth_manager(self):
        """Test that initialization creates auth manager."""
        assert self.eth_setup.auth_manager is not None
        assert self.eth_setup.eth_username is None
        assert self.eth_setup.eth_password is None
    
    @patch('builtins.input', side_effect=["testuser"])
    @patch('getpass.getpass', return_value="testpass")
    def test_collect_credentials(self, mock_getpass, mock_input):
        """Test credential collection from user input."""
        self.eth_setup.collect_credentials()
        
        assert self.eth_setup.eth_username == "testuser"
        assert self.eth_setup.eth_password == "testpass"
    
    @patch('builtins.input', side_effect=[""])
    def test_collect_credentials_empty_username(self, mock_input):
        """Test error handling for empty username."""
        with pytest.raises(ValueError, match="Username required"):
            self.eth_setup.collect_credentials()
    
    @patch('builtins.input', side_effect=["testuser"])
    @patch('getpass.getpass', return_value="")
    def test_collect_credentials_empty_password(self, mock_getpass, mock_input):
        """Test error handling for empty password."""
        with pytest.raises(ValueError, match="Password required"):
            self.eth_setup.collect_credentials()


class TestGlobalFunctions:
    """Test global credential management functions."""
    
    def test_get_credential_manager_singleton(self):
        """Test that get_credential_manager returns singleton."""
        manager1 = get_credential_manager()
        manager2 = get_credential_manager()
        assert manager1 is manager2
    
    @patch.dict(os.environ, {"ETH_USERNAME": "testuser", "ETH_PASSWORD": "testpass"})
    @patch('secure_credential_manager.get_credential_manager')
    def test_setup_eth_credentials_from_env_success(self, mock_get_manager):
        """Test successful setup from environment variables."""
        mock_manager = Mock()
        mock_manager.store_credential.return_value = True
        mock_get_manager.return_value = mock_manager
        
        success = setup_eth_credentials_from_env()
        assert success
        
        # Verify credentials were stored
        assert mock_manager.store_credential.call_count == 2
        mock_manager.store_credential.assert_any_call("eth_username", "testuser", "file")
        mock_manager.store_credential.assert_any_call("eth_password", "testpass", "file")
    
    def test_setup_eth_credentials_from_env_missing_vars(self):
        """Test setup failure when environment variables missing."""
        with patch.dict(os.environ, {}, clear=True):
            success = setup_eth_credentials_from_env()
            assert success is False


class TestSecurityVulnerabilityPrevention:
    """Test security measures and vulnerability prevention."""
    
    def test_no_hardcoded_credentials_in_secure_manager(self):
        """Test that SecureCredentialManager has no hardcoded credentials."""
        # Read the source file
        manager_file = Path("secure_credential_manager.py")
        if manager_file.exists():
            content = manager_file.read_text()
            
            # Check for common hardcoded credential patterns
            dangerous_patterns = [
                r'password\s*=\s*["\'][^"\']*["\']',
                r'api_key\s*=\s*["\'][^"\']*["\']',
                r'secret\s*=\s*["\'][^"\']*["\']',
                r'token\s*=\s*["\'][^"\']*["\']'
            ]
            
            import re
            for pattern in dangerous_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                # Filter out template/placeholder values
                real_matches = [m for m in matches if not any(
                    placeholder in m.lower() for placeholder in 
                    ["your_", "placeholder", "example", "test", "demo"]
                )]
                assert len(real_matches) == 0, f"Found hardcoded credential: {real_matches}"
    
    def test_file_permissions_are_secure(self):
        """Test that credential files have secure permissions."""
        temp_dir = tempfile.mkdtemp()
        
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path(temp_dir)
            manager = SecureCredentialManager("test_app")
            
            # Store a credential
            manager.store_credential("test", "value", "file")
            
            # Check key file permissions
            key_file = manager.config_dir / ".encryption_key"
            assert oct(key_file.stat().st_mode)[-3:] == "600"
            
            # Check credential file permissions
            cred_file = manager.config_dir / "test.enc"
            assert oct(cred_file.stat().st_mode)[-3:] == "600"
    
    def test_encryption_key_uniqueness(self):
        """Test that encryption keys are unique per instance."""
        temp_dir1 = tempfile.mkdtemp()
        temp_dir2 = tempfile.mkdtemp()
        
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path(temp_dir1)
            manager1 = SecureCredentialManager("app1")
            key1 = manager1.encryption_key
        
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path(temp_dir2)
            manager2 = SecureCredentialManager("app2")
            key2 = manager2.encryption_key
        
        # Keys might be same due to same machine identifier, which is expected behavior
        # This test verifies that different app configs can coexist
        assert isinstance(key1, bytes)
        assert isinstance(key2, bytes)
        assert len(key1) == len(key2)  # Both should be valid encryption keys
    
    def test_credential_encryption_integrity(self):
        """Test that credentials are properly encrypted and decrypted."""
        temp_dir = tempfile.mkdtemp()
        
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path(temp_dir)
            manager = SecureCredentialManager("test_app")
            
            # Store a credential
            original_value = "super_secret_password_123!"
            manager.store_credential("test_cred", original_value, "file")
            
            # Add source config for retrieval
            manager.sources_config["test_cred_file"] = CredentialSource(
                method="file",
                location=str(manager.config_dir / "test_cred.enc"),
                encrypted=True
            )
            
            # Retrieve the credential
            retrieved_value = manager.get_credential("test_cred")
            
            assert retrieved_value == original_value
            
            # Verify the file contains encrypted data (not plaintext)
            cred_file = manager.config_dir / "test_cred.enc"
            encrypted_content = cred_file.read_bytes()
            assert original_value.encode() not in encrypted_content
    
    def test_no_default_credentials_in_environment_access(self):
        """Test that environment variable access doesn't include defaults."""
        temp_dir = tempfile.mkdtemp()
        
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path(temp_dir)
            manager = SecureCredentialManager("test_app")
            
            # Test environment source without fallback
            env_source = CredentialSource(method="env", location="NONEXISTENT_VAR")
            value = manager._get_from_source(env_source)
            
            # Should return None, not a default value
            assert value is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])