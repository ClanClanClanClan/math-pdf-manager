#!/usr/bin/env python3
"""
SIMPLE BULLETPROOF CONNECT
==========================

Simplified but bulletproof Connect button clicking
"""

import subprocess
import time
import pyautogui
from secure_vpn_credentials import get_vpn_password

def simple_bulletproof_connect():
    """Simple but reliable Connect button clicking"""
    
    print("🎯 SIMPLE BULLETPROOF CONNECT")
    print("=" * 50)
    
    # Get password
    password = get_vpn_password()
    if password:
        print("✅ Password loaded")
    
    # Kill and launch Cisco
    print("\n1️⃣ Launching Cisco...")
    subprocess.run(["pkill", "-9", "-f", "Cisco"], capture_output=True)
    time.sleep(2)
    subprocess.run(["open", "-a", "Cisco Secure Client"])
    time.sleep(4)
    
    # Activate window
    subprocess.run(["osascript", "-e", 'tell application "Cisco Secure Client" to activate'])
    time.sleep(2)
    
    print("\n2️⃣ Clicking Connect button...")
    
    # Known working positions for Connect button
    # Based on the blue dialog we saw in screenshots
    connect_positions = [
        (484, 173),   # Primary position from screenshot
        (490, 173),   # Slightly right
        (478, 173),   # Slightly left
        (484, 170),   # Slightly up
        (484, 176),   # Slightly down
    ]
    
    # Click all positions
    for i, (x, y) in enumerate(connect_positions):
        print(f"   Click {i+1}: ({x}, {y})")
        
        # Use cliclick for reliable clicking
        try:
            subprocess.run(["cliclick", f"c:{x},{y}"])
        except:
            # Fallback to pyautogui
            pyautogui.click(x, y)
        
        time.sleep(0.5)
    
    # Also try keyboard
    print("\n3️⃣ Keyboard navigation...")
    pyautogui.press('tab')
    time.sleep(0.3)
    pyautogui.press('enter')
    
    print("\n4️⃣ Waiting for password prompt...")
    time.sleep(3)
    
    if password:
        print("5️⃣ Entering password...")
        # Clear field
        pyautogui.hotkey('cmd', 'a')
        pyautogui.press('delete')
        
        # Type password
        pyautogui.typewrite(password, interval=0.05)
        pyautogui.press('enter')
        
        print("✅ Password entered")
    
    print("\n6️⃣ Waiting for 2FA...")
    print("📱 Please enter 2FA code from your phone")
    
    # Monitor connection
    for i in range(120):
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
        
        if i % 20 == 0:
            print(f"   Waiting... {120-i}s")
        
        time.sleep(1)
    
    return False

def main():
    """Main execution"""
    
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
    
    # Run simple bulletproof connection
    success = simple_bulletproof_connect()
    
    if success:
        print("\n🏆 SUCCESS!")
        print("✅ VPN connected")
        print("✅ Password was auto-filled")
        print("📄 Ready for PDF downloads!")
    else:
        print("\n⚠️ Connection timeout")
        print("Check if 2FA was entered")

if __name__ == "__main__":
    main()