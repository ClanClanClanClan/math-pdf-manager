#!/usr/bin/env python3
"""
DEBUG WILEY PUBLISHER
=====================

Let's see what's actually happening with Wiley pages
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

async def debug_wiley():
    """Debug Wiley to see what's on the page"""
    
    print("🔍 WILEY DEBUG MODE")
    print("=" * 80)
    
    # Test with a known Wiley DOI
    test_doi = "10.1002/anie.202004934"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Show the browser
            args=[
                '--disable-blink-features=AutomationControlled',
                '--start-maximized'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        # Navigate to DOI
        url = f"https://doi.org/{test_doi}"
        print(f"📍 Navigating to: {url}")
        await page.goto(url, wait_until='domcontentloaded')
        
        # Wait for page to load
        await page.wait_for_timeout(5000)
        
        current_url = page.url
        print(f"📍 Current URL: {current_url}")
        
        # Take screenshot
        await page.screenshot(path='wiley_page.png')
        print("📸 Screenshot saved as wiley_page.png")
        
        # Look for access indicators
        page_content = await page.content()
        
        print("\n🔍 Access indicators found:")
        access_indicators = [
            'institutional access', 'subscribe', 'purchase', 'paywall',
            'login', 'sign in', 'access through your institution',
            'get access', 'rent or buy', 'pdf', 'download'
        ]
        
        for indicator in access_indicators:
            if indicator in page_content.lower():
                print(f"   ✓ Found: '{indicator}'")
        
        # Look for institutional links
        print("\n🔍 Looking for institutional access links:")
        
        # First try to find any links with institutional text
        inst_links = await page.query_selector_all('a')
        found_institutional = False
        
        for link in inst_links[:50]:  # Check first 50 links
            try:
                text = await link.inner_text()
                href = await link.get_attribute('href')
                
                if text and any(term in text.lower() for term in [
                    'institution', 'university', 'library', 'shibboleth', 
                    'sign in', 'log in', 'access'
                ]):
                    print(f"   📎 Link: '{text.strip()}' -> {href}")
                    
                    # Check if it's visible
                    is_visible = await link.is_visible()
                    if is_visible and 'institution' in text.lower():
                        found_institutional = True
                        print(f"      ✅ This looks like institutional access!")
                        
                        # Try to click it
                        print("      🖱️ Attempting to click...")
                        await link.click()
                        await page.wait_for_timeout(5000)
                        
                        new_url = page.url
                        print(f"      📍 New URL: {new_url}")
                        
                        # Take another screenshot
                        await page.screenshot(path='wiley_after_click.png')
                        print("      📸 Screenshot saved as wiley_after_click.png")
                        
                        break
                        
            except:
                continue
        
        if not found_institutional:
            print("   ❌ No institutional access link found")
            
            # Look for alternative access methods
            print("\n🔍 Alternative access methods:")
            
            # Check for PDF links
            pdf_links = await page.query_selector_all('a[href*="pdf"], a:has-text("PDF")')
            print(f"   Found {len(pdf_links)} PDF-related links")
            
            for i, link in enumerate(pdf_links[:5]):
                try:
                    text = await link.inner_text()
                    href = await link.get_attribute('href')
                    is_visible = await link.is_visible()
                    print(f"   PDF Link {i+1}: '{text.strip()}' visible={is_visible}")
                except:
                    pass
        
        print("\n⏸️ Keeping browser open for 30 seconds for manual inspection...")
        await page.wait_for_timeout(30000)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_wiley())