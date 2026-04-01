#!/usr/bin/env python3
"""
IEEE DOI Resolver
=================

Figure out how to properly resolve IEEE DOIs to actual IEEE document URLs.
"""

import asyncio
import requests
from pathlib import Path

async def resolve_ieee_dois():
    print("🔍 RESOLVING IEEE DOI FORMATS")
    print("=" * 50)
    
    # The failing DOIs from our tests
    failing_dois = [
        "10.1109/MC.2006.5",
        "10.1109/JPROC.2016.2515118", 
        "10.1109/JPROC.2015.2460651",
        "10.1109/5.869037",
        "10.1109/JPROC.2016.2571690"
    ]
    
    # Working DOIs from our tests
    working_dois = [
        "10.1109/5.726791",
        "10.1109/JPROC.2018.2820126",
        "10.1109/5.771073",
        "10.1109/5.726787",
        "10.1109/JPROC.2017.2761740"
    ]
    
    print("1️⃣ TESTING DOI RESOLUTION")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    def test_doi_resolution(doi, status="unknown"):
        print(f"\n📄 Testing {status}: {doi}")
        
        # Method 1: DOI resolver
        doi_url = f"https://doi.org/{doi}"
        print(f"   DOI URL: {doi_url}")
        
        try:
            response = session.get(doi_url, allow_redirects=True, timeout=10)
            final_url = response.url
            status_code = response.status
            
            print(f"   Status: {status_code}")
            print(f"   Final URL: {final_url}")
            
            if 'ieeexplore.ieee.org' in final_url:
                # Extract document ID from IEEE URL
                import re
                doc_id_match = re.search(r'/document/(\d+)', final_url)
                if doc_id_match:
                    doc_id = doc_id_match.group(1)
                    print(f"   ✅ Document ID: {doc_id}")
                    return doc_id
                else:
                    print(f"   ❌ Could not extract document ID")
            else:
                print(f"   ❌ Does not redirect to IEEE")
                
        except Exception as e:
            print(f"   ❌ Resolution failed: {e}")
        
        return None
    
    print("=" * 50)
    print("WORKING DOIs:")
    working_doc_ids = {}
    for doi in working_dois:
        doc_id = test_doi_resolution(doi, "WORKING")
        if doc_id:
            working_doc_ids[doi] = doc_id
    
    print("\n" + "=" * 50)
    print("FAILING DOIs:")
    failing_doc_ids = {}
    for doi in failing_dois:
        doc_id = test_doi_resolution(doi, "FAILING")
        if doc_id:
            failing_doc_ids[doi] = doc_id
    
    print(f"\n2️⃣ ANALYSIS")
    print(f"Working DOIs resolved: {len(working_doc_ids)}/{len(working_dois)}")
    print(f"Failing DOIs resolved: {len(failing_doc_ids)}/{len(failing_dois)}")
    
    if working_doc_ids:
        print("\n✅ Successfully resolved working DOIs:")
        for doi, doc_id in working_doc_ids.items():
            print(f"   {doi} -> document/{doc_id}")
    
    if failing_doc_ids:
        print("\n⚠️ Successfully resolved 'failing' DOIs:")
        for doi, doc_id in failing_doc_ids.items():
            print(f"   {doi} -> document/{doc_id}")
    
    # Check if any 'failing' DOIs actually resolve
    if failing_doc_ids:
        print(f"\n3️⃣ TESTING RESOLVED 'FAILING' DOIs")
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Test one of the resolved failing DOIs
            if failing_doc_ids:
                first_doi, first_doc_id = next(iter(failing_doc_ids.items()))
                ieee_url = f"https://ieeexplore.ieee.org/document/{first_doc_id}"
                
                print(f"   Testing resolved URL: {ieee_url}")
                
                try:
                    response = await page.goto(ieee_url, timeout=30000)
                    if response and response.status == 200:
                        await page.wait_for_timeout(5000)
                        title = await page.title()
                        print(f"   ✅ Page loaded: {title}")
                        
                        # Take screenshot
                        await page.screenshot(path="ieee_resolved_failing_doi.png")
                        print(f"   Screenshot: ieee_resolved_failing_doi.png")
                        
                        # Check if this looks like a real paper
                        if 'amdahl' in title.lower():
                            print(f"   🎉 This IS the Amdahl paper!")
                        else:
                            print(f"   ❓ Title doesn't match expected content")
                    else:
                        print(f"   ❌ Page failed to load: {response.status if response else 'None'}")
                        
                except Exception as e:
                    print(f"   ❌ Error loading page: {e}")
            
            await browser.close()

if __name__ == "__main__":
    asyncio.run(resolve_ieee_dois())