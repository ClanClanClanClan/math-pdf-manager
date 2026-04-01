#!/usr/bin/env python3
"""
AUTOMATIC VPN WILEY DOWNLOADER
==============================

Fully automatic Wiley downloader that:
1. Automatically connects VPN when needed
2. Maintains VPN connection during downloads
3. Handles all authentication automatically
4. Downloads PDFs without any manual intervention

ZERO manual VPN management required after first-time credential storage.
"""

import asyncio
import subprocess
import sys
import time
import os
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

class AutoVPNWileyDownloader:
    """Fully automatic VPN-enabled Wiley downloader"""
    
    def __init__(self):
        self.cisco_path = "/opt/cisco/secureclient/bin/vpn"
        self.credentials = None
        self.downloads_dir = Path("auto_downloads")
        self.downloads_dir.mkdir(exist_ok=True)
        self.vpn_attempts = 0
        self.max_vpn_attempts = 3
    
    async def initialize(self):
        """Initialize with ETH credentials"""
        try:
            from src.secure_credential_manager import get_credential_manager
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            if not (username and password):
                raise Exception("No ETH credentials")
                
            self.credentials = {'username': username, 'password': password}
            print(f"✅ ETH credentials loaded: {username[:3]}***")
            return True
            
        except Exception as e:
            print(f"❌ Credential error: {e}")
            return False
    
    def force_disconnect_vpn(self):
        """Force disconnect VPN to ensure clean state"""
        try:
            subprocess.run([self.cisco_path, "disconnect"], 
                          capture_output=True, timeout=10)
            time.sleep(2)
        except:
            pass
    
    def auto_connect_vpn(self):
        """Automatically connect to ETH VPN with retry logic"""
        
        print("🔄 Auto-connecting to ETH VPN...")
        
        # First ensure clean state
        self.force_disconnect_vpn()
        
        # Try multiple VPN servers
        vpn_servers = ["vpn.ethz.ch", "sslvpn.ethz.ch"]
        
        for attempt in range(self.max_vpn_attempts):
            for server in vpn_servers:
                try:
                    print(f"   Attempt {attempt + 1}: Connecting to {server}...")
                    
                    # Use expect script to handle interactive connection
                    expect_script = f'''#!/usr/bin/expect -f
set timeout 30
spawn {self.cisco_path} connect {server}
expect {{
    "Username:" {{
        send "{self.credentials['username']}\\r"
        exp_continue
    }}
    "Password:" {{
        send "{self.credentials['password']}\\r"
        exp_continue
    }}
    "state: Connected" {{
        exit 0
    }}
    "error:" {{
        exit 1
    }}
    timeout {{
        exit 1
    }}
}}
'''
                    
                    # Save expect script
                    expect_file = Path("vpn_connect.exp")
                    with open(expect_file, 'w') as f:
                        f.write(expect_script)
                    
                    # Make executable
                    os.chmod(expect_file, 0o755)
                    
                    # Run expect script
                    result = subprocess.run([str(expect_file)], 
                                          capture_output=True, text=True, timeout=45)
                    
                    # Clean up
                    expect_file.unlink()
                    
                    # Wait and check connection
                    time.sleep(5)
                    
                    if self.check_vpn_connected():
                        print(f"✅ VPN connected successfully to {server}")
                        return True
                    else:
                        print(f"❌ Connection to {server} failed")
                        
                except Exception as e:
                    print(f"❌ VPN connection attempt failed: {e}")
                    continue
            
            if attempt < self.max_vpn_attempts - 1:
                wait_time = (attempt + 1) * 10
                print(f"⏳ Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
        
        print("❌ All VPN connection attempts failed")
        return False
    
    def check_vpn_connected(self):
        """Check if VPN is currently connected"""
        try:
            result = subprocess.run([self.cisco_path, "status"], 
                                  capture_output=True, text=True, timeout=10)
            
            return "state: Connected" in result.stdout
            
        except:
            return False
    
    def ensure_vpn_connection(self):
        """Ensure VPN is connected, connect automatically if not"""
        
        if self.check_vpn_connected():
            print("✅ VPN already connected")
            return True
        
        print("🔌 VPN not connected - auto-connecting...")
        return self.auto_connect_vpn()
    
    async def test_pdf_access(self):
        """Test if we can access Wiley PDFs"""
        
        test_url = "https://onlinelibrary.wiley.com/doi/pdf/10.1002/anie.202004934"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                response = await page.goto(test_url, timeout=20000)
                
                if response and response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'pdf' in content_type.lower():
                        await browser.close()
                        return True
                
                await browser.close()
                return False
                
            except:
                await browser.close()
                return False
    
    async def download_wiley_paper(self, doi, title=""):
        """Download a Wiley paper with automatic VPN management"""
        
        print(f"\\n🎯 DOWNLOADING: {title or doi}")
        print("-" * 60)
        
        # Ensure VPN connection before download
        if not self.ensure_vpn_connection():
            print("❌ Could not establish VPN connection")
            return False
        
        # Verify PDF access
        if not await self.test_pdf_access():
            print("❌ PDF access verification failed")
            return False
        
        print("✅ PDF access verified - proceeding with download")
        
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
                await page.goto(paper_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # Handle cookies
                await self._handle_cookies(page)
                
                # Download PDF directly
                success = await self._download_pdf_direct(page, doi)
                
                await browser.close()
                
                if success:
                    print("🎉 Download successful!")
                else:
                    print("❌ Download failed")
                
                return success
                
            except Exception as e:
                print(f"❌ Download error: {e}")
                await browser.close()
                return False
    
    async def _handle_cookies(self, page):
        """Handle cookie banners"""
        try:
            cookie_btn = await page.wait_for_selector('button:has-text("Accept All")', timeout=3000)
            if cookie_btn and await cookie_btn.is_visible():
                await cookie_btn.click()
                await page.wait_for_timeout(1000)
        except:
            pass
    
    async def _download_pdf_direct(self, page, doi):
        """Download PDF using direct URL approach"""
        
        base_url = "https://onlinelibrary.wiley.com"
        pdf_urls = [
            f"{base_url}/doi/pdf/{doi}",
            f"{base_url}/doi/epdf/{doi}"
        ]
        
        for i, pdf_url in enumerate(pdf_urls, 1):
            try:
                print(f"   Trying PDF URL {i}: {pdf_url}")
                
                pdf_page = await page.context.new_page()
                response = await pdf_page.goto(pdf_url, timeout=20000)
                
                if response and response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    
                    if 'pdf' in content_type.lower():
                        print(f"   ✅ PDF response received")
                        
                        # Get PDF content
                        pdf_buffer = await response.body()
                        
                        if len(pdf_buffer) > 1000:
                            # Save PDF
                            filename = f"wiley_{doi.replace('/', '_').replace('.', '_')}.pdf"
                            save_path = self.downloads_dir / filename
                            
                            with open(save_path, 'wb') as f:
                                f.write(pdf_buffer)
                            
                            await pdf_page.close()
                            
                            size_mb = save_path.stat().st_size / (1024 * 1024)
                            print(f"   📄 PDF saved: {save_path} ({size_mb:.2f} MB)")
                            return True
                        else:
                            print(f"   ❌ PDF too small ({len(pdf_buffer)} bytes)")
                    else:
                        print(f"   ❌ Not a PDF response: {content_type}")
                else:
                    print(f"   ❌ Bad response: {response.status if response else 'No response'}")
                
                await pdf_page.close()
                
            except Exception as e:
                print(f"   ❌ PDF URL {i} failed: {e}")
                try:
                    await pdf_page.close()
                except:
                    pass
        
        return False
    
    async def download_multiple_papers(self, papers):
        """Download multiple papers with automatic VPN management"""
        
        print("🚀 AUTOMATIC BATCH WILEY DOWNLOAD")
        print("=" * 80)
        print("Fully automatic - no manual VPN management required!")
        print("=" * 80)
        
        successful = 0
        
        for i, paper in enumerate(papers, 1):
            print(f"\\n{'='*20} PAPER {i}/{len(papers)} {'='*20}")
            
            # Check VPN connection before each download
            if not self.ensure_vpn_connection():
                print(f"❌ VPN connection failed for paper {i}")
                continue
            
            if isinstance(paper, str):
                doi = paper
                title = ""
            else:
                doi = paper.get('doi', '')
                title = paper.get('title', '')
            
            success = await self.download_wiley_paper(doi, title)
            
            if success:
                successful += 1
        
        # Final results
        print(f"\\n{'='*25} FINAL RESULTS {'='*25}")
        print(f"Papers attempted: {len(papers)}")
        print(f"Successfully downloaded: {successful}")
        
        if successful > 0:
            pdf_files = list(self.downloads_dir.glob("*.pdf"))
            print(f"\\n📁 Downloaded files ({len(pdf_files)} total):")
            for pdf_file in pdf_files:
                size_mb = pdf_file.stat().st_size / (1024 * 1024)
                print(f"   📄 {pdf_file.name} ({size_mb:.2f} MB)")
            
            print(f"\\n🎉 AUTOMATIC DOWNLOADS COMPLETE!")
            print(f"✅ VPN managed automatically")
            print(f"✅ {successful} PDFs downloaded successfully")
        else:
            print(f"\\n❌ No successful downloads")
        
        return successful > 0

def install_expect_if_needed():
    """Install expect if not available"""
    try:
        subprocess.run(["which", "expect"], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        print("⚠️ 'expect' not found - installing via Homebrew...")
        try:
            subprocess.run(["brew", "install", "expect"], check=True)
            print("✅ expect installed successfully")
            return True
        except:
            print("❌ Could not install expect")
            print("💡 Please install manually: brew install expect")
            return False

async def main():
    """Main automatic download function"""
    
    print("🤖 FULLY AUTOMATIC WILEY DOWNLOADER")  
    print("=" * 80)
    print("NO MANUAL VPN MANAGEMENT REQUIRED!")
    print("=" * 80)
    
    # Check expect availability
    if not install_expect_if_needed():
        print("❌ expect tool required for automatic VPN connection")
        return False
    
    downloader = AutoVPNWileyDownloader()
    
    if not await downloader.initialize():
        return False
    
    # Test papers - subscription content
    test_papers = [
        {
            'doi': '10.1002/anie.202004934',
            'title': 'Angewandte Chemie - Chemical synthesis'
        },
        {
            'doi': '10.1111/1467-9523.00201', 
            'title': 'Economica - Economic research'
        },
        {
            'doi': '10.1002/adma.202001924',
            'title': 'Advanced Materials - Materials science'
        }
    ]
    
    success = await downloader.download_multiple_papers(test_papers)
    
    if success:
        print(f"\\n🎯 AUTOMATIC WILEY DOWNLOADER WORKING!")
        print(f"🤖 Fully automated - no manual intervention needed")
    else:
        print(f"\\n❌ Automatic downloader needs adjustment")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())