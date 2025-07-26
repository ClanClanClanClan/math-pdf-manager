#!/usr/bin/env python3
"""
SIAM Manual Assist Download
===========================

Semi-automated SIAM download that pauses for manual Cloudflare solving.
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


def siam_manual_assist():
    """SIAM download with manual assistance for Cloudflare."""
    print("📄 SIAM Semi-Automated Download")
    print("This script will pause for manual Cloudflare solving")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials required")
        return False
    
    print(f"🔐 ETH credentials ready for: {username}")
    
    paper_url = "https://epubs.siam.org/doi/10.1137/20M1339829"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=500,
                args=['--start-maximized']
            )
            
            page = browser.new_page()
            
            print("\n" + "="*60)
            print("STEP 1: Navigate to SIAM paper")
            print("="*60)
            print(f"🌐 Loading: {paper_url}")
            page.goto(paper_url, wait_until='domcontentloaded')
            
            print("\n⚠️  MANUAL ACTION REQUIRED:")
            print("1. Complete any Cloudflare challenges")
            print("2. Wait for the paper page to load")
            print("3. Press Enter to continue...")
            input()
            
            print("\n" + "="*60)
            print("STEP 2: Click institutional access")
            print("="*60)
            
            # Look for institutional button
            inst_button = page.query_selector('a.institutional__btn, a:has-text("Access via your Institution")')
            if inst_button:
                print("✅ Found institutional button")
                inst_button.click()
                print("🔗 Clicked institutional access")
            else:
                print("❌ Could not find institutional button")
                print("⚠️  MANUAL ACTION: Click 'Access via your Institution'")
            
            print("\n⚠️  MANUAL ACTION REQUIRED:")
            print("1. Complete any Cloudflare challenges on the SSO page")
            print("2. Wait for the institution search page to load")
            print("3. Press Enter to continue...")
            input()
            
            print("\n" + "="*60)
            print("STEP 3: Search for ETH Zurich")
            print("="*60)
            
            # Try to find search field
            search_input = page.query_selector('#shibboleth_search, input[aria-label*="institution"], .ms-sel-ctn input')
            if search_input:
                print("✅ Found search field")
                search_input.click()
                search_input.fill("ETH Zurich")
                print("📝 Typed: ETH Zurich")
                page.wait_for_timeout(2000)
                
                # Try to click on ETH result
                eth_option = page.query_selector('li:has-text("ETH Zurich"), div:has-text("ETH Zurich")')
                if eth_option:
                    eth_option.click()
                    print("🎯 Clicked ETH Zurich")
                else:
                    print("⚠️  Please click on ETH Zurich in the dropdown")
            else:
                print("❌ Could not find search field")
                print("⚠️  MANUAL ACTION: Search for and select ETH Zurich")
            
            print("\n⚠️  MANUAL ACTION REQUIRED:")
            print("1. Ensure ETH Zurich is selected")
            print("2. Wait for redirect to ETH login page")
            print("3. Press Enter to continue...")
            input()
            
            # Check if we're on ETH page
            if "ethz.ch" in page.url:
                print("\n" + "="*60)
                print("STEP 4: ETH Login")
                print("="*60)
                print("🎉 Reached ETH login page!")
                
                # Fill credentials
                username_field = page.query_selector('input[name="j_username"], input[name="username"]')
                if username_field:
                    username_field.fill(username)
                    print(f"✅ Username filled: {username}")
                
                password_field = page.query_selector('input[name="j_password"], input[name="password"]')
                if password_field:
                    password_field.fill(password)
                    print("✅ Password filled")
                
                submit_button = page.query_selector('input[type="submit"], button[type="submit"]')
                if submit_button:
                    submit_button.click()
                    print("🚀 Login submitted")
                else:
                    print("⚠️  MANUAL ACTION: Click login/submit button")
            else:
                print("❌ Not on ETH login page")
                print("⚠️  MANUAL ACTION: Complete ETH login manually")
            
            print("\n⚠️  MANUAL ACTION REQUIRED:")
            print("1. Complete ETH login if needed")
            print("2. Wait for redirect back to SIAM")
            print("3. Press Enter to continue...")
            input()
            
            print("\n" + "="*60)
            print("STEP 5: Download PDF")
            print("="*60)
            
            if "siam" in page.url.lower():
                print("✅ Back on SIAM site")
                
                # Try to navigate to PDF
                pdf_url = paper_url.replace("/doi/", "/doi/pdf/") + "?download=true"
                print(f"📄 Navigating to PDF: {pdf_url}")
                page.goto(pdf_url, wait_until='domcontentloaded')
                
                page.wait_for_timeout(5000)
                
                # Get cookies for download
                cookies = page.context.cookies()
                cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                
                # Try to download
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Accept': 'application/pdf,*/*'
                }
                
                response = requests.get(page.url, cookies=cookie_dict, headers=headers)
                
                if response.status_code == 200 and response.content.startswith(b'%PDF'):
                    download_path = "siam_manual_downloaded.pdf"
                    with open(download_path, 'wb') as f:
                        f.write(response.content)
                    
                    file_size = len(response.content)
                    print(f"\n🎉 SUCCESS! PDF DOWNLOADED: {file_size:,} bytes")
                    print(f"📁 Saved as: {download_path}")
                    print("\n✅ SIAM download complete with manual assistance!")
                    success = True
                else:
                    print(f"❌ Download failed: HTTP {response.status_code}")
                    print("⚠️  Try saving the PDF manually from the browser")
                    success = False
            else:
                print("❌ Not on SIAM site")
                success = False
            
            print("\n⏳ Browser stays open for 30 seconds...")
            page.wait_for_timeout(30000)
            
            browser.close()
            return success
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run SIAM manual assist download."""
    print("SIAM Manual Assist Download")
    print("===========================")
    print("Semi-automated download with manual Cloudflare solving\n")
    
    success = siam_manual_assist()
    
    print("\n" + "="*60)
    if success:
        print("✅ SIAM PDF downloaded successfully!")
        print("✅ Manual assistance method works")
    else:
        print("❌ SIAM download incomplete")
        print("💡 Manual intervention required for Cloudflare")


if __name__ == "__main__":
    main()