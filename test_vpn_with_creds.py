#!/usr/bin/env python3
"""
TEST VPN METHOD WITH CREDENTIALS
================================

Test if VPN + browser actually provides access to Econometrica papers.
"""

import asyncio
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).parent))

class VPNWithCredsTester:
    """Test VPN method with proper credentials"""
    
    def __init__(self):
        self.downloads_dir = Path("vpn_creds_test")
        self.downloads_dir.mkdir(exist_ok=True)
        
        print("🔒 VPN METHOD TEST WITH CREDENTIALS")
        print("=" * 60)
        
    def check_vpn_status(self) -> bool:
        """Check VPN status"""
        try:
            cisco_path = "/opt/cisco/secureclient/bin/vpn"
            result = subprocess.run([cisco_path, "status"], 
                                  capture_output=True, text=True, timeout=5)
            connected = "state: Connected" in result.stdout
            print(f"VPN Status: {'✅ CONNECTED' if connected else '❌ DISCONNECTED'}")
            return connected
        except:
            print("VPN Status: ❓ Unknown")
            return False
    
    async def test_econometrica_paper(self) -> dict:
        """Test a single Econometrica paper that failed with API"""
        
        # Load credentials
        try:
            from src.secure_credential_manager import get_credential_manager
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            if not username or not password:
                print("❌ No credentials found")
                return {'success': False, 'error': 'No credentials'}
            
            print(f"✅ Credentials loaded: {username[:3]}***")
        except Exception as e:
            print(f"❌ Credential error: {e}")
            return {'success': False, 'error': str(e)}
        
        # Test paper that failed with API
        test_paper = {
            'doi': '10.3982/ECTA20404',
            'journal': 'Econometrica',
            'url': 'https://onlinelibrary.wiley.com/doi/10.3982/ECTA20404'
        }
        
        print(f"\n📄 Testing: {test_paper['journal']}")
        print(f"DOI: {test_paper['doi']}")
        print(f"URL: {test_paper['url']}")
        print("(This paper returned 403 Forbidden with API)")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # Show browser to see what happens
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            
            page = await context.new_page()
            
            try:
                print("\n🔄 Step 1: Navigate to paper...")
                await page.goto(test_paper['url'], wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Take initial screenshot
                await page.screenshot(path=self.downloads_dir / "1_initial_page.png")
                
                # Handle cookies
                try:
                    cookie_btn = await page.wait_for_selector('button:has-text("Accept")', timeout=3000)
                    if cookie_btn:
                        await cookie_btn.click()
                        print("✅ Accepted cookies")
                        await page.wait_for_timeout(1000)
                except:
                    print("ℹ️ No cookie banner")
                
                # Check if already have access
                page_text = await page.inner_text('body')
                if 'download pdf' in page_text.lower() or 'pdf' in page_text.lower():
                    print("ℹ️ Checking for direct PDF access...")
                    
                    # Try direct PDF download
                    try:
                        pdf_link = await page.wait_for_selector('a[href*="pdf"], a:has-text("PDF")', timeout=3000)
                        if pdf_link:
                            print("✅ Found PDF link - attempting download...")
                            
                            async with page.expect_download() as download_info:
                                await pdf_link.click()
                                download = await download_info.value
                                
                                filename = f"vpn_{test_paper['doi'].replace('/', '_').replace('.', '_')}.pdf"
                                save_path = self.downloads_dir / filename
                                await download.save_as(save_path)
                                
                                size_mb = save_path.stat().st_size / (1024 * 1024)
                                print(f"🎉 SUCCESS: Downloaded {size_mb:.2f} MB via VPN!")
                                await browser.close()
                                return {'success': True, 'method': 'Direct PDF', 'size_mb': size_mb}
                    except:
                        pass
                
                # Need institutional login
                if 'institutional' in page_text.lower() or 'access through' in page_text.lower():
                    print("\n🔄 Step 2: Click institutional access...")
                    
                    inst_link = await page.wait_for_selector(
                        'a:has-text("institutional"), button:has-text("institutional"), a:has-text("Access through")',
                        timeout=5000
                    )
                    
                    if inst_link:
                        await inst_link.click()
                        print("✅ Clicked institutional access")
                        await page.wait_for_timeout(3000)
                        
                        await page.screenshot(path=self.downloads_dir / "2_institution_search.png")
                        
                        # Search for ETH
                        print("\n🔄 Step 3: Search for ETH Zurich...")
                        search_input = await page.wait_for_selector('input[type="search"], input[placeholder*="institution"]', timeout=5000)
                        if search_input:
                            await search_input.fill("ETH Zurich")
                            await page.wait_for_timeout(2000)
                            
                            # Click ETH option
                            eth_option = await page.wait_for_selector('text=ETH Zurich, text=Swiss Federal Institute', timeout=5000)
                            if eth_option:
                                await eth_option.click()
                                print("✅ Selected ETH Zurich")
                                await page.wait_for_timeout(5000)
                                
                                # Handle Switch AAI login
                                if 'switch.ch' in page.url or 'wayf' in page.url:
                                    print("\n🔄 Step 4: Switch AAI login...")
                                    await page.screenshot(path=self.downloads_dir / "3_switch_login.png")
                                    
                                    # Login
                                    username_input = await page.wait_for_selector('input[name="j_username"], input[name="username"]', timeout=5000)
                                    password_input = await page.wait_for_selector('input[name="j_password"], input[name="password"]', timeout=5000)
                                    
                                    if username_input and password_input:
                                        await username_input.fill(username)
                                        await password_input.fill(password)
                                        
                                        submit_btn = await page.wait_for_selector('button[type="submit"], input[type="submit"]', timeout=5000)
                                        if submit_btn:
                                            await submit_btn.click()
                                            print("✅ Submitted credentials")
                                            await page.wait_for_timeout(8000)
                                            
                                            # Now we should be back at the paper
                                            await page.screenshot(path=self.downloads_dir / "4_after_login.png")
                                            
                                            # Try to find PDF again
                                            print("\n🔄 Step 5: Looking for PDF after login...")
                                            
                                            try:
                                                pdf_link = await page.wait_for_selector('a[href*="pdf"], a:has-text("PDF")', timeout=5000)
                                                if pdf_link:
                                                    print("✅ Found PDF link!")
                                                    
                                                    async with page.expect_download() as download_info:
                                                        await pdf_link.click()
                                                        download = await download_info.value
                                                        
                                                        filename = f"vpn_auth_{test_paper['doi'].replace('/', '_').replace('.', '_')}.pdf"
                                                        save_path = self.downloads_dir / filename
                                                        await download.save_as(save_path)
                                                        
                                                        size_mb = save_path.stat().st_size / (1024 * 1024)
                                                        print(f"🎉 SUCCESS: Downloaded {size_mb:.2f} MB after authentication!")
                                                        await browser.close()
                                                        return {'success': True, 'method': 'Institutional login', 'size_mb': size_mb}
                                            except:
                                                # Try print to PDF as last resort
                                                if 'pdf' in page.url:
                                                    print("📄 PDF viewer detected - printing...")
                                                    
                                                    pdf_buffer = await page.pdf(format='A4')
                                                    filename = f"vpn_print_{test_paper['doi'].replace('/', '_').replace('.', '_')}.pdf"
                                                    save_path = self.downloads_dir / filename
                                                    
                                                    with open(save_path, 'wb') as f:
                                                        f.write(pdf_buffer)
                                                    
                                                    size_mb = save_path.stat().st_size / (1024 * 1024)
                                                    print(f"🎉 SUCCESS: Printed {size_mb:.2f} MB!")
                                                    await browser.close()
                                                    return {'success': True, 'method': 'Print to PDF', 'size_mb': size_mb}
                
                # If we get here, it failed
                await page.screenshot(path=self.downloads_dir / "5_failed_final.png")
                await browser.close()
                return {'success': False, 'error': 'Could not access PDF'}
                
            except Exception as e:
                print(f"❌ Error: {e}")
                await page.screenshot(path=self.downloads_dir / "error_screenshot.png")
                await browser.close()
                return {'success': False, 'error': str(e)}

async def main():
    """Main test"""
    
    print("🔒 TESTING VPN METHOD ON ECONOMETRICA")
    print("=" * 70)
    print("Testing paper that returned 403 with API")
    print("=" * 70)
    
    tester = VPNWithCredsTester()
    
    # Check VPN
    if not tester.check_vpn_status():
        print("\n❌ VPN not connected!")
        return
    
    # Test Econometrica
    result = await tester.test_econometrica_paper()
    
    print(f"\n{'='*30} FINAL RESULT {'='*30}")
    
    if result['success']:
        print(f"✅ VPN METHOD WORKS!")
        print(f"Method: {result['method']}")
        print(f"Size: {result['size_mb']:.2f} MB")
        print(f"\n🎉 This proves VPN provides access to papers that API blocks!")
    else:
        print(f"❌ VPN method failed: {result['error']}")
        print(f"Check screenshots in: {tester.downloads_dir}")
    
    print(f"\n🔒 VPN METHOD TEST COMPLETE!")

if __name__ == "__main__":
    asyncio.run(main())