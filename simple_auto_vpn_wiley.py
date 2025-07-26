#!/usr/bin/env python3
"""
SIMPLE AUTO VPN WILEY DOWNLOADER
================================

Uses AppleScript automation for macOS to handle VPN connection automatically.
This approach is more reliable than expect scripts.
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

class SimpleAutoVPNWiley:
    """Simple automatic VPN Wiley downloader"""
    
    def __init__(self):
        self.cisco_path = "/opt/cisco/secureclient/bin/vpn"
        self.credentials = None
        self.downloads_dir = Path("simple_auto_downloads")
        self.downloads_dir.mkdir(exist_ok=True)
    
    async def initialize(self):
        """Initialize credentials"""
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
    
    def is_vpn_connected(self):
        """Check VPN status"""
        try:
            result = subprocess.run([self.cisco_path, "status"], 
                                  capture_output=True, text=True, timeout=10)
            return "state: Connected" in result.stdout
        except:
            return False
    
    def connect_vpn_applescript(self):
        """Use AppleScript to automate Cisco Secure Client GUI"""
        
        print("🔄 Connecting VPN via AppleScript automation...")
        
        # AppleScript to automate Cisco Secure Client
        applescript = f'''
        tell application "Cisco Secure Client"
            activate
            delay 2
        end tell
        
        tell application "System Events"
            tell process "Cisco Secure Client"
                -- Look for server field and enter VPN server
                try
                    set serverField to text field 1 of window 1
                    set value of serverField to "vpn.ethz.ch"
                    delay 1
                    
                    -- Click connect button
                    click button "Connect" of window 1
                    delay 3
                    
                    -- Fill username if prompted
                    if exists text field "Username" of window 1 then
                        set value of text field "Username" of window 1 to "{self.credentials['username']}"
                        delay 1
                    end if
                    
                    -- Fill password if prompted  
                    if exists text field "Password" of window 1 then
                        set value of text field "Password" of window 1 to "{self.credentials['password']}"
                        delay 1
                        
                        -- Click OK or Connect
                        try
                            click button "OK" of window 1
                        on error
                            click button "Connect" of window 1
                        end try
                    end if
                    
                on error
                    -- If automation fails, at least open the app
                    log "GUI automation failed, opening Cisco client for manual connection"
                end try
            end tell
        end tell
        '''
        
        try:
            # Run AppleScript
            result = subprocess.run(['osascript', '-e', applescript], 
                                  capture_output=True, text=True, timeout=30)
            
            # Wait for connection to establish
            print("   ⏳ Waiting for VPN connection...")
            for i in range(15):  # Wait up to 15 seconds
                time.sleep(1)
                if self.is_vpn_connected():
                    print("   ✅ VPN connected successfully!")
                    return True
                print(f"   ⏳ Checking connection... ({i+1}/15)")
            
            print("   ⚠️ Automated connection may need manual completion")
            
            # Give user a moment to complete manually
            print("   💡 Please complete connection in Cisco Secure Client if needed")
            time.sleep(10)
            
            return self.is_vpn_connected()
            
        except Exception as e:
            print(f"   ❌ AppleScript automation failed: {e}")
            return False
    
    def ensure_vpn(self):
        """Ensure VPN is connected"""
        
        if self.is_vpn_connected():
            print("✅ VPN already connected")
            return True
        
        print("🔌 VPN disconnected - auto-connecting...")
        
        # Try AppleScript automation
        if self.connect_vpn_applescript():
            return True
        
        # Fallback: Open Cisco client and prompt
        print("🔧 Opening Cisco Secure Client for connection...")
        try:
            subprocess.run(['open', '-a', 'Cisco Secure Client'], timeout=5)
            
            print("💡 Cisco Secure Client opened")
            print("Please connect to: vpn.ethz.ch")
            print("Use your ETH credentials + 2FA")
            
            # Wait for connection
            for i in range(30):  # Wait up to 30 seconds
                time.sleep(1)
                if self.is_vpn_connected():
                    print("✅ VPN connection detected!")
                    return True
                if i % 5 == 0:
                    print(f"   ⏳ Waiting for connection... ({i+1}/30)")
            
            print("❌ VPN connection timeout")
            return False
            
        except Exception as e:
            print(f"❌ Could not open Cisco client: {e}")
            return False
    
    async def test_wiley_access(self):
        """Test Wiley PDF access"""
        
        test_url = "https://onlinelibrary.wiley.com/doi/pdf/10.1002/anie.202004934"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                response = await page.goto(test_url, timeout=15000)
                
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
    
    async def download_paper(self, doi, title=""):
        """Download a single paper"""
        
        print(f"\\n🎯 DOWNLOADING: {title or doi}")
        print("-" * 50)
        
        # Ensure VPN connection
        if not self.ensure_vpn():
            print("❌ VPN connection required")
            return False
        
        # Test access
        if not await self.test_wiley_access():
            print("❌ PDF access test failed")
            return False
        
        print("✅ Access verified - downloading...")
        
        # Download PDF
        pdf_url = f"https://onlinelibrary.wiley.com/doi/pdf/{doi}"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                response = await page.goto(pdf_url, timeout=20000)
                
                if response and response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    
                    if 'pdf' in content_type.lower():
                        pdf_buffer = await response.body()
                        
                        if len(pdf_buffer) > 1000:
                            filename = f"wiley_{doi.replace('/', '_').replace('.', '_')}.pdf"
                            save_path = self.downloads_dir / filename
                            
                            with open(save_path, 'wb') as f:
                                f.write(pdf_buffer)
                            
                            await browser.close()
                            
                            size_mb = save_path.stat().st_size / (1024 * 1024)
                            print(f"🎉 PDF saved: {save_path} ({size_mb:.2f} MB)")
                            return True
                
                await browser.close()
                print("❌ Could not download PDF")
                return False
                
            except Exception as e:
                print(f"❌ Download error: {e}")
                await browser.close()
                return False
    
    async def download_batch(self, papers):
        """Download multiple papers"""
        
        print("🚀 SIMPLE AUTO VPN BATCH DOWNLOAD")
        print("=" * 70)
        
        successful = 0
        
        for i, paper in enumerate(papers, 1):
            print(f"\\n{'='*15} PAPER {i}/{len(papers)} {'='*15}")
            
            if isinstance(paper, str):
                doi = paper
                title = ""
            else:
                doi = paper.get('doi', '')
                title = paper.get('title', '')
            
            success = await self.download_paper(doi, title)
            
            if success:
                successful += 1
                print(f"✅ PAPER {i} SUCCESS")
            else:
                print(f"❌ PAPER {i} FAILED")
        
        print(f"\\n{'='*20} RESULTS {'='*20}")
        print(f"Attempted: {len(papers)}")
        print(f"Successful: {successful}")
        
        if successful > 0:
            pdf_files = list(self.downloads_dir.glob("*.pdf"))
            print(f"\\n📁 Downloaded PDFs:")
            for pdf_file in pdf_files:
                size_mb = pdf_file.stat().st_size / (1024 * 1024)
                print(f"   📄 {pdf_file.name} ({size_mb:.2f} MB)")
        
        return successful > 0

async def main():
    """Main function"""
    
    print("🤖 SIMPLE AUTO VPN WILEY DOWNLOADER")
    print("=" * 70)
    print("Automatic VPN management + Wiley downloads")
    print("=" * 70)
    
    downloader = SimpleAutoVPNWiley()
    
    if not await downloader.initialize():
        return False
    
    # Test papers
    papers = [
        {
            'doi': '10.1002/anie.202004934',
            'title': 'Angewandte Chemie paper'
        },
        {
            'doi': '10.1111/1467-9523.00201',
            'title': 'Economica paper'
        }
    ]
    
    success = await downloader.download_batch(papers)
    
    if success:
        print("\\n🎉 AUTO VPN DOWNLOADER WORKING!")
    else:
        print("\\n❌ Downloads failed")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())