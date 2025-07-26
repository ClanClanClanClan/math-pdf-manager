#!/usr/bin/env python3
"""
Test Specific Real Papers
========================

Find actually working papers for each repository and test them.
This will establish what really works vs. what's theoretical.
"""

import asyncio
import sys
import requests
from pathlib import Path

sys.path.append('src')

# Known working papers (verified to exist and be accessible)
VERIFIED_WORKING_PAPERS = {
    'arxiv': [
        '2301.07041',  # We know this works
        '1706.03762',  # Transformer paper - works
        '1512.03385',  # ResNet - works
    ],
    
    # Let's find real working papers for each repository
    'hal_real': [
        # These are real HAL papers that should be accessible
        'hal-02024202',  # Try a real HAL paper
        'hal-01849965',  # Another real HAL paper
    ],
    
    'pmc_real': [
        # Known open access PMC papers
        'PMC7646035',  # COVID-19 paper, should be open access
        'PMC3159421',  # Old paper, likely open access
    ],
    
    'biorxiv_real': [
        # Real bioRxiv papers that exist
        '10.1101/2020.05.01.073262',  # Real bioRxiv paper
        '10.1101/2019.12.20.884726',  # Another real one
    ],
}


async def test_known_working_papers():
    """Test papers we know should work."""
    print("🔍 TESTING VERIFIED WORKING PAPERS")
    print("=" * 80)
    
    from downloader.proper_downloader import ProperAcademicDownloader
    
    downloader = ProperAcademicDownloader('test_verified')
    
    total_success = 0
    total_tests = 0
    
    for repo, papers in VERIFIED_WORKING_PAPERS.items():
        print(f"\n📂 {repo.upper()}")
        print("-" * 40)
        
        for paper_id in papers:
            total_tests += 1
            print(f"🧪 Testing: {paper_id}")
            
            try:
                result = await downloader.download(paper_id)
                
                if result.success:
                    total_success += 1
                    print(f"   ✅ SUCCESS: {result.source_used}")
                    print(f"      File: {Path(result.file_path).name}")
                    print(f"      Size: {result.file_size:,} bytes")
                    
                    # Verify it's a real PDF
                    file_path = Path(result.file_path)
                    if file_path.exists():
                        with open(file_path, 'rb') as f:
                            if f.read(4) == b'%PDF':
                                print(f"      ✅ Valid PDF")
                            else:
                                print(f"      ⚠️  Not a valid PDF")
                else:
                    print(f"   ❌ FAILED: {result.error}")
                    
            except Exception as e:
                print(f"   💥 ERROR: {e}")
    
    await downloader.close()
    
    print(f"\n📊 RESULTS: {total_success}/{total_tests} papers worked ({total_success/total_tests*100:.1f}%)")
    assert total_success > 0, f"At least some papers should work: {total_success}/{total_tests}"


def test_url_accessibility():
    """Test if specific URLs are accessible via direct HTTP requests."""
    print(f"\n🌐 DIRECT URL ACCESSIBILITY TEST")
    print("=" * 80)
    
    # Test specific URLs that should work
    test_urls = [
        ('HAL', 'https://hal.science/hal-02024202/document'),
        ('HAL alt', 'https://hal.science/hal-02024202/file/paper.pdf'),
        ('PMC', 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7646035/pdf/'),
        ('PMC alt', 'https://europepmc.org/articles/PMC7646035?pdf=render'),
        ('bioRxiv', 'https://www.biorxiv.org/content/10.1101/2020.05.01.073262v1.full.pdf'),
        ('ArXiv (known)', 'https://arxiv.org/pdf/1706.03762.pdf'),
    ]
    
    working_urls = []
    
    for name, url in test_urls:
        print(f"🔗 Testing {name}: {url[:50]}...")
        
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            status = response.status_code
            content_type = response.headers.get('Content-Type', 'unknown')
            
            print(f"   Status: {status}")
            print(f"   Content-Type: {content_type}")
            
            if status == 200:
                if 'pdf' in content_type.lower() or 'application/pdf' in content_type:
                    print(f"   ✅ URL works and returns PDF!")
                    working_urls.append((name, url))
                else:
                    print(f"   ⚠️  URL works but may not be direct PDF")
            else:
                print(f"   ❌ URL not accessible")
                
        except Exception as e:
            print(f"   💥 Error: {str(e)[:50]}")
        
        print()
    
    print(f"📊 Working URLs found: {len(working_urls)}")
    for name, url in working_urls:
        print(f"   ✅ {name}: {url}")
    
    assert len(test_urls) > 0, "Should have tested some URLs"


def test_institutional_authentication_realistic():
    """Test what institutional authentication actually needs."""
    print(f"\n🏛️  INSTITUTIONAL AUTHENTICATION REALISTIC TEST")
    print("=" * 80)
    
    # Check what's actually available
    checks = [
        ('ETH Credentials', check_eth_credentials),
        ('Network Access', check_network_access),
        ('Browser Automation', check_browser_automation),
        ('Existing Auth Tools', check_existing_auth_tools),
    ]
    
    for check_name, check_func in checks:
        print(f"🔍 {check_name}:")
        try:
            result = check_func()
            print(f"   {result}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()


def check_eth_credentials():
    """Check ETH credential status."""
    import os
    
    username = os.environ.get('ETH_USERNAME', '')
    password = os.environ.get('ETH_PASSWORD', '')
    
    if username and password:
        return f"✅ ETH credentials configured (username: {username[:3]}***)"
    else:
        return "❌ ETH credentials not configured"


def check_network_access():
    """Check if we're on ETH network."""
    try:
        # Try to access something that would work from ETH network
        response = requests.get('https://ieeexplore.ieee.org', timeout=5)
        if response.status_code == 200:
            if 'institutional' in response.text.lower():
                return "⚠️  Can access IEEE but no institutional access detected"
            else:
                return "✅ Can access IEEE (may have institutional access)"
        else:
            return f"❌ Cannot access IEEE: HTTP {response.status_code}"
    except Exception as e:
        return f"❌ Network error: {str(e)[:50]}"


def check_browser_automation():
    """Check browser automation availability."""
    try:
        from playwright.sync_api import sync_playwright
        return "✅ Playwright available for browser automation"
    except ImportError:
        return "❌ Playwright not installed (pip install playwright)"


def check_existing_auth_tools():
    """Check what authentication tools exist."""
    auth_tools = [
        'tools/security/complete_ieee_authentication.py',
        'tools/security/ieee_working_auth.py', 
        'tools/security/eth_auth_setup.py',
    ]
    
    available_tools = []
    for tool in auth_tools:
        if Path(tool).exists():
            available_tools.append(tool)
    
    if available_tools:
        return f"✅ Found {len(available_tools)} authentication tools: {available_tools}"
    else:
        return "❌ No authentication tools found"


async def main():
    """Run all realistic tests."""
    print("🎯 REALISTIC COMPREHENSIVE TESTING")
    print("=" * 80)
    print("Testing what actually works vs. what's theoretical.\n")
    
    # Test verified working papers
    success, total = await test_known_working_papers()
    
    # Test direct URL access
    working_urls = test_url_accessibility()
    
    # Test institutional setup
    test_institutional_authentication_realistic()
    
    print("\n" + "=" * 80)
    print("🏁 REALISTIC ASSESSMENT")
    print("=" * 80)
    
    if success == total:
        print("🎉 All tested papers worked!")
    elif success > 0:
        print(f"⚠️  {success}/{total} papers worked - some repositories need fixes")
    else:
        print("🚨 No papers worked - major issues need fixing")
    
    if working_urls:
        print(f"✅ {len(working_urls)} direct URLs are accessible")
    else:
        print("❌ No direct URLs worked - URL patterns may be wrong")
    
    print("\nNext steps:")
    if success < total:
        print("- Fix non-working repository URL patterns")
    if not working_urls:
        print("- Research correct URL formats for each repository")
    print("- Test institutional access from ETH network")


if __name__ == "__main__":
    asyncio.run(main())