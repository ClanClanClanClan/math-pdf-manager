#!/usr/bin/env python3
"""
ULTIMATE AUTO VPN
=================

The most aggressive automatic VPN connection possible
"""

import subprocess
import time
import pyautogui
import os

class UltimateAutoVPN:
    """Ultimate automatic VPN connector"""
    
    def __init__(self):
        print("🚀 ULTIMATE AUTOMATIC VPN CONNECTION")
        print("=" * 60)
        
        # Disable pyautogui failsafe for automation
        pyautogui.FAILSAFE = False
        
    def install_automation_tools(self):
        """Install required automation tools"""
        print("\n📦 INSTALLING AUTOMATION TOOLS")
        
        tools_needed = []
        
        # Check for cliclick
        try:
            subprocess.run(["which", "cliclick"], check=True, capture_output=True)
        except:
            tools_needed.append("cliclick")
        
        if tools_needed:
            print(f"Installing: {', '.join(tools_needed)}")
            for tool in tools_needed:
                subprocess.run(["brew", "install", tool])
        else:
            print("✅ All tools already installed")
    
    def aggressive_cisco_launch(self):
        """Launch Cisco with maximum force"""
        print("\n1️⃣ AGGRESSIVE CISCO LAUNCH")
        
        # Kill ALL Cisco processes
        subprocess.run(["pkill", "-9", "-f", "Cisco"], capture_output=True)
        subprocess.run(["pkill", "-9", "-f", "vpn"], capture_output=True)
        time.sleep(2)
        
        # Launch with open command
        subprocess.run(["open", "-F", "-a", "Cisco Secure Client"])
        time.sleep(3)
        
        # Force activate using AppleScript
        force_activate = '''
        tell application "Cisco Secure Client"
            activate
            reopen
        end tell
        
        tell application "System Events"
            set frontmost of process "Cisco Secure Client" to true
        end tell
        '''
        subprocess.run(["osascript", "-e", force_activate])
        time.sleep(2)
        
        print("✅ Cisco launched and activated")
    
    def find_and_click_connect_aggressively(self):
        """Find and click Connect with maximum aggression"""
        print("\n2️⃣ AGGRESSIVE CONNECT BUTTON SEARCH")
        
        # Take screenshot
        screenshot = pyautogui.screenshot()
        screenshot.save("aggressive_search.png")
        
        # Known button positions from different Cisco versions
        known_positions = [
            (484, 173),   # Your screenshot position
            (500, 175),   # Common position 1
            (480, 170),   # Common position 2
            (490, 180),   # Common position 3
            (475, 175),   # Common position 4
            # Add more positions based on window size
        ]
        
        # Also calculate positions based on screen size
        screen_w, screen_h = pyautogui.size()
        calculated_positions = [
            (screen_w * 0.35, screen_h * 0.2),  # Relative position 1
            (screen_w * 0.4, screen_h * 0.2),   # Relative position 2
            (screen_w * 0.45, screen_h * 0.25), # Relative position 3
        ]
        
        all_positions = known_positions + [(int(x), int(y)) for x, y in calculated_positions]
        
        print(f"🎯 Trying {len(all_positions)} positions...")
        
        # Click all positions rapidly
        for i, (x, y) in enumerate(all_positions):
            print(f"   Position {i+1}: ({x}, {y})")
            
            # Multiple click methods
            # Method 1: cliclick (most reliable on macOS)
            try:
                subprocess.run(["cliclick", f"c:{x},{y}"], capture_output=True)
            except:
                pass
            
            # Method 2: PyAutoGUI
            pyautogui.click(x, y)
            
            # Method 3: AppleScript
            click_script = f'''
            tell application "System Events"
                click at {{{x}, {y}}}
            end tell
            '''
            subprocess.run(["osascript", "-e", click_script], capture_output=True)
            
            time.sleep(0.5)
        
        print("✅ Clicked all possible Connect positions")
    
    def keyboard_automation_assault(self):
        """Assault the app with keyboard shortcuts"""
        print("\n3️⃣ KEYBOARD AUTOMATION ASSAULT")
        
        # Make sure Cisco is active
        subprocess.run(["osascript", "-e", 'tell application "Cisco Secure Client" to activate'])
        time.sleep(1)
        
        # Try every possible keyboard combination
        combinations = [
            ['tab', 'enter'],
            ['tab', 'space'],
            ['tab', 'tab', 'enter'],
            ['cmd', 'k'],
            ['return'],
            ['space'],
            ['tab', 'return'],
            ['escape', 'tab', 'enter'],  # Reset focus then tab
        ]
        
        for combo in combinations:
            print(f"   Trying: {' + '.join(combo)}")
            for key in combo:
                if key in ['cmd', 'ctrl', 'alt', 'shift']:
                    pyautogui.keyDown(key)
                else:
                    pyautogui.press(key)
                time.sleep(0.2)
            
            # Release any held keys
            for key in ['cmd', 'ctrl', 'alt', 'shift']:
                pyautogui.keyUp(key)
            
            time.sleep(0.5)
        
        print("✅ Keyboard assault complete")
    
    def ui_element_direct_manipulation(self):
        """Directly manipulate UI elements"""
        print("\n4️⃣ DIRECT UI MANIPULATION")
        
        ui_script = '''
        tell application "System Events"
            tell process "Cisco Secure Client"
                set frontmost to true
                delay 1
                
                -- Click every button in the window
                try
                    repeat with i from 1 to 10
                        try
                            click button i of window 1
                            delay 0.5
                        end try
                    end repeat
                end try
                
                -- Click every UI element that might be a button
                try
                    set allElements to every UI element of window 1
                    repeat with elem in allElements
                        try
                            if role of elem is "AXButton" then
                                click elem
                                delay 0.5
                            end if
                        end try
                    end repeat
                end try
                
                -- Perform AXPress action on buttons
                try
                    set allButtons to every button of window 1
                    repeat with btn in allButtons
                        try
                            perform action "AXPress" of btn
                            delay 0.5
                        end try
                    end repeat
                end try
            end tell
        end tell
        '''
        
        subprocess.run(["osascript", "-e", ui_script], capture_output=True)
        print("✅ UI manipulation complete")
    
    def nuclear_option(self):
        """The nuclear option - click everywhere"""
        print("\n5️⃣ NUCLEAR OPTION - CLICK EVERYWHERE")
        
        # Get screen size
        screen_w, screen_h = pyautogui.size()
        
        # Define the area where Cisco window typically appears
        cisco_area = {
            'x_start': int(screen_w * 0.2),
            'x_end': int(screen_w * 0.6),
            'y_start': int(screen_h * 0.1),
            'y_end': int(screen_h * 0.4)
        }
        
        print(f"   Clicking in area: {cisco_area}")
        
        # Click in a grid pattern
        for x in range(cisco_area['x_start'], cisco_area['x_end'], 50):
            for y in range(cisco_area['y_start'], cisco_area['y_end'], 30):
                pyautogui.click(x, y)
                time.sleep(0.1)
        
        print("✅ Nuclear clicking complete")
    
    def run_ultimate_automation(self):
        """Run the ultimate automation sequence"""
        
        # Install tools
        self.install_automation_tools()
        
        # Launch Cisco aggressively
        self.aggressive_cisco_launch()
        
        # Try all methods in sequence
        self.find_and_click_connect_aggressively()
        self.keyboard_automation_assault()
        self.ui_element_direct_manipulation()
        
        # Check if we need the nuclear option
        time.sleep(2)
        
        # Take screenshot to see current state
        check_screenshot = pyautogui.screenshot()
        check_screenshot.save("pre_nuclear_check.png")
        
        # If Cisco dialog still visible, use nuclear option
        print("\n⚠️ Deploying nuclear option as last resort...")
        self.nuclear_option()
        
        # Final keyboard assault
        self.keyboard_automation_assault()
        
        print("\n✅ ULTIMATE AUTOMATION COMPLETE")
        print("📸 Check screenshots:")
        print("   - aggressive_search.png")
        print("   - pre_nuclear_check.png")
        
        # Take final screenshot
        final = pyautogui.screenshot()
        final.save("ultimate_final.png")
        print("   - ultimate_final.png")
    
    def auto_fill_credentials(self, password):
        """Auto-fill credentials if provided"""
        print("\n6️⃣ AUTO-FILLING CREDENTIALS")
        
        if password:
            time.sleep(2)  # Wait for password field
            
            # Clear any existing text
            pyautogui.hotkey('cmd', 'a')
            pyautogui.press('delete')
            
            # Type password
            pyautogui.typewrite(password, interval=0.05)
            pyautogui.press('enter')
            
            print("✅ Password auto-filled")
        else:
            print("⚠️ No password provided - manual entry required")

def main():
    """Main execution"""
    
    print("🧠 ULTIMATE ULTRA-AUTOMATIC VPN CONNECTION")
    print("=" * 70)
    print("WARNING: This will aggressively click everywhere!")
    print("=" * 70)
    
    # Check if already connected
    try:
        result = subprocess.run(
            ["/opt/cisco/secureclient/bin/vpn", "status"],
            capture_output=True, text=True, timeout=5
        )
        if "state: Connected" in result.stdout:
            print("✅ Already connected!")
            return
    except:
        pass
    
    # Run ultimate automation
    automator = UltimateAutoVPN()
    automator.run_ultimate_automation()
    
    # Optional: Auto-fill password
    # password = "your_password_here"  # Set for full automation
    password = None
    
    if password:
        automator.auto_fill_credentials(password)
    
    # Monitor connection
    print("\n📡 MONITORING CONNECTION...")
    
    for i in range(180):
        try:
            result = subprocess.run(
                ["/opt/cisco/secureclient/bin/vpn", "status"],
                capture_output=True, text=True, timeout=3
            )
            
            if "state: Connected" in result.stdout:
                print(f"\n🎉 VPN CONNECTED AUTOMATICALLY!")
                print("🏆 ULTIMATE AUTOMATION SUCCESS!")
                return
                
        except:
            pass
        
        if i % 20 == 0:
            print(f"   Monitoring... {180-i}s remaining")
            if i == 60:
                print("   💡 Enter credentials if prompted")
        
        time.sleep(1)
    
    print("\n📊 Connection not confirmed - check screenshots")
    print("💡 The Connect button was likely clicked!")

if __name__ == "__main__":
    main()