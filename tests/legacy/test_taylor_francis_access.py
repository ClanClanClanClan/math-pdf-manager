#!/usr/bin/env python3
"""
Test Taylor & Francis ETH Institutional Access
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def test_taylor_francis_eth_access():
    """Test if Taylor & Francis has ETH institutional access."""
    
    # Use the working DOI from manual test
    working_doi = '10.1080/01621459.2021.1886936'
    
    print(f"🔍 TESTING TAYLOR & FRANCIS ETH ACCESS")
    print(f"=" * 50)
    print(f"DOI: {working_doi}")
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to paper
            url = f"https://doi.org/{working_doi}"
            print(f"🌐 Navigating to: {url}")
            
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            current_url = page.url
            title = await page.title()
            
            print(f"✅ Reached: {current_url}")
            print(f"Title: {title[:60]}...")
            
            # Look for institutional access
            print(f"\n🔐 Looking for institutional access...")
            
            # Handle cookies first
            cookie_buttons = await page.query_selector_all('button:has-text("Accept"), button:has-text("Allow")')
            for btn in cookie_buttons:
                try:
                    await btn.click()
                    await asyncio.sleep(1)
                    break
                except:
                    continue
            
            # Look for sign-in/institutional access
            signin_selectors = [
                'a:has-text("Sign in")',
                'a:has-text("Log in")', 
                'a:has-text("Institutional")',
                'a:has-text("Access through")',
                'a[href*="login"]',
                'a[href*="signin"]',
                'a[href*="institutional"]'
            ]
            
            signin_button = None
            for selector in signin_selectors:
                signin_button = await page.query_selector(selector)
                if signin_button:
                    text = await signin_button.inner_text()
                    print(f"✅ Found sign-in option: '{text}'")
                    break
            
            if not signin_button:
                print(f"❌ No sign-in options found")
                return False
            
            # Click sign-in
            print(f"\n🔗 Clicking sign-in...")
            await signin_button.click()
            await page.wait_for_load_state('domcontentloaded', timeout=15000)
            
            auth_url = page.url
            auth_title = await page.title()
            print(f"Auth page: {auth_url}")
            print(f"Auth title: {auth_title}")
            
            # Look for institution search
            print(f"\n🏛️  Looking for institution search...")
            
            # Common institution search patterns
            search_inputs = await page.query_selector_all('input[type="text"], input[type="search"], input[placeholder*="institution"], input[placeholder*="organization"]')
            
            institution_input = None
            for input_elem in search_inputs:
                try:
                    placeholder = await input_elem.get_attribute('placeholder')
                    name = await input_elem.get_attribute('name')
                    
                    if placeholder and any(term in placeholder.lower() for term in ['institution', 'organization', 'university']):
                        print(f"✅ Found institution search: placeholder='{placeholder}', name='{name}'")
                        institution_input = input_elem
                        break
                except:
                    continue
            
            if not institution_input:
                # Try any text input
                text_inputs = await page.query_selector_all('input[type="text"]')
                if text_inputs:
                    institution_input = text_inputs[0]
                    print(f"✅ Using first text input as institution search")
            
            if institution_input:
                # Test ETH search
                print(f"\n🔍 Testing ETH search...")
                
                await institution_input.click()
                await institution_input.fill("ETH Zurich")
                await asyncio.sleep(2000)
                
                # Look for ETH results
                page_content = await page.content()
                
                if 'ETH' in page_content or 'Zurich' in page_content:
                    print(f"✅ Found ETH/Zurich in page content!")
                    
                    # Look for clickable ETH options
                    eth_links = await page.query_selector_all('a, li, div')
                    eth_options = []
                    
                    for link in eth_links[:20]:
                        try:
                            text = await link.inner_text()
                            if text and ('ETH' in text or 'Zurich' in text):
                                eth_options.append(text.strip()[:80])
                        except:
                            continue
                    
                    if eth_options:
                        print(f"🎯 Found {len(eth_options)} ETH options:")
                        for option in eth_options[:5]:
                            print(f"   • {option}")
                        
                        # Try clicking first ETH option
                        for link in eth_links[:20]:
                            try:
                                text = await link.inner_text()
                                if text and 'ETH' in text and 'Zurich' in text:
                                    print(f"\n🔗 Clicking: '{text[:50]}'")
                                    await link.click()
                                    await page.wait_for_load_state('domcontentloaded', timeout=10000)
                                    
                                    final_url = page.url
                                    print(f"Final URL: {final_url}")
                                    
                                    if 'ethz.ch' in final_url:
                                        print(f"🎉 SUCCESS: Reached ETH login!")
                                        return True
                                    else:
                                        print(f"🔄 Redirected but not to ETH")
                                    break
                            except:
                                continue
                    else:
                        print(f"❌ No clickable ETH options found")
                else:
                    print(f"❌ No ETH/Zurich found in search results")
                    
                    # Try pressing Enter
                    print(f"🔍 Trying Enter key...")
                    await page.keyboard.press('Enter')
                    await page.wait_for_load_state('domcontentloaded', timeout=10000)
                    
                    enter_url = page.url
                    if 'ethz.ch' in enter_url:
                        print(f"🎉 SUCCESS: Enter key worked!")
                        return True
                    else:
                        print(f"❌ Enter didn't redirect to ETH")
            else:
                print(f"❌ No institution search input found")
            
            print(f"\n⏸️  Page analysis complete")
            return False
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_taylor_francis_eth_access())
    
    if result:
        print(f"\n🎉 TAYLOR & FRANCIS: ETH ACCESS CONFIRMED")
        print(f"✅ Recommended as third publisher")
    else:
        print(f"\n❌ TAYLOR & FRANCIS: ETH ACCESS NOT CONFIRMED") 
        print(f"⚠️  May need to try Wiley or other alternatives")