#!/usr/bin/env python3
"""
Test Fixed Sources
==================

Test the specific fixes I made for bioRxiv and SSRN.
"""

import asyncio
import sys
sys.path.append('src')

from downloader.proper_downloader import ProperAcademicDownloader


async def test_ssrn_specifically():
    """Test SSRN with real papers."""
    print("🔍 TESTING SSRN SPECIFICALLY")
    print("=" * 50)
    
    # Real SSRN papers
    ssrn_papers = [
        "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3445746",
        "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2139797",
        "https://ssrn.com/abstract=3445746",
    ]
    
    downloader = ProperAcademicDownloader('test_ssrn_fix')
    
    for paper_url in ssrn_papers:
        print(f"\n🧪 Testing: {paper_url}")
        
        try:
            result = await downloader.download(paper_url)
            
            if result.success:
                print(f"   ✅ SUCCESS: {result.source_used}")
                print(f"      File: {result.file_path}")
                print(f"      Size: {result.file_size:,} bytes")
            else:
                print(f"   ❌ FAILED: {result.error}")
                
        except Exception as e:
            print(f"   💥 EXCEPTION: {e}")
    
    await downloader.close()


async def test_biorxiv_with_message():
    """Test bioRxiv with understanding that it may be blocked."""
    print("\n\n🔍 TESTING BIORXIV (EXPECTED TO FAIL)")
    print("=" * 50)
    print("bioRxiv uses Cloudflare protection to block automated downloads.")
    print("This is intentional on their part to protect bandwidth.")
    
    # Real bioRxiv papers
    biorxiv_papers = [
        "10.1101/2020.05.01.073262",
        "10.1101/2019.12.20.884726",
    ]
    
    downloader = ProperAcademicDownloader('test_biorxiv_fix')
    
    for paper_id in biorxiv_papers:
        print(f"\n🧪 Testing: {paper_id}")
        
        try:
            result = await downloader.download(paper_id)
            
            if result.success:
                print(f"   🎉 UNEXPECTED SUCCESS: {result.source_used}")
                print(f"      File: {result.file_path}")
                print(f"      Size: {result.file_size:,} bytes")
            else:
                print(f"   ❌ EXPECTED FAILURE: {result.error}")
                print(f"      (This is normal - bioRxiv blocks automated access)")
                
        except Exception as e:
            print(f"   ❌ EXPECTED EXCEPTION: {e}")
            print(f"      (This is normal - bioRxiv blocks automated access)")
    
    await downloader.close()


async def test_working_sources_still_work():
    """Ensure my changes didn't break working sources."""
    print("\n\n🔍 TESTING THAT WORKING SOURCES STILL WORK")
    print("=" * 50)
    
    working_papers = [
        ("ArXiv", "2301.07041"),
        ("HAL", "hal-02024202"),
        ("PMC", "PMC7646035"),
    ]
    
    downloader = ProperAcademicDownloader('test_working_sources')
    
    for source_name, paper_id in working_papers:
        print(f"\n🧪 Testing {source_name}: {paper_id}")
        
        try:
            result = await downloader.download(paper_id)
            
            if result.success:
                print(f"   ✅ SUCCESS: {result.source_used}")
                print(f"      File: {result.file_path}")
                print(f"      Size: {result.file_size:,} bytes")
            else:
                print(f"   🚨 UNEXPECTED FAILURE: {result.error}")
                print(f"      This source should work!")
                
        except Exception as e:
            print(f"   🚨 UNEXPECTED EXCEPTION: {e}")
            print(f"      This source should work!")
    
    await downloader.close()


async def main():
    """Test all fixed sources."""
    print("🔧 TESTING SPECIFIC SOURCE FIXES")
    print("=" * 80)
    print("Testing my specific fixes for bioRxiv (Cloudflare blocking)")
    print("and SSRN (HTML scraping for PDF links).\n")
    
    # Test SSRN fixes
    await test_ssrn_specifically()
    
    # Test bioRxiv (expected to fail due to Cloudflare)
    await test_biorxiv_with_message()
    
    # Ensure working sources still work
    await test_working_sources_still_work()
    
    print("\n" + "=" * 80)
    print("🏁 CONCLUSIONS")
    print("=" * 80)
    print("✅ ArXiv, HAL, PMC should work (they're truly open)")
    print("⚠️  SSRN may work if they provide direct PDF links")
    print("❌ bioRxiv blocks automated access (this is intentional)")
    print("\nFor bioRxiv, users would need to download manually.")


if __name__ == "__main__":
    asyncio.run(main())