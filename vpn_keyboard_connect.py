#!/usr/bin/env python3
"""
VPN KEYBOARD CONNECT
====================

Use keyboard shortcuts to connect
"""

import subprocess
import time
import pyautogui

def keyboard_connect():
    """Connect using keyboard navigation"""
    
    print("⌨️ VPN CONNECTION WITH KEYBOARD")
    print("=" * 50)
    
    # Launch Cisco
    print("\n1️⃣ Launching Cisco...")
    subprocess.run(["open", "-a", "Cisco Secure Client"])
    time.sleep(3)
    
    # Activate window
    subprocess.run([
        "osascript", "-e", 
        'tell application "Cisco Secure Client" to activate'
    ])
    time.sleep(1)
    
    print("\n2️⃣ Using keyboard to navigate...")
    
    # Press Tab to focus on Connect button (usually first button)
    pyautogui.press('tab')
    time.sleep(0.5)
    
    # Press Enter/Space to click Connect
    pyautogui.press('enter')
    
    print("✅ Pressed Enter on Connect button")
    
    # Wait for password field
    time.sleep(2)
    
    print("\n3️⃣ Ready for password entry")
    print("   Type your password and press Enter")
    print("   Then complete 2FA on your phone")
    
    # Optional: Auto-type password
    # password = "your_password"
    # pyautogui.typewrite(password)
    # pyautogui.press('enter')

def main():
    keyboard_connect()
    
    print("\n⏳ Monitoring connection status...")
    
    # Monitor status
    connected = False
    for i in range(60):
        try:
            result = subprocess.run(
                ["/opt/cisco/secureclient/bin/vpn", "status"],
                capture_output=True, text=True
            )
            if "state: Connected" in result.stdout:
                print("\n✅ VPN CONNECTED!")
                connected = True
                break
        except:
            pass
        
        time.sleep(1)
        if i % 5 == 0:
            print(f"   {60-i}s remaining...")
    
    if not connected:
        print("\n❌ Connection timeout")
        print("💡 Try running again or connect manually")

if __name__ == "__main__":
    main()