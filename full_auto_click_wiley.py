#!/usr/bin/env python3
"""
FULL AUTO-CLICK WILEY DOWNLOADER
================================

This version WILL click the Connect button automatically using:
1. AppleScript with proper accessibility permissions
2. UI automation that works on macOS
3. Automatic VPN connection with minimal intervention

You'll need to grant accessibility permissions once, then it's fully automatic.
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

class FullAutoClickWiley:
    """Wiley downloader that actually clicks VPN connect button"""
    
    def __init__(self):
        self.cisco_path = "/opt/cisco/secureclient/bin/vpn"
        self.credentials = None
        self.downloads_dir = Path("auto_click_downloads")
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
    
    def check_accessibility_permissions(self):
        """Check if we have accessibility permissions"""
        
        print("🔍 Checking accessibility permissions...")
        
        # Test AppleScript access
        test_script = '''
        tell application "System Events"
            try
                get name of every process
                return "accessible"
            on error
                return "blocked"
            end try
        end tell
        '''
        
        try:
            result = subprocess.run(['osascript', '-e', test_script], 
                                  capture_output=True, text=True, timeout=10)
            
            if "accessible" in result.stdout:
                print("✅ Accessibility permissions granted")
                return True
            else:
                print("❌ Accessibility permissions needed")
                return False
                
        except Exception as e:
            print(f"❌ Permission check failed: {e}")
            return False
    
    def request_accessibility_permissions(self):
        """Guide user to grant accessibility permissions"""
        
        if self.check_accessibility_permissions():
            return True
        
        print("\\n🔐 ACCESSIBILITY PERMISSIONS NEEDED")
        print("=" * 60)
        print("To auto-click the VPN Connect button, please:")
        print("1. Go to System Preferences → Security & Privacy → Privacy")
        print("2. Click 'Accessibility' in the left sidebar")
        print("3. Click the lock icon and enter your password")
        print("4. Find 'Terminal' (or your Python app) and check the box")
        print("5. If not listed, click '+' and add Terminal")
        
        # Open System Preferences automatically
        try:
            subprocess.run(['open', '/System/Library/PreferencePanes/Security.prefPane'], timeout=5)
            print("\\n✅ System Preferences opened for you")
        except:
            print("\\n💡 Please open System Preferences manually")
        
        input("\\nPress Enter after granting accessibility permissions...")
        
        return self.check_accessibility_permissions()
    
    def is_vpn_connected(self):
        """Check VPN status"""
        try:
            result = subprocess.run([self.cisco_path, "status"], 
                                  capture_output=True, text=True, timeout=10)
            return "state: Connected" in result.stdout
        except:
            return False
    
    def auto_click_vpn_connect(self):
        """Automatically click VPN connect button using AppleScript"""
        
        print("🤖 Auto-clicking VPN connection...")
        
        # Enhanced AppleScript that handles multiple UI scenarios
        applescript = f'''
        on run
            try
                -- Open Cisco Secure Client
                tell application "Cisco Secure Client"
                    activate
                    delay 3
                end tell
                
                tell application "System Events"
                    tell process "Cisco Secure Client"
                        -- Wait for window to appear
                        repeat 10 times
                            if exists window 1 then exit repeat
                            delay 1
                        end repeat
                        
                        if not (exists window 1) then
                            return "No window found"
                        end if
                        
                        -- Strategy 1: Look for server field and connect button
                        try
                            -- Enter server if field is empty or contains different server
                            if exists text field 1 of window 1 then
                                set currentValue to value of text field 1 of window 1
                                if currentValue is "" or currentValue does not contain "vpn.ethz.ch" then
                                    set value of text field 1 of window 1 to "vpn.ethz.ch"
                                    delay 1
                                end if
                            end if
                            
                            -- Look for Connect button and click it
                            if exists button "Connect" of window 1 then
                                click button "Connect" of window 1
                                delay 2
                                return "Connect clicked"
                            end if
                            
                        on error connectError
                            log "Connect strategy failed: " & connectError
                        end try
                        
                        -- Strategy 2: Look for any clickable connect-related buttons
                        try
                            set allButtons to every button of window 1
                            repeat with btn in allButtons
                                set btnName to name of btn
                                if btnName contains "Connect" or btnName contains "connect" then
                                    click btn
                                    delay 2
                                    return "Connect button found and clicked"
                                end if
                            end repeat
                        on error
                            log "Button search strategy failed"
                        end try
                        
                        -- Strategy 3: Handle login dialog if it appears
                        try
                            delay 3
                            if exists text field "Username" of window 1 then
                                set value of text field "Username" of window 1 to "{self.credentials['username']}"
                                delay 1
                                
                                if exists text field "Password" of window 1 then
                                    set value of text field "Password" of window 1 to "{self.credentials['password']}"
                                    delay 1
                                    
                                    -- Click OK or Connect after filling credentials
                                    if exists button "OK" of window 1 then
                                        click button "OK" of window 1
                                    else if exists button "Connect" of window 1 then
                                        click button "Connect" of window 1
                                    end if
                                    
                                    return "Credentials filled and submitted"
                                end if
                            end if
                        on error
                            log "Credential filling failed"
                        end try
                        
                        return "UI automation completed"
                    end tell
                end tell
                
            on error mainError
                return "Error: " & mainError
            end try
        end run
        '''
        
        try:
            # Run the AppleScript
            result = subprocess.run(['osascript', '-e', applescript], 
                                  capture_output=True, text=True, timeout=45)
            
            print(f"   AppleScript result: {result.stdout.strip()}")
            
            # Wait for connection to establish
            print("   ⏳ Waiting for VPN connection...")
            
            for i in range(30):  # Wait up to 30 seconds
                time.sleep(1)
                if self.is_vpn_connected():
                    print("   🎉 VPN connected automatically!")
                    return True
                
                if i % 5 == 0 and i > 0:
                    print(f"   ⏳ Still connecting... ({i}/30)")
            
            # Check final status
            if self.is_vpn_connected():
                print("   ✅ VPN connection successful")
                return True
            else:
                print("   ⚠️ Auto-click completed but connection may need 2FA")
                print("   💡 Please complete 2FA if prompted")
                
                # Give extra time for 2FA
                for i in range(30):
                    time.sleep(1)
                    if self.is_vpn_connected():
                        print("   🎉 VPN connected after 2FA!")
                        return True
                
                return self.is_vpn_connected()
                
        except Exception as e:
            print(f"   ❌ Auto-click failed: {e}")
            return False
    
    def ensure_vpn_with_autoclick(self):
        """Ensure VPN connection with auto-clicking"""
        
        if self.is_vpn_connected():
            print("✅ VPN already connected")
            return True
        
        print("🔌 VPN not connected - auto-connecting with button clicks...")
        
        # Check permissions first
        if not self.request_accessibility_permissions():
            print("❌ Cannot auto-click without accessibility permissions")
            return False
        
        # Auto-click connect
        return self.auto_click_vpn_connect()
    
    async def download_paper(self, doi, title=""):
        """Download paper with full automation"""
        
        print(f"\\n🎯 AUTO-DOWNLOADING: {title or doi}")
        print("-" * 60)
        
        # Ensure VPN with auto-clicking
        if not self.ensure_vpn_with_autoclick():
            print("❌ VPN connection failed")
            return False
        
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
                            
                            size_mb = save_path.stat().st_size / (1024 * 1024)
                            print(f"🎉 AUTO-DOWNLOADED: {save_path} ({size_mb:.2f} MB)")
                            
                            await browser.close()
                            return True
                
                print("❌ Could not download PDF")
                await browser.close()
                return False
                
            except Exception as e:
                print(f"❌ Download error: {e}")
                await browser.close()
                return False
    
    async def full_auto_batch(self, papers):
        """Fully automatic batch download"""
        
        print("🤖 FULL AUTO-CLICK WILEY DOWNLOADER")
        print("=" * 80)
        print("TRULY AUTOMATIC - Even clicks Connect button for you!")
        print("=" * 80)
        
        successful = 0
        
        for i, paper in enumerate(papers, 1):
            print(f"\\n{'='*20} PAPER {i}/{len(papers)} {'='*20}")
            
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
        
        print(f"\\n{'='*25} AUTO-CLICK RESULTS {'='*25}")
        print(f"Papers: {len(papers)}")
        print(f"Downloaded: {successful}")
        
        if successful > 0:
            pdf_files = list(self.downloads_dir.glob("*.pdf"))
            print(f"\\n📁 Auto-downloaded files:")
            for pdf_file in pdf_files:
                size_mb = pdf_file.stat().st_size / (1024 * 1024)
                print(f"   📄 {pdf_file.name} ({size_mb:.2f} MB)")
            
            print(f"\\n🤖 FULL AUTOMATION WORKING!")
        else:
            print(f"\\n❌ Auto-click downloads failed")
        
        return successful > 0

async def main():
    """Main auto-click function"""
    
    print("🤖 FULL AUTO-CLICK WILEY DOWNLOADER")
    print("=" * 80)
    print("This WILL click the Connect button automatically!")
    print("(Just needs accessibility permissions once)")
    print("=" * 80)
    
    downloader = FullAutoClickWiley()
    
    if not await downloader.initialize():
        return False
    
    # Test papers
    papers = [
        {
            'doi': '10.1002/anie.202004934',
            'title': 'Chemistry Paper - Auto Download Test'
        },
        {
            'doi': '10.1111/1467-9523.00201',
            'title': 'Economics Paper - Auto Download Test'
        }
    ]
    
    success = await downloader.full_auto_batch(papers)
    
    if success:
        print("\\n🎉 FULL AUTO-CLICK SUCCESS!")
        print("🤖 VPN: Fully automatic (even clicks Connect!)")
        print("📄 Downloads: Fully automatic")
        print("👆 Your work: Just grant permissions once")
    else:
        print("\\n❌ Auto-click needs adjustment")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())