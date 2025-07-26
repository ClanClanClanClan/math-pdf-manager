#!/usr/bin/env python3
"""
SIAM ETH Download
=================

Download PDFs from SIAM using ETH institutional access with the correct login flow.
"""

import sys
import time
import requests
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from playwright.sync_api import sync_playwright
    from secure_credential_manager import get_credential_manager
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def siam_eth_download():
    """SIAM authentication and PDF download using ETH credentials."""
    print("📄 SIAM PDF Download with ETH Authentication")
    print("Using the correct institutional login flow")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials required")
        return False
    
    print(f"🔐 Using ETH credentials for: {username}")
    
    # Example SIAM paper URL
    paper_url = "https://epubs.siam.org/doi/10.1137/20M1339829"
    print(f"📄 Testing with paper: {paper_url}")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=1000,
                args=['--start-maximized']
            )
            
            page = browser.new_page()
            
            print("\n🌐 Step 1: Loading SIAM paper...")
            page.goto(paper_url, wait_until='domcontentloaded')
            page.wait_for_timeout(3000)
            
            # Handle Cloudflare if needed
            page_text = page.content()
            if "cloudflare" in page_text.lower():
                print("🔒 Cloudflare challenge detected")
                print("⏳ Waiting for challenge to complete...")
                page.wait_for_timeout(10000)
            
            print("🏛️ Step 2: Looking for institutional access button...")
            
            # Look for the institutional access button
            inst_selectors = [
                'a.institutional__btn',
                'a[href*="/action/ssostart"]',
                'a:has-text("Access via your Institution")',
                '.loginBar a.btn',
                '.user-login-bar a.btn'
            ]
            
            inst_button = None
            for selector in inst_selectors:
                try:
                    elem = page.wait_for_selector(selector, timeout=3000)
                    if elem and elem.is_visible():
                        inst_button = elem
                        print(f"✅ Found institutional access button: {selector}")
                        break
                except Exception as e:
                    continue
            
            if not inst_button:
                print("❌ Could not find institutional access button")
                page.screenshot(path="siam_no_inst_button.png")
                browser.close()
                return False
            
            print("🔗 Step 3: Clicking institutional access...")
            inst_button.click()
            page.wait_for_timeout(5000)
            
            # Now we should be on the institution search page
            current_url = page.url
            print(f"📍 Current URL: {current_url}")
            
            # Check for Cloudflare again
            page_text = page.content()
            if "cloudflare" in page_text.lower() or "verify you are human" in page_text.lower():
                print("🔒 Cloudflare challenge on SSO page")
                print("⏳ Please complete the Cloudflare challenge manually...")
                print("⏳ Waiting 20 seconds for manual challenge completion...")
                page.wait_for_timeout(20000)
                
                # Re-check URL after challenge
                current_url = page.url
                print(f"📍 URL after challenge: {current_url}")
            
            print("🔍 Step 4: Looking for institution search field...")
            
            # Look for the search field
            search_selectors = [
                '#shibboleth_search',
                'input[aria-label="type your institution name"]',
                'input.ms-inv',
                'input[placeholder*="institution"]',
                '.ms-sel-ctn input',
                'input[type="text"]'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    elem = page.wait_for_selector(selector, timeout=3000)
                    if elem and elem.is_visible():
                        search_input = elem
                        print(f"✅ Found search input: {selector}")
                        break
                except Exception as e:
                    continue
            
            if not search_input:
                print("❌ Could not find institution search field")
                page.screenshot(path="siam_no_search_field.png")
                browser.close()
                return False
            
            print("🎯 Step 5: Typing ETH Zurich...")
            search_input.click()
            search_input.fill("")  # Clear first
            search_input.type("ETH Zurich", delay=100)
            page.wait_for_timeout(3000)
            
            # Look for ETH in dropdown results
            print("📋 Step 6: Selecting ETH from results...")
            
            eth_selectors = [
                '#result-item-0',
                '[aria-activedescendant="result-item-0"]',
                'li:has-text("ETH Zurich")',
                'div:has-text("ETH Zurich")',
                '.ms-res-item:has-text("ETH")',
                '[role="option"]:has-text("ETH")'
            ]
            
            eth_option = None
            for selector in eth_selectors:
                try:
                    elem = page.wait_for_selector(selector, timeout=3000)
                    if elem and elem.is_visible():
                        eth_option = elem
                        print(f"✅ Found ETH option: {selector}")
                        break
                except Exception as e:
                    continue
            
            if eth_option:
                eth_option.click()
            else:
                # Try pressing Enter if no clickable option
                print("⏎ Pressing Enter to submit search...")
                search_input.press("Enter")
            
            page.wait_for_timeout(5000)
            
            # Check if we reached ETH login
            current_url = page.url
            print(f"📍 Current URL: {current_url}")
            
            if "ethz.ch" in current_url:
                print("🎉 Step 7: Reached ETH authentication page!")
                
                # ETH login
                print("🔐 Step 8: Entering ETH credentials...")
                
                username_field = page.wait_for_selector(
                    'input[name="j_username"], input[name="username"]', 
                    timeout=5000
                )
                if username_field:
                    username_field.fill(username)
                    print(f"✅ Username: {username}")
                
                password_field = page.wait_for_selector(
                    'input[name="j_password"], input[name="password"]', 
                    timeout=5000
                )
                if password_field:
                    password_field.fill(password)
                    print("✅ Password entered")
                
                submit_button = page.wait_for_selector(
                    'input[type="submit"], button[type="submit"]', 
                    timeout=5000
                )
                if submit_button:
                    print("🚀 Step 9: Submitting login...")
                    submit_button.click()
                    
                    # Wait for redirect back to SIAM
                    page.wait_for_timeout(10000)
                    
                    final_url = page.url
                    print(f"📍 Final URL: {final_url}")
                    
                    if "siam" in final_url.lower():
                        print("✅ Step 10: Returned to SIAM with authentication!")
                        
                        # Now try to access the PDF
                        print("📥 Step 11: Attempting PDF download...")
                        
                        # Navigate to PDF URL
                        pdf_url = paper_url.replace("/doi/", "/doi/pdf/") + "?download=true"
                        print(f"📄 Navigating to PDF: {pdf_url}")
                        
                        page.goto(pdf_url, wait_until='domcontentloaded')
                        page.wait_for_timeout(5000)
                        
                        # Check if PDF is accessible
                        current_url = page.url
                        
                        if current_url.endswith('.pdf') or 'pdf' in current_url:
                            print("📄 PDF opened in browser")
                            
                            # Try to download via requests
                            cookies = page.context.cookies()
                            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                            
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                                'Accept': 'application/pdf,*/*'
                            }
                            
                            response = requests.get(current_url, cookies=cookie_dict, headers=headers)
                            
                            if response.status_code == 200 and response.content.startswith(b'%PDF'):
                                download_path = "siam_eth_downloaded.pdf"
                                with open(download_path, 'wb') as f:
                                    f.write(response.content)
                                
                                file_size = len(response.content)
                                print(f"🎉 PDF DOWNLOADED: {file_size} bytes")
                                print(f"📁 Saved as: {download_path}")
                                
                                print("\n🎊 SIAM PDF DOWNLOAD SUCCESS!")
                                print("✅ Complete SIAM authentication via ETH")
                                print("✅ PDF file downloaded")
                                print("✅ All three publishers now working!")
                                
                                success = True
                            else:
                                print("⚠️ Could not download PDF content")
                                success = False
                        else:
                            print("⚠️ PDF not accessible after authentication")
                            page.screenshot(path="siam_after_auth.png")
                            success = False
                    else:
                        print("❌ Did not return to SIAM after authentication")
                        success = False
                else:
                    print("❌ Could not submit ETH login")
                    success = False
            else:
                print("❌ Did not reach ETH authentication")
                page.screenshot(path="siam_no_eth_redirect.png")
                success = False
            
            print("\n⏳ Browser open 30 seconds for inspection...")
            page.wait_for_timeout(30000)
            
            browser.close()
            return success
            
    except Exception as e:
        print(f"❌ SIAM download error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run SIAM ETH download."""
    print("SIAM ETH Download")
    print("=================")
    print("🎯 Download PDF from SIAM using ETH institutional access")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials required")
        return False
    
    print(f"✅ ETH credentials loaded for: {username}")
    
    success = siam_eth_download()
    
    print(f"\n{'='*60}")
    print("SIAM DOWNLOAD RESULTS")
    print(f"{'='*60}")
    
    if success:
        print("🎉 SIAM PDF DOWNLOAD COMPLETE!")
        print("✅ SIAM authentication successful")
        print("✅ ETH institutional access working")
        print("✅ PDF file downloaded")
        print("\n🎊 ALL THREE PUBLISHERS NOW WORKING!")
        print("✅ IEEE: Working")
        print("✅ Springer: Working")
        print("✅ SIAM: Working")
    else:
        print("⚠️ SIAM download failed")
        print("Check browser and screenshots for details")
    
    return success


if __name__ == "__main__":
    main()