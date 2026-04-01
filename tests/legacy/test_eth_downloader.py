#!/usr/bin/env python3
"""
Test script for ETH Publisher Downloader
Provides example URLs and usage instructions
"""

import asyncio
import sys
from pathlib import Path

# Test URLs from different publishers (these should be accessible via ETH)
TEST_PAPERS = {
    'ieee': [
        '10.1109/JPROC.2018.2820126',  # A well-known IEEE paper
        'https://ieeexplore.ieee.org/document/8347162',
    ],
    'springer': [
        '10.1007/s10994-018-5759-4',  # Machine Learning journal
        'https://link.springer.com/article/10.1007/s10994-018-5759-4',
    ],
    'nature': [
        '10.1038/s41586-019-1666-5',  # Nature paper
        'https://www.nature.com/articles/s41586-019-1666-5',
    ],
    'wiley': [
        '10.1002/nav.21692',  # Naval Research Logistics
        'https://onlinelibrary.wiley.com/doi/10.1002/nav.21692',
    ]
}

def print_usage():
    """Print usage instructions"""
    print("🏛️  ETH Publisher Downloader - Usage Guide")
    print("=" * 50)
    print()
    print("This tool downloads papers from publishers using your ETH institutional access.")
    print("It supports IEEE, Springer, Nature, Wiley, and Elsevier.")
    print()
    print("📋 REQUIREMENTS:")
    print("1. Valid ETH Zurich credentials")
    print("2. VPN connection to ETH network (if off-campus)")
    print("3. Python packages: playwright, requests")
    print("   Install with: pip install playwright requests")
    print("   Then run: playwright install chromium")
    print()
    print("🚀 USAGE:")
    print("python3 eth_publisher_downloader.py <paper_url_or_doi> [options]")
    print()
    print("📝 EXAMPLES:")
    print()
    
    for publisher, urls in TEST_PAPERS.items():
        print(f"  {publisher.upper()}:")
        for url in urls:
            print(f"    python3 eth_publisher_downloader.py '{url}'")
        print()
    
    print("📁 BATCH DOWNLOAD:")
    print("python3 eth_publisher_downloader.py \\")
    print("  '10.1109/JPROC.2018.2820126' \\")
    print("  '10.1007/s10994-018-5759-4' \\")
    print("  '10.1038/s41586-019-1666-5' \\")
    print("  --output-dir ./papers/")
    print()
    print("⚙️  OPTIONS:")
    print("  --username, -u     : ETH username (optional, will prompt if not provided)")
    print("  --output-dir, -o   : Output directory for downloaded papers")
    print("  --interactive, -i  : Interactive mode")
    print()
    print("🔐 AUTHENTICATION FLOW:")
    print("1. Tool opens browser and navigates to publisher")
    print("2. Clicks 'Institutional Access' link")
    print("3. Searches for and selects 'ETH Zurich'")
    print("4. Redirects to ETH login page")
    print("5. Enters your ETH credentials")
    print("6. Returns to publisher with authenticated session")
    print("7. Downloads PDF using authenticated access")
    print()
    print("💡 TIPS:")
    print("- Make sure you're connected to ETH VPN if off-campus")
    print("- The browser will open visually so you can see the authentication process")
    print("- First time may be slower as it needs to authenticate")
    print("- Subsequent downloads in the same session will be faster")
    print()

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    try:
        import requests
        print("✅ requests - OK")
    except ImportError:
        print("❌ requests - MISSING")
        print("   Install with: pip install requests")
        return False
    
    try:
        import playwright
        print("✅ playwright - OK")
        
        # Check if browsers are installed
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                print("✅ chromium browser - OK")
            except Exception:
                print("❌ chromium browser - MISSING")
                print("   Install with: playwright install chromium")
                return False
                
    except ImportError:
        print("❌ playwright - MISSING")
        print("   Install with: pip install playwright")
        print("   Then run: playwright install chromium")
        return False
    
    print("✅ All dependencies satisfied!")
    return True

async def test_publisher_identification():
    """Test publisher identification from URLs"""
    print("\n🧪 Testing publisher identification...")
    
    # Import our downloader
    try:
        from eth_publisher_downloader import ETHPublisherDownloader
    except ImportError:
        print("❌ Could not import ETHPublisherDownloader")
        return False
    
    downloader = ETHPublisherDownloader()
    
    test_cases = [
        ('10.1109/JPROC.2018.2820126', 'ieee'),
        ('https://ieeexplore.ieee.org/document/8347162', 'ieee'),
        ('10.1007/s10994-018-5759-4', 'springer'),
        ('https://link.springer.com/article/10.1007/s10994-018-5759-4', 'springer'),
        ('10.1038/s41586-019-1666-5', 'nature'),
        ('10.1002/nav.21692', 'wiley'),
        ('10.1016/j.neunet.2019.08.025', 'elsevier'),
    ]
    
    all_correct = True
    for url, expected in test_cases:
        result = downloader.identify_publisher_from_url(url)
        if result == expected:
            print(f"✅ {url} -> {result}")
        else:
            print(f"❌ {url} -> {result} (expected {expected})")
            all_correct = False
    
    if all_correct:
        print("✅ Publisher identification working correctly!")
    else:
        print("❌ Some publisher identification tests failed")
    
    return all_correct

def main():
    """Main test interface"""
    print_usage()
    
    print("\n" + "="*50)
    print("🔧 SYSTEM CHECK")
    print("="*50)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Please install missing dependencies before using the downloader")
        sys.exit(1)
    
    # Test publisher identification
    asyncio.run(test_publisher_identification())
    
    print("\n" + "="*50)
    print("🎯 QUICK TEST")
    print("="*50)
    
    print("\nTo test the downloader with a real paper, try:")
    print()
    print("python3 eth_publisher_downloader.py '10.1109/JPROC.2018.2820126'")
    print()
    print("This will:")
    print("1. Identify the paper as IEEE Xplore")
    print("2. Open browser for ETH authentication")
    print("3. Prompt for your ETH credentials")
    print("4. Download the PDF if successful")
    print()
    print("📋 REMEMBER:")
    print("- Have your ETH username and password ready")
    print("- Be connected to ETH VPN if off-campus")
    print("- The browser will open visually during authentication")
    print()
    
    # Offer to run a test
    user_input = input("Would you like to run a quick test now? (y/n): ").lower().strip()
    if user_input in ('y', 'yes'):
        print("\n🚀 Running quick test with IEEE paper...")
        print("Note: This will prompt for your ETH credentials")
        
        import subprocess
        import sys
        
        test_url = '10.1109/JPROC.2018.2820126'
        cmd = [sys.executable, 'eth_publisher_downloader.py', test_url]
        
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            print("\n⏹️  Test interrupted by user")
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
    else:
        print("\n✅ System check complete. You can now use the downloader!")

if __name__ == "__main__":
    main()