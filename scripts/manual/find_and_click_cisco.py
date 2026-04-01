#!/usr/bin/env python3
"""
FIND AND CLICK CISCO
===================

Actually find the Cisco window and click Connect
"""

import subprocess
import time
import pyautogui
import Quartz

def find_cisco_window():
    """Find the actual Cisco Secure Client window"""
    
    print("🔍 FINDING CISCO WINDOW")
    print("=" * 30)
    
    # Get all windows on screen
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID
    )
    
    cisco_windows = []
    
    for window in window_list:
        owner_name = window.get('kCGWindowOwnerName', '')
        window_name = window.get('kCGWindowName', '')
        
        if 'Cisco' in owner_name or 'Cisco' in window_name:
            bounds = window.get('kCGWindowBounds', {})
            
            cisco_window = {
                'owner': owner_name,
                'name': window_name,
                'x': int(bounds.get('X', 0)),
                'y': int(bounds.get('Y', 0)),
                'width': int(bounds.get('Width', 0)),
                'height': int(bounds.get('Height', 0)),
                'layer': window.get('kCGWindowLayer', 0)
            }
            
            cisco_windows.append(cisco_window)
            print(f"Found Cisco window: {cisco_window}")
    
    if not cisco_windows:
        print("❌ No Cisco windows found!")
        return None
    
    # Find the main Cisco window (usually the one with the largest area)
    main_window = max(cisco_windows, key=lambda w: w['width'] * w['height'])
    print(f"✅ Main Cisco window: {main_window}")
    
    return main_window

def launch_cisco_properly():
    """Launch Cisco and wait for it to appear"""
    
    print("\n🚀 LAUNCHING CISCO SECURE CLIENT")
    print("=" * 40)
    
    # Kill any existing Cisco processes
    print("1️⃣ Killing existing Cisco processes...")
    subprocess.run(["pkill", "-f", "Cisco"], capture_output=True)
    time.sleep(2)
    
    # Launch Cisco
    print("2️⃣ Starting Cisco Secure Client...")
    subprocess.run(["open", "-a", "Cisco Secure Client"])
    
    # Wait for window to appear and find it
    print("3️⃣ Waiting for Cisco window to appear...")
    
    cisco_window = None
    for attempt in range(15):  # Wait up to 15 seconds
        time.sleep(1)
        cisco_window = find_cisco_window()
        if cisco_window:
            break
        print(f"   Attempt {attempt + 1}: Still waiting...")
    
    if not cisco_window:
        print("❌ Cisco window never appeared!")
        return None
    
    print(f"✅ Cisco window found after {attempt + 1} seconds")
    return cisco_window

def click_connect_in_window(cisco_window):
    """Click Connect button within the Cisco window"""
    
    print(f"\n🖱️ CLICKING CONNECT IN CISCO WINDOW")
    print("=" * 40)
    
    window_x = cisco_window['x']
    window_y = cisco_window['y']
    window_width = cisco_window['width']
    window_height = cisco_window['height']
    
    print(f"Window bounds: ({window_x}, {window_y}) {window_width}x{window_height}")
    
    # First, make sure the window is active
    print("1️⃣ Activating Cisco window...")
    
    # Click on the window to focus it
    center_x = window_x + window_width // 2
    center_y = window_y + window_height // 2
    pyautogui.click(center_x, center_y)
    time.sleep(1)
    
    # Also use AppleScript to activate
    activate_script = '''
    tell application "Cisco Secure Client"
        activate
    end tell
    '''
    subprocess.run(["osascript", "-e", activate_script])
    time.sleep(1)
    
    # Take screenshot of just the Cisco window area
    print("2️⃣ Taking screenshot of Cisco window...")
    
    # Capture the specific window area
    cisco_screenshot = pyautogui.screenshot(region=(
        window_x, 
        window_y, 
        window_width, 
        window_height
    ))
    cisco_screenshot.save("cisco_window_only.png")
    print("   Saved cisco_window_only.png")
    
    print("3️⃣ Attempting to click Connect button...")
    
    # The Connect button is typically in the center-right area of Cisco dialogs
    # Try multiple positions within the window
    
    connect_positions = [
        # Relative positions within the window
        (window_width * 0.7, window_height * 0.5),   # Center-right
        (window_width * 0.6, window_height * 0.5),   # Center
        (window_width * 0.8, window_height * 0.5),   # Far right
        (window_width * 0.7, window_height * 0.4),   # Upper center-right
        (window_width * 0.7, window_height * 0.6),   # Lower center-right
    ]
    
    for i, (rel_x, rel_y) in enumerate(connect_positions):
        # Convert relative position to absolute screen coordinates
        abs_x = window_x + int(rel_x)
        abs_y = window_y + int(rel_y)
        
        print(f"   Attempt {i+1}: Clicking at ({abs_x}, {abs_y})")
        
        # Move mouse and click
        pyautogui.moveTo(abs_x, abs_y, duration=0.5)
        time.sleep(0.3)
        pyautogui.click()
        time.sleep(1)
        
        # Take screenshot after click
        after_click = pyautogui.screenshot()
        after_click.save(f"after_click_{i+1}.png")
    
    print("4️⃣ Using keyboard navigation...")
    
    # Make sure Cisco is still focused
    pyautogui.click(center_x, center_y)
    time.sleep(0.5)
    
    # Use Tab and Enter
    pyautogui.press('tab')
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(0.5)
    pyautogui.press('space')  # Also try space
    
    print("✅ All clicking attempts completed")

def monitor_vpn_connection():
    """Monitor VPN status"""
    
    print(f"\n📡 MONITORING VPN CONNECTION")
    print("=" * 40)
    print("🔑 Enter your password when prompted")
    print("📱 Complete 2FA on your phone")
    print("-" * 40)
    
    for i in range(120):
        try:
            result = subprocess.run(
                ["/opt/cisco/secureclient/bin/vpn", "status"],
                capture_output=True, text=True, timeout=3
            )
            
            if "state: Connected" in result.stdout:
                print(f"\n🎉 SUCCESS! VPN CONNECTED!")
                return True
            elif "state: Connecting" in result.stdout:
                if i % 15 == 0:
                    print(f"   Status: Connecting... ({120-i}s remaining)")
        except:
            pass
        
        time.sleep(1)
    
    print(f"\n⏸️ Connection timeout")
    return False

def main():
    """Main execution with proper window finding"""
    
    print("🎯 FIND AND CLICK CISCO CONNECT")
    print("=" * 50)
    
    # Step 1: Launch and find Cisco window
    cisco_window = launch_cisco_properly()
    
    if not cisco_window:
        print("❌ Failed to find Cisco window")
        return
    
    # Step 2: Click Connect within the window
    click_connect_in_window(cisco_window)
    
    # Step 3: Monitor connection status
    success = monitor_vpn_connection()
    
    if success:
        print("\n🏆 COMPLETE SUCCESS!")
        print("✅ Found Cisco window correctly")
        print("✅ Clicked Connect button")
        print("✅ VPN connection established")
    else:
        print("\n⚠️ Check debug screenshots:")
        print("   - cisco_window_only.png")
        print("   - after_click_*.png")
    
    print("\n🎯 Window-based clicking complete!")

if __name__ == "__main__":
    main()