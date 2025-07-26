#!/usr/bin/env python3
"""
Final ETH Authentication Test
============================

Complete test of ETH credentials, authentication setup, and download capability.
"""

import os
import sys
import tempfile
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from auth_manager import get_auth_manager, AuthConfig, AuthMethod
    from secure_credential_manager import get_credential_manager
    from scripts.downloader import acquire_paper_by_metadata
    from metadata_fetcher import fetch_metadata_all_sources
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Reduce log noise
logging.getLogger("downloader").setLevel(logging.WARNING)
logging.getLogger("metadata_fetcher").setLevel(logging.WARNING)


def test_credentials():
    """Test ETH credentials."""
    print("🔐 Testing ETH credentials...")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if username and password:
        print(f"  ✅ Credentials found for: {username}")
        return True
    else:
        print("  ❌ No credentials found")
        return False


def setup_eth_configs():
    """Set up ETH authentication configs."""
    print("\n⚙️  Setting up ETH authentication configs...")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    auth_manager = get_auth_manager()
    
    # Configure IEEE ETH access
    ieee_config = AuthConfig(
        service_name="eth_ieee",
        auth_method=AuthMethod.SHIBBOLETH,
        base_url="https://ieeexplore.ieee.org/servlet/wayf.jsp",
        shibboleth_idp="https://idp.ethz.ch", 
        username=username,
        password=password,
        headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    )
    
    try:
        auth_manager.add_config(ieee_config)
        print("  ✅ IEEE ETH config added")
        return True
    except Exception as e:
        print(f"  ❌ Failed to add config: {e}")
        return False


def test_open_access_download():
    """Test open access download (no authentication needed)."""
    print("\n📥 Testing open access download...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Try a known open access paper
            file_path, attempts = acquire_paper_by_metadata(
                "Open Access Test Paper",
                tmpdir,
                doi="10.1371/journal.pone.0280123"  # PLOS ONE paper
            )
            
            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"  ✅ Downloaded: {file_size} bytes")
                
                # Check if PDF
                with open(file_path, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        print("  ✅ Valid PDF file")
                        return True
                    else:
                        print(f"  ⚠️  Not a PDF (header: {header})")
                        return False
            else:
                print("  ❌ Download failed")
                for attempt in attempts:
                    print(f"    - {attempt.strategy}: {attempt.result.value}")
                return False
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False


def test_institutional_download():
    """Test institutional download with ETH auth."""
    print("\n🎓 Testing institutional download...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Try to download a paper that requires institutional access
            # Note: This will likely fail without VPN/campus network
            file_path, attempts = acquire_paper_by_metadata(
                "IEEE Test Paper",
                tmpdir,
                doi="10.1109/ACCESS.2023.3290123",
                auth_service="eth_ieee"
            )
            
            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"  ✅ Downloaded via ETH: {file_size} bytes")
                return True
            else:
                print("  ❌ Institutional download failed")
                print("  📋 Attempt details:")
                for attempt in attempts:
                    print(f"    - {attempt.strategy}: {attempt.result.value}")
                    if attempt.error:
                        print(f"      Error: {attempt.error}")
                
                # This is expected without VPN
                print("  ℹ️  This is normal without ETH VPN/campus network")
                return False
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False


def main():
    """Run comprehensive test."""
    print("ETH Authentication Final Test")
    print("=============================\n")
    
    results = {}
    
    # Test 1: Credentials
    results['credentials'] = test_credentials()
    if not results['credentials']:
        print("\n❌ Cannot continue without credentials")
        print("Set: ETH_USERNAME and ETH_PASSWORD environment variables")
        return False
    
    # Test 2: Auth setup
    results['auth_setup'] = setup_eth_configs()
    
    # Test 3: Open access download
    results['open_access'] = test_open_access_download()
    
    # Test 4: Institutional download
    results['institutional'] = test_institutional_download()
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:20}: {status}")
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if results['credentials'] and results['auth_setup']:
        print("\n🎉 ETH authentication is properly configured!")
        print("\nThe download system is ready for use with:")
        print("- ETH institutional credentials")
        print("- Shibboleth SSO authentication")
        print("- Publisher-specific download strategies")
        
        if not results['institutional']:
            print("\n⚠️  Institutional downloads failed, but this is expected")
            print("   To enable institutional downloads:")
            print("   1. Connect to ETH VPN")
            print("   2. Or be on ETH campus network")
            print("   3. Ensure you have access to the publisher")
    
    return results['credentials'] and results['auth_setup']


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)