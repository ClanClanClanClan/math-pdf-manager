#!/usr/bin/env python3
"""
Quick Anna's Archive Fix Verification
====================================

Just test the search parsing - no downloads.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def quick_test():
    """Quick test of Anna's Archive search parsing"""
    
    print("⚡ QUICK ANNA'S ARCHIVE FIX TEST")
    print("=" * 40)
    
    try:
        from src.downloader.universal_downloader import AnnaArchiveDownloader
        
        anna = AnnaArchiveDownloader()
        
        # Test search only (no downloads)
        print("🔍 Testing search parsing...")
        results = await anna.search("machine learning")
        
        print(f"Found {len(results)} results")
        
        # Check if we filtered out "Search settings..."
        has_settings = any("settings" in r.title.lower() for r in results)
        all_have_urls = all(r.url for r in results)
        
        if has_settings:
            print("❌ Still finding 'Search settings...' entries")
        else:
            print("✅ Filtered out 'Search settings...' entries")
        
        if all_have_urls:
            print("✅ All results have URLs")
        else:
            print("❌ Some results missing URLs")
        
        # Show first result
        if results:
            print(f"\nFirst result:")
            print(f"  Title: {results[0].title[:50]}...")
            print(f"  URL: {results[0].url}")
        
        # Close session
        if anna.session:
            await anna.session.close()
        
        return not has_settings and all_have_urls
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    success = await quick_test()
    
    if success:
        print("\n🎉 ANNA'S ARCHIVE FIX VERIFIED!")
    else:
        print("\n❌ Fix needs more work")

if __name__ == "__main__":
    asyncio.run(main())