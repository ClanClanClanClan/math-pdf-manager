#!/usr/bin/env python3
"""
Test IEEE Debug
===============

Debug the IEEE institutional login flow step by step to see what's happening.
"""

import asyncio
import sys
sys.path.append('src')

from playwright.async_api import async_playwright
from secure_credential_manager import get_credential_manager


async def debug_ieee_institutional_flow():
    """Debug the IEEE institutional login step by step."""
    print("🔍 DEBUGGING IEEE INSTITUTIONAL FLOW")
    print("=" * 60)
    
    # Get credentials
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        print("❌ No ETH credentials found!")
        return False
    
    test_doi = "10.1109/JPROC.2018.2820126"
    ieee_url = f"https://doi.org/{test_doi}"
    
    async with async_playwright() as p:
        # Launch with head for visual debugging
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print(f"\n1️⃣ NAVIGATING TO IEEE: {ieee_url}")
            await page.goto(ieee_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)
            print(f"   Current URL: {page.url}")
            
            print(f"\n2️⃣ HANDLING COOKIES")
            try:
                accept_button = await page.query_selector('button:has-text("Accept All")')
                if accept_button:
                    print("   ✅ Found and clicked Accept All")
                    await accept_button.click()
                    await page.wait_for_timeout(1000)
                else:
                    print("   ⚠️ No cookie dialog found")
            except Exception as e:
                print(f"   ⚠️ Cookie handling error: {e}")
            
            print(f"\n3️⃣ LOOKING FOR INSTITUTIONAL SIGN IN")
            try:
                # Try multiple selector variations
                selectors_to_try = [
                    'a:has-text("Institutional Sign In")',
                    'a:has-text("Institution")', 
                    'button:has-text("Institution")',
                    'a[href*="institution"]',
                    'a[href*="shibboleth"]',
                ]
                
                inst_button = None
                for selector in selectors_to_try:
                    print(f"   Trying selector: {selector}")
                    try:
                        inst_button = await page.wait_for_selector(selector, timeout=3000)
                        if inst_button:
                            text = await inst_button.text_content()
                            print(f"   ✅ Found: {text.strip()}")
                            break
                    except:
                        print(f"   ❌ Not found")
                        continue
                
                if not inst_button:
                    print("   🔍 Let's see what's actually on the page...")
                    # Get all links on the page
                    all_links = await page.query_selector_all('a')
                    print(f"   Found {len(all_links)} links on page:")
                    
                    for i, link in enumerate(all_links[:10]):  # Show first 10
                        try:
                            text = await link.text_content()
                            href = await link.get_attribute('href')
                            if text and text.strip():
                                print(f"     [{i+1}] '{text.strip()}' → {href}")
                        except:
                            continue
                    
                    # Also check for buttons
                    all_buttons = await page.query_selector_all('button')
                    print(f"   Found {len(all_buttons)} buttons on page:")
                    
                    for i, button in enumerate(all_buttons[:10]):  # Show first 10
                        try:
                            text = await button.text_content()
                            if text and text.strip():
                                print(f"     [{i+1}] BUTTON: '{text.strip()}'")
                        except:
                            continue
                    
                    return False
                
                print(f"   Clicking institutional button...")
                await inst_button.click()
                await page.wait_for_timeout(2000)
                print(f"   New URL: {page.url}")
                
            except Exception as e:
                print(f"   💥 Error finding institutional button: {e}")
                return False
            
            print(f"\n4️⃣ LOOKING FOR MODAL")
            try:
                modal_selectors = [
                    'ngb-modal-window',
                    '.modal',
                    '[role="dialog"]',
                    '.institutional-modal'
                ]
                
                modal = None
                for selector in modal_selectors:
                    try:
                        modal = await page.wait_for_selector(selector, timeout=3000)
                        if modal:
                            print(f"   ✅ Found modal with selector: {selector}")
                            break
                    except:
                        continue
                
                if modal:
                    # Get all links in modal
                    modal_links = await modal.query_selector_all('a')
                    print(f"   Modal has {len(modal_links)} links:")
                    
                    for i, link in enumerate(modal_links):
                        try:
                            text = await link.text_content()
                            href = await link.get_attribute('href')
                            if text and text.strip():
                                print(f"     [{i+1}] '{text.strip()}' → {href}")
                        except:
                            continue
                    
                    # Look for institution access
                    access_selectors = [
                        'a:has-text("Access through your institution")',
                        'a:has-text("Institution")',
                        'a:has-text("Institutional access")',
                        'a[href*="institution"]'
                    ]
                    
                    access_link = None
                    for selector in access_selectors:
                        try:
                            access_link = await modal.query_selector(selector)
                            if access_link:
                                text = await access_link.text_content()
                                print(f"   ✅ Found access link: '{text.strip()}'")
                                break
                        except:
                            continue
                    
                    if access_link:
                        await access_link.click()
                        await page.wait_for_load_state('networkidle')
                        print(f"   Clicked access link. New URL: {page.url}")
                    else:
                        print("   ❌ No access link found in modal")
                        return False
                        
                else:
                    print("   ❌ No modal found")
                    return False
                    
            except Exception as e:
                print(f"   💥 Modal handling error: {e}")
                return False
            
            print(f"\n5️⃣ INSTITUTION SELECTION PAGE")
            await page.wait_for_timeout(2000)
            current_url = page.url
            print(f"   Current URL: {current_url}")
            
            # Take screenshot of institution selection page
            await page.screenshot(path="ieee_institution_selection.png")
            print("   📸 Screenshot saved: ieee_institution_selection.png")
            
            # Look for search box
            print("   Looking for search functionality...")
            search_selectors = [
                'input[placeholder*="institution"]',
                'input[placeholder*="organization"]', 
                'input[id="search"]',
                'input[role="searchbox"]',
                'input[type="search"]',
                'input[type="text"]'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = await page.query_selector(selector)
                    if search_input and await search_input.is_visible():
                        placeholder = await search_input.get_attribute('placeholder')
                        print(f"   ✅ Found search input: {selector} (placeholder: {placeholder})")
                        break
                except:
                    continue
            
            if search_input:
                await search_input.fill("ETH Zurich")
                await page.keyboard.press('Enter')
                await page.wait_for_timeout(2000)
                print("   Searched for 'ETH Zurich'")
            else:
                print("   ⚠️ No search input found")
                
                # Show all text on the page to find ETH
                page_text = await page.text_content('body')
                if 'ETH' in page_text or 'Zurich' in page_text:
                    print("   ✅ Page contains 'ETH' or 'Zurich' text")
                else:
                    print("   ❌ Page doesn't contain ETH/Zurich text")
            
            # Look for ETH options
            print("   Looking for ETH options...")
            eth_selectors = [
                'text="ETH Zurich"',
                'text="ETH - Swiss Federal Institute of Technology Zurich"',
                ':text("ETH")',
                ':text("Zurich")',
                'a:has-text("ETH")',
                'button:has-text("ETH")'
            ]
            
            eth_found = False
            for selector in eth_selectors:
                try:
                    eth_element = await page.query_selector(selector)
                    if eth_element:
                        text = await eth_element.text_content()
                        print(f"   ✅ Found ETH option: '{text.strip()}'")
                        
                        await eth_element.click()
                        await page.wait_for_load_state('networkidle')
                        print(f"   Clicked ETH option. New URL: {page.url}")
                        eth_found = True
                        break
                except Exception as e:
                    print(f"   ⚠️ Error with selector {selector}: {e}")
                    continue
            
            if not eth_found:
                print("   ❌ Could not find ETH option")
                
                # Show all visible text elements
                all_text_elements = await page.query_selector_all('a, button, span, div')
                print("   Showing all clickable text (first 20):")
                
                count = 0
                for element in all_text_elements:
                    try:
                        if count >= 20:
                            break
                        text = await element.text_content()
                        if text and text.strip() and len(text.strip()) > 3:
                            tag = await element.evaluate('el => el.tagName.toLowerCase()')
                            print(f"     {tag}: '{text.strip()}'")
                            count += 1
                    except:
                        continue
                
                return False
            
            print(f"\n6️⃣ LOGIN FORM")
            # We should now be at ETH login
            await page.wait_for_timeout(3000)
            print(f"   Login page URL: {page.url}")
            
            # Take screenshot of login page
            await page.screenshot(path="ieee_eth_login.png")
            print("   📸 Screenshot saved: ieee_eth_login.png")
            
            # Try to fill login form
            username_selectors = [
                'input[name="j_username"]',
                'input[id="username"]',
                'input[name="username"]',
                'input[type="text"]',
                'input[placeholder*="username"]'
            ]
            
            username_input = None
            for selector in username_selectors:
                try:
                    username_input = await page.query_selector(selector)
                    if username_input and await username_input.is_visible():
                        print(f"   ✅ Found username input: {selector}")
                        break
                except:
                    continue
            
            if username_input:
                await username_input.fill(username)
                print(f"   Filled username: {username[:3]}***")
                
                # Find password field
                password_selectors = [
                    'input[name="j_password"]',
                    'input[id="password"]',
                    'input[name="password"]',
                    'input[type="password"]'
                ]
                
                password_input = None
                for selector in password_selectors:
                    try:
                        password_input = await page.query_selector(selector)
                        if password_input and await password_input.is_visible():
                            print(f"   ✅ Found password input: {selector}")
                            break
                    except:
                        continue
                
                if password_input:
                    await password_input.fill(password)
                    print("   Filled password: ***")
                    
                    # Find submit button
                    submit_selectors = [
                        'button[type="submit"]',
                        'input[type="submit"]',
                        'button:has-text("Login")',
                        'button:has-text("Sign in")',
                        'input[value="Login"]'
                    ]
                    
                    submit_button = None
                    for selector in submit_selectors:
                        try:
                            submit_button = await page.query_selector(selector)
                            if submit_button:
                                print(f"   ✅ Found submit button: {selector}")
                                break
                        except:
                            continue
                    
                    if submit_button:
                        await submit_button.click()
                        print("   Clicked submit button")
                        
                        # Wait for authentication
                        await page.wait_for_timeout(5000)
                        final_url = page.url
                        print(f"   Final URL: {final_url}")
                        
                        if 'ieee' in final_url:
                            print("   🎉 SUCCESS: Back at IEEE after authentication!")
                            return True
                        else:
                            print("   ❌ Authentication may have failed - not back at IEEE")
                            return False
                    else:
                        print("   ❌ Could not find submit button")
                        return False
                else:
                    print("   ❌ Could not find password input")
                    return False
            else:
                print("   ❌ Could not find username input")
                return False
            
        finally:
            # Keep browser open for debugging
            print("\n🔍 Browser staying open for manual inspection...")
            print("Press Enter to close...")
            input()
            await browser.close()


async def main():
    """Run IEEE debug."""
    print("🔍 IEEE INSTITUTIONAL LOGIN DEBUG")
    print("=" * 80)
    print("Step-by-step debugging of the IEEE authentication flow.\n")
    
    success = await debug_ieee_institutional_flow()
    
    print("\n" + "=" * 80)
    print("🏁 DEBUG RESULTS")
    print("=" * 80)
    
    if success:
        print("🎉 IEEE authentication flow completed successfully!")
        print("The selectors and flow are working correctly.")
    else:
        print("❌ IEEE authentication flow failed.")
        print("Check the screenshots and console output to see where it breaks.")
        print("The selectors may need to be updated for the current IEEE website.")


if __name__ == "__main__":
    asyncio.run(main())