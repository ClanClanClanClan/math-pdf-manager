#!/usr/bin/env python3
"""
TEST NATURE RA21 BUTTON
Test clicking the correct institutional access button
"""

import asyncio
import os

from playwright.async_api import async_playwright

ETH_USERNAME = os.getenv('ETH_USERNAME', '')
ETH_PASSWORD = os.getenv('ETH_PASSWORD', '')

async def test_ra21_button():
    """Test the RA21 institutional access button"""
    
    print("🧪 TESTING NATURE RA21 INSTITUTIONAL ACCESS")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # Load a paywalled Nature paper
            paper_url = "https://www.nature.com/articles/nature14539"  # AlphaGo paper
            print(f"1. Loading Nature paper: {paper_url}")
            await page.goto(paper_url)
            await page.wait_for_timeout(3000)
            
            # Dismiss cookie banner
            try:
                cookie_btn = page.locator('button:has-text("Accept"), button:has-text("OK")').first
                if await cookie_btn.count() > 0:
                    await cookie_btn.click()
                    await page.wait_for_timeout(1000)
                    print("   ✓ Dismissed cookie banner")
            except:
                pass
            
            # Click the RA21 button
            print("\n2. Clicking institutional access button...")
            ra21_button = page.locator('a[data-test="ra21"]').first
            
            if await ra21_button.count() > 0:
                print("   ✓ Found RA21 button")
                
                # Get the href to see where it goes
                href = await ra21_button.get_attribute('href')
                print(f"   Button href: {href}")
                
                await ra21_button.click()
                await page.wait_for_timeout(5000)
                
                print(f"\n3. After clicking RA21:")
                print(f"   Current URL: {page.url}")
                print(f"   Page title: {await page.title()}")
                
                # Check if we're on WAYF
                if "wayf.springernature.com" in page.url:
                    print("   ✅ Successfully reached WAYF!")
                    
                    print("\n4. Looking for search field...")
                    search_input = page.locator('input[type="search"], input[placeholder*="institution"], input[name*="search"]').first
                    
                    if await search_input.count() > 0:
                        print("   ✓ Found search field")
                        
                        # Get any placeholder or label
                        placeholder = await search_input.get_attribute('placeholder')
                        if placeholder:
                            print(f"   Placeholder: '{placeholder}'")
                        
                        print("\n5. IMPORTANT: Now I need to know:")
                        print("   - What EXACTLY to search for to find ETH")
                        print("   - Is it listed as 'ETH Zurich'? 'ETH'? Something else?")
                        print("   - Please type in the search box and show me")
                        
                        print("\n   Browser staying open for you to show me...")
                        print("   (Will monitor for 2 minutes)")
                        
                        # Monitor what happens
                        for i in range(120):
                            await asyncio.sleep(1)
                            
                            # Check if URL changed (maybe ETH was selected)
                            if "ethz.ch" in page.url or "switch.ch" in page.url:
                                print(f"\n   🎯 ETH SELECTED! Redirected to: {page.url}")
                                
                                # Fill credentials
                                username_field = page.locator('input[name="j_username"], input[name="username"], input[id="username"]').first
                                password_field = page.locator('input[type="password"]').first
                                
                                if await username_field.count() > 0:
                                    await username_field.fill(ETH_USERNAME)
                                    await password_field.fill(ETH_PASSWORD)
                                    print("   ✓ Filled ETH credentials")
                                    
                                    submit_btn = page.locator('button[type="submit"], input[type="submit"]').first
                                    await submit_btn.click()
                                    print("   ✓ Submitted login")
                                    
                                    await page.wait_for_timeout(10000)
                                    
                                    if "nature.com" in page.url:
                                        print(f"\n   🎉 SUCCESS! Back on Nature with access")
                                        
                                        # Check PDF access
                                        pdf_elem = page.locator('[data-test="download-pdf"]').first
                                        if await pdf_elem.count() > 0 and await pdf_elem.is_visible():
                                            print("   ✅ PDF is now accessible!")
                                break
                            
                            # Check search field value periodically
                            if i % 10 == 0:  # Every 10 seconds
                                try:
                                    search_value = await search_input.input_value()
                                    if search_value:
                                        print(f"   Search value: '{search_value}'")
                                except:
                                    pass
                    else:
                        print("   ❌ No search field found on WAYF")
                else:
                    print("   ❌ Not redirected to WAYF")
            else:
                print("   ❌ RA21 button not found")
            
            print("\n📝 Session ended")
            
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_ra21_button())
