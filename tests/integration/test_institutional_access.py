#!/usr/bin/env python3
"""
Test Institutional Access
==========================

Test the existing institutional authentication system to see 
exactly what's working vs. what's failing.
"""

import asyncio
import sys
sys.path.append('src')

from downloader.proper_downloader import ProperAcademicDownloader


async def test_ieee_papers():
    """Test IEEE papers with institutional authentication."""
    print("🏛️  TESTING IEEE INSTITUTIONAL ACCESS")
    print("=" * 50)
    
    ieee_papers = [
        "10.1109/CVPR.2016.90",  # ResNet paper
        "10.1109/TPAMI.2020.2992934",  # Another IEEE paper
        "https://ieeexplore.ieee.org/document/7780459",  # Direct URL
    ]
    
    downloader = ProperAcademicDownloader('test_ieee')
    
    for paper in ieee_papers:
        print(f"\n🧪 Testing IEEE: {paper}")
        
        try:
            result = await downloader.download(paper)
            
            if result.success:
                print(f"   ✅ SUCCESS: {result.source_used}")
                print(f"      File: {result.file_path}")
                print(f"      Size: {result.file_size:,} bytes")
            else:
                print(f"   ❌ FAILED: {result.error}")
                print(f"      This indicates institutional auth isn't working")
                
        except Exception as e:
            print(f"   💥 EXCEPTION: {e}")
    
    await downloader.close()


async def test_siam_papers():
    """Test SIAM papers with institutional authentication."""
    print("\n\n🏛️  TESTING SIAM INSTITUTIONAL ACCESS")
    print("=" * 50)
    
    siam_papers = [
        "10.1137/S0097539795293172",  # SIAM journal DOI
        "https://epubs.siam.org/doi/10.1137/1.9781611974737.1",  # SODA paper
        "10.1137/20M1320493",  # Another SIAM paper
    ]
    
    downloader = ProperAcademicDownloader('test_siam')
    
    for paper in siam_papers:
        print(f"\n🧪 Testing SIAM: {paper}")
        
        try:
            result = await downloader.download(paper)
            
            if result.success:
                print(f"   ✅ SUCCESS: {result.source_used}")
                print(f"      File: {result.file_path}")
                print(f"      Size: {result.file_size:,} bytes")
            else:
                print(f"   ❌ FAILED: {result.error}")
                print(f"      This indicates institutional auth isn't working")
                
        except Exception as e:
            print(f"   💥 EXCEPTION: {e}")
    
    await downloader.close()


async def test_springer_papers():
    """Test Springer papers with institutional authentication."""
    print("\n\n🏛️  TESTING SPRINGER INSTITUTIONAL ACCESS")
    print("=" * 50)
    
    springer_papers = [
        "10.1007/978-3-319-07443-6_15",  # Springer book chapter
        "10.1007/s10994-021-05946-3",  # Springer journal
        "https://link.springer.com/article/10.1007/s10994-021-05946-3",  # Direct URL
    ]
    
    downloader = ProperAcademicDownloader('test_springer')
    
    for paper in springer_papers:
        print(f"\n🧪 Testing Springer: {paper}")
        
        try:
            result = await downloader.download(paper)
            
            if result.success:
                print(f"   ✅ SUCCESS: {result.source_used}")
                print(f"      File: {result.file_path}")
                print(f"      Size: {result.file_size:,} bytes")
            else:
                print(f"   ❌ FAILED: {result.error}")
                print(f"      This indicates institutional auth isn't working")
                
        except Exception as e:
            print(f"   💥 EXCEPTION: {e}")
    
    await downloader.close()


def test_credential_setup():
    """Test ETH credential configuration."""
    print("\n\n🔐 TESTING CREDENTIAL SETUP")
    print("=" * 50)
    
    import os
    
    # Check environment variables
    eth_username = os.environ.get('ETH_USERNAME', '')
    eth_password = os.environ.get('ETH_PASSWORD', '')
    
    if eth_username and eth_password:
        print(f"✅ ETH credentials found:")
        print(f"   Username: {eth_username[:3]}***")
        print(f"   Password: {'*' * len(eth_password)} (length: {len(eth_password)})")
    else:
        print("❌ ETH credentials not configured in environment variables")
        print("   You may need to set ETH_USERNAME and ETH_PASSWORD")
    
    # Check if we can access institutional system
    try:
        sys.path.append('src')
        from publishers import publisher_registry
        from secure_credential_manager import get_credential_manager
        
        print(f"✅ Institutional system imports work")
        
        # Test credential manager
        cm = get_credential_manager()
        print(f"✅ Credential manager available: {type(cm).__name__}")
        
        # Check publisher registry
        print(f"✅ Publisher registry available")
        
    except ImportError as e:
        print(f"❌ Institutional system import failed: {e}")
    except Exception as e:
        print(f"⚠️  Institutional system issue: {e}")


async def main():
    """Test institutional authentication comprehensively."""
    print("🏛️  COMPREHENSIVE INSTITUTIONAL AUTHENTICATION TEST")
    print("=" * 80)
    print("Testing the existing institutional authentication system")
    print("to understand what works vs. what fails.\n")
    
    # Test credential setup first
    test_credential_setup()
    
    # Test each publisher
    await test_ieee_papers()
    await test_siam_papers() 
    await test_springer_papers()
    
    print("\n" + "=" * 80)
    print("🏁 INSTITUTIONAL ACCESS ASSESSMENT")
    print("=" * 80)
    print("If all tests failed, likely causes:")
    print("1. 🌐 Not on ETH network (need VPN or be on campus)")
    print("2. 🔐 Incorrect ETH credentials")
    print("3. 🔧 Authentication system needs browser automation")
    print("4. 🚫 Publishers have changed their authentication flow")
    print("\nFor 100% success rate, institutional access must work from ETH network.")


if __name__ == "__main__":
    asyncio.run(main())