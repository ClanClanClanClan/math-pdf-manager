#!/usr/bin/env python3
"""
SIAM Flow Debug
===============

Debug exactly what happens after clicking "GET ACCESS" in SIAM.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def debug_siam_flow():
    print("🔍 DEBUGGING SIAM FLOW: What happens after GET ACCESS?")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to SIAM paper
            test_doi = "10.1137/S0097539795293172"
            siam_url = f"https://epubs.siam.org/doi/{test_doi}"
            print(f"1. Navigating to: {siam_url}")
            await page.goto(siam_url, timeout=90000)
            await page.wait_for_timeout(8000)
            
            # Take initial screenshot
            await page.screenshot(path="siam_debug_1_initial.png")
            print("   Screenshot: siam_debug_1_initial.png")
            
            # Find and click GET ACCESS
            access_button = await page.wait_for_selector('a:has-text("GET ACCESS")', timeout=10000)
            print("2. Found GET ACCESS button, clicking...")
            await access_button.click()
            await page.wait_for_timeout(8000)
            
            # Take screenshot after GET ACCESS
            await page.screenshot(path="siam_debug_2_after_get_access.png")
            print("   Screenshot: siam_debug_2_after_get_access.png")
            
            # Check current URL
            current_url = page.url
            print(f"   URL after GET ACCESS: {current_url}")
            
            # Check page title
            page_title = await page.title()
            print(f"   Page title: '{page_title}'")
            
            # List all visible links and buttons
            print("3. Looking for all available access options...")
            
            # Check for different institutional access selectors
            institutional_selectors = [
                'a:has-text("Access via your Institution")',
                'button:has-text("Access via your Institution")',
                'a:has-text("Institution")',
                'a:has-text("Institutional")',
                'a:has-text("Login")',
                'a:has-text("Sign in")',
                '[href*="shibboleth"]',
                '[href*="institutional"]',
                'input#shibboleth_search'
            ]
            
            found_selectors = []
            for selector in institutional_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=3000)
                    if element:
                        text = await element.text_content()
                        href = await element.get_attribute('href')
                        print(f"   ✓ Found: {selector} - Text: '{text}' - Href: '{href}'")
                        found_selectors.append(selector)
                except:
                    continue
            
            if not found_selectors:
                print("   ❌ No institutional access selectors found!")
                print("   Let me check all links on the page...")
                
                # Get all links
                links = await page.query_selector_all('a')
                print(f"   Found {len(links)} links:")
                for i, link in enumerate(links[:20]):  # Show first 20
                    text = await link.text_content()
                    href = await link.get_attribute('href')
                    if text and text.strip():
                        print(f"     {i+1}. '{text.strip()}' -> {href}")
            
            # Wait a bit longer to see if anything loads
            print("4. Waiting to see if institutional options appear...")
            await page.wait_for_timeout(10000)
            
            # Take final screenshot
            await page.screenshot(path="siam_debug_3_final.png")
            print("   Screenshot: siam_debug_3_final.png")
            
            print("\n📊 SIAM Flow Debug Complete")
            print("Check the screenshots to see what's actually happening!")
            
        except Exception as e:
            print(f"❌ Debug error: {e}")
            await page.screenshot(path="siam_debug_error.png")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_siam_flow())