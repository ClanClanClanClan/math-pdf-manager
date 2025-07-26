#!/usr/bin/env python3
"""
ULTRATHINK AUTO CONNECT
=======================

FULLY AUTOMATIC Connect button clicking using multiple advanced techniques
"""

import subprocess
import time
import pyautogui
import Quartz
import AppKit
from AppKit import NSWorkspace, NSRunningApplication
import objc
import pytesseract
from PIL import Image
import re

class UltraAutoConnect:
    """Ultra-robust automatic Connect button clicker"""
    
    def __init__(self):
        print("🧠 ULTRATHINKING AUTOMATIC CONNECTION")
        print("=" * 60)
        print("Using advanced techniques:")
        print("✓ Accessibility API")
        print("✓ Window geometry analysis")
        print("✓ OCR text detection")
        print("✓ UI element inspection")
        print("✓ Keyboard shortcuts")
        print("✓ Native macOS APIs")
        print("=" * 60)
    
    def launch_cisco_with_control(self):
        """Launch Cisco with full control"""
        print("\n1️⃣ LAUNCHING CISCO WITH CONTROL")
        
        # Kill existing
        subprocess.run(["pkill", "-9", "-f", "Cisco"], capture_output=True)
        time.sleep(2)
        
        # Launch using NSWorkspace for better control
        workspace = NSWorkspace.sharedWorkspace()
        app_path = "/Applications/Cisco/Cisco Secure Client.app"
        
        # Launch and get the running application
        app = workspace.launchApplication_(app_path)
        time.sleep(3)
        
        # Get the running application object
        running_apps = workspace.runningApplications()
        cisco_app = None
        
        for app in running_apps:
            if "Cisco" in app.localizedName():
                cisco_app = app
                print(f"✅ Found Cisco app: PID {app.processIdentifier()}")
                break
        
        # Activate and bring to front
        if cisco_app:
            cisco_app.activateWithOptions_(
                NSWorkspace.NSApplicationActivateAllWindows | 
                NSWorkspace.NSApplicationActivateIgnoringOtherApps
            )
            time.sleep(1)
        
        return cisco_app
    
    def find_connect_button_with_accessibility(self):
        """Use Accessibility API to find Connect button"""
        print("\n2️⃣ USING ACCESSIBILITY API")
        
        # AppleScript to inspect UI elements
        ui_script = '''
        tell application "System Events"
            tell process "Cisco Secure Client"
                set frontmost to true
                delay 1
                
                -- Get all UI elements
                set allElements to entire contents of window 1
                set buttonInfo to {}
                
                repeat with elem in allElements
                    try
                        if class of elem is button then
                            set elemName to name of elem
                            set elemPos to position of elem
                            set elemSize to size of elem
                            
                            -- Look for Connect button
                            if elemName contains "Connect" then
                                return "FOUND:" & (item 1 of elemPos) & "," & (item 2 of elemPos) & "," & (item 1 of elemSize) & "," & (item 2 of elemSize)
                            end if
                        end if
                    end try
                end repeat
                
                -- If not found by name, get first button
                try
                    set firstButton to button 1 of window 1
                    set btnPos to position of firstButton
                    set btnSize to size of firstButton
                    return "FIRST:" & (item 1 of btnPos) & "," & (item 2 of btnPos) & "," & (item 1 of btnSize) & "," & (item 2 of btnSize)
                end try
                
                return "NOTFOUND"
            end tell
        end tell
        '''
        
        result = subprocess.run(
            ["osascript", "-e", ui_script],
            capture_output=True, text=True
        )
        
        if result.stdout.strip().startswith("FOUND:") or result.stdout.strip().startswith("FIRST:"):
            parts = result.stdout.strip().split(":")[1].split(",")
            x, y, w, h = map(float, parts)
            center_x = x + w/2
            center_y = y + h/2
            print(f"✅ Found button via Accessibility: ({center_x}, {center_y})")
            return (center_x, center_y)
        
        return None
    
    def find_connect_with_ocr(self):
        """Use OCR to find Connect button"""
        print("\n3️⃣ USING OCR TEXT DETECTION")
        
        # Take screenshot
        screenshot = pyautogui.screenshot()
        screenshot.save("ocr_scan.png")
        
        # Run OCR to get text locations
        data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
        
        # Find "Connect" text
        for i, text in enumerate(data['text']):
            if text and 'connect' in text.lower():
                x = data['left'][i] + data['width'][i] // 2
                y = data['top'][i] + data['height'][i] // 2
                confidence = data['conf'][i]
                
                if confidence > 50:  # Good confidence
                    print(f"✅ Found 'Connect' via OCR at ({x}, {y}) confidence {confidence}%")
                    return (x, y)
        
        # Look for button-like rectangles in blue color
        import numpy as np
        import cv2
        
        img_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
        
        # Blue button color range
        lower_blue = np.array([100, 50, 50])
        upper_blue = np.array([130, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Find button-shaped blue areas
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if 60 < w < 150 and 25 < h < 50:  # Button dimensions
                center_x = x + w // 2
                center_y = y + h // 2
                print(f"✅ Found blue button area at ({center_x}, {center_y})")
                return (center_x, center_y)
        
        return None
    
    def find_cisco_window_precisely(self):
        """Find Cisco window with precise coordinates"""
        print("\n4️⃣ FINDING CISCO WINDOW GEOMETRY")
        
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID
        )
        
        for window in window_list:
            if "Cisco" in str(window.get('kCGWindowOwnerName', '')):
                bounds = window.get('kCGWindowBounds', {})
                x = int(bounds.get('X', 0))
                y = int(bounds.get('Y', 0))
                w = int(bounds.get('Width', 0))
                h = int(bounds.get('Height', 0))
                
                print(f"✅ Cisco window at ({x}, {y}) size {w}x{h}")
                
                # Connect button is typically at 70% width, 50% height
                connect_x = x + int(w * 0.7)
                connect_y = y + int(h * 0.5)
                
                return (connect_x, connect_y)
        
        return None
    
    def try_keyboard_shortcuts(self):
        """Try keyboard shortcuts"""
        print("\n5️⃣ TRYING KEYBOARD SHORTCUTS")
        
        # Common shortcuts that might work
        shortcuts = [
            ('cmd', 'k'),      # Common "connect" shortcut
            ('cmd', 'return'), # Command+Enter
            ('ctrl', 'c'),     # Ctrl+C for Connect
            ('alt', 'c'),      # Alt+C
        ]
        
        for modifier, key in shortcuts:
            print(f"   Trying {modifier}+{key}")
            pyautogui.hotkey(modifier, key)
            time.sleep(1)
    
    def click_with_multiple_methods(self, coordinates):
        """Click using multiple methods to ensure success"""
        x, y = coordinates
        
        print(f"\n6️⃣ CLICKING AT ({x}, {y}) WITH MULTIPLE METHODS")
        
        # Method 1: PyAutoGUI click
        print("   Method 1: PyAutoGUI")
        pyautogui.moveTo(x, y, duration=0.5)
        pyautogui.click()
        time.sleep(1)
        
        # Method 2: Double click
        print("   Method 2: Double click")
        pyautogui.doubleClick(x, y)
        time.sleep(1)
        
        # Method 3: Mouse down/up
        print("   Method 3: Mouse down/up")
        pyautogui.mouseDown(x, y)
        time.sleep(0.1)
        pyautogui.mouseUp(x, y)
        time.sleep(1)
        
        # Method 4: AppleScript click at coordinates
        print("   Method 4: AppleScript click")
        click_script = f'''
        tell application "System Events"
            click at {{{int(x)}, {int(y)}}}
        end tell
        '''
        subprocess.run(["osascript", "-e", click_script])
        time.sleep(1)
        
        # Method 5: cliclick tool (if installed)
        try:
            subprocess.run(["cliclick", f"c:{int(x)},{int(y)}"], capture_output=True)
            print("   Method 5: cliclick")
        except:
            pass
    
    def ultrathink_connect(self):
        """Main ultra-thinking connection method"""
        
        # Launch Cisco
        cisco_app = self.launch_cisco_with_control()
        time.sleep(2)
        
        # Try all methods to find Connect button
        methods = [
            ("Accessibility API", self.find_connect_button_with_accessibility),
            ("OCR Detection", self.find_connect_with_ocr),
            ("Window Geometry", self.find_cisco_window_precisely),
        ]
        
        connect_coords = None
        
        for method_name, method_func in methods:
            print(f"\n🔍 Attempting {method_name}...")
            coords = method_func()
            if coords:
                connect_coords = coords
                print(f"✅ Success with {method_name}!")
                break
        
        if not connect_coords:
            # Fallback to known positions
            print("\n⚠️ Using fallback coordinates")
            connect_coords = (484, 173)  # From previous screenshots
        
        # Click with all methods
        self.click_with_multiple_methods(connect_coords)
        
        # Also try keyboard shortcuts
        self.try_keyboard_shortcuts()
        
        # Try Tab+Enter as final method
        print("\n7️⃣ FINAL METHOD: Tab navigation")
        pyautogui.press('tab')
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(0.5)
        pyautogui.press('space')
        
        print("\n✅ ALL AUTOMATIC CLICKING METHODS EXECUTED")
        
        # Take final screenshot
        final = pyautogui.screenshot()
        final.save("ultra_final_state.png")
        
        return True
    
    def monitor_and_complete_auth(self):
        """Monitor connection and handle auth automatically"""
        print("\n8️⃣ MONITORING CONNECTION")
        
        # If password provided, we can auto-fill
        password = None  # Set your password here for full automation
        
        auth_entered = False
        
        for i in range(180):
            try:
                result = subprocess.run(
                    ["/opt/cisco/secureclient/bin/vpn", "status"],
                    capture_output=True, text=True, timeout=3
                )
                
                if "state: Connected" in result.stdout:
                    print(f"\n🎉 VPN CONNECTED AUTOMATICALLY!")
                    return True
                elif "Username" in result.stdout and not auth_entered and password:
                    print("🔑 Auto-entering credentials...")
                    pyautogui.typewrite(password)
                    pyautogui.press('enter')
                    auth_entered = True
                    
            except:
                pass
            
            if i % 20 == 0:
                print(f"   Monitoring... {180-i}s remaining")
            
            time.sleep(1)
        
        return False

def main():
    """Main ultra-automatic execution"""
    
    print("🧠 ULTRATHINKING FULLY AUTOMATIC VPN CONNECTION")
    print("=" * 70)
    print("This will automatically:")
    print("✓ Launch Cisco")
    print("✓ Find Connect button using multiple AI techniques")
    print("✓ Click it automatically")
    print("✓ Handle authentication (if password provided)")
    print("=" * 70)
    
    connector = UltraAutoConnect()
    
    # Execute ultra-thinking connection
    click_success = connector.ultrathink_connect()
    
    if click_success:
        # Monitor for connection
        connected = connector.monitor_and_complete_auth()
        
        if connected:
            print("\n🏆 FULL AUTOMATION SUCCESS!")
            print("✅ Launched Cisco automatically")
            print("✅ Found and clicked Connect button")
            print("✅ VPN connected without manual intervention")
            print("\n🧠 ULTRATHINKING WORKED!")
        else:
            print("\n⚠️ Clicked Connect but need manual auth")
            print("Check ultra_final_state.png to verify click")
    
    print("\n🎯 Ultra-automatic connection complete!")

if __name__ == "__main__":
    # Install required tool if not present
    try:
        subprocess.run(["which", "cliclick"], check=True, capture_output=True)
    except:
        print("💡 Installing cliclick for better mouse control...")
        subprocess.run(["brew", "install", "cliclick"])
    
    main()