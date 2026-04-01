#!/usr/bin/env python3
"""
Fixed IEEE Test - Handle IEEE Xplore Page State and Modal System Correctly
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def test_fixed_ieee():
    """Test IEEE with correct handling of page state and modal system."""
    
    test_doi = "10.1109/JPROC.2018.2820126"
    
    print(f"\n🔧 FIXED IEEE TEST")
    print(f"DOI: {test_doi}")
    print("Handling IEEE Xplore page state correctly...")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            from src.secure_credential_manager import get_credential_manager
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            # Navigate to paper
            url = f"https://doi.org/{test_doi}"
            print(f"🌐 Navigating to: {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(5000)  # Let page fully load
            
            print(f"📍 Current URL: {page.url}")
            
            # Accept cookies first
            try:
                cookie_btn = await page.query_selector('button:has-text("Accept All")')
                if cookie_btn:
                    await cookie_btn.click()
                    print("✅ Accepted cookies")
                    await page.wait_for_timeout(2000)
            except:
                pass
            
            print(f"\n🔐 STARTING AUTHENTICATION...")
            
            # The key insight: IEEE shows institutional login but page state shows restrictions
            # We need to authenticate first to change the page state
            
            # Step 1: Find institutional sign in (we know it exists from debug)
            institutional_selectors = [
                'a.inst-sign-in',
                'xpl-login-modal-trigger:has-text("Institutional Sign In")',
                'div.institution-container a'
            ]
            
            login_button = None
            for selector in institutional_selectors:
                try:
                    login_button = await page.query_selector(selector)
                    if login_button and await login_button.is_visible():
                        print(f"✅ Found institutional login: {selector}")
                        break
                except:
                    continue
            
            if not login_button:
                print("❌ Could not find institutional login button")
                return False
            
            # Click institutional sign in
            await login_button.click()
            print("✅ Clicked institutional sign in")
            await page.wait_for_timeout(3000)
            
            # Step 2: Handle the modal that appears
            # Look for SeamlessAccess button in modal
            seamless_selectors = [
                'button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn',
                'button:has-text("Access Through Your Institution")',
                'div.seamless-access-btn-idp'
            ]
            
            seamless_btn = None
            for selector in seamless_selectors:
                try:
                    seamless_btn = await page.wait_for_selector(selector, timeout=5000, state='visible')
                    if seamless_btn:
                        print(f"✅ Found SeamlessAccess: {selector}")
                        break
                except:
                    continue
            
            if not seamless_btn:
                print("❌ Could not find SeamlessAccess button")
                return False
            
            await seamless_btn.click()
            print("✅ Clicked SeamlessAccess button")
            await page.wait_for_timeout(3000)
            
            # Step 3: Search for ETH in the institution search
            search_selectors = [
                'input.inst-typeahead-input',
                'input[aria-label*="Institution"]',
                'input[placeholder*="institution"]'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = await page.wait_for_selector(selector, timeout=5000, state='visible')
                    if search_input:
                        print(f"✅ Found search input: {selector}")
                        break
                except:
                    continue
            
            if not search_input:
                print("❌ Could not find institution search input")
                return False
            
            # Clear and type ETH Zurich
            await search_input.click()
            await search_input.fill("")
            await search_input.type("ETH Zurich", delay=100)
            print("✅ Entered ETH Zurich")
            await page.wait_for_timeout(3000)  # Wait for dropdown
            
            # Step 4: Select ETH from dropdown
            eth_selectors = [
                'a[id="ETH Zurich - ETH Zurich"]',
                'a#ETH\\\\ Zurich\\\\ -\\\\ ETH\\\\ Zurich',
                'div.selection-item a:has-text("ETH Zurich")',
                'a[href*="aai-logon.ethz.ch"]'
            ]
            
            eth_option = None
            for selector in eth_selectors:
                try:
                    eth_option = await page.wait_for_selector(selector, timeout=5000, state='visible')
                    if eth_option:
                        print(f"✅ Found ETH option: {selector}")
                        break
                except:
                    continue
            
            if not eth_option:
                # If specific selectors fail, try finding any option with ETH text
                dropdown_items = await page.query_selector_all('div.selection-item a, .institution-option a')
                for item in dropdown_items:
                    text = await item.text_content()
                    if text and 'ETH' in text and 'Zurich' in text:
                        eth_option = item
                        print(f"✅ Found ETH option by text: {text}")
                        break
            
            if not eth_option:
                print("❌ Could not find ETH option in dropdown")
                return False
            
            await eth_option.click()
            print("✅ Selected ETH Zurich")
            await page.wait_for_timeout(8000)  # Wait for navigation to ETH
            
            # Step 5: Handle ETH login
            if 'ethz.ch' in page.url.lower():
                print("✅ Reached ETH login page")
                
                # Fill username
                username_field = await page.wait_for_selector('input[name="j_username"]', timeout=10000)
                await username_field.fill(username)
                
                # Fill password
                password_field = await page.wait_for_selector('input[name="j_password"]', timeout=10000)
                await password_field.fill(password)
                
                # Submit
                submit_btn = await page.wait_for_selector('button[type="submit"]', timeout=10000)
                await submit_btn.click()
                print("✅ Submitted ETH credentials")
                
                # Wait for redirect back to IEEE
                await page.wait_for_timeout(15000)
                
                if 'ieeexplore.ieee.org' in page.url:
                    print("🎉 AUTHENTICATION SUCCESSFUL!")
                    print(f"📍 Back at IEEE: {page.url}")
                    
                    # Check if authentication changed the page state
                    sign_out = await page.query_selector('*:has-text("Sign Out")')
                    if sign_out:
                        print("✅ Confirmed authenticated - found Sign Out")
                    
                    # Now check PDF access state
                    print(f"\n📄 TESTING PDF ACCESS AFTER AUTHENTICATION...")
                    
                    # Look for PDF button or access
                    pdf_selectors = [
                        'a[href*="/stamp/stamp.jsp"]',
                        'xpl-view-pdf a',
                        'div.pdf-btn-container a'
                    ]
                    
                    pdf_button = None
                    for selector in pdf_selectors:
                        try:
                            pdf_button = await page.query_selector(selector)
                            if pdf_button and await pdf_button.is_visible():
                                href = await pdf_button.get_attribute('href')
                                print(f"✅ Found PDF button: {selector} -> {href}")
                                break
                        except:
                            continue
                    
                    if pdf_button:
                        # Test clicking the PDF button
                        print("🖱️  Clicking PDF button...")
                        
                        # Record current state
                        before_url = page.url
                        
                        # Click and wait for navigation or response
                        try:
                            # Try with navigation expectation
                            async with page.expect_navigation(timeout=10000) as nav_info:
                                await pdf_button.click()
                            
                            after_url = page.url
                            print(f"📍 After click: {after_url}")
                            
                            if '/stamp/stamp.jsp' in after_url:
                                print("🎉 PDF ACCESS SUCCESS!")
                                return True
                            else:
                                print(f"⚠️  PDF click redirected to: {after_url}")
                                
                        except Exception as nav_e:
                            # Navigation might have failed, check current state
                            await page.wait_for_timeout(3000)
                            current = page.url
                            
                            if current != before_url:
                                print(f"📍 Navigation occurred to: {current}")
                                if '/stamp/stamp.jsp' in current:
                                    print("🎉 PDF ACCESS SUCCESS (delayed)!")
                                    return True
                            else:
                                print("❌ PDF click failed - no navigation")
                        
                        # Try direct URL approach
                        print("🔗 Trying direct PDF URL approach...")
                        href = await pdf_button.get_attribute('href')
                        if href:
                            pdf_url = f"https://ieeexplore.ieee.org{href}" if href.startswith('/') else href
                            
                            response = await page.goto(pdf_url, timeout=10000)
                            final_url = page.url
                            
                            print(f"📍 Direct URL result: {final_url}")
                            
                            if '/stamp/stamp.jsp' in final_url:
                                print("🎉 DIRECT PDF ACCESS SUCCESS!")
                                return True
                            else:
                                print(f"❌ Direct PDF access redirected to: {final_url}")
                                
                    else:
                        print("❌ No PDF button found after authentication")
                        
                        # Check if page shows different content now
                        page_text = await page.evaluate("() => document.body.innerText")
                        if 'not available' in page_text.lower():
                            print("⚠️  Page still shows 'not available' after authentication")
                        else:
                            print("✅ Page restrictions may have been removed")
                
                else:
                    print("❌ Not redirected back to IEEE after authentication")
                    
            else:
                print("❌ Not redirected to ETH login page")
                
            return False
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            print(f"\n⏸️  Browser staying open for manual verification...")
            await page.wait_for_timeout(60000)  # 1 minute
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(test_fixed_ieee())
    if success:
        print("\n🎉 FIXED IEEE ACCESS SUCCESSFUL!")
    else:
        print("\n❌ Issues still remain - needs more investigation")