#!/usr/bin/env python3
"""
IEEE Debug Real Issues
======================

Debug exactly why IEEE authentication fails when user has access.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def ieee_debug_real():
    print("🔍 DEBUGGING REAL IEEE AUTHENTICATION ISSUES")
    print("=" * 60)
    
    # Get credentials
    try:
        from src.secure_credential_manager import get_credential_manager
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        if not username or not password:
            print("❌ No ETH credentials")
            return False
            
        print(f"✅ Using credentials: {username[:3]}***")
            
    except Exception as e:
        print(f"❌ Credential error: {e}")
        return False
    
    # Test one of the failing DOIs
    test_doi = "10.1109/MC.2006.5"  # Amdahl's law - user confirmed accessible
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            print(f"\n1️⃣ TESTING DIRECT IEEE ACCESS")
            # Try both DOI resolver and direct IEEE URL
            urls_to_test = [
                f"https://doi.org/{test_doi}",
                f"https://ieeexplore.ieee.org/document/{test_doi.split('/')[-1]}"
            ]
            
            working_url = None
            for url in urls_to_test:
                print(f"   Testing: {url}")
                try:
                    response = await page.goto(url, timeout=30000)
                    if response and response.status == 200:
                        await page.wait_for_timeout(5000)
                        
                        # Check if we actually got the paper page
                        title = await page.title()
                        current_url = page.url
                        
                        print(f"   Status: {response.status}")
                        print(f"   Title: {title}")
                        print(f"   Final URL: {current_url}")
                        
                        # Look for signs this is the actual paper
                        if 'amdahl' in title.lower() or 'multicore' in title.lower():
                            print(f"   ✅ Found the paper page!")
                            working_url = current_url
                            break
                        else:
                            print(f"   ❌ This doesn't look like the paper page")
                    else:
                        print(f"   ❌ HTTP {response.status if response else 'failed'}")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
            
            if not working_url:
                print("\n❌ Could not find the paper at all!")
                await browser.close()
                return False
            
            print(f"\n2️⃣ CHECKING ACCESS WITHOUT LOGIN")
            # Take screenshot to see what we get
            await page.screenshot(path="ieee_debug_no_login.png")
            
            # Look for download/access indicators
            content = await page.content()
            
            access_indicators = {
                'pdf_available': 'download pdf' in content.lower() or 'view pdf' in content.lower(),
                'full_text': 'full text access' in content.lower(),
                'abstract_only': 'abstract' in content.lower() and 'full text' not in content.lower(),
                'paywall': 'purchase' in content.lower() or 'subscribe' in content.lower(),
                'institutional_access': 'institutional' in content.lower()
            }
            
            print("   Access indicators:")
            for indicator, present in access_indicators.items():
                status = "✅" if present else "❌"
                print(f"     {status} {indicator}: {present}")
            
            print(f"\n3️⃣ LOOKING FOR INSTITUTIONAL LOGIN")
            # Look for various institutional login options
            institutional_selectors = [
                'a:has-text("Institutional Sign In")',
                'a:has-text("Access through your institution")',  
                'a:has-text("Sign in via your institution")',
                'button:has-text("Institutional")',
                'a[href*="institutional"]',
                'a[href*="shibboleth"]',
                '.institutional-signin',
                '#institutional-signin'
            ]
            
            institutional_option = None
            for selector in institutional_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=3000)
                    if element:
                        text = await element.text_content()
                        is_visible = await element.is_visible()
                        href = await element.get_attribute('href')
                        print(f"   ✅ Found: {selector}")
                        print(f"      Text: '{text}'")
                        print(f"      Visible: {is_visible}")
                        print(f"      Href: {href}")
                        if is_visible:
                            institutional_option = element
                            break
                except:
                    continue
            
            if not institutional_option:
                print("   ❌ No institutional login option found!")
                
                # Let's see what login options ARE available
                print("\n   Looking for any login options...")
                login_selectors = [
                    'a:has-text("Sign In")',
                    'a:has-text("Login")',
                    'button:has-text("Sign In")',
                    'button:has-text("Login")',
                    '[href*="login"]',
                    '[href*="signin"]'
                ]
                
                for selector in login_selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=2000)
                        if element:
                            text = await element.text_content()
                            is_visible = await element.is_visible()
                            href = await element.get_attribute('href')
                            print(f"     Found login option: {selector}")
                            print(f"       Text: '{text}', Visible: {is_visible}, Href: {href}")
                    except:
                        continue
                
                await browser.close()
                return False
            
            print(f"\n4️⃣ TRYING INSTITUTIONAL LOGIN")
            await institutional_option.click()
            await page.wait_for_timeout(5000)
            
            current_url = page.url
            print(f"   URL after institutional click: {current_url}")
            
            await page.screenshot(path="ieee_debug_after_institutional.png")
            
            # Look for ETH in the list
            print("   Looking for ETH Zurich...")
            eth_selectors = [
                'text="ETH Zurich"',
                'text="Swiss Federal Institute of Technology"',
                ':has-text("ETH")',
                ':has-text("Zurich")',
                'option:has-text("ETH")'
            ]
            
            found_eth = False
            for selector in eth_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        print(f"   ✅ Found ETH option: {selector}")
                        await element.click()
                        found_eth = True
                        break
                except:
                    continue
            
            if not found_eth:
                print("   ❌ Could not find ETH in institutional list!")
                await browser.close()
                return False
            
            await page.wait_for_timeout(5000)
            
            print(f"\n5️⃣ ETH LOGIN")
            try:
                # ETH login form
                username_input = await page.wait_for_selector('input[name="j_username"]', timeout=15000)
                await username_input.fill(username)
                
                password_input = await page.wait_for_selector('input[name="j_password"]', timeout=5000)
                await password_input.fill(password)
                
                submit_button = await page.wait_for_selector('button[type="submit"]', timeout=5000)
                await submit_button.click()
                
                print("   ✅ Submitted ETH credentials")
                await page.wait_for_timeout(10000)
                
                # Check if we're back at the paper with access
                final_url = page.url
                final_title = await page.title()
                
                print(f"   Final URL: {final_url}")
                print(f"   Final title: {final_title}")
                
                await page.screenshot(path="ieee_debug_after_login.png")
                
                # Check if we now have PDF access
                final_content = await page.content()
                has_pdf_access = 'download pdf' in final_content.lower() or 'view pdf' in final_content.lower()
                
                if has_pdf_access:
                    print("   🎉 SUCCESS: Now have PDF access!")
                    return True
                else:
                    print("   ❌ Still no PDF access after login")
                    return False
                
            except Exception as e:
                print(f"   ❌ ETH login failed: {e}")
                return False
            
            await browser.close()
            
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        return False

async def main():
    success = await ieee_debug_real()
    
    if success:
        print("\n🎉 IEEE authentication flow is working!")
        print("The issue might be in how the publisher class handles the flow.")
    else:
        print("\n❌ IEEE authentication has fundamental issues")
        print("Need to investigate why manual access works but automation doesn't")

if __name__ == "__main__":
    asyncio.run(main())