#!/usr/bin/env python3
"""
TEST NATURE WAYF
Focus on the working WAYF URL to find ETH
"""

import asyncio

from playwright.async_api import async_playwright


async def test_nature_wayf():
    """Test Nature's WAYF page thoroughly"""
    
    print("🧪 TESTING NATURE WAYF PAGE")
    print("=" * 40)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Go directly to the working WAYF URL
            wayf_url = "https://wayf.springernature.com/?redirect_uri=https://www.nature.com/articles/nature12373"
            print(f"Loading WAYF: {wayf_url}")
            
            await page.goto(wayf_url)
            await page.wait_for_timeout(3000)
            
            print(f"Title: {await page.title()}")
            print(f"URL: {page.url}")
            
            # Look for search input
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="institution"]',
                'input[placeholder*="organization"]',
                'input[name*="search"]',
                'input[name*="institution"]'
            ]
            
            search_found = False
            for selector in search_selectors:
                search_elem = page.locator(selector).first
                if await search_elem.count() > 0:
                    print(f"\\nFound search field: {selector}")
                    
                    # Get placeholder text
                    placeholder = await search_elem.get_attribute('placeholder')
                    print(f"Placeholder: {placeholder}")
                    
                    search_found = True
                    
                    # Try different search terms for ETH
                    eth_searches = [
                        "ETH Zurich",
                        "ETH Zürich", 
                        "Swiss Federal Institute of Technology",
                        "Eidgenössische Technische Hochschule",
                        "ETH",
                        "Zurich",
                        "Switzerland"
                    ]
                    
                    for search_term in eth_searches:
                        print(f"\\n  Testing search: '{search_term}'")
                        
                        # Clear and type search term
                        await search_elem.fill("")
                        await search_elem.type(search_term, delay=100)
                        await page.wait_for_timeout(2000)
                        
                        # Look for results containing ETH/Zurich
                        result_selectors = [
                            'text="ETH"',
                            'text="Zurich"',
                            'text="Swiss"',
                            'li:has-text("ETH")',
                            'option:has-text("ETH")',
                            '.result:has-text("ETH")',
                            '[role="option"]:has-text("ETH")'
                        ]
                        
                        found_results = []
                        for result_sel in result_selectors:
                            count = await page.locator(result_sel).count()
                            if count > 0:
                                found_results.append((result_sel, count))
                        
                        if found_results:
                            print(f"    ✅ Found results:")
                            for result_sel, count in found_results:
                                print(f"      {result_sel}: {count}")
                                
                                # Get actual text
                                elems = await page.locator(result_sel).all()
                                for i, elem in enumerate(elems[:3]):  # Show first 3
                                    try:
                                        text = await elem.text_content()
                                        print(f"        [{i+1}] '{text.strip()}'")
                                    except:
                                        continue
                                        
                            # Try clicking the first ETH result
                            first_result = page.locator(found_results[0][0]).first
                            try:
                                await first_result.click()
                                await page.wait_for_timeout(3000)
                                
                                print(f"    After click: {page.url}")
                                
                                if "ethz.ch" in page.url:
                                    print(f"    ✅ SUCCESS! Redirected to ETH login")
                                    break
                                else:
                                    print(f"    ❌ Not redirected to ETH")
                            except Exception as e:
                                print(f"    Error clicking result: {e}")
                        else:
                            print(f"    ❌ No results for '{search_term}'")
                    
                    break
            
            if not search_found:
                print(f"\\n❌ No search field found")
                
                # Look for direct institution links/lists
                print(f"\\nLooking for direct institution list...")
                institution_selectors = [
                    'a:has-text("ETH")',
                    'button:has-text("ETH")',
                    'li:has-text("ETH")',
                    'text="ETH"'
                ]
                
                for selector in institution_selectors:
                    count = await page.locator(selector).count()
                    if count > 0:
                        print(f"  Found ETH link: {selector} ({count})")
            
            print(f"\\nBrowser staying open for manual inspection...")
            print(f"Try searching manually to see what institutions are available")
            await page.wait_for_timeout(60000)  # 1 minute
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_nature_wayf())