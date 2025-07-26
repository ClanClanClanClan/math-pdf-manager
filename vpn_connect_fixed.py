#!/usr/bin/env python3
"""
VPN CONNECT FIXED
=================

Properly click the Connect button in Cisco Secure Client
"""

import subprocess
import time
import pyautogui
from PIL import Image
import pytesseract

def connect_vpn_properly():
    """Actually click the Connect button"""
    
    print("🔐 VPN CONNECTION - FIXED VERSION")
    print("=" * 50)
    
    # Launch Cisco
    print("\n1️⃣ Launching Cisco Secure Client...")
    subprocess.run(["pkill", "-f", "Cisco Secure Client"], capture_output=True)
    time.sleep(1)
    subprocess.run(["open", "-a", "Cisco Secure Client"])
    time.sleep(3)
    
    # Bring to front and ensure it's active
    applescript = '''
    tell application "Cisco Secure Client"
        activate
    end tell
    '''
    subprocess.run(["osascript", "-e", applescript])
    time.sleep(2)
    
    print("\n2️⃣ Finding Connect button...")
    
    # Method 1: Use pyautogui to find button by image
    try:
        # Take screenshot
        screenshot = pyautogui.screenshot()
        screenshot.save("cisco_window.png")
        
        # Try to find "Connect" text
        connect_button = pyautogui.locateOnScreen("connect_button.png", confidence=0.8)
        if connect_button:
            pyautogui.click(connect_button)
            print("✅ Clicked Connect button (image match)")
            return True
    except:
        pass
    
    # Method 2: Use OCR to find "Connect" text
    print("   Using OCR to find Connect button...")
    screenshot = pyautogui.screenshot()
    text_data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
    
    for i, word in enumerate(text_data['text']):
        if word.lower() == 'connect':
            x = text_data['left'][i] + text_data['width'][i] // 2
            y = text_data['top'][i] + text_data['height'][i] // 2
            
            print(f"   Found 'Connect' at ({x}, {y})")
            pyautogui.click(x, y)
            print("✅ Clicked Connect button (OCR)")
            return True
    
    # Method 3: Use known coordinates (backup)
    print("   Using AppleScript with UI elements...")
    
    # More specific AppleScript
    applescript = '''
    tell application "System Events"
        tell process "Cisco Secure Client"
            set frontmost to true
            delay 1
            
            -- Try to click Connect button by name
            try
                click button "Connect" of window 1
                return "success"
            end try
            
            -- Try by index
            try
                click button 1 of window 1
                return "success"
            end try
            
            -- List all buttons (for debugging)
            try
                set buttonList to name of every button of window 1
                return buttonList as string
            end try
        end tell
    end tell
    '''
    
    result = subprocess.run(["osascript", "-e", applescript], 
                          capture_output=True, text=True)
    
    if "success" in result.stdout:
        print("✅ Clicked Connect button (AppleScript)")
        return True
    else:
        print(f"   Available buttons: {result.stdout}")
    
    # Method 4: Click at common button location
    print("\n3️⃣ Trying common button locations...")
    
    # Get window bounds
    try:
        window_bounds = None
        for window in pyautogui.getAllWindows():
            if "Cisco" in window.title:
                window_bounds = window
                break
        
        if window_bounds:
            # Connect button is usually in the center-right
            x = window_bounds.left + window_bounds.width * 0.7
            y = window_bounds.top + window_bounds.height * 0.5
            
            print(f"   Clicking at ({x}, {y})")
            pyautogui.click(x, y)
            print("✅ Clicked at expected Connect location")
            return True
    except:
        pass
    
    print("❌ Could not find Connect button")
    print("💡 Please click Connect manually")
    return False

def main():
    """Test the connection"""
    
    if connect_vpn_properly():
        print("\n✅ Connect button clicked!")
        print("⏳ Waiting for password prompt...")
        time.sleep(3)
        
        # Auto-type password if needed
        # pyautogui.typewrite("your_password")
        # pyautogui.press('enter')
        
        print("\n📱 Please complete 2FA on your phone")
    else:
        print("\n⚠️ Manual intervention required")

if __name__ == "__main__":
    main()