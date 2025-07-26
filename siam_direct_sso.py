#!/usr/bin/env python3
"""
SIAM Direct SSO
===============

Bypass the modal click issue by navigating directly to the SSO URL.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).parent))

async def siam_direct_sso():
    print("🚀 SIAM DIRECT SSO: Bypassing modal click issue")
    print("=" * 50)
    
    # Get credentials
    try:
        from src.secure_credential_manager import get_credential_manager
        
        cm = get_credential_manager()
        username = cm.get_credential("eth_username")
        password = cm.get_credential("eth_password")
        
        if not username or not password:
            print("❌ No ETH credentials for SIAM")
            return False
            
        print(f"✅ Using ETH credentials: {username[:3]}***")
            
    except ImportError as e:
        print(f"❌ Cannot import credentials: {e}")
        return False
    
    # Test paper
    test_doi = "10.1137/S0097539795293172" 
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            print("\n🔄 STEP 1: Navigate directly to SIAM SSO start")
            # Navigate directly to the SSO URL with proper redirect URI
            base_url = "https://epubs.siam.org"
            doi_url = f"/doi/{test_doi}"
            sso_url = f"{base_url}/action/ssostart?redirectUri={doi_url}"
            
            print(f"   SSO URL: {sso_url}")
            await page.goto(sso_url, timeout=90000)
            await page.wait_for_timeout(8000)
            print("   ✓ Navigated to SSO start")
            
            # Take screenshot to see what we get
            await page.screenshot(path="siam_direct_sso_1.png")
            print("   Screenshot: siam_direct_sso_1.png")
            
            # Check current URL and title
            current_url = page.url
            page_title = await page.title()
            print(f"   Current URL: {current_url}")
            print(f"   Page title: '{page_title}'")
            
            print("\n🔄 STEP 2: Look for institutional/shibboleth login")
            
            # Now look for the shibboleth search that we expect
            try:
                search_input = await page.wait_for_selector('input#shibboleth_search', timeout=15000)
                print("   ✓ Found shibboleth search input!")
                
                print("\n🔄 STEP 3: Search for ETH Zurich")
                await search_input.click()
                await search_input.fill("")
                await page.wait_for_timeout(1000)
                await search_input.type("ETH Zurich", delay=150)
                await page.wait_for_timeout(5000)
                print("   ✓ Typed ETH Zurich")
                
                print("\n🔄 STEP 4: Click ETH Zurich option")
                eth_option = await page.wait_for_selector('.ms-res-item a.sso-institution:has-text("ETH Zurich")', timeout=15000)
                await eth_option.click()
                await page.wait_for_timeout(10000)
                print("   ✓ ETH Zurich selected")
                
                print("\n🔄 STEP 5: ETH Login")
                username_input = await page.wait_for_selector('input[name="j_username"]', timeout=30000)
                await username_input.fill(username)
                
                password_input = await page.wait_for_selector('input[name="j_password"]', timeout=10000)
                await password_input.fill(password)
                
                submit_button = await page.wait_for_selector('button[type="submit"]', timeout=10000)
                await submit_button.click()
                await page.wait_for_timeout(20000)
                print("   ✓ ETH credentials submitted")
                
                # Check if we're back at the paper page with access
                final_url = page.url
                print(f"   Final URL: {final_url}")
                
                # Take screenshot of final state
                await page.screenshot(path="siam_direct_sso_2_after_auth.png")
                print("   Screenshot: siam_direct_sso_2_after_auth.png")
                
                print("\n🔄 STEP 6: Try to access PDF")
                # Navigate to PDF URL
                pdf_url = f"{base_url}/doi/epdf/{test_doi}"
                await page.goto(pdf_url, timeout=90000)
                await page.wait_for_timeout(15000)
                print("   ✓ Navigated to PDF URL")
                
                print("\n🔄 STEP 7: Download PDF")
                download_happened = False
                downloaded_file = None
                output_dir = Path("siam_direct_sso")
                output_dir.mkdir(exist_ok=True)
                
                async def handle_download(download):
                    nonlocal download_happened, downloaded_file
                    download_happened = True
                    filename = f"siam_{test_doi.replace('/', '_').replace('.', '_')}_DIRECT_SSO.pdf"
                    save_path = output_dir / filename
                    await download.save_as(str(save_path))
                    downloaded_file = save_path
                    print(f"   ✓ Download triggered: {save_path.name}")
                
                page.on('download', handle_download)
                
                # Look for download button
                download_button = await page.wait_for_selector('a[title*="Download"]', timeout=15000)
                await download_button.click()
                await page.wait_for_timeout(15000)
                print("   ✓ Download button clicked")
                
                # Verify download
                if download_happened and downloaded_file and downloaded_file.exists():
                    with open(downloaded_file, 'rb') as f:
                        header = f.read(8)
                        if header.startswith(b'%PDF'):
                            size_kb = downloaded_file.stat().st_size / 1024
                            print(f"\n🎉 SUCCESS! Downloaded: {downloaded_file.name} ({size_kb:.0f} KB)")
                            await browser.close()
                            return True
                        else:
                            print(f"\n❌ Invalid PDF format")
                else:
                    print(f"\n❌ No download occurred")
                
            except Exception as e:
                print(f"   ❌ Shibboleth flow failed: {e}")
                # Take error screenshot
                await page.screenshot(path="siam_direct_sso_error.png")
                
                # Let's see what we actually got
                print("   Checking what's actually on the page...")
                page_content = await page.content()
                
                # Look for alternative login methods
                if 'login' in page_content.lower():
                    print("   Page contains 'login' - might be a different login form")
                
                # List all forms
                forms = await page.query_selector_all('form')
                print(f"   Found {len(forms)} forms:")
                for i, form in enumerate(forms[:3]):  # Show first 3 forms
                    action = await form.get_attribute('action')
                    print(f"     Form {i+1}: action='{action}'")
            
            await browser.close()
            return False
            
    except Exception as e:
        print(f"\n💥 Error: {e}")
        return False

async def main():
    success = await siam_direct_sso()
    
    if success:
        print("\n🎉 SIAM DIRECT SSO SUCCESSFUL!")
        print("Successfully bypassed the modal click issue!")
    else:
        print("\n❌ Still having issues with SIAM SSO flow")

if __name__ == "__main__":
    asyncio.run(main())