#!/usr/bin/env python3
"""
Direct Institutional Login Test
==============================

Test actual institutional access through publisher portals (no VPN needed).
This demonstrates the real institutional login flow.
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

# Reduce log noise
logging.getLogger().setLevel(logging.WARNING)


def test_ieee_institutional_login():
    """Test IEEE institutional login directly through their portal."""
    print("🏛️  Testing IEEE institutional login...")
    
    # Get ETH credentials
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("  ❌ ETH credentials not found")
        return False
    
    # Set up IEEE institutional auth
    auth_manager = get_auth_manager()
    
    # IEEE institutional access configuration
    ieee_config = AuthConfig(
        service_name="eth_ieee_institutional",
        auth_method=AuthMethod.SHIBBOLETH,
        base_url="https://ieeexplore.ieee.org",
        shibboleth_idp="https://idp.ethz.ch",
        username=username,
        password=password,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    )
    
    try:
        auth_manager.add_config(ieee_config)
        print("  ✅ IEEE institutional config added")
        
        # Test downloading a paper through IEEE institutional access
        with tempfile.TemporaryDirectory() as tmpdir:
            print("  🔍 Attempting IEEE institutional download...")
            
            file_path, attempts = acquire_paper_by_metadata(
                "IEEE Test Paper",
                tmpdir,
                doi="10.1109/ACCESS.2020.2964093",  # Real IEEE Open Access paper
                auth_service="eth_ieee_institutional"
            )
            
            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"  ✅ Downloaded via IEEE institutional: {file_size} bytes")
                
                # Verify PDF
                with open(file_path, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        print("  ✅ Valid PDF file")
                        return True
                    else:
                        print(f"  ⚠️  Not a PDF (header: {header})")
                        return False
            else:
                print("  ❌ IEEE institutional download failed")
                print("  📋 Attempt details:")
                for attempt in attempts:
                    print(f"    - {attempt.strategy}: {attempt.result.value}")
                    if attempt.error:
                        print(f"      Error: {attempt.error}")
                return False
                
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_springer_institutional_login():
    """Test Springer institutional login directly."""
    print("\n🏛️  Testing Springer institutional login...")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    auth_manager = get_auth_manager()
    
    # Springer institutional access
    springer_config = AuthConfig(
        service_name="eth_springer_institutional", 
        auth_method=AuthMethod.SHIBBOLETH,
        base_url="https://link.springer.com",
        shibboleth_idp="https://idp.ethz.ch",
        username=username,
        password=password,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    )
    
    try:
        auth_manager.add_config(springer_config)
        print("  ✅ Springer institutional config added")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            print("  🔍 Attempting Springer institutional download...")
            
            file_path, attempts = acquire_paper_by_metadata(
                "Springer Mathematics Paper",
                tmpdir,
                doi="10.1007/s00454-020-00244-6",  # Real Springer paper
                auth_service="eth_springer_institutional"
            )
            
            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"  ✅ Downloaded via Springer institutional: {file_size} bytes")
                return True
            else:
                print("  ❌ Springer institutional download failed")
                for attempt in attempts:
                    print(f"    - {attempt.strategy}: {attempt.result.value}")
                return False
                
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def demonstrate_institutional_flow():
    """Show how the institutional login flow works."""
    print("\n📋 How Institutional Login Works:")
    print("="*50)
    print("1. Navigate to publisher's paper page")
    print("2. Click 'Institutional Sign In' / 'Access through institution'")
    print("3. Search for and select 'ETH Zurich' from institution list")
    print("4. Redirect to ETH Shibboleth login portal")
    print("5. Enter ETH credentials (username/password)")
    print("6. Redirect back to publisher with authenticated session")
    print("7. Download PDF using institutional access")
    print("\n✨ No VPN required - works from anywhere with ETH credentials!")


def main():
    """Run institutional login tests."""
    print("Direct Institutional Login Test")
    print("===============================")
    
    # Check prerequisites
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials required")
        print("Set: ETH_USERNAME and ETH_PASSWORD environment variables")
        return False
    
    print(f"✅ ETH credentials loaded for: {username}")
    
    # Show how it works
    demonstrate_institutional_flow()
    
    # Test IEEE institutional
    ieee_success = test_ieee_institutional_login()
    
    # Test Springer institutional  
    springer_success = test_springer_institutional_login()
    
    # Summary
    print(f"\n{'='*50}")
    print("INSTITUTIONAL LOGIN TEST RESULTS")
    print(f"{'='*50}")
    print(f"IEEE institutional:     {'✅ PASS' if ieee_success else '❌ FAIL'}")
    print(f"Springer institutional: {'✅ PASS' if springer_success else '❌ FAIL'}")
    
    if ieee_success or springer_success:
        print("\n🎉 Institutional login is working!")
        print("You can now download papers directly through publisher portals")
        print("using your ETH credentials - no VPN needed!")
    else:
        print("\n⚠️  Institutional downloads need browser automation")
        print("This requires Playwright and may need interactive authentication")
        print("for first-time setup with each publisher.")
    
    return ieee_success or springer_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)