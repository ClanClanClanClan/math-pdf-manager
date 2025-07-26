#!/usr/bin/env python3
"""
SIAM Ultrathink Fix
===================

Using the EXACT selectors and approach from the original working implementation.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).parent))

async def siam_ultrathink_fix():
    print("🧠 SIAM ULTRATHINK FIX - Using Original Working Implementation")
    print("=" * 60)
    
    # Get credentials
    try:
        from src.secure_credential_manager import get_credential_manager
        
        cm = get_credential_manager()
        username = cm.get_credential("eth_username")
        password = cm.get_credential("eth_password")
        
        if not username or not password:
            print("❌ No ETH credentials")
            return False
            
        print(f"✅ Using ETH credentials: {username[:3]}***")
            
    except ImportError as e:
        print(f"❌ Cannot import credentials: {e}")
        return False
    
    # Test SIAM paper
    test_doi = "10.1137/S0097539795293172" 
    
    try:
        async with async_playwright() as p:
            # Use EXACT browser settings from working implementation
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-dev-shm-usage',
                    '--disable-extensions',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ]
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            # Add anti-webdriver script
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            page = await context.new_page()
            
            print("\n🔄 STEP 1: Navigate to SIAM SSO")
            base_url = "https://epubs.siam.org"
            
            # Use the exact SSO URL format from the working implementation
            sso_url = f"{base_url}/action/ssostart?redirectUri=/doi/{test_doi}"
            
            await page.goto(sso_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(3000)
            print("   ✓ SIAM institutional login page loaded")
            
            # Take screenshot
            await page.screenshot(path="siam_ultrathink_1_initial.png")
            print("   Screenshot: siam_ultrathink_1_initial.png")
            
            print("\n🔄 STEP 2: Find institution search using EXACT selector")
            
            # Use the EXACT selector from working implementation
            search_input = await page.wait_for_selector('input#shibboleth_search', timeout=15000, state='visible')
            
            if search_input:
                print("   ✅ Found search input with #shibboleth_search!")
                
                # Clear and type ETH Zurich
                await search_input.click()
                await search_input.fill("")
                await page.wait_for_timeout(500)
                
                # Type slowly to trigger dropdown
                print("   Typing 'ETH Zurich' slowly...")
                await search_input.type("ETH Zurich", delay=100)
                await page.wait_for_timeout(2000)
                
                # Also dispatch input event
                await search_input.dispatch_event('input')
                await page.wait_for_timeout(1000)
                
                print("\n🔄 STEP 3: Wait for dropdown with EXACT selectors")
                
                # Check if dropdown container exists
                dropdown = await page.query_selector('.ms-res-ctn')
                if dropdown:
                    print("   ✅ Found dropdown container (.ms-res-ctn)")
                    
                    # Check for dropdown items
                    items = await page.query_selector_all('.ms-res-item')
                    print(f"   Found {len(items)} items in dropdown")
                
                # Wait for the dropdown menu to appear
                try:
                    await page.wait_for_selector('.ms-res-ctn.dropdown-menu', timeout=3000)
                    print("   ✅ Dropdown menu is visible!")
                    
                    # Take screenshot
                    await page.screenshot(path="siam_ultrathink_2_dropdown.png")
                    print("   Screenshot: siam_ultrathink_2_dropdown.png")
                    
                    # Look for ETH using EXACT selectors from working implementation
                    eth_selectors = [
                        '.ms-res-item a.sso-institution:has-text("ETH Zurich")',  # The actual link
                        '.ms-res-item[data-json*="ETH Zurich"]',  # The result item
                        'a[data-entityid*="ethz.ch"]',  # By entity ID
                        '#result-item-0:has-text("ETH Zurich")'  # First result if it's ETH
                    ]
                    
                    eth_found = False
                    for selector in eth_selectors:
                        try:
                            eth_option = await page.wait_for_selector(selector, timeout=2000)
                            if eth_option:
                                print(f"   ✅ Found ETH Zurich with selector: {selector}")
                                await eth_option.click()
                                print("   ✅ Clicked ETH Zurich!")
                                eth_found = True
                                break
                        except:
                            continue
                    
                    if not eth_found:
                        # Try clicking first result if it contains ETH
                        first_result = await page.query_selector('.ms-res-item')
                        if first_result:
                            text = await first_result.text_content()
                            if 'ETH' in text:
                                print("   Clicking first result (appears to be ETH)")
                                await first_result.click()
                                eth_found = True
                    
                    if eth_found:
                        print("\n🔄 STEP 4: Wait for ETH login redirect")
                        await page.wait_for_timeout(10000)
                        
                        current_url = page.url
                        print(f"   Current URL: {current_url}")
                        
                        if 'ethz.ch' in current_url or 'aai-logon' in current_url:
                            print("   ✅ Successfully redirected to ETH login!")
                            
                            # Fill ETH credentials
                            print("\n🔄 STEP 5: Fill ETH credentials")
                            username_input = await page.wait_for_selector('input[name="j_username"]', timeout=30000)
                            await username_input.fill(username)
                            print("   ✓ Filled username")
                            
                            password_input = await page.wait_for_selector('input[name="j_password"]', timeout=10000)
                            await password_input.fill(password)
                            print("   ✓ Filled password")
                            
                            submit_button = await page.wait_for_selector('button[type="submit"]', timeout=10000)
                            await submit_button.click()
                            print("   ✓ Submitted login")
                            
                            await page.wait_for_timeout(20000)
                            
                            final_url = page.url
                            print(f"\n   Final URL: {final_url}")
                            
                            if 'siam' in final_url.lower() or 'epubs.siam.org' in final_url:
                                print("\n🎉 SIAM AUTHENTICATION SUCCESSFUL!")
                                
                                # Try to download a PDF
                                print("\n🔄 STEP 6: Test PDF download")
                                pdf_url = f"{base_url}/doi/epdf/{test_doi}"
                                await page.goto(pdf_url, timeout=90000)
                                await page.wait_for_timeout(15000)
                                
                                # Setup download
                                download_happened = False
                                output_dir = Path("siam_ultrathink")
                                output_dir.mkdir(exist_ok=True)
                                
                                async def handle_download(download):
                                    nonlocal download_happened
                                    download_happened = True
                                    filename = f"siam_{test_doi.replace('/', '_').replace('.', '_')}_ULTRATHINK.pdf"
                                    save_path = output_dir / filename
                                    await download.save_as(str(save_path))
                                    print(f"   ✓ Download started: {save_path.name}")
                                
                                page.on('download', handle_download)
                                
                                # Look for download button
                                download_button = await page.wait_for_selector('a[title*="Download"]', timeout=15000)
                                if download_button:
                                    await download_button.click()
                                    await page.wait_for_timeout(15000)
                                    
                                    if download_happened:
                                        print("\n🎉 PDF DOWNLOAD SUCCESSFUL!")
                                        print("🎉 SIAM IS WORKING PERFECTLY!")
                                        await browser.close()
                                        return True
                                
                except Exception as e:
                    print(f"   ❌ Dropdown handling failed: {e}")
                    
                    # Debug: print page content
                    content = await page.content()
                    if 'seamlessaccess' in content.lower():
                        print("   ℹ️ This appears to be a SeamlessAccess interface")
                        print("   The dropdown might work differently than expected")
                
            await browser.close()
            
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        return False
    
    return False

async def main():
    success = await siam_ultrathink_fix()
    
    if success:
        print("\n" + "=" * 80)
        print("🎉 ULTRATHINK SUCCESS!")
        print("=" * 80)
        print("The original SIAM implementation DOES work!")
        print("Key insights:")
        print("  1. Use selector 'input#shibboleth_search' for search")
        print("  2. Wait for '.ms-res-ctn.dropdown-menu' for dropdown")
        print("  3. Click '.ms-res-item a.sso-institution:has-text(\"ETH Zurich\")'")
        print("  4. The implementation was correct all along!")
    else:
        print("\n⚠️ SIAM still needs investigation")

if __name__ == "__main__":
    asyncio.run(main())