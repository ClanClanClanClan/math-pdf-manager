#!/usr/bin/env python3
"""
ACTUALLY CLICK CONNECT
======================

Directly click the Connect button using coordinates
"""

import subprocess
import time
import pyautogui
import cv2
import numpy as np
from PIL import Image

def find_connect_button():
    """Find the Connect button on screen"""
    
    print("🔍 FINDING CONNECT BUTTON")
    print("=" * 40)
    
    # Take screenshot
    screenshot = pyautogui.screenshot()
    screenshot.save("current_screen.png")
    
    # Convert to OpenCV format
    screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    # Look for the blue Connect button
    # The button appears to be blue in the Cisco window
    hsv = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2HSV)
    
    # Blue color range for Connect button
    lower_blue = np.array([100, 50, 50])
    upper_blue = np.array([130, 255, 255])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    connect_buttons = []
    
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # Button-like dimensions
        if 50 < w < 150 and 20 < h < 50:
            center_x = x + w // 2
            center_y = y + h // 2
            
            # Check if this area might contain "Connect" text
            button_area = screenshot.crop((x, y, x + w, y + h))
            button_area.save(f"button_candidate_{len(connect_buttons)}.png")
            
            connect_buttons.append({
                'x': center_x,
                'y': center_y,
                'width': w,
                'height': h,
                'area': w * h
            })
    
    print(f"Found {len(connect_buttons)} potential Connect buttons")
    for i, btn in enumerate(connect_buttons):
        print(f"  Button {i}: ({btn['x']}, {btn['y']}) size {btn['width']}x{btn['height']}")
    
    return connect_buttons

def click_connect_directly():
    """Directly click the Connect button"""
    
    print("🔐 ACTUALLY CLICKING CONNECT")
    print("=" * 40)
    
    # Launch Cisco
    print("\n1️⃣ Launching Cisco...")
    subprocess.run(["pkill", "-f", "Cisco Secure Client"], capture_output=True)
    time.sleep(2)
    subprocess.run(["open", "-a", "Cisco Secure Client"])
    time.sleep(4)
    
    # Activate
    activate_script = '''
    tell application "Cisco Secure Client"
        activate
    end tell
    '''
    subprocess.run(["osascript", "-e", activate_script])
    time.sleep(2)
    
    print("\n2️⃣ Taking screenshot...")
    screenshot = pyautogui.screenshot()
    screenshot.save("cisco_ready.png")
    
    # Based on the previous screenshot, the Connect button appears to be
    # in the blue dialog box, roughly at these coordinates:
    screen_width, screen_height = pyautogui.size()
    
    # From the screenshot, the Connect button is approximately:
    # - In a blue dialog in the center-right area
    # - The dialog appears to be around x=400-500, y=170-180
    
    # Try multiple likely positions
    click_positions = [
        (503, 174),  # Exact position from screenshot analysis
        (480, 174),  # Slightly left
        (520, 174),  # Slightly right
        (503, 180),  # Slightly down
        (503, 168),  # Slightly up
    ]
    
    print("\n3️⃣ Clicking Connect button positions...")
    
    for i, (x, y) in enumerate(click_positions):
        print(f"   Attempt {i+1}: Clicking at ({x}, {y})")
        
        # Move mouse to position
        pyautogui.moveTo(x, y, duration=0.5)
        time.sleep(0.2)
        
        # Click
        pyautogui.click()
        time.sleep(1)
        
        # Check if dialog disappeared (success indicator)
        new_screenshot = pyautogui.screenshot()
        new_screenshot.save(f"after_click_{i+1}.png")
        
        # Simple check: if the blue area is gone, we probably succeeded
        if i == 0:  # First attempt
            original = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            current = cv2.cvtColor(np.array(new_screenshot), cv2.COLOR_RGB2BGR)
            
            # Look for significant change in the dialog area
            dialog_area = original[150:200, 350:550]  # Approximate dialog area
            current_area = current[150:200, 350:550]
            
            diff = cv2.absdiff(dialog_area, current_area)
            change_amount = np.sum(diff)
            
            print(f"   Change detected: {change_amount}")
            
            if change_amount > 100000:  # Significant change
                print("   ✅ Dialog changed - likely successful!")
                break
    
    print("\n4️⃣ Using keyboard method as backup...")
    
    # Keyboard method
    pyautogui.press('tab')
    time.sleep(0.5)
    pyautogui.press('enter')
    
    print("\n5️⃣ Final screenshot...")
    final_screenshot = pyautogui.screenshot()
    final_screenshot.save("cisco_final.png")
    
    print("✅ Connect clicking attempts complete")
    print("📸 Check screenshots: cisco_ready.png, after_click_*.png, cisco_final.png")

def monitor_connection():
    """Monitor VPN connection status"""
    
    print("\n6️⃣ Monitoring connection...")
    print("💡 Please enter password and complete 2FA")
    
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
        
        if i % 15 == 0:
            print(f"   Waiting... {120-i}s remaining")
        time.sleep(1)
    
    print("\n⏸️ Monitoring timeout")
    return False

def main():
    """Main execution"""
    
    # Find button first (optional diagnostic)
    # buttons = find_connect_button()
    
    # Actually click Connect
    click_connect_directly()
    
    # Monitor for success
    connected = monitor_connection()
    
    if connected:
        print("\n🚀 SUCCESS! VPN is connected")
        print("Now you can run PDF download scripts")
    else:
        print("\n❌ VPN connection not confirmed")
        print("Check the screenshots to see what happened")

if __name__ == "__main__":
    main()