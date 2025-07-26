#!/usr/bin/env python3
"""
Test just the login flow for Wiley
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def test_wiley_login():
    """Test just the login process"""
    
    print("🔑 WILEY LOGIN TEST")
    print("=" * 40)
    
    try:
        from src.publishers.wiley_publisher import WileyPublisher
        from src.publishers import AuthenticationConfig
        from src.secure_credential_manager import get_credential_manager
        
        # Get credentials
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        if not (username and password):
            print("❌ No credentials")
            return False
        
        auth_config = AuthenticationConfig(
            username=username,
            password=password,
            institutional_login='eth'
        )
        
        wiley = WileyPublisher(auth_config)
        
        # Test a simple DOI
        test_doi = "10.1002/anie.202004934"
        save_path = Path("test_wiley.pdf")
        
        print(f"🔄 Testing login with DOI: {test_doi}")
        
        result = await wiley.download_paper(test_doi, save_path)
        
        if result.success:
            print("✅ SUCCESS!")
            return True
        else:
            print(f"❌ FAILED: {getattr(result, 'error_message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_wiley_login())
    print(f"\n{'🎉' if success else '💥'} Test {'passed' if success else 'failed'}")