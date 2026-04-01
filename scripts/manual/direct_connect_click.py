#!/usr/bin/env python3
"""
DIRECT CONNECT CLICK
====================

Click Connect button using exact coordinates from screenshot
"""

import subprocess
import time
import pyautogui

def click_connect_precisely():
    """Click Connect button using precise coordinates"""
    
    print("🎯 DIRECT CONNECT BUTTON CLICK")
    print("=" * 50)
    
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
    
    # Kill and restart for clean state
    subprocess.run(["pkill", "-f", "Cisco Secure Client"], capture_output=True)
    time.sleep(2)
    subprocess.run(["open", "-a", "Cisco Secure Client"])
    time.sleep(5)  # Give more time to fully load
    
    # Activate window
    print("\n2️⃣ Activating window...")
    activate_script = '''
    tell application "Cisco Secure Client"
        activate
        delay 1
    end tell
    '''
    subprocess.run(["osascript", "-e", activate_script])
    time.sleep(2)
    
    # Take screenshot for debugging
    print("\n3️⃣ Taking screenshot...")
    screenshot = pyautogui.screenshot()
    screenshot.save("connect_click_debug.png")
    print("   Screenshot saved to connect_click_debug.png")
    
    print("\n4️⃣ Clicking Connect button...")
    
    # From the previous screenshot analysis, the Connect button
    # is in the blue dialog at approximately these coordinates:
    
    # Method 1: Click at the exact "Connect" text location
    connect_coordinates = [
        (503, 173),  # Primary location from screenshot
        (480, 173),  # Slightly left
        (520, 173),  # Slightly right
        (503, 180),  # Slightly lower
        (460, 173),  # Further left
        (540, 173),  # Further right
    ]
    
    for i, (x, y) in enumerate(connect_coordinates):
        print(f"   Attempt {i+1}: Clicking at ({x}, {y})")
        
        # Slow, deliberate click
        pyautogui.moveTo(x, y, duration=0.8)
        time.sleep(0.5)
        pyautogui.click()
        time.sleep(2)
        
        # Take screenshot after each click
        after_screenshot = pyautogui.screenshot()
        after_screenshot.save(f"after_click_attempt_{i+1}.png")
        
        # Brief pause between attempts
        if i < len(connect_coordinates) - 1:
            time.sleep(1)
    
    print("\n5️⃣ Using keyboard navigation as backup...")
    
    # Make sure Cisco is still active
    subprocess.run(["osascript", "-e", 'tell application "Cisco Secure Client" to activate'])
    time.sleep(1)
    
    # Tab to button and press Enter
    pyautogui.press('tab')
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(1)
    
    # Also try Space key
    pyautogui.press('space')
    
    print("\n6️⃣ Trying AppleScript UI clicking...")
    
    # More aggressive AppleScript
    ui_click_script = '''
    tell application "System Events"
        tell process "Cisco Secure Client"
            set frontmost to true
            delay 1
            
            -- Try to find and click any button with "Connect" in name
            try
                click button "Connect" of window 1
                return "Clicked Connect button"
            end try
            
            -- Try clicking first button
            try
                click button 1 of window 1
                return "Clicked first button"
            end try
            
            -- Try clicking any UI element that might be the button
            try
                set allButtons to every UI element of window 1 whose role is "AXButton"
                if (count of allButtons) > 0 then
                    click item 1 of allButtons
                    return "Clicked UI button"
                end if
            end try
            
            return "No buttons found"
        end tell
    end tell
    '''
    
    result = subprocess.run(
        ["osascript", "-e", ui_click_script],
        capture_output=True, text=True
    )
    print(f"   AppleScript result: {result.stdout.strip()}")
    
    print("\n7️⃣ Final screenshot...")
    final_screenshot = pyautogui.screenshot()
    final_screenshot.save("connect_final_state.png")
    
    print("✅ All Connect button click attempts complete")
    
    return True

def wait_for_auth():
    """Wait for authentication and connection"""
    
    print("\n8️⃣ Waiting for authentication...")
    print("🔑 Please enter your password when prompted")
    print("📱 Then complete 2FA on your phone")
    print("-" * 50)
    
    # Monitor connection status
    for i in range(180):  # 3 minute timeout
        try:
            result = subprocess.run(
                ["/opt/cisco/secureclient/bin/vpn", "status"],
                capture_output=True, text=True, timeout=3
            )
            
            status_lines = result.stdout.strip().split('\n')
            for line in status_lines:
                if "state:" in line:
                    state = line.split("state:")[-1].strip()
                    if i % 30 == 0:  # Print status every 30 seconds
                        print(f"   VPN Status: {state}")
                    
                    if "Connected" in state:
                        print(f"\n🎉 VPN CONNECTED! ({state})")
                        return True
        except:
            pass
        
        if i % 30 == 0 and i > 0:
            print(f"   Still waiting... {180-i}s remaining")
        
        time.sleep(1)
    
    print("\n⏸️ Authentication timeout")
    print("💡 Check if VPN connected manually")
    return False

def main():
    """Main execution"""
    
    success = click_connect_precisely()
    
    if success:
        connected = wait_for_auth()
        
        if connected:
            print("\n🚀 SUCCESS! VPN automation working!")
            print("✅ Connect button clicked successfully")
            print("✅ VPN connection established")
            print("\n📁 Check these debug files:")
            print("   - connect_click_debug.png")
            print("   - after_click_attempt_*.png") 
            print("   - connect_final_state.png")
        else:
            print("\n⚠️ Connect button clicked but VPN not confirmed")
            print("Check debug screenshots to see what happened")
    
    print("\n🎯 Direct clicking complete!")

if __name__ == "__main__":
    main()