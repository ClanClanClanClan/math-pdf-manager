"""
Secure Credential Storage

Secure credential storage using system keyring and encryption.
Extracted from auth_manager.py for better modularity.
"""

import os
import json
import base64
import logging
from pathlib import Path
from typing import Optional

# Cryptography imports
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

# Keyring import
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

logger = logging.getLogger(__name__)


class CredentialStore:
    """Secure credential storage using system keyring and encryption."""

    def __init__(self, app_name: str = "academic_papers"):
        self.app_name = app_name
        self.config_dir = Path.home() / ".academic_papers" / "auth"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "auth_config.json"
        self._init_encryption()

    def _init_encryption(self):
        """Initialize encryption key for sensitive data."""
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning(
                "Cryptography not available - falling back to basic encoding"
            )
            self.fernet = None
            return

        key_file = self.config_dir / ".key"
        if key_file.exists():
            with open(key_file, "rb") as f:
                self.fernet = Fernet(f.read())
        else:
            # Generate new key
            password = os.urandom(32)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"academic_papers_salt",
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            self.fernet = Fernet(key)
            with open(key_file, "wb") as f:
                f.write(key)
            # Restrict permissions
            os.chmod(key_file, 0o600)

    def store_credential(self, service: str, username: str, password: str):
        """Store credentials securely in system keyring."""
        if not KEYRING_AVAILABLE:
            logger.warning("Keyring not available - using fallback storage")
            self._store_encrypted(service, username, password)
            return
            
        try:
            keyring.set_password(self.app_name, f"{service}:{username}", password)
            logger.info(f"Stored credentials for {service}:{username}")
        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
            # Fallback to encrypted file storage
            self._store_encrypted(service, username, password)

    def get_credential(self, service: str, username: str) -> Optional[str]:
        """Retrieve password from keyring."""
        if KEYRING_AVAILABLE:
            try:
                password = keyring.get_password(self.app_name, f"{service}:{username}")
                if password:
                    return password
            except Exception as e:
                logger.warning(f"Keyring retrieval failed: {e}")

        # Try encrypted file storage
        return self._get_encrypted(service, username)

    def _store_encrypted(self, service: str, username: str, password: str):
        """Fallback encrypted storage."""
        creds_file = self.config_dir / f"{service}_creds.enc"
        if self.fernet:
            # Use proper encryption if available
            encrypted_password = self.fernet.encrypt(password.encode()).decode()
        else:
            # Fallback to base64 encoding (not secure but functional)
            encrypted_password = base64.b64encode(password.encode()).decode()

        data = {"username": username, "password": encrypted_password}
        with open(creds_file, "w") as f:
            json.dump(data, f)
        os.chmod(creds_file, 0o600)

    def _get_encrypted(self, service: str, username: str) -> Optional[str]:
        """Retrieve from encrypted storage."""
        creds_file = self.config_dir / f"{service}_creds.enc"
        if not creds_file.exists():
            return None

        try:
            with open(creds_file, "r") as f:
                data = json.load(f)
            if data.get("username") == username:
                if self.fernet:
                    # Use proper decryption if available
                    return self.fernet.decrypt(data["password"].encode()).decode()
                else:
                    # Fallback to base64 decoding
                    return base64.b64decode(data["password"].encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt credentials: {e}")
        return None