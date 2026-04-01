#!/usr/bin/env python3
"""
TEST NATURE RESEARCH PAPER
Find and test with an actual Nature research paper (likely paywalled)
"""

import asyncio

from playwright.async_api import async_playwright

from nature_downloader_working import WorkingNatureDownloader


async def find_nature_research_paper():
    """Find a Nature research paper (not news/commentary)"""
    
    print("🔍 FINDING NATURE RESEARCH PAPER")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Search for recent research articles on Nature
            search_url = "https://www.nature.com/search?q=research&journal=nature&article_type=research&date_range=last_year"
            print(f"Searching: {search_url}")
            
            await page.goto(search_url, timeout=30000)
            await page.wait_for_timeout(5000)
            
            # Look for research article links
            research_links = await page.evaluate('''
                () => {
                    const links = Array.from(document.querySelectorAll('a[href*="/articles/"]'));
                    return links
                        .map(link => link.href)
                        .filter(href => 
                            href.includes('/articles/') && 
                            href.includes('s41586') &&  // Nature journal format
                            !href.includes('d41586')    // Not news articles
                        )
                        .slice(0, 3);
                }
            ''')
            
            if research_links:
                print(f"Found {len(research_links)} research papers:")
                for i, url in enumerate(research_links):
                    print(f"  {i+1}. {url}")
                return research_links[0]  # Return the first one
                
        except Exception as e:
            print(f"Search failed: {e}")
            
        finally:
            await browser.close()
    
    # Fallback: Use a known recent research paper
    print("Using known recent research paper...")
    return "https://www.nature.com/articles/s41586-024-07123-y"  # Recent 2024 research

async def test_nature_research():
    """Test with Nature research paper"""
    
    research_url = await find_nature_research_paper()
    
    print(f"\\n🧪 TESTING NATURE RESEARCH PAPER")
    print("=" * 60)
    print(f"URL: {research_url}")
    print("This should be paywalled and require authentication")
    print()
    
    downloader = WorkingNatureDownloader()
    paper = await downloader.download_with_eth(research_url)
    
    if paper.success:
        print(f"\\n✅ UNEXPECTED SUCCESS!")
        print(f"   File: {paper.pdf_path.name}")
        print(f"   Size: {paper.file_size:,} bytes") 
        print(f"   This paper might be open access")
    else:
        print(f"\\n❌ EXPECTED FAILURE: {paper.error}")
        
        if "Failed to select ETH institution" in paper.error:
            print(f"\\n💡 CONFIRMED: ETH Authentication Issue")
            print(f"   - ETH is not in SpringerNature's WAYF federation")
            print(f"   - This explains why ETH students/staff cannot access Nature via institutional login")
            print(f"   - Need alternative solution:")
            print(f"     1. Direct ETH proxy/VPN approach")
            print(f"     2. Different authentication method")
            print(f"     3. Sci-Hub fallback (as you requested)")
            
        elif "open access" in paper.error.lower():
            print(f"\\n💡 Paper is actually open access")
        
        else:
            print(f"\\n💡 Different authentication issue - need to investigate")

if __name__ == "__main__":
    asyncio.run(test_nature_research())