#!/usr/bin/env python3
"""
Find IEEE Institutional Access
================================

Find the actual institutional access flow on IEEE.
"""

import asyncio
from playwright.async_api import async_playwright


async def find_institutional_access():
    """Find how to actually get to institutional access."""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        page = await browser.new_page()
        
        # Go to IEEE main page
        print("1️⃣ Going to IEEE main page...")
        await page.goto("https://ieeexplore.ieee.org/", wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        # Accept cookies
        try:
            accept = await page.query_selector('button:has-text("Accept All")')
            if accept:
                await accept.click()
                print("   ✅ Accepted cookies")
                await page.wait_for_timeout(1000)
        except:
            pass
        
        # Look for ALL sign in options
        print("\n2️⃣ Looking for ALL sign in related links/buttons...")
        
        # Get all links and buttons
        all_elements = await page.query_selector_all('a, button')
        sign_in_elements = []
        
        for elem in all_elements:
            try:
                text = await elem.text_content()
                if text and ('sign' in text.lower() or 'login' in text.lower() or 
                           'institution' in text.lower() or 'access' in text.lower()):
                    tag = await elem.evaluate('el => el.tagName')
                    href = await elem.get_attribute('href') if tag == 'A' else None
                    sign_in_elements.append((text.strip(), tag, href))
            except:
                pass
        
        print("   Found sign-in related elements:")
        for text, tag, href in sign_in_elements:
            print(f"   • <{tag}> '{text}' → {href}")
        
        # Try clicking "Sign In" first
        print("\n3️⃣ Clicking main Sign In...")
        sign_in = await page.query_selector('a:has-text("Sign In"), button:has-text("Sign In")')
        if sign_in:
            await sign_in.click()
            await page.wait_for_timeout(2000)
            print("   ✅ Clicked Sign In")
        
        # Now look for institutional options
        print("\n4️⃣ Looking for institutional access options...")
        
        # Check if we're on a sign-in page
        current_url = page.url
        print(f"   Current URL: {current_url}")
        
        # Look for institutional links
        inst_links = await page.query_selector_all('a, button')
        for link in inst_links:
            try:
                text = await link.text_content()
                if text and 'institution' in text.lower():
                    href = await link.get_attribute('href') if await link.evaluate('el => el.tagName') == 'A' else None
                    print(f"   Found: '{text.strip()}' → {href}")
            except:
                pass
        
        # Check for OpenAthens or Shibboleth links
        print("\n5️⃣ Looking for OpenAthens/Shibboleth...")
        auth_methods = await page.query_selector_all('a[href*="openathens"], a[href*="shibboleth"], a[href*="wayf"], a[href*="institution"]')
        for link in auth_methods:
            text = await link.text_content()
            href = await link.get_attribute('href')
            print(f"   Found auth method: '{text}' → {href}")
        
        # Try a different approach - go directly to a paper
        print("\n6️⃣ Going to a specific paper to test access...")
        paper_url = "https://ieeexplore.ieee.org/document/7780459"  # ResNet paper
        await page.goto(paper_url, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        # Look for access options on the paper page
        print("\n7️⃣ Looking for access options on paper page...")
        
        # Look for "Get Full Text" or similar
        access_buttons = await page.query_selector_all('button, a')
        for btn in access_buttons:
            try:
                text = await btn.text_content()
                if text and ('full text' in text.lower() or 'pdf' in text.lower() or 
                           'download' in text.lower() or 'access' in text.lower()):
                    print(f"   Found access option: '{text.strip()}'")
            except:
                pass
        
        print("\n🔍 Keeping browser open for manual exploration...")
        print("Try to find the institutional access manually.")
        print("Press Enter to close...")
        input()
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(find_institutional_access())