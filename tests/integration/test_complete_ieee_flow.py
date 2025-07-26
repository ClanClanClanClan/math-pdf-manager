#!/usr/bin/env python3
"""
Test Complete IEEE Flow
======================

Test the complete IEEE publisher flow: authentication + download
"""

import sys
from pathlib import Path

# Add src to path  
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.publishers.ieee_publisher import IEEEPublisher
from src.publishers import AuthenticationConfig
from src.secure_credential_manager import get_credential_manager

def test_complete_ieee_flow():
    """Test complete IEEE authentication and download flow."""
    
    # Enable debug logging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    print("🧪 TESTING COMPLETE IEEE FLOW")
    print("=" * 40)
    
    # Get credentials
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        print("❌ No ETH credentials found!")
        # Skip test if no credentials available
        import pytest
        pytest.skip("No ETH credentials found for IEEE flow test")
    
    print(f"🔑 ETH credentials: {username}")
    
    # Create authentication config
    auth_config = AuthenticationConfig(
        username=username,
        password=password,
        institutional_login='eth'
    )
    
    # Create IEEE publisher
    ieee = IEEEPublisher(auth_config)
    
    print("\n1️⃣ Testing authentication...")
    auth_success = ieee.authenticate()
    
    if auth_success:
        print("✅ Authentication successful!")
        
        # Check if we have cookies
        if ieee.session and ieee.session.cookies:
            cookie_count = len(ieee.session.cookies)
            print(f"✅ Session has {cookie_count} cookies")
            
            # Show some cookie info (without values for security)
            for cookie in ieee.session.cookies:
                print(f"   Cookie: {cookie.name} (domain: {cookie.domain})")
        else:
            print("⚠️ No session or cookies found!")
        
        print("\n2️⃣ Testing document ID extraction...")
        test_doi = "10.1109/JPROC.2018.2820126"
        doc_id = ieee._extract_document_id(test_doi)
        
        if doc_id:
            print(f"✅ Document ID extracted: {doc_id}")
        else:
            print("❌ Failed to extract document ID")
            assert False, "Failed to extract document ID"
        
        print("\n3️⃣ Testing PDF download...")
        output_dir = Path("complete_ieee_test")
        output_dir.mkdir(exist_ok=True)
        
        download_path = output_dir / f"ieee_paper_{doc_id}.pdf"
        result = ieee.download_paper(test_doi, download_path)
        
        if result.success:
            file_size = download_path.stat().st_size
            print(f"🎉 SUCCESS! PDF downloaded: {download_path}")
            print(f"📊 File size: {file_size:,} bytes")
            
            # Basic validation
            if file_size > 100000:  # At least 100KB
                with open(download_path, 'rb') as f:
                    header = f.read(8)
                    if header.startswith(b'%PDF'):
                        print("✅ Valid PDF header confirmed")
                        assert True, "IEEE flow test completed successfully"
                    else:
                        print("⚠️ Invalid PDF header")
                        assert False, "Invalid PDF header"
            else:
                print("⚠️ File size seems too small")
                assert False, "Downloaded file size too small"
        else:
            print(f"❌ Download failed: {result.error_message}")
            assert False, f"Download failed: {result.error_message}"
    else:
        print("❌ Authentication failed!")
        assert False, "Authentication failed"

if __name__ == "__main__":
    success = test_complete_ieee_flow()
    
    if success:
        print(f"\n🎉 COMPLETE IEEE FLOW SUCCESS!")
        print("✅ Authentication works")
        print("✅ Document ID extraction works") 
        print("✅ PDF download works")
        print("✅ File validation works")
    else:
        print(f"\n❌ IEEE flow test failed")
    
    exit(0 if success else 1)