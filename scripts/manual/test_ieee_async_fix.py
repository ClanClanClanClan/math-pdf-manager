#!/usr/bin/env python3
"""
Test IEEE Async Fix
===================

Quick test to verify IEEE async issue is resolved.
"""

import sys
import asyncio
import concurrent.futures
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def test_ieee_single():
    """Test single IEEE download with async fix"""
    print("🔧 Testing IEEE async fix...")
    
    try:
        from src.publishers.ieee_publisher import IEEEPublisher
        from src.publishers import AuthenticationConfig
        from src.secure_credential_manager import get_credential_manager
        
        # Get credentials
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        if not username or not password:
            print("❌ No ETH credentials available")
            return False
        
        # Create publisher
        auth_config = AuthenticationConfig(
            username=username,
            password=password,
            institutional_login='eth'
        )
        ieee = IEEEPublisher(auth_config)
        
        # Test DOI
        test_doi = "10.1109/5.726791"
        output_path = Path("test_ieee_async.pdf")
        
        print(f"Downloading {test_doi}...")
        
        # Use ThreadPoolExecutor to handle sync function in async context
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(ieee.download_paper, test_doi, output_path)
            result = future.result(timeout=180)  # 3 minute timeout
        
        if result.success and output_path.exists():
            # Verify PDF
            with open(output_path, 'rb') as f:
                header = f.read(8)
                if header.startswith(b'%PDF'):
                    size_kb = output_path.stat().st_size / 1024
                    print(f"✅ IEEE download successful! ({size_kb:.0f} KB)")
                    return True
                else:
                    print("❌ Invalid PDF downloaded")
                    output_path.unlink()
                    return False
        else:
            error_msg = result.error_message if hasattr(result, 'error_message') else 'Unknown'
            print(f"❌ IEEE download failed: {error_msg}")
            return False
            
    except Exception as e:
        print(f"💥 Exception during IEEE test: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ieee_single())
    if success:
        print("🎉 IEEE async fix is working!")
    else:
        print("💀 IEEE async fix still has issues")