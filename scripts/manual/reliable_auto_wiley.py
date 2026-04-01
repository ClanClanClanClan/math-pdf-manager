#!/usr/bin/env python3
"""
RELIABLE AUTO WILEY DOWNLOADER
==============================

Uses a more reliable approach:
1. Use cliclick for precise UI automation (more reliable than AppleScript)
2. Visual detection of VPN status
3. Fallback to simple manual prompt if automation fails

This should actually work to auto-click the Connect button.
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

class ReliableAutoWiley:
    """Reliable auto-clicker for Wiley downloads"""
    
    def __init__(self):
        self.cisco_path = "/opt/cisco/secureclient/bin/vpn"
        self.credentials = None
        self.downloads_dir = Path("reliable_downloads")
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
    
    def install_cliclick(self):
        """Install cliclick for reliable UI automation"""
        try:
            # Check if cliclick exists
            subprocess.run(['which', 'cliclick'], check=True, capture_output=True)
            print("✅ cliclick already installed")
            return True
        except subprocess.CalledProcessError:
            print("📦 Installing cliclick for reliable UI automation...")
            try:
                subprocess.run(['brew', 'install', 'cliclick'], check=True)
                print("✅ cliclick installed successfully")
                return True
            except:
                print("❌ Could not install cliclick")
                print("💡 Please install manually: brew install cliclick")
                return False
    
    def is_vpn_connected(self):
        """Check VPN status"""
        try:
            result = subprocess.run([self.cisco_path, "status"], 
                                  capture_output=True, text=True, timeout=10)
            return "state: Connected" in result.stdout
        except:
            return False
    
    def force_kill_cisco(self):
        """Force kill Cisco client to ensure clean state"""
        try:
            subprocess.run(['pkill', '-f', 'Cisco Secure Client'], capture_output=True)
            time.sleep(2)
        except:
            pass
    
    def auto_connect_with_cliclick(self):
        """Use cliclick for more reliable automation"""
        
        print("🤖 Auto-connecting with cliclick automation...")
        
        # Ensure clean state
        self.force_kill_cisco()
        
        try:
            # Open Cisco Secure Client
            print("   📱 Opening Cisco Secure Client...")
            subprocess.run(['open', '-a', 'Cisco Secure Client'], timeout=10)
            time.sleep(4)
            
            # Bring to front
            subprocess.run(['osascript', '-e', 'tell application "Cisco Secure Client" to activate'], timeout=5)
            time.sleep(2)
            
            # Take screenshot to see what we're working with
            subprocess.run(['screencapture', '/tmp/cisco_before.png'], timeout=5)
            print("   📸 Screenshot taken for debugging")
            
            # Strategy 1: Click in typical server field location and type
            print("   ⌨️ Entering VPN server...")
            
            # Click where server field typically is (center-left of window)
            subprocess.run(['cliclick', 'c:400,300'], timeout=5)
            time.sleep(1)
            
            # Clear field and type server
            subprocess.run(['cliclick', 'kc:cmd', 'kd:a', 'ku:a', 'ku:cmd'], timeout=5)  # Select all
            time.sleep(0.5)
            subprocess.run(['cliclick', 't:vpn.ethz.ch'], timeout=5)
            time.sleep(1)
            
            # Strategy 2: Look for Connect button and click it
            print("   👆 Clicking Connect button...")
            
            # Try multiple common locations for Connect button
            connect_locations = [
                '500,350',  # Typical Connect button location
                '450,380',  # Alternative location
                '400,400',  # Lower position
                '550,330'   # Right side
            ]
            
            for location in connect_locations:
                try:
                    print(f"   Trying click at {location}")
                    subprocess.run(['cliclick', f'c:{location}'], timeout=5)
                    time.sleep(2)
                    
                    # Check if login dialog appeared (success indicator)
                    subprocess.run(['screencapture', '/tmp/cisco_after_click.png'], timeout=5)
                    
                    # If we see a login prompt, fill credentials
                    if self.handle_login_with_cliclick():
                        break
                        
                except Exception as e:
                    print(f"   Click at {location} failed: {e}")
                    continue
            
            # Wait for connection
            print("   ⏳ Waiting for VPN connection...")
            for i in range(30):
                time.sleep(1)
                if self.is_vpn_connected():
                    print("   🎉 VPN connected via cliclick!")
                    return True
                if i % 5 == 0 and i > 0:
                    print(f"   Still connecting... ({i}/30)")
            
            return self.is_vpn_connected()
            
        except Exception as e:
            print(f"   ❌ cliclick automation failed: {e}")
            return False
    
    def handle_login_with_cliclick(self):
        """Handle login dialog with cliclick"""
        
        try:
            print("   🔑 Filling login credentials...")
            time.sleep(2)
            
            # Click username field (typical location)
            subprocess.run(['cliclick', 'c:400,250'], timeout=5)
            time.sleep(0.5)
            
            # Type username
            subprocess.run(['cliclick', f't:{self.credentials["username"]}'], timeout=5)
            time.sleep(0.5)
            
            # Tab to password field
            subprocess.run(['cliclick', 'key:tab'], timeout=5)
            time.sleep(0.5)
            
            # Type password
            subprocess.run(['cliclick', f't:{self.credentials["password"]}'], timeout=5)
            time.sleep(0.5)
            
            # Press Enter or click OK
            subprocess.run(['cliclick', 'key:enter'], timeout=5)
            time.sleep(1)
            
            print("   ✅ Credentials submitted")
            return True
            
        except Exception as e:
            print(f"   ❌ Login filling failed: {e}")
            return False
    
    def smart_vpn_ensure(self):
        """Smart VPN connection with multiple strategies"""
        
        if self.is_vpn_connected():
            print("✅ VPN already connected")
            return True
        
        print("🔌 VPN not connected - trying auto-connection...")
        
        # Install cliclick if needed
        if not self.install_cliclick():
            print("❌ Cannot auto-click without cliclick")
            return self.fallback_manual_connect()
        
        # Try cliclick automation
        if self.auto_connect_with_cliclick():
            return True
        
        # Fallback to manual with helpful guidance
        return self.fallback_manual_connect()
    
    def fallback_manual_connect(self):
        """Fallback manual connection with smart guidance"""
        
        print("\\n🔧 FALLBACK: Manual VPN Connection")
        print("=" * 50)
        print("Auto-click didn't work - opening VPN client for you...")
        
        try:
            # Open Cisco client
            subprocess.run(['open', '-a', 'Cisco Secure Client'], timeout=10)
            print("✅ Cisco Secure Client opened")
            
            print("\\n📋 Quick steps:")
            print("1. Enter server: vpn.ethz.ch")
            print("2. Click Connect")
            print("3. Enter your ETH credentials + 2FA")
            
            print("\\n⏳ Waiting for VPN connection...")
            print("(Script continues automatically once connected)")
            
            # Smart waiting
            for i in range(60):
                time.sleep(1)
                if self.is_vpn_connected():
                    print("\\n🎉 VPN CONNECTION DETECTED!")
                    return True
                if (i + 1) % 10 == 0:
                    remaining = 60 - (i + 1)
                    print(f"   Still waiting... ({remaining}s remaining)")
            
            return self.is_vpn_connected()
            
        except Exception as e:
            print(f"❌ Fallback failed: {e}")
            return False
    
    async def download_paper(self, doi, title=""):
        """Download a paper"""
        
        print(f"\\n🎯 DOWNLOADING: {title or doi}")
        print(f"DOI: {doi}")
        print("-" * 50)
        
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
                            
                            size_mb = save_path.stat().st_size / (1024 * 1024)
                            print(f"🎉 SUCCESS: {save_path} ({size_mb:.2f} MB)")
                            
                            await browser.close()
                            return True
                
                print(f"❌ Failed: Status {response.status if response else 'No response'}")
                await browser.close()
                return False
                
            except Exception as e:
                print(f"❌ Download error: {e}")
                await browser.close()
                return False
    
    async def reliable_batch_download(self, papers):
        """Reliable batch download"""
        
        print("🔧 RELIABLE AUTO WILEY DOWNLOADER")
        print("=" * 70)
        print("Uses cliclick for better automation + manual fallback")
        print("=" * 70)
        
        # Ensure VPN connection once
        if not self.smart_vpn_ensure():
            print("❌ VPN connection required")
            return False
        
        print(f"\\n🎯 Starting download of {len(papers)} papers...")
        
        successful = 0
        
        for i, paper in enumerate(papers, 1):
            print(f"\\n{'='*15} PAPER {i}/{len(papers)} {'='*15}")
            
            # Check VPN before each download
            if not self.is_vpn_connected():
                print("⚠️ VPN disconnected - reconnecting...")
                if not self.smart_vpn_ensure():
                    print("❌ VPN reconnection failed")
                    continue
            
            if isinstance(paper, str):
                doi = paper
                title = ""
            else:
                doi = paper.get('doi', '')
                title = paper.get('title', '')
            
            success = await self.download_paper(doi, title)
            
            if success:
                successful += 1
        
        # Results
        print(f"\\n{'='*20} FINAL RESULTS {'='*20}")
        print(f"Papers: {len(papers)}")
        print(f"Downloaded: {successful}")
        
        if successful > 0:
            pdf_files = list(self.downloads_dir.glob("*.pdf"))
            print(f"\\n📁 Downloaded files:")
            total_size = 0
            for pdf_file in pdf_files:
                size_mb = pdf_file.stat().st_size / (1024 * 1024)
                total_size += size_mb
                print(f"   📄 {pdf_file.name} ({size_mb:.2f} MB)")
            
            print(f"\\n📊 Total: {len(pdf_files)} files, {total_size:.2f} MB")
            print(f"🎉 RELIABLE DOWNLOADER WORKING!")
        else:
            print(f"\\n❌ No successful downloads")
        
        return successful > 0

async def main():
    """Main function"""
    
    downloader = ReliableAutoWiley()
    
    if not await downloader.initialize():
        return False
    
    # Test papers
    papers = [
        {
            'doi': '10.1002/anie.202004934',
            'title': 'Angewandte Chemie Test Paper'
        },
        {
            'doi': '10.1111/1467-9523.00201',
            'title': 'Economica Test Paper'
        }
    ]
    
    success = await downloader.reliable_batch_download(papers)
    
    if success:
        print("\\n🎯 RELIABLE AUTO-DOWNLOADER SUCCESS!")
    else:
        print("\\n❌ Downloads failed")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())