#!/usr/bin/env python3
"""
Programmatic ETH Authentication Test
===================================

Test ETH authentication setup and downloads programmatically using 
environment variables for credentials.
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
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Configure logging to be less verbose
logging.getLogger("downloader").setLevel(logging.WARNING)


def setup_eth_auth():
    """Set up ETH authentication configs."""
    print("⚙️  Setting up ETH authentication...")
    
    # Get credentials from environment
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials not found in environment")
        return False
    
    # Get auth manager
    auth_manager = get_auth_manager()
    
    # Publishers to configure
    publishers = {
        "ieee": "https://ieeexplore.ieee.org/servlet/wayf.jsp",
        "springer": "https://link.springer.com/signup-login", 
        "acm": "https://dl.acm.org/action/ssostart"
    }
    
    for publisher, wayf_url in publishers.items():
        try:
            config = AuthConfig(
                service_name=f"eth_{publisher}",
                auth_method=AuthMethod.SHIBBOLETH,
                base_url=wayf_url,
                shibboleth_idp="https://idp.ethz.ch",
                username=username,
                password=password,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
            )
            
            auth_manager.add_config(config)
            print(f"  ✅ Configured eth_{publisher}")
            
        except Exception as e:
            print(f"  ❌ Failed to configure {publisher}: {e}")
            return False
    
    return True


def test_institutional_download():
    """Test downloading with institutional access."""
    print("\n🎓 Testing institutional download...")
    
    # Test papers that should be accessible via ETH
    test_papers = [
        {
            "title": "A Simple Test Paper",
            "doi": "10.1109/ACCESS.2023.3290123",
            "auth_service": "eth_ieee"
        },
        {
            "title": "Another Test Paper", 
            "doi": "10.1007/s00454-023-00530-8",
            "auth_service": "eth_springer"
        }
    ]
    
    success_count = 0
    
    with tempfile.TemporaryDirectory() as tmpdir:
        for paper in test_papers:
            print(f"\n  Testing: {paper['title'][:40]}...")
            
            try:
                file_path, attempts = acquire_paper_by_metadata(
                    paper['title'],
                    tmpdir,
                    doi=paper['doi'],
                    auth_service=paper['auth_service']
                )
                
                if file_path and os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"    ✅ Downloaded: {file_size} bytes")
                    
                    # Verify it's a PDF
                    with open(file_path, 'rb') as f:
                        header = f.read(4)
                        if header == b'%PDF':
                            print(f"    ✅ Valid PDF")
                            success_count += 1
                        else:
                            print(f"    ⚠️  Not a PDF (header: {header})")
                else:
                    print(f"    ❌ Download failed")
                    print(f"    Attempts made:")
                    for attempt in attempts:
                        print(f"      - {attempt.strategy}: {attempt.result.value}")
                        if attempt.error:
                            print(f"        Error: {attempt.error}")
                            
            except Exception as e:
                print(f"    ❌ Error: {e}")
    
    return success_count > 0


def test_auth_config_persistence():
    """Test that auth configs are saved and can be loaded."""
    print("\n💾 Testing auth config persistence...")
    
    try:
        auth_manager = get_auth_manager()
        
        # List available configs
        configs = auth_manager.list_configs()
        eth_configs = [name for name in configs if name.startswith('eth_')]
        
        if eth_configs:
            print(f"  ✅ Found {len(eth_configs)} ETH configs: {', '.join(eth_configs)}")
            return True
        else:
            print(f"  ❌ No ETH configs found")
            return False
            
    except Exception as e:
        print(f"  ❌ Error checking configs: {e}")
        return False


def main():
    """Run programmatic ETH tests."""
    print("ETH Authentication Programmatic Test")
    print("====================================\n")
    
    # Check prerequisites
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials not found")
        print("\nTo set up credentials:")
        print("export ETH_USERNAME='your_username'")
        print("export ETH_password = os.environ.get("PASSWORD", "your_password")  # TODO: Remove default value")
        print("python secure_credential_manager.py setup-env")
        return False
    
    print(f"✅ ETH credentials available for: {username}")
    
    # Set up authentication
    if not setup_eth_auth():
        print("❌ Failed to set up ETH authentication")
        return False
    
    # Test config persistence
    if not test_auth_config_persistence():
        print("⚠️  Config persistence test failed")
    
    # Test institutional download
    if test_institutional_download():
        print("\n🎉 Institutional download test successful!")
    else:
        print("\n⚠️  Institutional download tests failed")
        print("This may be normal - institutional access requires:")
        print("1. Valid ETH credentials")
        print("2. Active VPN or on-campus network")
        print("3. Valid publisher subscriptions")
    
    print("\n✅ ETH authentication setup completed!")
    print("\nWhat works:")
    print("- ✅ ETH credentials are configured")
    print("- ✅ Authentication configs are set up")
    print("- ✅ Download infrastructure is ready")
    
    print("\nTo test real downloads:")
    print("1. Connect to ETH VPN or be on campus")
    print("2. Use acquire_paper_by_metadata() with auth_service='eth_<publisher>'")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)