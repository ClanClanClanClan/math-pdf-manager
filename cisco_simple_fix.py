#!/usr/bin/env python3
"""
CISCO SIMPLE FIX
================

Simple, reliable Cisco Connect button click
"""

import subprocess
import time
import pyautogui

def launch_and_click_connect():
    """Launch Cisco and click Connect"""
    
    print("🔐 CISCO VPN CONNECTION")
    print("=" * 40)
    
    # Check if already connected
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
    
    print("\n1️⃣ Launching Cisco Secure Client...")
    
    # Kill existing and launch fresh
    subprocess.run(["pkill", "-f", "Cisco Secure Client"], capture_output=True)
    time.sleep(2)
    subprocess.run(["open", "-a", "Cisco Secure Client"])
    time.sleep(4)  # Give it more time to load
    
    print("\n2️⃣ Bringing to front...")
    
    # Activate window using AppleScript
    activate_script = '''
    tell application "Cisco Secure Client"
        activate
    end tell
    '''
    subprocess.run(["osascript", "-e", activate_script])
    time.sleep(2)
    
    print("\n3️⃣ Taking screenshot for debugging...")
    screenshot = pyautogui.screenshot()
    screenshot.save("cisco_before_click.png")
    print("   Saved to cisco_before_click.png")
    
    print("\n4️⃣ Attempting to click Connect...")
    
    # Method 1: Use pyautogui to find and click
    try:
        # Look for common button locations
        screen_width, screen_height = pyautogui.size()
        
        # Try center-right area where Connect usually is
        possible_locations = [
            (screen_width * 0.6, screen_height * 0.4),  # Upper center-right
            (screen_width * 0.6, screen_height * 0.5),  # Middle center-right
            (screen_width * 0.7, screen_height * 0.4),  # Right area
            (screen_width * 0.5, screen_height * 0.6),  # Lower center
        ]
        
        for i, (x, y) in enumerate(possible_locations):
            print(f"   Trying location {i+1}: ({x:.0f}, {y:.0f})")
            pyautogui.click(x, y)
            time.sleep(1)
    
    except Exception as e:
        print(f"   pyautogui error: {e}")
    
    # Method 2: Use AppleScript with better error handling
    print("\n5️⃣ Using AppleScript...")
    
    click_scripts = [
        # Try by button name
        '''
        tell application "System Events"
            tell process "Cisco Secure Client"
                set frontmost to true
                delay 1
                click button "Connect" of window 1
            end tell
        end tell
        ''',
        
        # Try first button
        '''
        tell application "System Events"
            tell process "Cisco Secure Client"
                set frontmost to true
                delay 1
                click button 1 of window 1
            end tell
        end tell
        ''',
        
        # Try with UI elements
        '''
        tell application "System Events"
            tell process "Cisco Secure Client"
                set frontmost to true
                delay 1
                set allButtons to every button of window 1
                if (count of allButtons) > 0 then
                    click item 1 of allButtons
                end if
            end tell
        end tell
        '''
    ]
    
    for i, script in enumerate(click_scripts):
        print(f"   AppleScript attempt {i+1}...")
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            print(f"   ✅ AppleScript {i+1} succeeded")
            break
        else:
            print(f"   ❌ AppleScript {i+1} failed: {result.stderr}")
    
    # Method 3: Keyboard navigation
    print("\n6️⃣ Using keyboard navigation...")
    
    # Make sure window is active
    pyautogui.press('cmd')  # Ensure we're in the app
    time.sleep(0.5)
    
    # Tab to button and press Enter
    pyautogui.press('tab')
    time.sleep(0.5)
    pyautogui.press('enter')
    
    print("✅ Pressed Enter on focused element")
    
    # Give some time for the click to register
    time.sleep(3)
    
    # Take another screenshot
    screenshot_after = pyautogui.screenshot()
    screenshot_after.save("cisco_after_click.png")
    print("   Saved after screenshot to cisco_after_click.png")
    
    return True

def wait_for_auth():
    """Wait for authentication"""
    
    print("\n7️⃣ Waiting for authentication...")
    print("   Enter password and complete 2FA")
    
    # Monitor for connection
    for i in range(120):  # 2 minute timeout
        try:
            result = subprocess.run(
                ["/opt/cisco/secureclient/bin/vpn", "status"],
                capture_output=True, text=True
            )
            if "state: Connected" in result.stdout:
                print("\n✅ VPN CONNECTED!")
                return True
        except:
            pass
        
        if i % 10 == 0:
            print(f"   Waiting... {120-i}s remaining")
        time.sleep(1)
    
    print("\n⏸️ Timeout - but connection may still be in progress")
    return False

def main():
    """Main execution"""
    
    success = launch_and_click_connect()
    
    if success:
        wait_for_auth()
    
    print("\n📊 Debug info:")
    print("   Check cisco_before_click.png and cisco_after_click.png")
    print("   to see what happened")

if __name__ == "__main__":
    main()