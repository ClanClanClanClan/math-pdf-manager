#!/usr/bin/env python3
"""
DETAILED WILEY DEBUG
====================

Let's see exactly what links are available after accepting cookies
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

async def debug_wiley_detailed():
    """Detailed debug of Wiley page"""
    
    print("🔍 DETAILED WILEY DEBUG")
    print("=" * 80)
    
    test_doi = "10.1002/anie.202004934"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Show browser
            args=['--start-maximized']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        # Navigate to DOI
        url = f"https://doi.org/{test_doi}"
        print(f"📍 Navigating to: {url}")
        await page.goto(url, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        # Accept cookies
        try:
            cookie_btn = await page.wait_for_selector('button:has-text("Accept All")', timeout=5000)
            if cookie_btn:
                print("🍪 Accepting cookies...")
                await cookie_btn.click()
                await page.wait_for_timeout(2000)
        except:
            print("❌ No cookie banner found")
        
        # Screenshot after cookies
        await page.screenshot(path='wiley_after_cookies.png')
        print("📸 Screenshot: wiley_after_cookies.png")
        
        # Check all links in the top navigation area
        print("\n🔍 Top navigation links:")
        nav_links = await page.query_selector_all('nav a, header a, [role="navigation"] a')
        for link in nav_links[:20]:
            try:
                text = await link.inner_text()
                href = await link.get_attribute('href')
                if text.strip():
                    print(f"   📎 '{text.strip()}' -> {href}")
            except:
                pass
        
        # Look for any login/sign in related elements
        print("\n🔍 Login-related elements:")
        login_selectors = [
            'a:has-text("Login")',
            'a:has-text("Sign in")',
            'a:has-text("Register")',
            'button:has-text("Login")',
            'button:has-text("Sign in")',
            '*:has-text("Institutional")',
            'a[href*="login"]',
            'a[href*="signin"]',
            'a[href*="sso"]',
            'a[href*="institution"]'
        ]
        
        for selector in login_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"\n   Found {len(elements)} elements matching: {selector}")
                    for i, elem in enumerate(elements[:3]):
                        try:
                            text = await elem.inner_text()
                            tag = await elem.evaluate('el => el.tagName')
                            href = await elem.get_attribute('href') if tag.lower() == 'a' else None
                            visible = await elem.is_visible()
                            print(f"      [{i+1}] <{tag}> '{text.strip()}' visible={visible}")
                            if href:
                                print(f"          href: {href}")
                        except:
                            pass
            except:
                pass
        
        # Check the article access status
        print("\n🔍 Article access status:")
        
        # Look for access indicators
        access_elements = await page.query_selector_all('*:has-text("access"), *:has-text("Access")')
        for elem in access_elements[:10]:
            try:
                text = await elem.inner_text()
                if len(text) < 100 and text.strip():
                    print(f"   📌 '{text.strip()}'")
            except:
                pass
        
        # Try clicking on Login/Register if found
        print("\n🖱️ Trying to click Login/Register...")
        try:
            login_link = await page.wait_for_selector('a:has-text("Login / Register")', timeout=5000)
            if login_link:
                print("   ✅ Found 'Login / Register' link")
                await login_link.click()
                await page.wait_for_timeout(5000)
                
                new_url = page.url
                print(f"   📍 New URL: {new_url}")
                
                # Screenshot after click
                await page.screenshot(path='wiley_after_login_click.png')
                print("   📸 Screenshot: wiley_after_login_click.png")
                
                # Look for institutional options
                print("\n   🔍 Looking for institutional options after login click:")
                inst_options = await page.query_selector_all('*:has-text("institution"), *:has-text("Institution")')
                for opt in inst_options[:10]:
                    try:
                        text = await opt.inner_text()
                        if len(text) < 100:
                            print(f"      📌 '{text.strip()}'")
                    except:
                        pass
        except:
            print("   ❌ Could not find Login/Register link")
        
        print("\n⏸️ Keeping browser open for 30 seconds...")
        await page.wait_for_timeout(30000)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_wiley_detailed())