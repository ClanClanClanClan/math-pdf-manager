#!/usr/bin/env python3
"""
Secure Credential Manager for Automated Workflows
=================================================

Provides multiple secure methods for storing and retrieving credentials
that work in automated/headless environments without user interaction.
"""

import os
import json
import base64
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger("secure_credential_manager")


@dataclass
class CredentialSource:
    """Configuration for credential sources."""
    method: str  # 'env', 'file', 'keyring', 'config'
    location: Optional[str] = None  # File path, env var name, etc.
    encrypted: bool = False
    description: str = ""


class SecureCredentialManager:
    """
    Manages credentials for automated workflows using multiple secure methods:
    
    1. Environment variables (for CI/CD, containers)
    2. Encrypted credential files (for local automation)
    3. System keyring (for interactive development)
    4. Cloud secret managers (for production)
    """
    
    def __init__(self, app_name: str = "academic_papers"):
        self.app_name = app_name
        self.config_dir = Path.home() / f".{app_name}" / "credentials"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize encryption
        self._init_encryption()
        
        # Load credential sources configuration
        self.sources_config = self._load_sources_config()
        
        # Priority order for credential lookup
        self.lookup_priority = ['env', 'file', 'keyring', 'cloud']
    
    def _init_encryption(self):
        """Initialize encryption for file-based credentials."""
        key_file = self.config_dir / ".encryption_key"
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                self.encryption_key = f.read()
        else:
            # Generate new encryption key from machine-specific data
            machine_id = self._get_machine_identifier()
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=machine_id[:16],  # Use part of machine ID as salt
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(machine_id))
            self.encryption_key = key
            
            # Save key (protected by file permissions)
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)
        
        self.fernet = Fernet(self.encryption_key)
    
    def _get_machine_identifier(self) -> bytes:
        """Get a machine-specific identifier for encryption."""
        import platform
        import uuid
        
        # Combine multiple machine identifiers
        identifiers = [
            platform.node(),  # Hostname
            str(uuid.getnode()),  # MAC address
            platform.machine(),  # Architecture
            str(os.getuid()) if hasattr(os, 'getuid') else 'unknown'  # User ID
        ]
        
        combined = "|".join(identifiers).encode('utf-8')
        
        # Hash to create consistent 32-byte key material
        # Use app name as domain-separation tag (not a cryptographic salt)
        digest = hashes.Hash(hashes.SHA256())
        digest.update(combined)
        digest.update(self.app_name.encode("utf-8"))

        return digest.finalize()
    
    def _load_sources_config(self) -> Dict[str, CredentialSource]:
        """Load configuration for credential sources."""
        config_file = self.config_dir / "sources.json"
        
        default_sources = {
            # Environment variables (highest priority for automation)
            "eth_username_env": CredentialSource(
                method="env",
                location="ETH_USERNAME",
                description="ETH username from environment variable"
            ),
            "eth_password_env": CredentialSource(
                method="env", 
                location="ETH_PASSWORD",
                description="ETH password from environment variable"
            ),
            
            # Encrypted files (for local automation)
            "eth_username_file": CredentialSource(
                method="file",
                location=str(self.config_dir / "eth_username.enc"),
                encrypted=True,
                description="ETH username from encrypted file"
            ),
            "eth_password_file": CredentialSource(
                method="file",
                location=str(self.config_dir / "eth_password.enc"),
                encrypted=True,
                description="ETH password from encrypted file"
            ),
            
            # System keyring (for development)
            "eth_keyring": CredentialSource(
                method="keyring",
                location="eth_credentials",
                description="ETH credentials from system keyring"
            )
        }
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                
                # Convert dict to CredentialSource objects
                loaded_sources = {}
                for name, source_data in data.items():
                    loaded_sources[name] = CredentialSource(**source_data)
                
                return loaded_sources
            except Exception as e:
                logger.warning(f"Failed to load sources config: {e}")
        
        # Save default config
        self._save_sources_config(default_sources)
        return default_sources
    
    def _save_sources_config(self, sources: Dict[str, CredentialSource]):
        """Save credential sources configuration."""
        config_file = self.config_dir / "sources.json"
        
        # Convert to serializable format
        data = {}
        for name, source in sources.items():
            data[name] = {
                'method': source.method,
                'location': source.location,
                'encrypted': source.encrypted,
                'description': source.description
            }
        
        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def store_credential(self, credential_name: str, value: str, method: str = "file") -> bool:
        """
        Store a credential using the specified method.
        
        Args:
            credential_name: Name of the credential (e.g., 'eth_username')
            value: The credential value
            method: Storage method ('env', 'file', 'keyring')
        """
        try:
            if method == "env":
                # For environment variables, just show what to set
                env_var = f"{credential_name.upper()}"
                logger.info(f"Set environment variable: export {env_var}='{value}'")
                return True
            
            elif method == "file":
                # Encrypt and store in file
                encrypted_value = self.fernet.encrypt(value.encode())
                file_path = self.config_dir / f"{credential_name}.enc"
                
                with open(file_path, 'wb') as f:
                    f.write(encrypted_value)
                os.chmod(file_path, 0o600)
                
                logger.info(f"Stored {credential_name} in encrypted file: {file_path}")
                return True
            
            elif method == "keyring":
                # Store in system keyring
                try:
                    import keyring
                    keyring.set_password(self.app_name, credential_name, value)
                    logger.info(f"Stored {credential_name} in system keyring")
                    return True
                except ImportError:
                    logger.error("Keyring not available")
                    return False
            
            else:
                logger.error(f"Unknown storage method: {method}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to store credential {credential_name}: {e}")
            return False
    
    def get_credential(self, credential_type: str) -> Optional[str]:
        """
        Retrieve a credential using the priority order.
        
        Args:
            credential_type: Type of credential ('eth_username', 'eth_password')
        """
        # Try each source in priority order
        source_patterns = [
            f"{credential_type}_env",
            f"{credential_type}_file", 
            f"{credential_type}_keyring"
        ]
        
        for pattern in source_patterns:
            if pattern in self.sources_config:
                source = self.sources_config[pattern]
                value = self._get_from_source(source)
                if value:
                    logger.debug(f"Found {credential_type} via {source.method}")
                    return value
        
        # Try generic keyring lookup
        try:
            import keyring
            value = keyring.get_password(self.app_name, credential_type)
            if value:
                logger.debug(f"Found {credential_type} via generic keyring")
                return value
        except ImportError:
            pass
        
        logger.warning(f"Credential {credential_type} not found in any source")
        return None
    
    def _get_from_source(self, source: CredentialSource) -> Optional[str]:
        """Retrieve credential from a specific source."""
        try:
            if source.method == "env":
                return os.getenv(source.location)
            
            elif source.method == "file":
                if not source.location or not os.path.exists(source.location):
                    return None
                
                with open(source.location, 'rb') as f:
                    data = f.read()
                
                if source.encrypted:
                    decrypted = self.fernet.decrypt(data)
                    return decrypted.decode('utf-8')
                else:
                    return data.decode('utf-8')
            
            elif source.method == "keyring":
                try:
                    import keyring
                    return keyring.get_password(self.app_name, source.location)
                except ImportError:
                    return None
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to get credential from {source.method}: {e}")
            return None
    
    def get_eth_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """Get ETH username and password."""
        username = self.get_credential("eth_username")
        password = self.get_credential("eth_password") 
        return username, password
    
    def has_eth_credentials(self) -> bool:
        """Check if ETH credentials are available."""
        username, password = self.get_eth_credentials()
        return username is not None and password is not None
    
    def setup_credentials_from_dict(self, credentials: Dict[str, str], method: str = "file") -> bool:
        """
        Setup multiple credentials from a dictionary.
        Useful for initial configuration.
        """
        success = True
        for name, value in credentials.items():
            if not self.store_credential(name, value, method):
                success = False
        return success
    
    def list_available_credentials(self) -> Dict[str, str]:
        """List which credentials are available and from which sources."""
        available = {}
        
        for credential_type in ['eth_username', 'eth_password']:
            source_found = None
            
            # Check each source
            patterns = [f"{credential_type}_env", f"{credential_type}_file", f"{credential_type}_keyring"]
            for pattern in patterns:
                if pattern in self.sources_config:
                    source = self.sources_config[pattern]
                    if self._get_from_source(source):
                        source_found = source.method
                        break
            
            available[credential_type] = source_found or "not_found"
        
        return available
    
    def create_setup_instructions(self) -> str:
        """Generate setup instructions for different environments."""
        instructions = """
# Academic Papers - Credential Setup Instructions

## Method 1: Environment Variables (Recommended for CI/CD)
```bash
export ETH_USERNAME="your_eth_username"
export ETH_PASSWORD="your_eth_password_here"
```

## Method 2: Encrypted Files (Recommended for local automation)
```python
from secure_credential_manager import SecureCredentialManager

manager = SecureCredentialManager()
manager.store_credential("eth_username", "your_eth_username", "file")
manager.store_credential("eth_password", "your_eth_password", "file")
```

## Method 3: System Keyring (Development only)
```python
import keyring
keyring.set_password("academic_papers", "eth_username", "your_eth_username")
keyring.set_password("academic_papers", "eth_password", "your_eth_password")
```

## Docker/Container Setup
```dockerfile
ENV ETH_USERNAME=your_username
ENV ETH_PASSWORD=your_password
```

## Verification
```python
from secure_credential_manager import SecureCredentialManager
manager = SecureCredentialManager()
print(manager.list_available_credentials())
```
"""
        return instructions


# Global instance
_credential_manager: Optional[SecureCredentialManager] = None


def get_credential_manager() -> SecureCredentialManager:
    """Get or create the global credential manager."""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = SecureCredentialManager()
    return _credential_manager


def setup_eth_credentials_from_env() -> bool:
    """Quick setup from environment variables."""
    username = os.getenv("ETH_USERNAME")
    password = os.getenv("ETH_PASSWORD")
    
    if not username or not password:
        logger.error("ETH_USERNAME and ETH_PASSWORD environment variables required")
        return False
    
    manager = get_credential_manager()
    success = True
    success &= manager.store_credential("eth_username", username, "file")
    success &= manager.store_credential("eth_password", password, "file")
    
    return success


if __name__ == "__main__":
    # Command line interface for credential setup
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "setup-env":
            success = setup_eth_credentials_from_env()
            if success:
                print("✅ Credentials setup from environment variables")
            else:
                print("❌ Failed to setup credentials")
                sys.exit(1)
        
        elif command == "list":
            manager = get_credential_manager()
            available = manager.list_available_credentials()
            print("Available credentials:")
            for cred, source in available.items():
                print(f"  {cred}: {source}")
        
        elif command == "instructions":
            manager = get_credential_manager()
            print(manager.create_setup_instructions())
        
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    
    else:
        print("Usage:")
        print("  python secure_credential_manager.py setup-env   # Setup from env vars")
        print("  python secure_credential_manager.py list       # List available creds")
        print("  python secure_credential_manager.py instructions # Show setup guide")