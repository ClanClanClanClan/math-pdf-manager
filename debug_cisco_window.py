#!/usr/bin/env python3
"""
DEBUG CISCO WINDOW
==================

Take screenshot and analyze Cisco window
"""

import subprocess
import time
import pyautogui
import pytesseract
from PIL import Image

def debug_cisco():
    """Debug what's in the Cisco window"""
    
    print("🔍 DEBUGGING CISCO WINDOW")
    print("=" * 50)
    
    # Launch Cisco
    print("\n1️⃣ Launching Cisco...")
    subprocess.run(["open", "-a", "Cisco Secure Client"])
    time.sleep(3)
    
    # Activate
    subprocess.run([
        "osascript", "-e", 
        'tell application "Cisco Secure Client" to activate'
    ])
    time.sleep(1)
    
    # Take screenshot
    print("\n2️⃣ Taking screenshot...")
    screenshot = pyautogui.screenshot()
    screenshot.save("cisco_debug.png")
    print("✅ Saved to cisco_debug.png")
    
    # OCR the screenshot
    print("\n3️⃣ Running OCR to find text...")
    text = pytesseract.image_to_string(screenshot)
    print("\nText found in window:")
    print("-" * 40)
    print(text)
    print("-" * 40)
    
    # Find button locations
    print("\n4️⃣ Finding button locations...")
    data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
    
    buttons = []
    for i, word in enumerate(data['text']):
        if word.lower() in ['connect', 'disconnect', 'settings', 'ok', 'cancel']:
            x = data['left'][i] + data['width'][i] // 2
            y = data['top'][i] + data['height'][i] // 2
            buttons.append({
                'text': word,
                'x': x,
                'y': y
            })
            print(f"   Found '{word}' at ({x}, {y})")
    
    # Try AppleScript to get UI elements
    print("\n5️⃣ Getting UI elements via AppleScript...")
    
    ui_script = '''
    tell application "System Events"
        tell process "Cisco Secure Client"
            set uiElements to entire contents of window 1
            set buttonNames to {}
            
            repeat with elem in uiElements
                try
                    if class of elem is button then
                        set end of buttonNames to name of elem
                    end if
                end try
            end repeat
            
            return buttonNames as string
        end tell
    end tell
    '''
    
    result = subprocess.run(["osascript", "-e", ui_script], 
                          capture_output=True, text=True)
    
    if result.stdout:
        print(f"   Buttons found: {result.stdout}")
    
    return buttons

def main():
    buttons = debug_cisco()
    
    if buttons:
        print(f"\n✅ Found {len(buttons)} buttons")
        print("\n💡 To click Connect, use:")
        for btn in buttons:
            if 'connect' in btn['text'].lower():
                print(f"   pyautogui.click({btn['x']}, {btn['y']})")
    else:
        print("\n❌ No buttons found via OCR")
        print("💡 Check cisco_debug.png manually")

if __name__ == "__main__":
    main()