#!/usr/bin/env python3
"""
CISCO CONNECT - PROPERLY FIXED
==============================

Actually click the Connect button
"""

import subprocess
import time
import pyautogui
import Quartz
from AppKit import NSWorkspace, NSApplicationActivateIgnoringOtherApps

def get_cisco_window_info():
    """Get Cisco window position and size"""
    # Get all windows
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID
    )
    
    for window in window_list:
        if window.get('kCGWindowOwnerName') == 'Cisco Secure Client':
            bounds = window.get('kCGWindowBounds', {})
            return {
                'x': bounds.get('X', 0),
                'y': bounds.get('Y', 0),
                'width': bounds.get('Width', 0),
                'height': bounds.get('Height', 0)
            }
    return None

def click_connect_properly():
    """Properly click the Connect button"""
    
    print("🔐 CISCO CONNECT - FIXED VERSION")
    print("=" * 50)
    
    # Check current status first
    try:
        result = subprocess.run(
            ["/opt/cisco/secureclient/bin/vpn", "status"],
            capture_output=True, text=True, timeout=5
        )
        if "state: Connected" in result.stdout:
            print("✅ Already connected!")
            return True
    except:
        pass
    
    # Kill and restart Cisco
    print("\n1️⃣ Launching Cisco Secure Client...")
    subprocess.run(["pkill", "-f", "Cisco Secure Client"], capture_output=True)
    time.sleep(2)
    
    # Launch using NSWorkspace for better control
    workspace = NSWorkspace.sharedWorkspace()
    app_path = "/Applications/Cisco/Cisco Secure Client.app"
    workspace.launchApplication_activate_identifier_(
        app_path, 
        NSApplicationActivateIgnoringOtherApps, 
        "com.cisco.Cisco-Secure-Client"
    )
    time.sleep(3)
    
    # Get window position
    window_info = get_cisco_window_info()
    if not window_info:
        print("❌ Could not find Cisco window")
        return False
    
    print(f"✅ Found Cisco window at ({window_info['x']}, {window_info['y']})")
    
    # Method 1: Click using relative position
    # Connect button is typically in the middle-right area
    connect_x = window_info['x'] + window_info['width'] * 0.7
    connect_y = window_info['y'] + window_info['height'] * 0.5
    
    print(f"\n2️⃣ Clicking Connect at ({connect_x:.0f}, {connect_y:.0f})...")
    
    # Move mouse and click
    pyautogui.moveTo(connect_x, connect_y, duration=0.5)
    time.sleep(0.5)
    pyautogui.click()
    
    print("✅ Clicked at Connect button location")
    
    # Alternative: Use accessibility API
    print("\n3️⃣ Trying accessibility click...")
    
    accessibility_script = '''
    tell application "System Events"
        tell process "Cisco Secure Client"
            set frontmost to true
            delay 1
            
            -- Find and click Connect button
            repeat with w in windows
                repeat with b in buttons of w
                    if name of b contains "Connect" then
                        click b
                        return "Clicked " & name of b
                    end if
                end repeat
            end repeat
            
            -- If not found, click first button (often Connect)
            if exists button 1 of window 1 then
                click button 1 of window 1
                return "Clicked first button"
            end if
        end tell
    end tell
    '''
    
    result = subprocess.run(
        ["osascript", "-e", accessibility_script],
        capture_output=True, text=True
    )
    
    if result.stdout:
        print(f"✅ {result.stdout.strip()}")
    
    return True

def enter_credentials(password=None):
    """Enter credentials when prompted"""
    
    print("\n4️⃣ Waiting for credential prompt...")
    time.sleep(3)
    
    if password:
        print("🔑 Entering password...")
        # Clear field first
        pyautogui.hotkey('cmd', 'a')
        pyautogui.press('delete')
        # Type password
        pyautogui.typewrite(password, interval=0.05)
        pyautogui.press('enter')
        print("✅ Password entered")
    else:
        print("⏸️ Enter password manually")

def handle_2fa_smartly():
    """Smart 2FA handling"""
    
    print("\n5️⃣ 2FA HANDLING")
    print("-" * 40)
    
    # Option 1: Check if phone is connected via USB
    usb_check = subprocess.run(
        ["system_profiler", "SPUSBDataType"],
        capture_output=True, text=True
    )
    
    if "iPhone" in usb_check.stdout or "Android" in usb_check.stdout:
        print("📱 Phone detected via USB!")
        print("   Run: scrcpy")
        print("   Then use OCR to read 2FA code")
    else:
        print("📱 Options for 2FA:")
        print("   1. Type code from authenticator app")
        print("   2. Connect phone via USB and run: scrcpy")
        print("   3. Use notification mirroring (Pushbullet)")
    
    print("\n⏳ Waiting for 2FA completion...")

def main():
    """Main execution"""
    
    # Click Connect
    if click_connect_properly():
        # Enter password (set to None for manual entry)
        password = None  # Set your password here if desired
        enter_credentials(password)
        
        # Handle 2FA
        handle_2fa_smartly()
        
        # Monitor connection
        print("\n⏳ Monitoring connection...")
        for i in range(60):
            try:
                result = subprocess.run(
                    ["/opt/cisco/secureclient/bin/vpn", "status"],
                    capture_output=True, text=True
                )
                if "state: Connected" in result.stdout:
                    print("\n✅ VPN CONNECTED SUCCESSFULLY!")
                    return True
            except:
                pass
            
            if i % 5 == 0:
                print(f"   Waiting... {60-i}s")
            time.sleep(1)
    
    print("\n❌ Connection failed")
    print("💡 Try running with debug: python debug_cisco_window.py")

if __name__ == "__main__":
    main()