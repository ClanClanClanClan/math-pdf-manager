#!/usr/bin/env python3
"""
SIMPLE VPN CONNECT
==================

Simple approach to clicking Connect button
"""

import subprocess
import time
import pyautogui

def connect_vpn_simple():
    """Simple VPN connection"""
    
    print("🔐 SIMPLE VPN CONNECTION")
    print("=" * 50)
    
    # Check if already connected
    try:
        result = subprocess.run(
            ["/opt/cisco/secureclient/bin/vpn", "status"],
            capture_output=True, text=True, timeout=5
        )
        if "state: Connected" in result.stdout:
            print("✅ VPN already connected!")
            return True
    except:
        pass
    
    # Kill and relaunch
    print("\n1️⃣ Launching Cisco Secure Client...")
    subprocess.run(["pkill", "-f", "Cisco Secure Client"], capture_output=True)
    time.sleep(1)
    subprocess.run(["open", "-a", "Cisco Secure Client"])
    time.sleep(3)
    
    # Use simple AppleScript to activate and click
    print("\n2️⃣ Clicking Connect button...")
    
    # First, make sure window is active
    activate_script = '''
    tell application "Cisco Secure Client"
        activate
    end tell
    '''
    subprocess.run(["osascript", "-e", activate_script])
    time.sleep(1)
    
    # Method 1: Direct button click
    click_script = '''
    tell application "System Events"
        tell process "Cisco Secure Client"
            set frontmost to true
            delay 0.5
            
            -- Click the Connect button
            click button "Connect" of window 1
        end tell
    end tell
    '''
    
    result = subprocess.run(["osascript", "-e", click_script], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Clicked Connect button!")
        return True
    
    # Method 2: Try tab navigation
    print("   Trying tab navigation...")
    
    tab_script = '''
    tell application "System Events"
        tell process "Cisco Secure Client"
            set frontmost to true
            delay 0.5
            
            -- Tab to Connect button and press space
            key code 48 -- Tab
            delay 0.2
            key code 49 -- Space
        end tell
    end tell
    '''
    
    subprocess.run(["osascript", "-e", tab_script])
    
    # Method 3: Use coordinates
    print("   Trying coordinate-based click...")
    
    # Take screenshot to see what we're working with
    screenshot = pyautogui.screenshot()
    screenshot.save("cisco_window_debug.png")
    print("   Screenshot saved to cisco_window_debug.png")
    
    # Common Connect button location (center-right of window)
    # You may need to adjust these based on your screen
    pyautogui.click(x=800, y=400)  # Adjust these coordinates
    
    print("\n✅ Connection attempt complete")
    print("📱 Please complete authentication if prompted")
    
    return True

def main():
    """Test connection"""
    
    if connect_vpn_simple():
        print("\n⏳ Waiting for authentication...")
        
        # Give time for password/2FA
        for i in range(60):
            try:
                result = subprocess.run(
                    ["/opt/cisco/secureclient/bin/vpn", "status"],
                    capture_output=True, text=True, timeout=2
                )
                if "state: Connected" in result.stdout:
                    print("\n✅ VPN CONNECTED!")
                    break
            except:
                pass
            
            if i % 10 == 0:
                print(f"   Waiting... {60-i}s remaining")
            time.sleep(1)

if __name__ == "__main__":
    main()