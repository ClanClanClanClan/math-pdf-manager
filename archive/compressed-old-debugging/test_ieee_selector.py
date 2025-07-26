#!/usr/bin/env python3
"""
Test IEEE Selectors
==================

Check what's on the IEEE page.
"""

import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("Going to IEEE...")
        await page.goto("https://doi.org/10.1109/JPROC.2018.2820126")
        await page.wait_for_timeout(5000)
        
        # Accept cookies
        try:
            await page.click('button:has-text("Accept All")')
            await page.wait_for_timeout(1000)
            print("✓ Accepted cookies")
        except:
            print("- No cookie banner")
        
        # Look for sign in options
        print("\nLooking for sign in links...")
        
        # Find all links
        links = await page.query_selector_all('a')
        sign_in_links = []
        
        for link in links:
            text = await link.text_content()
            if text and ('sign' in text.lower() or 'login' in text.lower() or 'institution' in text.lower()):
                href = await link.get_attribute('href') or ''
                sign_in_links.append((text.strip(), href))
        
        print(f"\nFound {len(sign_in_links)} sign-in related links:")
        for text, href in sign_in_links:
            print(f"  - '{text}' -> {href[:50]}...")
        
        # Try different selectors
        selectors = [
            'a:has-text("Institutional Sign In")',
            'a:has-text("Sign in")',
            'a:has-text("Sign In")',
            'button:has-text("Sign in")',
            'button:has-text("Sign In")',
            'a:has-text("Institution")',
            'text="Institutional Sign In"'
        ]
        
        print("\nTrying selectors:")
        for selector in selectors:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.text_content()
                    print(f"  ✓ '{selector}' found: '{text.strip()}'")
                else:
                    print(f"  ✗ '{selector}' not found")
            except Exception as e:
                print(f"  ✗ '{selector}' error: {e}")
        
        await page.screenshot(path="ieee_page.png")
        print("\nScreenshot saved to ieee_page.png")
        
        print("\nBrowser will close in 30 seconds...")
        await page.wait_for_timeout(30000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())