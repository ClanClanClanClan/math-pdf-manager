#!/usr/bin/env python3
"""
SIMPLE CLICK TEST
=================

Let's test a simple approach to click the Connect button.
This will help us understand exactly where and how to click.
"""

import subprocess
import time

def test_simple_click():
    """Test simple clicking on Cisco Connect button"""
    
    print("🔍 SIMPLE CISCO CONNECT CLICK TEST")
    print("=" * 50)
    
    try:
        # Open Cisco
        print("1. Opening Cisco Secure Client...")
        subprocess.run(['open', '-a', 'Cisco Secure Client'])
        time.sleep(6)
        
        # Activate it
        subprocess.run(['osascript', '-e', 'tell application "Cisco Secure Client" to activate'])
        time.sleep(2)
        
        print("2. Cisco should now be open with sslvpn.ethz.ch/staff-net pre-filled")
        print("3. Looking for Connect button using AppleScript...")
        
        # Try to find and click Connect button using AppleScript
        click_script = '''
        tell application "System Events"
            tell process "Cisco Secure Client"
                try
                    -- Look for Connect button
                    if exists button "Connect" of window 1 then
                        click button "Connect" of window 1
                        return "Connect button clicked"
                    else
                        -- Try to find any button with "Connect" in name
                        set allButtons to every button of window 1
                        repeat with btn in allButtons
                            if name of btn contains "Connect" then
                                click btn
                                return "Found and clicked Connect button: " & name of btn
                            end if
                        end repeat
                        return "No Connect button found"
                    end if
                on error errMsg
                    return "Error: " & errMsg
                end try
            end tell
        end tell
        '''
        
        print("4. Attempting to click Connect button...")
        result = subprocess.run(['osascript', '-e', click_script], 
                              capture_output=True, text=True, timeout=15)
        
        print(f"AppleScript result: {result.stdout.strip()}")
        
        if "clicked" in result.stdout:
            print("✅ Connect button was clicked!")
            print("5. Waiting to see if login dialog appears...")
            time.sleep(5)
            
            # Check if login dialog appeared
            login_check = subprocess.run([
                'osascript', '-e', '''
                tell application "System Events"
                    tell process "Cisco Secure Client"
                        try
                            return exists text field 1 of window 1
                        on error
                            return false
                        end try
                    end tell
                end tell
                '''
            ], capture_output=True, text=True)
            
            if 'true' in login_check.stdout:
                print("✅ Login dialog appeared! The click worked!")
                return True
            else:
                print("❌ No login dialog detected")
                return False
        else:
            print("❌ Could not click Connect button")
            print("Let's try manual inspection...")
            
            # Get all UI elements for debugging
            ui_debug = subprocess.run([
                'osascript', '-e', '''
                tell application "System Events"
                    tell process "Cisco Secure Client"
                        try
                            set allButtons to every button of window 1
                            set buttonNames to {}
                            repeat with btn in allButtons
                                set end of buttonNames to name of btn
                            end repeat
                            return buttonNames as string
                        on error
                            return "No buttons found"
                        end try
                    end tell
                end tell
                '''
            ], capture_output=True, text=True)
            
            print(f"Available buttons: {ui_debug.stdout.strip()}")
            return False
            
    except Exception as e:
        print(f"Test failed: {e}")
        return False

def main():
    """Main test"""
    
    success = test_simple_click()
    
    if success:
        print("\n🎉 CLICK TEST SUCCESSFUL!")
        print("We can auto-click the Connect button!")
    else:
        print("\n❌ Click test failed")
        print("Need to debug the UI interaction")

if __name__ == "__main__":
    main()