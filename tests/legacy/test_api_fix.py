#!/usr/bin/env python3
"""
Test script to validate arXiv API integration is fixed
"""

import asyncio
import time
import xml.etree.ElementTree as ET

import aiohttp


async def test_arxiv_api():
    """Test that we can actually fetch papers from arXiv"""
    
    print("=" * 80)
    print("🔧 TESTING ARXIV API FIX")
    print("=" * 80)
    print()
    
    # Test configuration
    arxiv_api = "http://export.arxiv.org/api/query"
    test_categories = ['cs.LG', 'cs.AI', 'math.PR', 'cs.CL']
    
    # Create session with proper configuration
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(
        timeout=timeout,
        headers={'User-Agent': 'arxiv-bot/2.0 (test)'},
        connector=aiohttp.TCPConnector(force_close=True)
    ) as session:
        
        for category in test_categories:
            print(f"📊 Testing category: {category}")
            
            # Construct query
            params = {
                'search_query': f'cat:{category}',
                'start': 0,
                'max_results': 10,
                'sortBy': 'submittedDate', 
                'sortOrder': 'descending'
            }
            
            try:
                start = time.time()
                
                # Make request with redirect following
                async with session.get(arxiv_api, params=params, allow_redirects=True) as response:
                    print(f"  • Status: {response.status}")
                    print(f"  • Final URL: {response.url}")
                    
                    if response.status != 200:
                        print(f"  ❌ ERROR: Non-200 status")
                        continue
                    
                    content = await response.text()
                    elapsed = time.time() - start
                    
                    print(f"  • Response time: {elapsed*1000:.1f}ms")
                    print(f"  • Content length: {len(content)} bytes")
                    
                    # Parse XML
                    root = ET.fromstring(content)
                    ns = {'atom': 'http://www.w3.org/2005/Atom'}
                    
                    # Count entries
                    entries = root.findall('atom:entry', ns)
                    print(f"  • Papers found: {len(entries)}")
                    
                    # Show first paper if any
                    if entries:
                        first = entries[0]
                        title = first.find('atom:title', ns)
                        id_elem = first.find('atom:id', ns)
                        
                        if title is not None and title.text:
                            print(f"  • First paper: {title.text.strip()[:60]}...")
                        if id_elem is not None and id_elem.text:
                            paper_id = id_elem.text.split('/')[-1]
                            print(f"  • Paper ID: {paper_id}")
                        
                        print(f"  ✅ SUCCESS: Category {category} works!")
                    else:
                        print(f"  ⚠️ WARNING: No papers found for {category}")
                    
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
            
            print()
    
    print("=" * 80)
    print("🏁 API TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_arxiv_api())