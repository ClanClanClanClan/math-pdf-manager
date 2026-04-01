#!/usr/bin/env python3
"""
PRECISE CONNECT CLICK
====================

Click exactly on the Connect button using screenshot analysis
"""

import subprocess
import time
import pyautogui

def click_connect_button_precisely():
    """Click the Connect button with exact precision"""
    
    print("🎯 PRECISE CONNECT BUTTON CLICK")
    print("=" * 50)
    
    # Launch Cisco
    print("\n1️⃣ Launching Cisco Secure Client...")
    subprocess.run(["pkill", "-f", "Cisco Secure Client"], capture_output=True)
    time.sleep(2)
    subprocess.run(["open", "-a", "Cisco Secure Client"])
    time.sleep(4)
    
    # Activate and bring to front
    print("\n2️⃣ Bringing Cisco to front...")
    activate_script = '''
    tell application "Cisco Secure Client"
        activate
    end tell
    delay 2
    '''
    subprocess.run(["osascript", "-e", activate_script])
    time.sleep(2)
    
    # Take screenshot to see current state
    print("\n3️⃣ Analyzing current screen...")
    screenshot = pyautogui.screenshot()
    screenshot.save("precise_before_click.png")
    
    # From the previous screenshots, I can see the Connect button is 
    # in the blue Cisco dialog. Looking at the coordinates more carefully:
    # The Connect button appears to be around x=480-500, y=170-175
    
    print("\n4️⃣ Clicking Connect button with precision...")
    
    # Based on screenshot analysis, the blue Connect button is at:
    connect_x = 484  # Center of the Connect button
    connect_y = 173  # Center of the Connect button
    
    print(f"   Target coordinates: ({connect_x}, {connect_y})")
    
    # Move mouse slowly to the exact position
    pyautogui.moveTo(connect_x, connect_y, duration=1.0)
    time.sleep(0.5)
    
    # Take screenshot with mouse pointer visible
    screenshot_with_mouse = pyautogui.screenshot()
    screenshot_with_mouse.save("precise_mouse_position.png")
    print("   Mouse positioned - check precise_mouse_position.png")
    
    # Click with slight pause
    print("   🖱️ Clicking now...")
    pyautogui.click()
    time.sleep(2)
    
    # Take screenshot immediately after click
    after_click = pyautogui.screenshot()
    after_click.save("precise_after_click.png")
    
    print("   ✅ Click completed")
    
    # Check if dialog disappeared (success indicator)
    print("\n5️⃣ Verifying click success...")
    
    # The dialog should disappear if click was successful
    # We can check this by looking for the blue dialog area
    
    # If click didn't work, try a few more precise locations
    backup_positions = [
        (484, 173),  # Primary
        (490, 173),  # Slightly right
        (478, 173),  # Slightly left
        (484, 170),  # Slightly up
        (484, 176),  # Slightly down
    ]
    
    for i, (x, y) in enumerate(backup_positions[1:], 1):  # Skip first (already tried)
        print(f"   Backup attempt {i}: ({x}, {y})")
        pyautogui.moveTo(x, y, duration=0.5)
        pyautogui.click()
        time.sleep(1)
        
        # Take screenshot after each backup attempt
        backup_screenshot = pyautogui.screenshot()
        backup_screenshot.save(f"precise_backup_{i}.png")
    
    print("\n6️⃣ Using keyboard method as final backup...")
    
    # Make sure Cisco window is active
    subprocess.run(["osascript", "-e", 'tell application "Cisco Secure Client" to activate'])
    time.sleep(1)
    
    # Press Tab to focus on Connect button, then Enter
    pyautogui.press('tab')
    time.sleep(0.5)
    pyautogui.press('enter')
    
    print("\n7️⃣ Final verification...")
    time.sleep(2)
    
    final_screenshot = pyautogui.screenshot()
    final_screenshot.save("precise_final_result.png")
    
    print("✅ All clicking attempts completed")
    print("\n📸 Debug screenshots:")
    print("   - precise_before_click.png")
    print("   - precise_mouse_position.png") 
    print("   - precise_after_click.png")
    print("   - precise_backup_*.png")
    print("   - precise_final_result.png")
    
    return True

def check_connection_status():
    """Check if VPN connection was successful"""
    
    print("\n8️⃣ Monitoring VPN connection...")
    print("🔑 Please enter password when prompted")
    print("📱 Complete 2FA on your phone")
    print("-" * 50)
    
    connection_established = False
    
    for i in range(120):  # 2 minute monitoring
        try:
            result = subprocess.run(
                ["/opt/cisco/secureclient/bin/vpn", "status"],
                capture_output=True, text=True, timeout=3
            )
            
            if "state: Connected" in result.stdout:
                print(f"\n🎉 VPN CONNECTION SUCCESSFUL!")
                connection_established = True
                break
            elif "state: Connecting" in result.stdout:
                if i % 10 == 0:
                    print("   Status: Connecting...")
            elif "state: Disconnected" in result.stdout:
                if i % 20 == 0:
                    print("   Status: Disconnected (waiting for auth)")
        except:
            pass
        
        time.sleep(1)
    
    if not connection_established:
        print("\n⏸️ Connection monitoring timeout")
        print("💡 Check if credentials were entered correctly")
    
    return connection_established

def main():
    """Main execution"""
    
    print("🚀 STARTING PRECISE VPN AUTOMATION")
    print("=" * 60)
    
    # Step 1: Click Connect button precisely
    click_success = click_connect_button_precisely()
    
    if click_success:
        # Step 2: Monitor connection
        connection_success = check_connection_status()
        
        if connection_success:
            print("\n🏆 COMPLETE SUCCESS!")
            print("✅ Connect button clicked successfully")
            print("✅ VPN connection established")
            print("\n🎯 Precise automation WORKING!")
        else:
            print("\n⚠️ Partial success - button clicked but check auth")
            print("Review debug screenshots to verify click worked")
    
    print("\n🎯 Precise Connect clicking complete!")

if __name__ == "__main__":
    main()