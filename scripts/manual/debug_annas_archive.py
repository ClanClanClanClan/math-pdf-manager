#!/usr/bin/env python3
"""
Debug Anna's Archive Integration
================================

Diagnose and fix Anna's Archive URL extraction issues.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def debug_annas_archive():
    """Debug Anna's Archive step by step"""
    
    print("🔧 DEBUGGING ANNA'S ARCHIVE URL EXTRACTION")
    print("=" * 60)
    
    try:
        from src.downloader.universal_downloader import AnnaArchiveDownloader
        
        anna = AnnaArchiveDownloader()
        
        # Test 1: Check if we can find active mirror
        print("\n1️⃣ Testing mirror connectivity...")
        mirror_found = await anna._find_active_mirror()
        print(f"   Active mirror found: {mirror_found}")
        if anna.active_base_url:
            print(f"   Using mirror: {anna.active_base_url}")
        
        if not mirror_found:
            print("❌ No active mirror - Anna's Archive may be blocked or down")
            return False
        
        # Test 2: Try search
        print("\n2️⃣ Testing search functionality...")
        test_queries = [
            "machine learning",
            "neural networks", 
            "10.1016/j.jcp.2019.07.031"  # Specific DOI
        ]
        
        for query in test_queries:
            print(f"\n   🔍 Searching for: '{query}'")
            try:
                results = await anna.search(query)
                print(f"   Found {len(results)} results")
                
                if results:
                    # Examine first few results
                    for i, result in enumerate(results[:3]):
                        print(f"\n   Result {i+1}:")
                        print(f"     Title: {result.title[:80]}...")
                        print(f"     URL: {result.url}")
                        print(f"     Source: {result.source}")
                        print(f"     Confidence: {result.confidence}")
                        
                        # Check if URL is valid
                        if result.url:
                            print(f"     ✅ URL available")
                        else:
                            print(f"     ❌ NO URL - This is the problem!")
                
                else:
                    print("   ❌ No results returned")
                    
            except Exception as e:
                print(f"   ❌ Search failed: {e}")
        
        # Test 3: Check HTML parsing (if we have a working mirror)
        if anna.active_base_url:
            print(f"\n3️⃣ Testing raw HTML response...")
            try:
                search_url = anna.active_base_url + "search?q=machine%20learning&ext=pdf"
                print(f"   URL: {search_url}")
                
                if not anna.session:
                    from src.downloader.credentials import create_secure_session
                    import aiohttp
                    anna.session = create_secure_session(timeout=aiohttp.ClientTimeout(total=15))
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                }
                
                async with anna.session.get(search_url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        print(f"   ✅ Got HTML response ({len(html)} chars)")
                        
                        # Save sample HTML for inspection
                        with open('anna_debug_sample.html', 'w', encoding='utf-8') as f:
                            f.write(html[:10000])  # First 10k chars
                        print(f"   Saved sample HTML to anna_debug_sample.html")
                        
                        # Try to find what looks like result items
                        if 'mb-4' in html:
                            print("   ✅ Found 'mb-4' classes (potential results)")
                        else:
                            print("   ⚠️  No 'mb-4' classes found")
                            
                        if 'search-result' in html:
                            print("   ✅ Found 'search-result' text")
                        else:
                            print("   ⚠️  No 'search-result' text found")
                            
                        if '<a href=' in html:
                            print("   ✅ Found links in HTML")
                        else:
                            print("   ❌ No links found in HTML")
                    else:
                        print(f"   ❌ HTTP {response.status}")
                        
            except Exception as e:
                print(f"   ❌ Raw HTML test failed: {e}")
        
        # Test 4: Try BeautifulSoup import
        print(f"\n4️⃣ Testing BeautifulSoup...")
        try:
            from bs4 import BeautifulSoup
            print("   ✅ BeautifulSoup available")
        except ImportError as e:
            print(f"   ❌ BeautifulSoup NOT available: {e}")
            print("   💡 This is likely the root cause!")
            return False
        
        # Close session
        if anna.session:
            await anna.session.close()
            
        return True
        
    except Exception as e:
        print(f"💥 Debug failed: {e}")
        return False

async def main():
    success = await debug_annas_archive()
    
    print("\n" + "=" * 60)  
    print("🎯 ANNA'S ARCHIVE DEBUG RESULTS")
    print("=" * 60)
    
    if success:
        print("✅ Anna's Archive connectivity and parsing working")
        print("🔍 Check debug output above for URL extraction issues")
    else:
        print("❌ Anna's Archive has fundamental issues")
        print("💡 Most likely causes:")
        print("   1. BeautifulSoup not installed")
        print("   2. All mirrors are blocked/down")
        print("   3. HTML parsing logic needs updating")
    
    print("\n🚀 Next: Install missing dependencies and fix URL extraction")

if __name__ == "__main__":
    asyncio.run(main())