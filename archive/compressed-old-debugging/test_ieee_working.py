#!/usr/bin/env python3
"""
Test IEEE working
==================

Use the original working IEEE authentication directly.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add both src and tools/security to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "tools" / "security"))

from ieee_working_auth import ieee_working_auth


async def test_working_ieee_auth():
    """Test the working IEEE authentication."""
    print("🔍 TESTING WORKING IEEE AUTHENTICATION")
    print("=" * 60)
    print("Using the original working implementation from tools/security/\n")
    
    success = await ieee_working_auth()
    
    if success:
        print("🎉 SUCCESS: IEEE authentication worked perfectly!")
        
        # Check if PDF was downloaded
        ieee_dir = Path("ieee_working")
        pdf_files = list(ieee_dir.glob("*.pdf"))
        
        if pdf_files:
            for pdf_file in pdf_files:
                size = pdf_file.stat().st_size
                print(f"   📁 Downloaded: {pdf_file.name} ({size:,} bytes)")
        else:
            print("   ⚠️  No PDF files found in ieee_working directory")
            
    else:
        print("❌ IEEE authentication failed")
    
    return success


def test_publisher_with_working_auth():
    """Test publisher with working authentication cookies."""
    print("\n\n🔍 TESTING PUBLISHER WITH WORKING AUTH")
    print("=" * 60)
    
    try:
        sys.path.append('src')
        from publishers.ieee_publisher import IEEEPublisher
        from publishers import AuthenticationConfig
        
        # Create auth config
        auth_config = AuthenticationConfig(
            username=os.environ.get('ETH_USERNAME', ''),
            password=os.environ.get('ETH_PASSWORD', ''),
            institutional_login='eth'
        )
        
        # Create publisher instance
        ieee = IEEEPublisher(auth_config)
        
        print("✅ IEEE publisher created successfully")
        
        # Test download with existing session
        test_paper_id = "7780459"  # ResNet paper
        download_path = Path("test_ieee_working") / f"ieee_{test_paper_id}.pdf"
        download_path.parent.mkdir(exist_ok=True)
        
        print(f"\n📄 Testing IEEE download...")
        print(f"   Paper ID: {test_paper_id}")
        print(f"   Target: {download_path}")
        
        result = ieee.download_paper(test_paper_id, download_path)
        
        if result.success:
            print(f"   ✅ Download successful!")
            print(f"      File: {result.file_path}")
            if download_path.exists():
                print(f"      Size: {download_path.stat().st_size:,} bytes")
        else:
            print(f"   ❌ Download failed: {result.error_message}")
            
    except Exception as e:
        print(f"   💥 Publisher test failed: {e}")


async def main():
    """Run IEEE working tests."""
    print("🎯 IEEE WORKING AUTHENTICATION TEST")
    print("=" * 80)
    print("Testing the original working IEEE implementation.\n")
    
    # Test the working authentication
    auth_success = await test_working_ieee_auth()
    
    # Test publisher integration
    test_publisher_with_working_auth()
    
    print("\n" + "=" * 80)
    print("🏁 RESULTS")
    print("=" * 80)
    
    if auth_success:
        print("✅ The original working IEEE authentication is functional!")
        print("   This proves that institutional access CAN work.")
        print("   The publisher integration may need session cookie sharing.")
    else:
        print("❌ Even the original working authentication failed.")
        print("   May need ETH network access or credential issues.")
    
    print("\n🔧 NEXT STEPS:")
    print("   1. If auth worked: Integrate session cookies into publisher")
    print("   2. If auth failed: Check network/credentials requirements")
    print("   3. Fix publisher implementation to use working auth flow")


if __name__ == "__main__":
    asyncio.run(main())