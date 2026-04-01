#!/usr/bin/env python3
"""
Test Wiley ETH Institutional Access
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def test_wiley_eth_access():
    """Test if Wiley has ETH institutional access."""
    
    # Use the working DOI from manual test
    working_doi = '10.1002/9781119083405.ch1'
    
    print(f"🔍 TESTING WILEY ETH ACCESS")
    print(f"=" * 40)
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
            
            # Handle cookies aggressively
            print(f"\n🍪 Handling cookies...")
            cookie_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Allow")', 
                'button:has-text("Agree")',
                'button[id*="accept"]',
                'button[class*="accept"]',
                '.cookie-accept button',
                '#cookie-banner button'
            ]
            
            for selector in cookie_selectors:
                try:
                    btn = await page.query_selector(selector)
                    if btn:
                        await btn.click()
                        await asyncio.sleep(1)
                        print(f"✅ Clicked cookie button: {selector}")
                        break
                except:
                    continue
            
            # Look for institutional access
            print(f"\n🔐 Looking for institutional access...")
            
            signin_selectors = [
                'a:has-text("Institutional Login")',
                'a:has-text("Sign in")',
                'a:has-text("Log in")', 
                'a:has-text("Access through")',
                'a[href*="login"]',
                'a[href*="institutional"]',
                '.institutional-login a'
            ]
            
            signin_button = None
            for selector in signin_selectors:
                signin_button = await page.query_selector(selector)
                if signin_button:
                    text = await signin_button.inner_text()
                    print(f"✅ Found sign-in: '{text}'")
                    break
            
            if not signin_button:
                print(f"❌ No institutional sign-in found")
                return False
            
            # Click with force to bypass overlays
            print(f"\n🔗 Clicking institutional login...")
            await signin_button.click(force=True)
            await page.wait_for_load_state('domcontentloaded', timeout=15000)
            
            auth_url = page.url
            print(f"Auth page: {auth_url}")
            
            # Look for WAYF or institution search
            print(f"\n🏛️  Looking for institution selection...")
            
            # Check if we're at a WAYF page
            page_content = await page.content()
            if 'wayf' in page_content.lower() or 'where are you from' in page_content.lower():
                print(f"✅ Detected WAYF system")
            
            # Look for institution search input
            search_selectors = [
                'input[placeholder*="institution"]',
                'input[placeholder*="organization"]',
                'input[placeholder*="university"]',
                'input[type="search"]',
                'input[name*="institution"]',
                'input[name*="org"]'
            ]
            
            institution_input = None
            for selector in search_selectors:
                institution_input = await page.query_selector(selector)
                if institution_input:
                    placeholder = await institution_input.get_attribute('placeholder') or ""
                    print(f"✅ Found search input: '{placeholder}'")
                    break
            
            if institution_input:
                # Test ETH search
                print(f"\n🔍 Searching for ETH...")
                
                await institution_input.click(force=True)
                await institution_input.fill("ETH Zurich")
                await asyncio.sleep(3000)
                
                # Look for ETH in results
                eth_found = False
                
                # Check if page content updated
                updated_content = await page.content()
                if 'ETH' in updated_content or 'Zurich' in updated_content:
                    print(f"✅ ETH found in page content!")
                    
                    # Look for clickable ETH options
                    all_elements = await page.query_selector_all('a, li, div, option')
                    
                    for element in all_elements[:30]:
                        try:
                            text = await element.inner_text()
                            if text and 'ETH' in text and len(text) > 5:
                                print(f"🎯 Found ETH option: '{text[:60]}'")
                                
                                # Try clicking it
                                await element.click()
                                await page.wait_for_timeout(3000)
                                
                                final_url = page.url
                                if 'ethz.ch' in final_url:
                                    print(f"🎉 SUCCESS: Reached ETH at {final_url}")
                                    return True
                                elif final_url != auth_url:
                                    print(f"🔄 Redirected to: {final_url}")
                                    if 'shibboleth' in final_url or 'wayf' in final_url:
                                        print(f"✅ Looks like Shibboleth redirect")
                                        return True
                                
                                eth_found = True
                                break
                        except:
                            continue
                
                if not eth_found:
                    # Try Enter key
                    print(f"🔍 Trying Enter key...")
                    await page.keyboard.press('Enter')
                    await page.wait_for_timeout(3000)
                    
                    enter_url = page.url
                    if 'ethz.ch' in enter_url:
                        print(f"🎉 SUCCESS: Enter worked!")
                        return True
                    elif enter_url != auth_url:
                        print(f"🔄 Enter redirected to: {enter_url}")
                        return True
            else:
                # Look for direct ETH links
                print(f"🔍 Looking for direct ETH links...")
                
                all_links = await page.query_selector_all('a')
                for link in all_links[:30]:
                    try:
                        text = await link.inner_text()
                        href = await link.get_attribute('href')
                        
                        if text and ('ETH' in text or 'Zurich' in text):
                            print(f"🎯 Found ETH link: '{text[:50]}'")
                            await link.click()
                            await page.wait_for_timeout(3000)
                            
                            final_url = page.url
                            if 'ethz.ch' in final_url:
                                print(f"🎉 SUCCESS: Direct link worked!")
                                return True
                            
                    except:
                        continue
            
            print(f"❌ No ETH access found")
            return False
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_wiley_eth_access())
    
    if result:
        print(f"\n🎉 WILEY: ETH ACCESS CONFIRMED")
        print(f"✅ Recommended as third publisher")
    else:
        print(f"\n❌ WILEY: ETH ACCESS NOT CONFIRMED") 
        print(f"⚠️  All tested publishers may lack ETH access")