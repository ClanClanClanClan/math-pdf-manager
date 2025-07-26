#!/usr/bin/env python3
"""
TEST VPN METHOD
===============

Test if VPN + browser automation actually works on papers that failed with API,
especially Econometrica papers.
"""

import asyncio
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright
import time

class VPNMethodTester:
    """Test VPN + browser method on papers that API can't access"""
    
    def __init__(self):
        self.downloads_dir = Path("vpn_test_downloads")
        self.downloads_dir.mkdir(exist_ok=True)
        self.credentials_file = Path.home() / '.config' / 'eth_credentials.json'
        
        print("🔒 VPN METHOD TESTER")
        print("=" * 60)
        print("Testing papers that failed with API")
        print("=" * 60)
    
    def check_vpn_status(self) -> bool:
        """Check if VPN is connected"""
        try:
            cisco_path = "/opt/cisco/secureclient/bin/vpn"
            result = subprocess.run([cisco_path, "status"], 
                                  capture_output=True, text=True, timeout=5)
            connected = "state: Connected" in result.stdout
            
            if connected:
                print("✅ VPN Status: CONNECTED")
            else:
                print("❌ VPN Status: DISCONNECTED")
                print("Please connect to ETH VPN first!")
            
            return connected
        except:
            print("❓ Cannot check VPN status")
            return False
    
    def load_credentials(self) -> dict:
        """Load ETH credentials"""
        try:
            import json
            if self.credentials_file.exists():
                with open(self.credentials_file, 'r') as f:
                    creds = json.load(f)
                    print(f"✅ Credentials loaded: {creds['username'][:3]}***")
                    return creds
            else:
                print("❌ No credentials found")
                return None
        except Exception as e:
            print(f"❌ Credential error: {e}")
            return None
    
    async def test_single_paper(self, doi: str, journal: str, url: str) -> dict:
        """Test downloading a single paper via browser"""
        
        result = {
            'doi': doi,
            'journal': journal,
            'url': url,
            'success': False,
            'method': None,
            'file_size': 0,
            'error': None
        }
        
        print(f"\n📄 Testing: {journal}")
        print(f"DOI: {doi}")
        print(f"URL: {url}")
        
        credentials = self.load_credentials()
        if not credentials:
            result['error'] = "No credentials available"
            return result
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # Show browser to see what's happening
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            
            page = await context.new_page()
            
            try:
                print("🔄 Navigating to paper...")
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Handle cookie banners
                try:
                    cookie_button = await page.wait_for_selector('button:has-text("Accept")', timeout=3000)
                    if cookie_button:
                        await cookie_button.click()
                        print("✅ Accepted cookies")
                        await page.wait_for_timeout(1000)
                except:
                    pass
                
                # Check if we need to log in
                page_text = await page.inner_text('body')
                
                if 'institutional' in page_text.lower() or 'access through your institution' in page_text.lower():
                    print("🔐 Institutional login required")
                    
                    # Look for institutional login button
                    try:
                        inst_button = await page.wait_for_selector(
                            'a:has-text("institutional"), button:has-text("institutional"), a:has-text("Access through")', 
                            timeout=5000
                        )
                        
                        if inst_button:
                            await inst_button.click()
                            print("✅ Clicked institutional access")
                            await page.wait_for_timeout(3000)
                            
                            # Look for ETH Zurich
                            try:
                                # Search for institution
                                search_input = await page.wait_for_selector('input[type="search"], input[placeholder*="institution"]', timeout=5000)
                                if search_input:
                                    await search_input.fill("ETH Zurich")
                                    await page.wait_for_timeout(2000)
                                
                                # Click ETH option
                                eth_option = await page.wait_for_selector('text=ETH Zurich, text=Swiss Federal Institute', timeout=5000)
                                if eth_option:
                                    await eth_option.click()
                                    print("✅ Selected ETH Zurich")
                                    await page.wait_for_timeout(3000)
                            except:
                                print("❌ Could not find ETH in institution list")
                            
                            # Handle Switch AAI login
                            if 'switch.ch' in page.url or 'wayf' in page.url:
                                print("🔑 Switch AAI login page")
                                
                                # Enter credentials
                                try:
                                    username_input = await page.wait_for_selector('input[name="j_username"], input[name="username"]', timeout=5000)
                                    password_input = await page.wait_for_selector('input[name="j_password"], input[name="password"]', timeout=5000)
                                    
                                    if username_input and password_input:
                                        await username_input.fill(credentials['username'])
                                        await password_input.fill(credentials['password'])
                                        
                                        # Submit
                                        submit_button = await page.wait_for_selector('button[type="submit"], input[type="submit"]', timeout=5000)
                                        if submit_button:
                                            await submit_button.click()
                                            print("✅ Submitted credentials")
                                            await page.wait_for_timeout(5000)
                                except Exception as e:
                                    print(f"❌ Login failed: {e}")
                    except:
                        print("❌ Could not find institutional login")
                
                # Now try to find PDF download
                print("🔍 Looking for PDF...")
                
                # Method 1: Direct PDF link
                try:
                    pdf_link = await page.wait_for_selector('a[href*="pdf"], a:has-text("PDF"), button:has-text("PDF")', timeout=5000)
                    if pdf_link:
                        # Start download monitoring
                        download_path = None
                        
                        async with page.expect_download() as download_info:
                            await pdf_link.click()
                            download = await download_info.value
                            
                            # Save the download
                            filename = f"vpn_{doi.replace('/', '_').replace('.', '_')}.pdf"
                            save_path = self.downloads_dir / filename
                            await download.save_as(save_path)
                            download_path = save_path
                        
                        if download_path and download_path.exists():
                            size_mb = download_path.stat().st_size / (1024 * 1024)
                            print(f"✅ Downloaded via PDF link: {size_mb:.2f} MB")
                            result['success'] = True
                            result['method'] = 'Direct PDF download'
                            result['file_size'] = size_mb
                            await browser.close()
                            return result
                except:
                    print("❌ No direct PDF download available")
                
                # Method 2: Print to PDF if we can see the content
                if not result['success']:
                    # Check if we're viewing a PDF in browser
                    if 'pdf' in page.url or await page.query_selector('embed[type="application/pdf"], iframe[src*="pdf"]'):
                        print("📄 PDF viewer detected - printing to PDF...")
                        
                        pdf_buffer = await page.pdf(
                            format='A4',
                            margin={'top': '1cm', 'right': '1cm', 'bottom': '1cm', 'left': '1cm'},
                            print_background=True
                        )
                        
                        if len(pdf_buffer) > 10000:
                            filename = f"vpn_print_{doi.replace('/', '_').replace('.', '_')}.pdf"
                            save_path = self.downloads_dir / filename
                            
                            with open(save_path, 'wb') as f:
                                f.write(pdf_buffer)
                            
                            size_mb = save_path.stat().st_size / (1024 * 1024)
                            print(f"✅ Printed to PDF: {size_mb:.2f} MB")
                            result['success'] = True
                            result['method'] = 'Print to PDF'
                            result['file_size'] = size_mb
                            await browser.close()
                            return result
                
                # If still no success, capture what we see
                if not result['success']:
                    page_text = await page.inner_text('body')
                    if 'access denied' in page_text.lower():
                        result['error'] = "Access denied even with VPN"
                    elif 'subscription' in page_text.lower():
                        result['error'] = "Subscription required"
                    else:
                        result['error'] = "Could not download PDF"
                    
                    # Take screenshot for debugging
                    screenshot = self.downloads_dir / f"failed_{doi.replace('/', '_')}.png"
                    await page.screenshot(path=screenshot)
                    print(f"📸 Screenshot saved: {screenshot}")
                
            except Exception as e:
                result['error'] = f"Browser error: {str(e)[:50]}"
                print(f"❌ Error: {str(e)}")
            
            finally:
                await browser.close()
        
        return result
    
    async def run_vpn_test(self):
        """Test papers that failed with API"""
        
        # First check VPN
        if not self.check_vpn_status():
            print("\n⚠️ Please connect to ETH VPN first!")
            print("Run: /opt/cisco/secureclient/bin/vpn connect sslvpn.ethz.ch/student-net")
            return
        
        # Papers to test - the ones that failed with API
        test_papers = [
            # Econometrica papers that returned 403
            {
                'doi': '10.3982/ECTA20404',
                'journal': 'Econometrica',
                'url': 'https://onlinelibrary.wiley.com/doi/10.3982/ECTA20404'
            },
            {
                'doi': '10.3982/ECTA20411',
                'journal': 'Econometrica', 
                'url': 'https://onlinelibrary.wiley.com/doi/10.3982/ECTA20411'
            },
            # Also test one that worked with API to compare
            {
                'doi': '10.1111/jofi.13412',
                'journal': 'Journal of Finance',
                'url': 'https://onlinelibrary.wiley.com/doi/10.1111/jofi.13412'
            }
        ]
        
        results = []
        
        print("\n🧪 TESTING VPN METHOD")
        print("=" * 60)
        
        for i, paper in enumerate(test_papers, 1):
            print(f"\n{'='*15} PAPER {i}/{len(test_papers)} {'='*15}")
            
            result = await self.test_single_paper(
                paper['doi'], 
                paper['journal'],
                paper['url']
            )
            
            results.append(result)
            
            if result['success']:
                print(f"✅ SUCCESS via {result['method']}")
            else:
                print(f"❌ FAILED: {result['error']}")
            
            # Delay between papers
            if i < len(test_papers):
                print("\n⏳ Waiting 10 seconds...")
                await asyncio.sleep(10)
        
        # Summary
        print(f"\n{'='*30} VPN TEST RESULTS {'='*30}")
        
        successful = sum(1 for r in results if r['success'])
        total = len(results)
        success_rate = (successful / total * 100) if total > 0 else 0
        
        print(f"Success rate: {successful}/{total} ({success_rate:.1f}%)")
        
        if successful > 0:
            total_size = sum(r['file_size'] for r in results if r['success'])
            print(f"Total downloaded: {total_size:.2f} MB")
            
            print(f"\n✅ VPN METHOD WORKS!")
            print(f"Successfully downloaded papers that API couldn't access")
            
            # Show what worked
            for result in results:
                if result['success']:
                    print(f"  ✅ {result['journal']}: {result['method']} ({result['file_size']:.2f} MB)")
                else:
                    print(f"  ❌ {result['journal']}: {result['error']}")
        else:
            print(f"\n❌ VPN method failed")
            print(f"Check credentials and VPN connection")
        
        return results

async def main():
    """Main test function"""
    
    print("🔒 TESTING VPN METHOD ON PAPERS THAT FAILED WITH API")
    print("=" * 70)
    print("Verifying if VPN actually provides access")
    print("=" * 70)
    
    tester = VPNMethodTester()
    await tester.run_vpn_test()
    
    print("\n🔒 VPN METHOD TEST COMPLETE!")

if __name__ == "__main__":
    asyncio.run(main())