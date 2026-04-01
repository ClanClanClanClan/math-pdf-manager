#!/usr/bin/env python3
"""
TEST PAYWALLED NATURE PAPER
Test our Nature downloader with a paywalled paper to see ETH authentication
"""

import asyncio

from nature_downloader_working import WorkingNatureDownloader


async def test_paywalled_nature():
    """Test with paywalled Nature papers"""
    
    print("🧪 TESTING PAYWALLED NATURE PAPERS")
    print("=" * 60)
    
    # Recent Nature papers (likely paywalled)
    paywalled_papers = [
        "https://www.nature.com/articles/s41586-024-07871-z",  # Recent 2024 paper
        "https://www.nature.com/articles/s41586-024-07899-1",  # Recent 2024 paper  
        "https://www.nature.com/articles/s41586-024-07872-y",  # Recent 2024 paper
    ]
    
    downloader = WorkingNatureDownloader()
    
    for i, url in enumerate(paywalled_papers, 1):
        print(f"\n[{i}/{len(paywalled_papers)}] Testing: {url}")
        print("-" * 80)
        
        paper = await downloader.download_with_eth(url)
        
        if paper.success:
            print(f"✅ SUCCESS: {paper.pdf_path.name}")
            print(f"   Size: {paper.file_size:,} bytes")
            print(f"   Source: {paper.download_source}")
        else:
            print(f"❌ FAILED: {paper.error}")
            
            if "Failed to select ETH institution" in paper.error:
                print(f"💡 As expected: ETH not in SpringerNature WAYF federation")
                print(f"💡 This confirms our discovery - need alternative approach")
        
        # Small delay between papers
        await asyncio.sleep(2)
    
    print(f"\n{'=' * 60}")
    print("📊 PAYWALLED NATURE TEST SUMMARY")
    print("=" * 60)
    print("Expected result: ETH authentication will fail")
    print("Reason: ETH is not federated with SpringerNature's WAYF")
    print("Solution: Need direct ETH institutional access or different approach")

if __name__ == "__main__":
    asyncio.run(test_paywalled_nature())