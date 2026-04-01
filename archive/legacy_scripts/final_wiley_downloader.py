#!/usr/bin/env python3
"""
VPN-AWARE WILEY DOWNLOADER
==========================

Downloads Wiley papers with intelligent VPN handling.
Works with manual or automatic VPN connection.
"""

import asyncio
import subprocess
import sys
from pathlib import Path
from playwright.async_api import async_playwright
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).parent))

class VPNAwareWileyDownloader:
    """Wiley downloader with VPN awareness"""
    
    def __init__(self):
        self.cisco_path = "/opt/cisco/secureclient/bin/vpn"
        self.credentials = None
        self.downloads_dir = Path("final_downloads")
        self.downloads_dir.mkdir(exist_ok=True)
    
    async def initialize(self):
        """Initialize with credentials"""
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
    
    def check_vpn_status(self):
        """Check VPN connection status"""
        try:
            result = subprocess.run([self.cisco_path, "status"], 
                                  capture_output=True, text=True, timeout=10)
            
            if "state: Connected" in result.stdout:
                print("✅ VPN connected")
                return True
            else:
                print("❌ VPN not connected")
                return False
                
        except Exception as e:
            print(f"❌ VPN check failed: {e}")
            return False
    
    def prompt_vpn_connection(self):
        """Prompt user to connect VPN if needed"""
        
        if self.check_vpn_status():
            return True
        
        print("\n🔌 VPN CONNECTION REQUIRED")
        print("=" * 50)
        print("Wiley subscription downloads require ETH VPN connection.")
        print("Please connect to ETH VPN using Cisco Secure Client.")
        print("\nOptions:")
        print("1. Open Cisco Secure Client GUI")
        print("2. Connect to: vpn.ethz.ch (or sslvpn.ethz.ch)")
        print("3. Enter ETH credentials + 2FA")
        
        input("\nPress Enter when VPN is connected...")
        
        return self.check_vpn_status()
    
    async def download_wiley_paper(self, doi, title=""):
        """Download a Wiley paper"""
        
        print(f"\n🎯 DOWNLOADING: {title or doi}")
        print("-" * 50)
        
        paper_url = f"https://onlinelibrary.wiley.com/doi/{doi}"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=['--start-maximized']
            )
            
            context = await browser.new_context(accept_downloads=True)
            page = await context.new_page()
            
            try:
                # Load paper
                print("📍 Loading paper...")
                await page.goto(paper_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(5000)
                
                # Handle cookies
                await self._handle_cookies(page)
                
                # Check authentication need
                page_text = await page.inner_text('body')
                needs_auth = any(indicator in page_text.lower() for indicator in [
                    'institutional access', 'sign in to access', 'purchase'
                ])
                
                if needs_auth:
                    print("🔑 Handling authentication...")
                    await self._handle_authentication(page)
                    await page.wait_for_timeout(5000)
                
                # Download PDF
                print("📄 Downloading PDF...")
                success = await self._download_pdf(page, doi)
                
                await browser.close()
                return success
                
            except Exception as e:
                print(f"❌ Download failed: {e}")
                await browser.close()
                return False
    
    async def _handle_cookies(self, page):
        """Handle cookies"""
        try:
            cookie_btn = await page.wait_for_selector('button:has-text("Accept All")', timeout=5000)
            if cookie_btn and await cookie_btn.is_visible():
                await cookie_btn.click()
                await page.wait_for_timeout(2000)
        except:
            pass
    
    async def _handle_authentication(self, page):
        """Handle institutional authentication"""
        
        institutional_selectors = [
            'a:has-text("Institutional Login")',
            'a[href*="ssostart"]',
            'button:has-text("Login")'
        ]
        
        for selector in institutional_selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=5000)
                if element and await element.is_visible():
                    await element.click()
                    await page.wait_for_timeout(8000)
                    
                    if 'ethz' in page.url or 'shibboleth' in page.url:
                        await self._do_eth_login(page)
                    return
            except:
                continue
    
    async def _do_eth_login(self, page):
        """Perform ETH login"""
        try:
            await page.wait_for_timeout(3000)
            
            # Username
            username_field = await page.wait_for_selector('input[name="username"]', timeout=10000)
            if username_field:
                await username_field.fill(self.credentials['username'])
            
            # Password
            password_field = await page.wait_for_selector('input[name="password"]', timeout=5000)
            if password_field:
                await password_field.fill(self.credentials['password'])
            
            # Submit
            submit_btn = await page.wait_for_selector('input[type="submit"]', timeout=5000)
            if submit_btn:
                await submit_btn.click()
                await page.wait_for_timeout(15000)
                
        except Exception as e:
            print(f"Authentication error: {e}")
    
    async def _download_pdf(self, page, doi):
        """Download PDF with multiple strategies"""
        
        base_url = "https://onlinelibrary.wiley.com"
        
        # Strategy 1: Direct PDF URLs
        pdf_urls = [
            f"{base_url}/doi/pdf/{doi}",
            f"{base_url}/doi/epdf/{doi}"
        ]
        
        for pdf_url in pdf_urls:
            try:
                pdf_page = await page.context.new_page()
                response = await pdf_page.goto(pdf_url, timeout=20000)
                
                if response and response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    
                    if 'pdf' in content_type.lower():
                        pdf_buffer = await response.body()
                        
                        if len(pdf_buffer) > 1000:
                            filename = f"wiley_{doi.replace('/', '_').replace('.', '_')}.pdf"
                            save_path = self.downloads_dir / filename
                            
                            with open(save_path, 'wb') as f:
                                f.write(pdf_buffer)
                            
                            await pdf_page.close()
                            
                            size_mb = save_path.stat().st_size / (1024 * 1024)
                            print(f"🎉 PDF saved: {save_path} ({size_mb:.2f} MB)")
                            return True
                
                await pdf_page.close()
                
            except Exception as e:
                print(f"PDF URL failed: {e}")
                try:
                    await pdf_page.close()
                except:
                    pass
        
        return False
    
    async def download_multiple_papers(self, papers):
        """Download multiple papers"""
        
        print("🚀 BATCH WILEY DOWNLOAD")
        print("=" * 60)
        
        successful = 0
        
        for i, paper in enumerate(papers, 1):
            print(f"\n{'='*15} PAPER {i}/{len(papers)} {'='*15}")
            
            if isinstance(paper, str):
                doi = paper
                title = ""
            else:
                doi = paper.get('doi', '')
                title = paper.get('title', '')
            
            success = await self.download_wiley_paper(doi, title)
            
            if success:
                successful += 1
                print(f"✅ PAPER {i} SUCCESS")
            else:
                print(f"❌ PAPER {i} FAILED")
        
        print(f"\n{'='*20} FINAL RESULTS {'='*20}")
        print(f"Papers attempted: {len(papers)}")
        print(f"Successfully downloaded: {successful}")
        
        if successful > 0:
            # Show downloaded files
            pdf_files = list(self.downloads_dir.glob("*.pdf"))
            if pdf_files:
                print(f"\n📁 Downloaded files:")
                for pdf_file in pdf_files:
                    size_mb = pdf_file.stat().st_size / (1024 * 1024)
                    print(f"   📄 {pdf_file.name} ({size_mb:.2f} MB)")
        
        return successful > 0

async def main():
    """Main download function"""
    
    downloader = VPNAwareWileyDownloader()
    
    if not await downloader.initialize():
        return False
    
    # Ensure VPN connection
    if not downloader.prompt_vpn_connection():
        print("❌ VPN connection required for subscription downloads")
        return False
    
    # Test papers - mix of subscription content
    test_papers = [
        {
            'doi': '10.1002/anie.202004934',
            'title': 'Angewandte Chemie paper'
        },
        {
            'doi': '10.1111/1467-9523.00201',
            'title': 'Economica paper' 
        },
        {
            'doi': '10.1002/adma.202001924',
            'title': 'Advanced Materials paper'
        }
    ]
    
    success = await downloader.download_multiple_papers(test_papers)
    
    if success:
        print("\n🎉 WILEY DOWNLOADS WORKING!")
    else:
        print("\n❌ Downloads still not working")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
