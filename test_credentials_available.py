#!/usr/bin/env python3
"""
Check what credentials are available in the system
"""

import os
import sys
from pathlib import Path

def check_environment_variables():
    """Check for credentials in environment variables"""
    print("Environment Variables:")
    print("-" * 30)
    
    env_vars = [
        'ETH_USERNAME', 'ETH_PASSWORD',
        'IEEE_USERNAME', 'IEEE_PASSWORD', 
        'SIAM_USERNAME', 'SIAM_PASSWORD',
        'SPRINGER_USERNAME', 'SPRINGER_PASSWORD'
    ]
    
    found_vars = []
    for var in env_vars:
        value = os.getenv(var)
        if value:
            found_vars.append(var)
            print(f"✓ {var}: {'*' * len(value)}")  # Mask the value
        else:
            print(f"✗ {var}: Not set")
    
    return found_vars

def check_credential_files():
    """Check for credential files"""
    print("\nCredential Files:")
    print("-" * 30)
    
    home = Path.home()
    possible_locations = [
        home / ".academic_papers" / "credentials",
        home / ".config" / "academic_papers",
        Path("config"),
        Path("credentials"),
        home / ".credentials"
    ]
    
    found_files = []
    for location in possible_locations:
        if location.exists():
            print(f"✓ Directory exists: {location}")
            # List files in directory
            try:
                files = list(location.glob("*"))
                for file in files:
                    if file.is_file():
                        print(f"  - {file.name}")
                        found_files.append(file)
            except Exception as e:
                print(f"  Error reading directory: {e}")
        else:
            print(f"✗ Directory not found: {location}")
    
    return found_files

def check_secure_credential_manager():
    """Check if SecureCredentialManager can find credentials"""
    print("\nSecure Credential Manager:")
    print("-" * 30)
    
    try:
        from src.secure_credential_manager import SecureCredentialManager
        
        manager = SecureCredentialManager()
        print("✓ SecureCredentialManager loaded")
        
        # Try to get ETH credentials
        try:
            username = manager.get_credential("eth_username")
            password = manager.get_credential("eth_password")
            
            if username and password:
                print(f"✓ ETH credentials found")
                print(f"  Username: {username[:3]}***")
                print(f"  Password: {'*' * len(password)}")
                return True
            else:
                print("✗ ETH credentials not found")
                return False
                
        except Exception as e:
            print(f"✗ Error getting ETH credentials: {e}")
            return False
            
    except ImportError as e:
        print(f"✗ Cannot import SecureCredentialManager: {e}")
        return False

def check_legacy_credentials():
    """Check legacy credential system"""
    print("\nLegacy Credentials:")
    print("-" * 30)
    
    try:
        from src.downloader.credentials import CredentialManager
        
        # Try default location
        cred_file = Path("config/credentials.enc")
        if cred_file.exists():
            print(f"✓ Found legacy credential file: {cred_file}")
            
            # Try to load (would need master password)
            print("  Note: Legacy credentials require master password")
            return True
        else:
            print(f"✗ Legacy credential file not found: {cred_file}")
            return False
            
    except ImportError as e:
        print(f"✗ Cannot import CredentialManager: {e}")
        return False

def main():
    print("Credential Availability Check")
    print("=" * 40)
    
    # Check all sources
    env_vars = check_environment_variables()
    files = check_credential_files()
    secure_mgr = check_secure_credential_manager()
    legacy = check_legacy_credentials()
    
    print("\n" + "=" * 40)
    print("Summary:")
    
    if env_vars:
        print(f"✓ Environment variables: {len(env_vars)} found")
    if files:
        print(f"✓ Credential files: {len(files)} found")
    if secure_mgr:
        print("✓ Secure credential manager: Working")
    if legacy:
        print("✓ Legacy credentials: Available")
    
    if not any([env_vars, files, secure_mgr, legacy]):
        print("✗ No credentials found in any location")
        print("\nTo set up credentials, you can:")
        print("1. Set environment variables: ETH_USERNAME, ETH_PASSWORD")
        print("2. Use the SecureCredentialManager setup")
        print("3. Run the credential setup script")
    else:
        print("\n✓ Credentials are available for testing!")

if __name__ == "__main__":
    main()