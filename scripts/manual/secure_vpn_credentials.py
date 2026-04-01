#!/usr/bin/env python3
"""
SECURE VPN CREDENTIALS
======================

Securely store VPN password forever
"""

import os
import json
from pathlib import Path
from cryptography.fernet import Fernet
import keyring

class SecureVPNCredentials:
    """Securely store and retrieve VPN credentials"""
    
    def __init__(self):
        self.service_name = "ETH_VPN_AUTO"
        self.username_key = "eth_username"
        self.password_key = "eth_password"
        
    def store_password_securely(self, password):
        """Store password in macOS Keychain"""
        try:
            # Store in macOS Keychain (most secure)
            keyring.set_password(self.service_name, self.password_key, password)
            print("✅ Password stored securely in macOS Keychain")
            
            # Also create encrypted backup
            self._create_encrypted_backup(password)
            
            return True
        except Exception as e:
            print(f"❌ Error storing password: {e}")
            return False
    
    def get_password(self):
        """Retrieve password from secure storage"""
        try:
            # Try macOS Keychain first
            password = keyring.get_password(self.service_name, self.password_key)
            if password:
                return password
            
            # Try encrypted backup
            password = self._read_encrypted_backup()
            if password:
                # Restore to keychain
                keyring.set_password(self.service_name, self.password_key, password)
                return password
                
        except Exception as e:
            print(f"❌ Error retrieving password: {e}")
        
        return None
    
    def _create_encrypted_backup(self, password):
        """Create encrypted backup file"""
        try:
            # Generate key
            key = Fernet.generate_key()
            fernet = Fernet(key)
            
            # Encrypt password
            encrypted_password = fernet.encrypt(password.encode())
            
            # Save to hidden file
            backup_dir = Path.home() / ".eth_vpn_secure"
            backup_dir.mkdir(exist_ok=True)
            
            # Save encrypted password
            (backup_dir / "pwd.enc").write_bytes(encrypted_password)
            
            # Save key separately (still on same machine, but separated)
            (backup_dir / "key.enc").write_bytes(key)
            
            # Set restrictive permissions
            os.chmod(backup_dir, 0o700)
            os.chmod(backup_dir / "pwd.enc", 0o600)
            os.chmod(backup_dir / "key.enc", 0o600)
            
            print("✅ Created encrypted backup")
            
        except Exception as e:
            print(f"⚠️ Backup creation error: {e}")
    
    def _read_encrypted_backup(self):
        """Read from encrypted backup"""
        try:
            backup_dir = Path.home() / ".eth_vpn_secure"
            
            if not backup_dir.exists():
                return None
            
            # Read key and encrypted password
            key = (backup_dir / "key.enc").read_bytes()
            encrypted_password = (backup_dir / "pwd.enc").read_bytes()
            
            # Decrypt
            fernet = Fernet(key)
            password = fernet.decrypt(encrypted_password).decode()
            
            return password
            
        except Exception as e:
            print(f"⚠️ Backup read error: {e}")
            return None

def store_vpn_password(password):
    """Store the VPN password securely"""
    manager = SecureVPNCredentials()
    success = manager.store_password_securely(password)
    
    if success:
        # Verify storage
        retrieved = manager.get_password()
        if retrieved == password:
            print("✅ Password stored and verified successfully!")
            print("🔒 Password will be available forever (survives reboots)")
            return True
    
    return False

def get_vpn_password():
    """Get the stored VPN password"""
    manager = SecureVPNCredentials()
    return manager.get_password()

if __name__ == "__main__":
    # Store the password securely
    password = "LmQBCqkuxgbNUFBYMyXJmuTAU2g8yLY"
    store_vpn_password(password)