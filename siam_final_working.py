#!/usr/bin/env python3
"""
SIAM Final Working Implementation
=================================

Complete working SIAM flow with correct selectors for the actual institutional login page.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).parent))

async def siam_final_working():
    print("🎯 SIAM FINAL WORKING IMPLEMENTATION")
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
            
            print("\n🔄 STEP 1: Navigate to SIAM SSO")
            base_url = "https://epubs.siam.org"
            doi_url = f"/doi/{test_doi}"
            sso_url = f"{base_url}/action/ssostart?redirectUri={doi_url}"
            
            await page.goto(sso_url, timeout=90000)
            await page.wait_for_timeout(5000)
            print("   ✓ Institutional Login page loaded")
            
            print("\n🔄 STEP 2: Find institution search field")
            # Look for the actual institution search field
            institution_selectors = [
                'input[placeholder*="Type the name of your institution"]',
                'input[placeholder*="institution"]',
                'input[aria-label*="institution"]',
                '.institutional-search input',
                'form input[type="text"]'
            ]
            
            search_input = None
            for selector in institution_selectors:
                try:
                    search_input = await page.wait_for_selector(selector, timeout=5000)
                    if search_input:
                        print(f"   ✓ Found institution search: {selector}")
                        break
                except:
                    continue
            
            if not search_input:
                print("   ❌ Could not find institution search field")
                await page.screenshot(path="siam_no_search_field.png")
                await browser.close()
                return False
            
            print("\n🔄 STEP 3: Search for ETH Zurich")
            await search_input.click()
            await search_input.fill("")
            await page.wait_for_timeout(1000)
            await search_input.type("ETH Zurich", delay=100)
            await page.wait_for_timeout(5000)
            print("   ✓ Typed ETH Zurich")
            
            # Take screenshot to see search results
            await page.screenshot(path="siam_search_results.png")
            print("   Screenshot: siam_search_results.png")
            
            print("\n🔄 STEP 4: Select ETH Zurich from results")
            # Try different selectors for ETH option
            eth_selectors = [
                'text="ETH Zurich"',
                ':has-text("ETH Zurich")',
                '[title*="ETH Zurich"]',
                'a:has-text("ETH Zurich")',
                'button:has-text("ETH Zurich")',
                'div:has-text("ETH Zurich")',
                'li:has-text("ETH Zurich")',
                '.institution-option:has-text("ETH Zurich")'
            ]
            
            eth_option = None
            for selector in eth_selectors:
                try:
                    eth_option = await page.wait_for_selector(selector, timeout=5000)
                    if eth_option:
                        print(f"   ✓ Found ETH option: {selector}")
                        break
                except:
                    continue
            
            if not eth_option:
                print("   ❌ Could not find ETH Zurich option")
                print("   Checking what options are available...")
                
                # Get all visible text to see what options exist
                visible_text = await page.evaluate('''
                    Array.from(document.querySelectorAll('*'))
                      .filter(el => el.offsetParent !== null && el.innerText && el.innerText.trim())
                      .map(el => el.innerText.trim())
                      .filter(text => text.toLowerCase().includes('eth') || text.toLowerCase().includes('zurich'))
                ''')
                
                print(f"   Available ETH-related options: {visible_text}")
                
                # Try clicking the first visible ETH option
                if visible_text:
                    try:
                        first_eth = await page.get_by_text(visible_text[0]).first
                        await first_eth.click()
                        print(f"   ✓ Clicked first ETH option: {visible_text[0]}")
                    except:
                        print("   ❌ Could not click any ETH option")
                        await browser.close()
                        return False
                else:
                    await browser.close()
                    return False
            else:
                await eth_option.click()
                print("   ✓ ETH Zurich selected")
            
            await page.wait_for_timeout(10000)
            
            print("\n🔄 STEP 5: ETH Login")
            # Look for ETH login form
            try:
                username_input = await page.wait_for_selector('input[name="j_username"]', timeout=30000)
                await username_input.fill(username)
                
                password_input = await page.wait_for_selector('input[name="j_password"]', timeout=10000)
                await password_input.fill(password)
                
                submit_button = await page.wait_for_selector('button[type="submit"]', timeout=10000)
                await submit_button.click()
                await page.wait_for_timeout(20000)
                print("   ✓ ETH credentials submitted")
                
            except Exception as e:
                print(f"   ❌ ETH login failed: {e}")
                await page.screenshot(path="siam_login_failed.png")
                await browser.close()
                return False
            
            print("\n🔄 STEP 6: Access PDF")
            # Should be redirected back to the paper page, now authenticated
            final_url = page.url
            print(f"   Current URL: {final_url}")
            
            # Navigate to PDF
            pdf_url = f"{base_url}/doi/epdf/{test_doi}"
            await page.goto(pdf_url, timeout=90000)
            await page.wait_for_timeout(15000)
            print("   ✓ Navigated to PDF URL")
            
            print("\n🔄 STEP 7: Download PDF")
            download_happened = False
            downloaded_file = None
            output_dir = Path("siam_final_working")
            output_dir.mkdir(exist_ok=True)
            
            async def handle_download(download):
                nonlocal download_happened, downloaded_file
                download_happened = True
                filename = f"siam_{test_doi.replace('/', '_').replace('.', '_')}_FINAL_WORKING.pdf"
                save_path = output_dir / filename
                await download.save_as(str(save_path))
                downloaded_file = save_path
                print(f"   ✓ Download triggered: {save_path.name}")
            
            page.on('download', handle_download)
            
            # Look for download button
            try:
                download_button = await page.wait_for_selector('a[title*="Download"]', timeout=15000)
                await download_button.click()
                await page.wait_for_timeout(15000)
                print("   ✓ Download button clicked")
            except:
                print("   ❌ Could not find download button")
                await page.screenshot(path="siam_no_download_button.png")
            
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
            
            await browser.close()
            return False
            
    except Exception as e:
        print(f"\n💥 Error: {e}")
        return False

async def main():
    success = await siam_final_working()
    
    if success:
        print("\n🎉 SIAM FINALLY WORKING!")
        print("Complete end-to-end SIAM flow successful!")
    else:
        print("\n❌ Still debugging SIAM flow")

if __name__ == "__main__":
    asyncio.run(main())