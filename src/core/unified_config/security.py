#!/usr/bin/env python3
"""
Unified Configuration System - Security

Provides security features for configuration management.
"""

import os
import base64
from typing import Any
from cryptography.fernet import Fernet

from .interfaces import ConfigSecurityLevel


class ConfigSecurityManager:
    """Manages security for configuration values."""
    
    def __init__(self):
        self._encryption_key = self._get_or_create_key()
        self._cipher = Fernet(self._encryption_key) if self._encryption_key else None
    
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key."""
        key_env = os.environ.get('CONFIG_ENCRYPTION_KEY')
        if key_env:
            return base64.urlsafe_b64decode(key_env.encode())
        
        # For development, create a key (in production, this should be managed securely)
        return Fernet.generate_key()
    
    def encrypt_if_needed(self, value: Any, security_level: ConfigSecurityLevel) -> Any:
        """Encrypt value if security level requires it."""
        if security_level == ConfigSecurityLevel.SECRET and self._cipher:
            if isinstance(value, str):
                encrypted = self._cipher.encrypt(value.encode())
                return base64.urlsafe_b64encode(encrypted).decode()
        
        return value
    
    def decrypt_if_needed(self, value: Any) -> Any:
        """Decrypt value if it appears to be encrypted."""
        if isinstance(value, str) and self._cipher:
            try:
                # Check if it looks like our encrypted format
                if self._looks_encrypted(value):
                    encrypted_bytes = base64.urlsafe_b64decode(value.encode())
                    decrypted = self._cipher.decrypt(encrypted_bytes)
                    return decrypted.decode()
            except Exception:
                pass  # Not encrypted or failed to decrypt
        
        return value
    
    def _looks_encrypted(self, value: str) -> bool:
        """Heuristic to check if a string looks encrypted."""
        try:
            base64.urlsafe_b64decode(value.encode())
            # If it's valid base64 and long enough, might be encrypted
            return len(value) > 40 and not any(c in value for c in [' ', '.', '/', '\\'])
        except (ValueError, TypeError):
            return False
    
    def should_encrypt(self, config_value) -> bool:
        """Check if a configuration value should be encrypted."""
        return config_value.security_level in [ConfigSecurityLevel.SENSITIVE, ConfigSecurityLevel.SECRET]
    
    def encrypt_value(self, config_value) -> str:
        """Encrypt a configuration value."""
        if not self._cipher:
            return str(config_value.value)
        
        if isinstance(config_value.value, str):
            encrypted = self._cipher.encrypt(config_value.value.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        
        return str(config_value.value)
    
    def decrypt_value(self, encrypted_value: str, config_value) -> str:
        """Decrypt an encrypted configuration value."""
        if not self._cipher:
            return encrypted_value
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted = self._cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception:
            return encrypted_value  # Return as-is if decryption fails
