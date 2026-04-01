#!/usr/bin/env python3
"""
REAL WORKING WILEY DOWNLOADER
=============================

Now with the correct understanding:
1. Cisco already has "sslvpn.ethz.ch/staff-net" pre-filled
2. Just need to click Connect button on the actual Cisco window
3. No need to type server address

This should actually work since the server is already there!
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

class RealWorkingWiley:
    """Wiley downloader that works with actual Cisco interface"""
    
    def __init__(self):
        self.cisco_path = "/opt/cisco/secureclient/bin/vpn"
        self.credentials = None
        self.downloads_dir = Path("real_working_downloads")
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
    
    def get_cisco_window_info(self):
        """Get Cisco window position and size"""
        try:
            # Get window info using AppleScript
            window_info = subprocess.run([
                'osascript', '-e', '''
                tell application "System Events"
                    tell process "Cisco Secure Client"
                        if exists window 1 then
                            set windowBounds to position of window 1
                            set windowSize to size of window 1
                            return (item 1 of windowBounds) & "," & (item 2 of windowBounds) & "," & (item 1 of windowSize) & "," & (item 2 of windowSize)
                        else
                            return "no window"
                        end if
                    end tell
                end tell
                '''
            ], capture_output=True, text=True, timeout=10)
            
            if "no window" not in window_info.stdout:
                coords = window_info.stdout.strip().split(',')
                if len(coords) == 4:
                    x, y, width, height = map(int, coords)
                    return {
                        'x': x,
                        'y': y, 
                        'width': width,
                        'height': height,
                        'center_x': x + width // 2,
                        'center_y': y + height // 2,
                        'connect_x': x + width // 2,
                        'connect_y': y + height - 80  # Connect button usually near bottom
                    }
            
            return None
            
        except Exception as e:
            print(f"Could not get window info: {e}")
            return None
    
    def real_auto_click_vpn(self):
        """Actually click the real Cisco Connect button"""
        
        print("🤖 Auto-clicking REAL Cisco Connect button...")
        
        try:
            # Clean start
            subprocess.run(['pkill', '-f', 'Cisco'], capture_output=True)
            time.sleep(2)
            
            # Open Cisco Secure Client
            print("   📱 Opening Cisco Secure Client...")
            subprocess.run(['open', '-a', 'Cisco Secure Client'])
            time.sleep(8)  # Give it plenty of time to load
            
            # Bring to front
            subprocess.run(['osascript', '-e', 'tell application "Cisco Secure Client" to activate'])
            time.sleep(2)
            
            # Get actual window information
            print("   📐 Getting Cisco window position...")
            window_info = self.get_cisco_window_info()
            
            if window_info:
                print(f"   ✅ Found Cisco window at ({window_info['x']}, {window_info['y']}) size {window_info['width']}x{window_info['height']}")
                
                # Since server is already filled (sslvpn.ethz.ch/staff-net), just click Connect
                print("   👆 Clicking Connect button in actual window...")
                
                # Try multiple positions relative to the actual window
                connect_positions = [
                    (window_info['connect_x'], window_info['connect_y']),  # Bottom center
                    (window_info['center_x'], window_info['center_y'] + 50),  # Center-bottom
                    (window_info['center_x'] - 30, window_info['connect_y']),  # Left of bottom center
                    (window_info['center_x'] + 30, window_info['connect_y']),  # Right of bottom center
                    (window_info['center_x'], window_info['y'] + window_info['height'] - 60)  # Alternative bottom
                ]
                
                clicked_successfully = False
                
                for x, y in connect_positions:
                    try:
                        print(f"     Trying Connect click at ({x},{y})")
                        subprocess.run(['cliclick', f'c:{x},{y}'])
                        time.sleep(4)
                        
                        # Check if credential dialog appeared
                        cred_check = subprocess.run([
                            'osascript', '-e', '''
                            tell application "System Events"
                                tell process "Cisco Secure Client"
                                    try
                                        -- Look for username or password fields
                                        set fieldExists to (exists text field 1 of window 1) or (exists text field 2 of window 1)
                                        return fieldExists
                                    on error
                                        return false
                                    end try
                                end tell
                            end tell
                            '''
                        ], capture_output=True, text=True, timeout=10)
                        
                        if 'true' in cred_check.stdout:
                            print("     ✅ Credential dialog detected!")
                            clicked_successfully = True
                            break
                        else:
                            print(f"     No credential dialog yet...")
                            
                    except Exception as e:
                        print(f"     Click at ({x},{y}) failed: {e}")
                        continue
                
                if clicked_successfully:
                    print("   🔑 Filling credentials in actual dialog...")
                    time.sleep(2)
                    
                    # Get credential field positions relative to window
                    username_x = window_info['center_x']
                    username_y = window_info['center_y'] - 20
                    password_x = window_info['center_x'] 
                    password_y = window_info['center_y'] + 20
                    
                    # Fill username
                    print("     📝 Filling username...")
                    subprocess.run(['cliclick', f'c:{username_x},{username_y}'])
                    time.sleep(0.5)
                    subprocess.run(['cliclick', f't:{self.credentials["username"]}'])
                    time.sleep(0.5)
                    
                    # Tab to password
                    subprocess.run(['cliclick', 'kp:tab'])
                    time.sleep(0.5)
                    
                    # Fill password
                    print("     📝 Filling password...")
                    subprocess.run(['cliclick', f't:{self.credentials["password"]}'])
                    time.sleep(0.5)
                    
                    # Submit
                    subprocess.run(['cliclick', 'kp:return'])
                    time.sleep(3)
                    
                    print("   ✅ Credentials submitted to real dialog!")
                else:
                    print("   ⚠️ Could not detect credential dialog")
            else:
                print("   ❌ Could not find Cisco window")
                return False
            
            # Wait for connection
            print("   ⏳ Waiting for VPN connection...")
            
            for i in range(60):
                time.sleep(1)
                
                if self.is_vpn_connected():
                    print("   🎉 VPN CONNECTED via real auto-click!")
                    return True
                
                if i == 20:
                    print("   💡 Complete 2FA if prompted")
                elif i == 45:
                    print("   ⏳ Final moments...")
            
            connected = self.is_vpn_connected()
            if connected:
                print("   ✅ VPN connection established!")
            else:
                print("   ❌ VPN connection timeout")
                
            return connected
            
        except Exception as e:
            print(f"   ❌ Real auto-click failed: {e}")
            return False
    
    def ensure_vpn_with_real_clicking(self):
        """Ensure VPN connection with real window clicking"""
        
        if self.is_vpn_connected():
            print("✅ VPN already connected")
            return True
        
        print("🔌 VPN not connected - using REAL auto-clicking...")
        
        # Try real auto-click
        if self.real_auto_click_vpn():
            return True
        
        # Fallback 
        print("\\n🔧 Real auto-click needs completion")
        print("Cisco should be open with server pre-filled (sslvpn.ethz.ch/staff-net)")
        print("Please complete authentication if needed")
        
        # Wait for completion
        for i in range(30):
            time.sleep(1)
            if self.is_vpn_connected():
                print("\\n✅ VPN connected!")
                return True
            if (i + 1) % 10 == 0:
                print(f"   Waiting... ({i+1}/30)")
        
        return self.is_vpn_connected()
    
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
                
                print(f"❌ Failed - Status: {response.status if response else 'No response'}")
                await browser.close()
                return False
                
            except Exception as e:
                print(f"❌ Download error: {e}")
                await browser.close()
                return False
    
    async def real_working_batch(self, papers):
        """Real working batch download"""
        
        print("🎯 REAL WORKING WILEY DOWNLOADER")
        print("=" * 80)
        print("Clicks on actual Cisco window with pre-filled server!")
        print("=" * 80)
        
        # Ensure VPN with real clicking
        if not self.ensure_vpn_with_real_clicking():
            print("❌ VPN connection required")
            return False
        
        print(f"\\n🚀 Starting downloads for {len(papers)} papers...")
        
        successful = 0
        
        for i, paper in enumerate(papers, 1):
            print(f"\\n{'='*20} PAPER {i}/{len(papers)} {'='*20}")
            
            # Check VPN before each download
            if not self.is_vpn_connected():
                print("⚠️ VPN disconnected - attempting reconnection...")
                if not self.ensure_vpn_with_real_clicking():
                    print("❌ Cannot reconnect VPN")
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
                print(f"✅ PAPER {i} SUCCESS")
            else:
                print(f"❌ PAPER {i} FAILED")
        
        # Results
        print(f"\\n{'='*25} FINAL RESULTS {'='*25}")
        print(f"Papers: {len(papers)}")
        print(f"Downloaded: {successful}")
        
        if successful > 0:
            pdf_files = list(self.downloads_dir.glob("*.pdf"))
            print(f"\\n📁 Downloaded Files:")
            for pdf_file in pdf_files:
                size_mb = pdf_file.stat().st_size / (1024 * 1024)
                print(f"   📄 {pdf_file.name} ({size_mb:.2f} MB)")
            
            print(f"\\n🎉 REAL WORKING DOWNLOADER SUCCESS!")
            print(f"🤖 Clicked actual Cisco Connect button")
            print(f"📄 Downloaded {successful} PDFs")
        else:
            print(f"\\n❌ No successful downloads")
        
        return successful > 0

async def main():
    """Main function"""
    
    print("🎯 REAL WORKING WILEY DOWNLOADER")
    print("=" * 80)
    print("Finally! Clicks on actual Cisco window with real coordinates!")
    print("=" * 80)
    
    downloader = RealWorkingWiley()
    
    if not await downloader.initialize():
        return False
    
    # Test papers
    papers = [
        {
            'doi': '10.1002/anie.202004934',
            'title': 'Chemistry Test Paper'
        },
        {
            'doi': '10.1111/1467-9523.00201',
            'title': 'Economics Test Paper'
        }
    ]
    
    success = await downloader.real_working_batch(papers)
    
    if success:
        print("\\n🎉 IT ACTUALLY WORKS!")
        print("🤖 Real auto-clicking successful!")
    else:
        print("\\n❌ Still debugging...")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())