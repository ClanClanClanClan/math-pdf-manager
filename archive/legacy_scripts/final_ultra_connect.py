#!/usr/bin/env python3
"""
FINAL ULTRA CONNECT
===================

The ultimate Connect button solution
"""

import subprocess
import time
from secure_vpn_credentials import get_vpn_password

def final_ultra_connect():
    """Final ultra-reliable Connect clicking"""
    
    print("🚀 FINAL ULTRA CONNECT")
    print("=" * 50)
    
    # Get password
    password = get_vpn_password()
    
    # Kill and launch
    print("\n1️⃣ Launching Cisco fresh...")
    subprocess.run(["pkill", "-9", "-f", "Cisco"], capture_output=True)
    time.sleep(2)
    subprocess.run(["open", "-a", "Cisco Secure Client"])
    time.sleep(5)  # Give more time
    
    print("\n2️⃣ Using comprehensive AppleScript...")
    
    # Comprehensive AppleScript that tries everything
    connect_script = '''
    tell application "Cisco Secure Client"
        activate
        delay 2
    end tell
    
    tell application "System Events"
        tell process "Cisco Secure Client"
            set frontmost to true
            delay 1
            
            -- Method 1: Direct button click
            try
                click button "Connect" of window 1
                delay 1
            end try
            
            -- Method 2: Click first button
            try
                click button 1 of window 1
                delay 1
            end try
            
            -- Method 3: Tab and Enter
            key code 48 -- Tab
            delay 0.5
            key code 36 -- Return
            delay 1
            
            -- Method 4: Click at Connect button coordinates
            do shell script "cliclick c:484,173"
            delay 0.5
            do shell script "cliclick c:490,173"
            delay 0.5
            
            -- Method 5: Space key
            key code 49 -- Space
        end tell
    end tell
    '''
    
    subprocess.run(["osascript", "-e", connect_script])
    
    print("✅ All Connect methods executed")
    
    # Wait and enter password
    print("\n3️⃣ Waiting for password field...")
    time.sleep(4)
    
    if password:
        print("4️⃣ Entering password...")
        
        password_script = f'''
        tell application "System Events"
            -- Clear field
            key code 0 using {{command down}} -- Cmd+A
            delay 0.2
            key code 51 -- Delete
            delay 0.2
            
            -- Type password
            keystroke "{password}"
            delay 0.5
            
            -- Press Enter
            key code 36 -- Return
        end tell
        '''
        
        subprocess.run(["osascript", "-e", password_script])
        print("✅ Password entered")
    
    print("\n5️⃣ Waiting for 2FA...")
    print("📱 Enter code from your authenticator app")
    
    # Monitor
    for i in range(180):
        try:
            result = subprocess.run(
                ["/opt/cisco/secureclient/bin/vpn", "status"],
                capture_output=True, text=True, timeout=3
            )
            
            if "state: Connected" in result.stdout:
                print(f"\n🎉 VPN CONNECTED!")
                return True
        except:
            pass
        
        if i == 30:
            print("💡 Make sure you entered the 2FA code")
        elif i == 60:
            print("💡 Still waiting for connection...")
        elif i == 120:
            print("💡 Check if Cisco window is open")
        
        time.sleep(1)
    
    return False

def main():
    # Check status
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
    
    # Install cliclick if needed
    try:
        subprocess.run(["which", "cliclick"], check=True, capture_output=True)
    except:
        print("Installing cliclick...")
        subprocess.run(["brew", "install", "cliclick"])
    
    # Run connection
    success = final_ultra_connect()
    
    if success:
        print("\n🏆 FINAL SUCCESS!")
        print("The ultra-robust system worked!")
        
        # Now run PDF downloads
        print("\n📄 Ready to download PDFs!")
        print("Run: python download_pdfs_with_vpn.py")
    else:
        print("\n⚠️ Connection not confirmed")
        print("But VPN might still be connecting")

if __name__ == "__main__":
    main()