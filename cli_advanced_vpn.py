#!/usr/bin/env python3
"""
CLI ADVANCED VPN
================

Advanced CLI automation for Cisco VPN
"""

import subprocess
import time
import os
import pexpect
from pathlib import Path

class CLIAdvancedVPN:
    """Advanced CLI-based VPN automation"""
    
    def __init__(self):
        print("🔧 ADVANCED CLI VPN AUTOMATION")
        print("=" * 50)
        self.vpn_host = "sslvpn.ethz.ch/staff-net"
        self.vpn_cli = "/opt/cisco/secureclient/bin/vpn"
    
    def check_vpn_profiles(self):
        """Check for saved VPN profiles"""
        print("\n1️⃣ CHECKING VPN PROFILES")
        
        # Check for Cisco configuration
        config_paths = [
            Path.home() / ".cisco",
            Path("/opt/cisco/secureclient/.cisco"),
            Path.home() / "Library/Preferences/com.cisco.secureclient",
            Path("/Library/Preferences/com.cisco.secureclient"),
        ]
        
        for path in config_paths:
            if path.exists():
                print(f"✅ Found config: {path}")
                # List contents
                try:
                    for item in path.iterdir():
                        print(f"   - {item.name}")
                except:
                    pass
        
        # Try to list hosts
        try:
            result = subprocess.run(
                [self.vpn_cli, "hosts"],
                capture_output=True, text=True, timeout=5
            )
            print(f"\nConfigured hosts:")
            print(result.stdout)
        except:
            pass
    
    def create_response_file(self, username, password):
        """Create response file for non-interactive connection"""
        print("\n2️⃣ CREATING RESPONSE FILE")
        
        response_content = f"""connect {self.vpn_host}
{username}
{password}
y
"""
        
        response_file = Path("vpn_response.txt")
        response_file.write_text(response_content)
        
        print(f"✅ Created {response_file}")
        return response_file
    
    def connect_with_response_file(self, response_file):
        """Connect using response file"""
        print("\n3️⃣ CONNECTING WITH RESPONSE FILE")
        
        try:
            # Use response file for non-interactive connection
            with open(response_file, 'r') as f:
                process = subprocess.Popen(
                    [self.vpn_cli, "-s"],
                    stdin=f,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Give it time to process
                time.sleep(10)
                
                # Check output
                stdout, stderr = process.communicate(timeout=30)
                print(f"Output: {stdout}")
                if stderr:
                    print(f"Errors: {stderr}")
                    
        except subprocess.TimeoutExpired:
            print("⏳ Connection in progress...")
        except Exception as e:
            print(f"❌ Response file error: {e}")
    
    def connect_with_pexpect(self, username=None, password=None):
        """Use pexpect for interactive automation"""
        print("\n4️⃣ USING PEXPECT FOR INTERACTIVE AUTOMATION")
        
        try:
            # Start VPN connection
            child = pexpect.spawn(f"{self.vpn_cli} connect {self.vpn_host}")
            child.timeout = 30
            
            # Handle prompts
            prompts = [
                ("Username:", username),
                ("Password:", password),
                ("accept?", "y"),
                ("Do you wish to continue?", "y"),
                ("Second Password:", None),  # 2FA
            ]
            
            for prompt, response in prompts:
                try:
                    index = child.expect([prompt, pexpect.EOF, pexpect.TIMEOUT], timeout=10)
                    if index == 0 and response:
                        print(f"   Responding to '{prompt}'")
                        child.sendline(response)
                    elif index == 0 and not response:
                        print(f"   Found '{prompt}' - requires manual input")
                        print("   💡 Enter 2FA code from your phone")
                except:
                    pass
            
            # Let it run
            time.sleep(5)
            
            print("✅ Interactive automation complete")
            
        except Exception as e:
            print(f"❌ Pexpect error: {e}")
    
    def direct_system_call(self):
        """Try direct system call with expect script"""
        print("\n5️⃣ USING EXPECT SCRIPT")
        
        expect_script = '''#!/usr/bin/expect -f
set timeout 30
spawn /opt/cisco/secureclient/bin/vpn connect sslvpn.ethz.ch/staff-net

expect {
    "Username:" {
        send "\\r"
        exp_continue
    }
    "Password:" {
        send "\\r"
        exp_continue
    }
    "accept?" {
        send "y\\r"
        exp_continue
    }
    timeout {
        puts "Timeout reached"
    }
    eof {
        puts "Connection process ended"
    }
}

wait
'''
        
        # Save expect script
        expect_file = Path("vpn_connect.exp")
        expect_file.write_text(expect_script)
        expect_file.chmod(0o755)
        
        print(f"✅ Created {expect_file}")
        
        # Run expect script
        try:
            subprocess.run(["expect", str(expect_file)])
        except:
            print("❌ Expect not available")
    
    def gui_with_osascript_typing(self):
        """Launch GUI and type using osascript"""
        print("\n6️⃣ GUI WITH OSASCRIPT TYPING")
        
        # Launch GUI
        subprocess.run(["open", "-a", "Cisco Secure Client"])
        time.sleep(3)
        
        # Complex AppleScript to find and click Connect
        complex_script = '''
        tell application "System Events"
            tell process "Cisco Secure Client"
                set frontmost to true
                delay 1
                
                -- Try multiple methods to find Connect
                
                -- Method 1: By button name
                try
                    click button "Connect" of window 1
                    return "Clicked by name"
                end try
                
                -- Method 2: By button index
                try
                    set buttonCount to count of buttons of window 1
                    repeat with i from 1 to buttonCount
                        set btnName to name of button i of window 1
                        if btnName contains "Connect" then
                            click button i of window 1
                            return "Clicked button " & i
                        end if
                    end repeat
                end try
                
                -- Method 3: Click at specific coordinates relative to window
                try
                    set windowPos to position of window 1
                    set windowSize to size of window 1
                    set clickX to (item 1 of windowPos) + ((item 1 of windowSize) * 0.7)
                    set clickY to (item 2 of windowPos) + ((item 2 of windowSize) * 0.5)
                    
                    do shell script "cliclick c:" & clickX & "," & clickY
                    return "Clicked at calculated position"
                end try
                
                -- Method 4: Use System Events click
                try
                    set {xPosition, yPosition} to position of window 1
                    set {xSize, ySize} to size of window 1
                    set clickPosX to xPosition + (xSize * 0.7)
                    set clickPosY to yPosition + (ySize / 2)
                    
                    click at {clickPosX, clickPosY}
                    return "Clicked with System Events"
                end try
                
                return "No method worked"
            end tell
        end tell
        '''
        
        result = subprocess.run(
            ["osascript", "-e", complex_script],
            capture_output=True, text=True
        )
        
        print(f"   AppleScript result: {result.stdout.strip()}")

def main():
    """Main advanced CLI execution"""
    
    print("🚀 ADVANCED CLI VPN AUTOMATION")
    print("=" * 60)
    
    # Check if already connected
    try:
        result = subprocess.run(
            ["/opt/cisco/secureclient/bin/vpn", "status"],
            capture_output=True, text=True, timeout=5
        )
        if "state: Connected" in result.stdout:
            print("✅ Already connected!")
            return
    except:
        pass
    
    automator = CLIAdvancedVPN()
    
    # Try all methods
    automator.check_vpn_profiles()
    
    # Method 1: Response file (if credentials available)
    # username = "your_username"
    # password = "your_password"
    # response_file = automator.create_response_file(username, password)
    # automator.connect_with_response_file(response_file)
    
    # Method 2: Pexpect
    # Install pexpect first
    try:
        import pexpect
    except:
        print("\n📦 Installing pexpect...")
        subprocess.run(["pip", "install", "pexpect"])
    
    # automator.connect_with_pexpect(username, password)
    
    # Method 3: Expect script
    automator.direct_system_call()
    
    # Method 4: GUI with advanced AppleScript
    automator.gui_with_osascript_typing()
    
    # Monitor connection
    print("\n📡 MONITORING CONNECTION...")
    
    for i in range(120):
        try:
            result = subprocess.run(
                ["/opt/cisco/secureclient/bin/vpn", "status"],
                capture_output=True, text=True, timeout=3
            )
            
            if "state: Connected" in result.stdout:
                print(f"\n🎉 VPN CONNECTED!")
                print("🏆 ADVANCED AUTOMATION SUCCESS!")
                return
                
        except:
            pass
        
        if i % 20 == 0:
            print(f"   Monitoring... {120-i}s remaining")
        
        time.sleep(1)
    
    print("\n⏸️ Connection timeout")
    print("💡 Check if manual intervention needed")

if __name__ == "__main__":
    main()