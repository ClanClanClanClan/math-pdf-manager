#!/usr/bin/env python3
"""
PROVE WILEY DOWNLOADS ACTUALLY WORK
===================================

Direct test to ACTUALLY DOWNLOAD PDFs from Wiley subscription journals.
No excuses - this must produce real PDF files or it's useless.

Focus: Get real PDFs from subscription content through ETH access.
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

class WileyDownloadProof:
    """Prove Wiley downloads work by actually downloading PDFs"""
    
    def __init__(self):
        self.cisco_path = "/opt/cisco/secureclient/bin/vpn"
        self.credentials = None
        self.downloads_dir = Path("proof_downloads")
        self.downloads_dir.mkdir(exist_ok=True)
    
    async def initialize(self):
        """Get ETH credentials"""
        try:
            from src.secure_credential_manager import get_credential_manager
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            if not (username and password):
                raise Exception("No ETH credentials")
                
            self.credentials = {'username': username, 'password': password}
            print(f"✅ ETH credentials: {username[:3]}***")
            return True
            
        except Exception as e:
            print(f"❌ Credential error: {e}")
            return False
    
    def ensure_vpn_connection(self):
        """Ensure VPN is connected"""
        try:
            # Check status
            result = subprocess.run([self.cisco_path, "status"], 
                                  capture_output=True, text=True, timeout=10)
            
            if "state: Connected" in result.stdout:
                print("✅ ETH VPN connected")
                return True
            else:
                print("❌ ETH VPN not connected")
                print("🔧 Attempting automatic connection...")
                
                # Try to connect (may require 2FA)
                connect_result = subprocess.run([self.cisco_path, "connect", "vpn.ethz.ch"], 
                                              capture_output=True, text=True, timeout=30)
                
                # Wait and check again
                time.sleep(10)
                status_result = subprocess.run([self.cisco_path, "status"], 
                                            capture_output=True, text=True, timeout=10)
                
                if "state: Connected" in status_result.stdout:
                    print("✅ VPN connection successful")
                    return True
                else:
                    print("⚠️ VPN may need manual connection with 2FA")
                    print("💡 Continuing anyway - may work on ETH network")
                    return False
                    
        except Exception as e:
            print(f"❌ VPN check failed: {e}")
            return False
    
    async def download_from_wiley_journal(self, doi, journal_name, expected_title):
        """Download a specific paper from Wiley journal"""
        
        print(f"\n🎯 DOWNLOADING: {journal_name}")
        print(f"DOI: {doi}")
        print(f"Expected: {expected_title}")
        print("-" * 60)
        
        paper_url = f"https://onlinelibrary.wiley.com/doi/{doi}"
        filename = f"wiley_{journal_name.lower().replace(' ', '_')}_{doi.replace('/', '_').replace('.', '_')}.pdf"
        save_path = self.downloads_dir / filename
        
        # Remove existing file
        if save_path.exists():
            save_path.unlink()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--start-maximized',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # Enhanced context for downloads
            context = await browser.new_context(
                accept_downloads=True,
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = await context.new_page()
            
            try:
                # Navigate to paper
                print(f"📍 Navigating to: {paper_url}")
                response = await page.goto(paper_url, wait_until='domcontentloaded', timeout=30000)
                
                if not response or response.status != 200:
                    print(f"❌ Failed to load page: {response.status if response else 'No response'}")
                    await browser.close()
                    return False
                
                await page.wait_for_timeout(5000)
                print(f"✅ Page loaded successfully")
                
                # Handle cookies aggressively
                print("🍪 Handling cookies...")
                await self._force_accept_cookies(page)
                
                # Check what we're seeing
                page_text = await page.inner_text('body')
                print(f"📄 Page contains: {len(page_text)} characters")
                
                # Look for paywall/access issues
                if any(indicator in page_text.lower() for indicator in [
                    'purchase this article', 'subscription required', 'sign in to access'
                ]):
                    print("🔒 Paywall detected - attempting institutional access")
                    success = await self._handle_institutional_access(page)
                    if not success:
                        print("❌ Institutional access failed")
                        await browser.close()
                        return False
                    
                    # Re-check page after auth
                    await page.wait_for_timeout(5000)
                    page_text = await page.inner_text('body')
                
                # Now aggressively look for PDF download
                print("📄 Looking for PDF download...")
                download_success = await self._aggressive_pdf_download(page, save_path)
                
                if download_success:
                    print(f"🎉 SUCCESS: Downloaded {save_path}")
                    print(f"   File size: {save_path.stat().st_size} bytes")
                    await browser.close()
                    return True
                else:
                    print("❌ PDF download failed")
                    
                    # Keep browser open for debugging
                    print("🔍 Keeping browser open for manual inspection...")
                    await page.wait_for_timeout(30000)
                    
                    await browser.close()
                    return False
                    
            except Exception as e:
                print(f"❌ Download failed: {e}")
                await browser.close()
                return False
    
    async def _force_accept_cookies(self, page):
        """Aggressively handle cookie banners"""
        cookie_selectors = [
            'button:has-text("Accept All")',
            'button:has-text("Accept Cookies")', 
            'button:has-text("Accept")',
            '#onetrust-accept-btn-handler',
            '.cookie-accept',
            'button[id*="cookie"]',
            'button[class*="cookie"]'
        ]
        
        for selector in cookie_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible():
                        print(f"   🍪 Clicking: {selector}")
                        await element.click()
                        await page.wait_for_timeout(2000)
                        return
            except:
                continue
    
    async def _handle_institutional_access(self, page):
        """Handle institutional access aggressively"""
        
        # Look for institutional access buttons
        institutional_selectors = [
            'a:has-text("Institutional Login")',
            'a:has-text("Access through institution")',
            'button:has-text("Login")',
            'a:has-text("Sign in")',
            'a[href*="ssostart"]',
            '.institutional-login'
        ]
        
        for selector in institutional_selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=5000)
                if element and await element.is_visible():
                    print(f"   🔑 Clicking institutional access: {selector}")
                    await element.click()
                    await page.wait_for_timeout(8000)
                    
                    # Handle ETH authentication
                    current_url = page.url
                    if 'ethz' in current_url or 'shibboleth' in current_url:
                        print(f"   🔐 ETH authentication required")
                        return await self._handle_eth_auth(page)
                    
                    return True
            except:
                continue
        
        return False
    
    async def _handle_eth_auth(self, page):
        """Handle ETH authentication"""
        try:
            # Check for Cloudflare
            page_content = await page.content()
            if 'cloudflare' in page_content.lower() or 'verify you are human' in page_content.lower():
                print("     ❌ Cloudflare detected - this blocks access")
                return False
            
            await page.wait_for_timeout(3000)
            
            # Username
            username_selectors = ['input[name="username"]', 'input[type="text"]']
            for selector in username_selectors:
                try:
                    field = await page.wait_for_selector(selector, timeout=5000)
                    if field and await field.is_visible():
                        await field.fill(self.credentials['username'])
                        print("     ✅ Username filled")
                        break
                except:
                    continue
            
            # Password
            password_selectors = ['input[name="password"]', 'input[type="password"]']
            for selector in password_selectors:
                try:
                    field = await page.wait_for_selector(selector, timeout=5000)
                    if field and await field.is_visible():
                        await field.fill(self.credentials['password'])
                        print("     ✅ Password filled")
                        break
                except:
                    continue
            
            # Submit
            submit_selectors = ['input[type="submit"]', 'button[type="submit"]', 'button:has-text("Login")']
            for selector in submit_selectors:
                try:
                    button = await page.wait_for_selector(selector, timeout=5000)
                    if button and await button.is_visible():
                        await button.click()
                        await page.wait_for_timeout(10000)
                        print("     ✅ Credentials submitted")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            print(f"     ❌ ETH auth error: {e}")
            return False
    
    async def _aggressive_pdf_download(self, page, save_path):
        """Aggressively try to download PDF"""
        
        # Multiple PDF selectors to try
        pdf_selectors = [
            'a:has-text("Download PDF")',
            'a:has-text("PDF")',
            'a[href*="pdf"]',
            'a[href*="pdfdirect"]',
            'button:has-text("Download")',
            '.pdf-download',
            'a[title*="PDF"]',
            'a[aria-label*="PDF"]'
        ]
        
        for selector in pdf_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible():
                        print(f"   🎯 Trying PDF download: {selector}")
                        
                        # Method 1: Expect download
                        try:
                            async with page.expect_download(timeout=20000) as download_info:
                                await element.click()
                                download = await download_info.value
                                await download.save_as(save_path)
                                
                                if save_path.exists() and save_path.stat().st_size > 1000:
                                    return True
                        except:
                            print(f"   ❌ Direct download failed")
                        
                        # Method 2: Check if URL changed to PDF
                        try:
                            await element.click()
                            await page.wait_for_timeout(5000)
                            
                            if 'pdf' in page.url.lower():
                                print(f"   🎯 PDF URL detected, attempting save")
                                # Try to save current page as PDF
                                pdf_content = await page.content()
                                if len(pdf_content) > 1000 and '%PDF' in pdf_content:
                                    with open(save_path, 'wb') as f:
                                        f.write(pdf_content.encode())
                                    return True
                        except:
                            print(f"   ❌ URL method failed")
                        
                        # Method 3: Navigate to href directly
                        try:
                            href = await element.get_attribute('href')
                            if href and 'pdf' in href.lower():
                                print(f"   🎯 Direct PDF URL: {href}")
                                
                                # Open in new tab
                                new_page = await page.context.new_page()
                                response = await new_page.goto(href, timeout=15000)
                                
                                if response and response.status == 200:
                                    content_type = response.headers.get('content-type', '')
                                    if 'pdf' in content_type.lower():
                                        # This is a PDF response
                                        pdf_buffer = await response.body()
                                        with open(save_path, 'wb') as f:
                                            f.write(pdf_buffer)
                                        
                                        await new_page.close()
                                        
                                        if save_path.exists() and save_path.stat().st_size > 1000:
                                            return True
                                
                                await new_page.close()
                        except:
                            print(f"   ❌ Direct href method failed")
            except:
                continue
        
        return False
    
    async def run_proof_test(self):
        """Run proof test with real journal papers"""
        
        print("🔬 WILEY DOWNLOAD PROOF TEST")
        print("=" * 80)
        print("GOAL: Actually download PDFs from subscription journals")
        print("=" * 80)
        
        # Test papers from different journal types
        test_papers = [
            {
                'doi': '10.1002/anie.202004934',
                'journal': 'Angewandte Chemie',
                'title': 'Chemistry paper'
            },
            {
                'doi': '10.1111/1467-9523.00201', 
                'journal': 'Economica',
                'title': 'Economics paper'
            },
            {
                'doi': '10.1002/adma.202001924',
                'journal': 'Advanced Materials', 
                'title': 'Materials science paper'
            }
        ]
        
        # Ensure VPN
        self.ensure_vpn_connection()
        
        successful_downloads = 0
        total_tests = len(test_papers)
        
        for i, paper in enumerate(test_papers, 1):
            print(f"\n{'='*20} TEST {i}/{total_tests} {'='*20}")
            
            success = await self.download_from_wiley_journal(
                paper['doi'], 
                paper['journal'],
                paper['title']
            )
            
            if success:
                successful_downloads += 1
                print(f"✅ DOWNLOAD {i} SUCCESS")
            else:
                print(f"❌ DOWNLOAD {i} FAILED")
        
        # Final results
        print(f"\n{'='*25} FINAL PROOF {'='*25}")
        print(f"Downloads attempted: {total_tests}")
        print(f"Downloads successful: {successful_downloads}")
        
        if successful_downloads > 0:
            print(f"🎉 PROOF COMPLETE: {successful_downloads} PDFs downloaded!")
            print(f"📁 Check folder: {self.downloads_dir}")
            
            # List downloaded files
            pdf_files = list(self.downloads_dir.glob("*.pdf"))
            if pdf_files:
                print(f"\n📄 Downloaded files:")
                for pdf_file in pdf_files:
                    size_mb = pdf_file.stat().st_size / (1024 * 1024)
                    print(f"   {pdf_file.name} ({size_mb:.1f} MB)")
            
            return True
        else:
            print(f"❌ PROOF FAILED: No successful downloads")
            print(f"💡 Wiley subscription access still not working properly")
            return False

async def main():
    """Main proof test"""
    
    prover = WileyDownloadProof()
    
    if not await prover.initialize():
        return False
    
    success = await prover.run_proof_test()
    
    if success:
        print(f"\n🎯 WILEY DOWNLOADS PROVEN TO WORK!")
    else:
        print(f"\n💥 WILEY DOWNLOADS STILL NOT WORKING")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())