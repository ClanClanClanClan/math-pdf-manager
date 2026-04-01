#!/usr/bin/env python3
"""
Test with a different IEEE paper that should have proper DOI
"""

import asyncio

from ultimate_all_publishers_downloader import UltimateAllPublishersDownloader


async def test_different_ieee():
    """Test with different IEEE papers"""
    
    # Try different IEEE papers that should have DOIs
    test_papers = [
        "https://ieeexplore.ieee.org/document/9134692",  # Computer Vision survey paper
        "https://ieeexplore.ieee.org/document/8099500",  # Another academic paper
        "https://ieeexplore.ieee.org/document/9999743",  # Grasping paper
    ]
    
    downloader = UltimateAllPublishersDownloader()
    
    for url in test_papers:
        print(f"\n🔍 TESTING: {url}")
        
        # Test DOI extraction from URL
        doi = downloader.extract_doi(url)
        print(f"   DOI from URL: {doi}")
        
        # If no DOI from URL, we need to test the ultimate downloader
        # which should extract DOI from the page content
        await downloader.setup_browser()
        paper = await downloader.download_paper(url)
        await downloader.context.browser.close()
        
        if paper.success:
            print(f"   ✅ SUCCESS via {paper.download_source}")
        else:
            print(f"   ❌ FAILED: {paper.error}")
            if paper.doi:
                print(f"   Found DOI: {paper.doi}")
        
        # Try manual Sci-Hub with a known DOI pattern
        if not paper.success and "Computer Vision" in url:
            # This paper should have DOI 10.1109/TPAMI.2020.3019330
            manual_doi = "10.1109/TPAMI.2020.3019330"
            print(f"   🧪 Testing manual DOI: {manual_doi}")
            manual_paper = await downloader.try_scihub_download(url, manual_doi)
            if manual_paper.success:
                print(f"   ✅ Manual DOI worked via Sci-Hub")
        
        print("-" * 60)

if __name__ == "__main__":
    asyncio.run(test_different_ieee())