#!/usr/bin/env python3
"""
Interactive Credential Setup
============================

Simple script to securely store ETH credentials.
"""

import getpass
import sys
from secure_credential_manager import get_credential_manager

def setup_credentials_interactive():
    """Interactive credential setup with secure password input."""
    print("🔐 ETH Credential Setup")
    print("=" * 30)
    
    # Get username
    username = input("ETH Username: ").strip()
    if not username:
        print("❌ Username cannot be empty")
        return False
    
    # Get password securely (won't echo to screen)
    password = getpass.getpass("ETH Password: ")
    if not password:
        print("❌ Password cannot be empty")
        return False
    
    # Store credentials
    manager = get_credential_manager()
    success = manager.setup_credentials_from_dict({
        "eth_username": username,
        "eth_password": password
    })
    
    if success:
        print(f"✅ Credentials stored securely for: {username}")
        print("🔒 Credentials are encrypted and machine-specific")
        
        # Verify storage
        available = manager.list_available_credentials()
        print("\n📊 Available credentials:")
        for cred, source in available.items():
            print(f"  {cred}: {source}")
        
        return True
    else:
        print("❌ Failed to store credentials")
        return False

def setup_credentials_programmatic(username: str, password: str):
    """Programmatic credential setup."""
    manager = get_credential_manager()
    success = manager.setup_credentials_from_dict({
        "eth_username": username,
        "eth_password": password
    })
    
    if success:
        print(f"✅ Credentials stored securely for: {username}")
        return True
    else:
        print("❌ Failed to store credentials")
        return False

if __name__ == "__main__":
    if len(sys.argv) == 3:
        # Command line usage: python setup_credentials.py username password
        username, password = sys.argv[1], sys.argv[2]
        success = setup_credentials_programmatic(username, password)
    else:
        # Interactive usage
        success = setup_credentials_interactive()
    
    if success:
        print("\n🚀 Next step: Run the ETH setup")
        print("python automated_eth_setup.py")
    else:
        sys.exit(1)