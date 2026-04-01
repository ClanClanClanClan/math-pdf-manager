#!/usr/bin/env python3
"""Quick SIAM verification test"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_siam():
    print("🔍 QUICK SIAM VERIFICATION")
    print("=" * 50)
    
    try:
        from src.publishers.siam_publisher import SIAMPublisher
        from src.publishers import AuthenticationConfig
        from src.secure_credential_manager import get_credential_manager
        
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        if not username or not password:
            print("❌ No ETH credentials")
            return False
            
        print(f"✅ Credentials: {username[:3]}***")
        
        # Test DOI
        test_doi = '10.1137/S0097539795293172'
        
        auth_config = AuthenticationConfig(
            username=username,
            password=password,
            institutional_login='eth'
        )
        siam = SIAMPublisher(auth_config)
        
        output_dir = Path("verify_siam")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "siam_test.pdf"
        
        print(f"\nTesting SIAM download: {test_doi}")
        print("This will open a browser window...")
        
        result = siam.download_paper(test_doi, output_path)
        
        if result.success and output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"\n✅ SUCCESS! Downloaded {size_mb:.2f} MB PDF")
            
            # Verify it's a real PDF
            with open(output_path, 'rb') as f:
                header = f.read(8)
                if header.startswith(b'%PDF'):
                    print("✅ Valid PDF file!")
                    return True
                else:
                    print("❌ Not a valid PDF")
                    return False
        else:
            print(f"\n❌ Failed: {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_siam()
    
    if success:
        print("\n🎉 SIAM IS WORKING PERFECTLY!")
        print("Ready to run ultimate 400 test!")
    else:
        print("\n⚠️ SIAM needs attention")