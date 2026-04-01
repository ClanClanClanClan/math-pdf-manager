#!/usr/bin/env python3
"""
Test Springer institutional access implementation
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.secure_credential_manager import get_credential_manager


async def test_springer_selectors():
    """Test with a real Springer DOI to identify selectors."""
    
    # Test with a Springer mathematics paper
    test_doi = "10.1007/s00211-021-01234-3"  # Numerical mathematics paper
    
    print(f"🧪 Testing Springer selectors with DOI: {test_doi}")
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            # Navigate to DOI (should redirect to Springer)
            url = f"https://doi.org/{test_doi}"
            print(f"🌐 Navigating to: {url}")
            
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Handle cookie banner first
            print("🍪 Checking for cookie banner...")
            cookie_candidates = [
                'button:has-text("Accept all")',
                'button:has-text("Accept All")', 
                'button:has-text("Accept")',
                'button.cc-allow',
                'button[data-cc-action="allow"]',
                'button[aria-label*="Accept"]'
            ]
            
            for selector in cookie_candidates:
                try:
                    cookie_btn = await page.query_selector(selector)
                    if cookie_btn:
                        print(f"  ✅ Found cookie button: {selector}")
                        await cookie_btn.click()
                        await page.wait_for_timeout(2000)
                        print("  ✅ Cookies accepted")
                        break
                except:
                    pass
            
            current_url = page.url
            print(f"📍 Current URL: {current_url}")
            
            # Check if we're at Springer
            if 'springer.com' in current_url:
                print("✅ At Springer Link")
            else:
                print(f"❌ Not at Springer: {current_url}")
                return
            
            # Look for login/sign in buttons
            print("\n🔍 Looking for login buttons...")
            
            login_candidates = [
                'a:has-text("Log in")',
                'a:has-text("Sign in")', 
                'a:has-text("Login")',
                'button:has-text("Log in")',
                'button:has-text("Sign in")',
                'a[class*="login"]',
                'button[class*="login"]',
                'a[href*="login"]',
                'a[href*="signin"]'
            ]
            
            found_login = None
            for selector in login_candidates:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        print(f"  ✅ Found: {selector} - '{text.strip()}'")
                        if not found_login:
                            found_login = selector
                except:
                    pass
            
            if not found_login:
                print("  ❌ No login button found")
                
                # Take screenshot for manual inspection
                await page.screenshot(path="springer_initial.png")
                print("📸 Screenshot saved: springer_initial.png")
                
                # List all links for inspection
                print("\n🔗 All links on page:")
                links = await page.query_selector_all('a')
                for i, link in enumerate(links[:20]):  # First 20 links
                    try:
                        href = await link.get_attribute('href')
                        text = await link.text_content()
                        if text and text.strip():
                            print(f"  {i+1}. '{text.strip()}' -> {href}")
                    except:
                        pass
                
                return
            
            # Click the login button
            print(f"\n🖱️  Clicking login button: {found_login}")
            try:
                await page.click(found_login, timeout=10000)
                await page.wait_for_timeout(3000)
            except Exception as e:
                print(f"  ❌ Click failed: {e}")
                # Try force click
                print("  🔧 Trying force click...")
                await page.locator(found_login).click(force=True)
                await page.wait_for_timeout(3000)
            
            # Check what page we're on now
            current_url = page.url
            print(f"📍 After login click: {current_url}")
            
            # Check page title and content
            title = await page.title()
            print(f"📜 Page title: {title}")
            
            # Look for all text content to understand the page
            print("\n📝 Page content preview:")
            try:
                body_text = await page.locator('body').text_content()
                # Show first 500 chars
                preview = body_text[:500].replace('\n', ' ').strip()
                print(f"  {preview}...")
            except:
                pass
            
            # Look for all buttons and links
            print("\n🔍 All buttons on page:")
            buttons = await page.query_selector_all('button')
            for i, button in enumerate(buttons[:10]):  # First 10 buttons
                try:
                    text = await button.text_content()
                    classes = await button.get_attribute('class')
                    if text and text.strip():
                        print(f"  {i+1}. Button: '{text.strip()}' (class: {classes})")
                except:
                    pass
            
            # Look for institutional login option
            print("\n🔍 Looking for institutional login options...")
            
            institutional_candidates = [
                'a:has-text("institutional")',
                'button:has-text("institutional")',
                'a:has-text("institution")',
                'button:has-text("institution")',
                'a:has-text("Shibboleth")',
                'a:has-text("federated")',
                'a:has-text("university")',
                'a:has-text("via your institution")',
                'a:has-text("through your institution")',
                'button:has-text("via your institution")',
                'button:has-text("through your institution")',
                'a[href*="shibboleth"]',
                'a[href*="institutional"]',
                'a[href*="saml"]'
            ]
            
            found_institutional = None
            for selector in institutional_candidates:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        print(f"  ✅ Found: {selector} - '{text.strip()}'")
                        if not found_institutional:
                            found_institutional = selector
                except:
                    pass
            
            if found_institutional:
                # Click institutional option
                print(f"\n🖱️  Clicking institutional: {found_institutional}")
                await page.click(found_institutional)
                await page.wait_for_timeout(3000)
                
                current_url = page.url
                print(f"📍 After institutional click: {current_url}")
            else:
                # Try clicking "Continue" button to see what happens
                continue_btn = await page.query_selector('button:has-text("Continue")')
                if continue_btn:
                    print("\n🖱️  Trying Continue button...")
                    await continue_btn.click()
                    await page.wait_for_timeout(3000)
                    
                    current_url = page.url
                    print(f"📍 After Continue: {current_url}")
                    
                    # Check page content again
                    title = await page.title()
                    print(f"📜 Page title: {title}")
                    
                    # Look for institutional options now
                    print("\n🔍 Re-checking for institutional options...")
                    for selector in institutional_candidates:
                        try:
                            element = await page.query_selector(selector)
                            if element:
                                text = await element.text_content()
                                print(f"  ✅ Found: {selector} - '{text.strip()}'")
                        except:
                            pass
            
            # Look for institution search/selection
            print("\n🔍 Looking for institution search...")
            
            search_candidates = [
                'input[placeholder*="institution"]',
                'input[placeholder*="university"]', 
                'input[placeholder*="search"]',
                'input[type="search"]',
                'input.search',
                'input#institution',
                'select[name*="institution"]',
                'select#institution'
            ]
            
            for selector in search_candidates:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        placeholder = await element.get_attribute('placeholder') 
                        name = await element.get_attribute('name')
                        print(f"  ✅ Found search: {selector} - placeholder:'{placeholder}' name:'{name}'")
                except:
                    pass
            
            # Look for ETH in any lists or options
            print("\n🔍 Looking for ETH options...")
            
            eth_candidates = [
                '*:has-text("ETH Zurich")',
                '*:has-text("Swiss Federal Institute")',
                '*:has-text("Zurich")',
                'option:has-text("ETH")',
                'a:has-text("ETH")'
            ]
            
            for selector in eth_candidates:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements[:3]:  # First 3 matches
                        text = await element.text_content()
                        tag = await element.evaluate('el => el.tagName')
                        print(f"  ✅ Found ETH: <{tag}> '{text.strip()}'")
                except:
                    pass
            
            # Take final screenshot
            await page.screenshot(path="springer_final_state.png")
            print("\n📸 Final screenshot: springer_final_state.png")
            
            print(f"\n✅ Selector discovery complete. Check screenshots for manual verification.")
            
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            await page.screenshot(path="springer_error.png")
        
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_springer_selectors())