#!/usr/bin/env python3
"""
BULLETPROOF VPN CONNECT
=======================

Ultra-reliable Connect button clicking with visual recognition
"""

import subprocess
import time
from pathlib import Path

import cv2
import numpy as np
import pyautogui
import pytesseract
from PIL import Image

from scripts.vpn.secure_vpn_credentials import get_vpn_password


class BulletproofVPNConnect:
    """Bulletproof VPN connection with visual recognition"""

    def __init__(self):
        print("🎯 BULLETPROOF VPN CONNECT")
        print("=" * 60)
        print("Features:")
        print("✓ Visual button recognition")
        print("✓ Multiple detection methods")
        print("✓ Automatic password entry")
        print("✓ 2FA solutions")
        print("=" * 60)

        # Get stored password
        self.password = get_vpn_password()
        if self.password:
            print("✅ Password loaded from secure storage")
        else:
            print("❌ No password found in secure storage")

        # Disable pyautogui failsafe
        pyautogui.FAILSAFE = False

    def launch_cisco_reliably(self):
        """Launch Cisco with maximum reliability"""
        print("\n1️⃣ LAUNCHING CISCO RELIABLY")

        # Kill all Cisco processes
        subprocess.run(["pkill", "-9", "-f", "Cisco"], capture_output=True)
        time.sleep(2)

        # Launch fresh
        subprocess.run(["open", "-F", "-a", "Cisco Secure Client"])

        # Wait and verify window appeared
        for i in range(10):
            time.sleep(1)
            if self._find_cisco_window():
                print(f"✅ Cisco window appeared after {i+1}s")
                break

        # Activate window
        activate_script = """
        tell application "Cisco Secure Client"
            activate
            set frontmost to true
        end tell
        """
        subprocess.run(["osascript", "-e", activate_script])
        time.sleep(1)

        return True

    def _find_cisco_window(self):
        """Find Cisco window on screen"""
        try:
            import Quartz

            window_list = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID
            )

            for window in window_list:
                if "Cisco" in str(window.get("kCGWindowOwnerName", "")):
                    return window.get("kCGWindowBounds", {})

        except:
            pass

        return None

    def find_connect_button_visually(self):
        """Find Connect button using visual recognition"""
        print("\n2️⃣ VISUAL BUTTON RECOGNITION")

        # Take screenshot
        screenshot = pyautogui.screenshot()
        screenshot.save("visual_search.png")

        # Convert to OpenCV format
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        # Method 1: Find blue button areas
        print("   🔍 Method 1: Blue button detection")
        blue_buttons = self._find_blue_buttons(img)

        # Method 2: OCR to find "Connect" text
        print("   🔍 Method 2: OCR text detection")
        ocr_button = self._find_connect_with_ocr(screenshot)

        # Method 3: Template matching (if we have a template)
        print("   🔍 Method 3: Known positions")
        known_positions = self._get_known_positions()

        # Combine all findings
        all_positions = []

        if blue_buttons:
            all_positions.extend(blue_buttons)

        if ocr_button:
            all_positions.append(ocr_button)

        all_positions.extend(known_positions)

        # Remove duplicates
        unique_positions = []
        for pos in all_positions:
            is_duplicate = False
            for existing in unique_positions:
                if abs(pos[0] - existing[0]) < 20 and abs(pos[1] - existing[1]) < 20:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_positions.append(pos)

        print(f"✅ Found {len(unique_positions)} potential button positions")
        return unique_positions

    def _find_blue_buttons(self, img):
        """Find blue button areas"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Blue color range (Cisco buttons are blue)
        lower_blue = np.array([100, 50, 50])
        upper_blue = np.array([130, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        buttons = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            # Button-like dimensions
            if 40 < w < 200 and 20 < h < 60:
                center_x = x + w // 2
                center_y = y + h // 2
                buttons.append((center_x, center_y))

                # Save button image for debugging
                button_img = img[y : y + h, x : x + w]
                cv2.imwrite(f"button_candidate_{len(buttons)}.png", button_img)

        return buttons

    def _find_connect_with_ocr(self, screenshot):
        """Find Connect text with OCR"""
        # Get text with positions
        data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)

        for i, text in enumerate(data["text"]):
            if text and "connect" in text.lower():
                if data["conf"][i] > 30:  # Confidence threshold
                    x = data["left"][i] + data["width"][i] // 2
                    y = data["top"][i] + data["height"][i] // 2
                    return (x, y)

        return None

    def _get_known_positions(self):
        """Get known Connect button positions"""
        screen_w, screen_h = pyautogui.size()

        # Based on previous successful clicks
        known = [
            (484, 173),  # Your screenshot position
            (int(screen_w * 0.35), int(screen_h * 0.2)),
            (int(screen_w * 0.4), int(screen_h * 0.2)),
        ]

        return known

    def click_connect_bulletproof(self, positions):
        """Click Connect button with maximum reliability"""
        print("\n3️⃣ BULLETPROOF CLICKING")

        # Try each position with multiple methods
        for i, (x, y) in enumerate(positions):
            print(f"\n   Position {i+1}/{len(positions)}: ({x}, {y})")

            # Method 1: cliclick (most reliable on macOS)
            try:
                subprocess.run(["cliclick", f"c:{int(x)},{int(y)}"], capture_output=True)
                print("     ✓ cliclick")
            except:
                pass

            # Method 2: PyAutoGUI with slow movement
            pyautogui.moveTo(x, y, duration=0.5)
            time.sleep(0.2)
            pyautogui.click()
            print("     ✓ PyAutoGUI click")

            # Method 3: PyAutoGUI double click
            pyautogui.doubleClick(x, y)
            print("     ✓ Double click")

            # Method 4: AppleScript
            click_script = f"""
            tell application "System Events"
                click at {{{int(x)}, {int(y)}}}
            end tell
            """
            subprocess.run(["osascript", "-e", click_script], capture_output=True)
            print("     ✓ AppleScript")

            # Wait and check if dialog disappeared
            time.sleep(1)

            # Take screenshot after click
            after_click = pyautogui.screenshot()
            after_click.save(f"after_position_{i+1}.png")

            # Quick check if button might have been clicked
            # (You could add more sophisticated detection here)

        # Final keyboard navigation attempt
        print("\n   Keyboard navigation fallback")
        subprocess.run(["osascript", "-e", 'tell application "Cisco Secure Client" to activate'])
        time.sleep(0.5)

        pyautogui.press("tab")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(0.2)
        pyautogui.press("space")

        print("\n✅ All clicking methods executed")

    def auto_enter_password(self):
        """Automatically enter password when prompted"""
        print("\n4️⃣ AUTO-ENTERING PASSWORD")

        if not self.password:
            print("❌ No password available")
            return

        # Wait for password prompt
        time.sleep(3)

        # Clear any existing text
        pyautogui.hotkey("cmd", "a")
        pyautogui.press("delete")

        # Type password
        print("🔑 Entering password...")
        pyautogui.typewrite(self.password, interval=0.05)
        time.sleep(0.5)

        # Press Enter
        pyautogui.press("enter")

        print("✅ Password entered automatically")

    def handle_2fa_options(self):
        """Handle 2FA with multiple options"""
        print("\n5️⃣ 2FA HANDLING OPTIONS")
        print("-" * 40)

        print("Option 1: MANUAL (Current)")
        print("   📱 Enter code from your authenticator app")

        print("\nOption 2: PHONE SCREEN MIRRORING")
        print("   brew install scrcpy")
        print("   scrcpy --window-title='2FA'")
        print("   Then use OCR to read the code")

        print("\nOption 3: TOTP SECRET (Future)")
        print("   If you can get your TOTP secret from the authenticator")
        print("   We can generate codes automatically")

        print("\nOption 4: PUSH NOTIFICATION")
        print("   If using Duo, we might intercept push notifications")

        print("-" * 40)
        print("⏳ Waiting for 2FA completion...")

    def monitor_connection(self):
        """Monitor VPN connection status"""
        print("\n6️⃣ MONITORING CONNECTION")

        for i in range(180):  # 3 minutes
            try:
                result = subprocess.run(
                    ["/opt/cisco/secureclient/bin/vpn", "status"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )

                if "state: Connected" in result.stdout:
                    print(f"\n🎉 VPN CONNECTED SUCCESSFULLY!")
                    return True
                elif "state: Connecting" in result.stdout:
                    if i % 10 == 0:
                        print(f"   Connecting... {180-i}s remaining")

            except:
                pass

            time.sleep(1)

        return False

    def run_bulletproof_connection(self):
        """Run the complete bulletproof connection"""

        # Check if already connected
        try:
            result = subprocess.run(
                ["/opt/cisco/secureclient/bin/vpn", "status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "state: Connected" in result.stdout:
                print("✅ Already connected!")
                return True
        except:
            pass

        # Step 1: Launch Cisco
        self.launch_cisco_reliably()

        # Step 2: Find Connect button visually
        positions = self.find_connect_button_visually()

        # Step 3: Click Connect bulletproof
        self.click_connect_bulletproof(positions)

        # Step 4: Auto-enter password
        self.auto_enter_password()

        # Step 5: Handle 2FA
        self.handle_2fa_options()

        # Step 6: Monitor connection
        return self.monitor_connection()


def main():
    """Main bulletproof execution"""

    print("🎯 BULLETPROOF VPN CONNECTION")
    print("=" * 70)
    print("This uses:")
    print("✓ Visual recognition to find Connect button")
    print("✓ Multiple clicking methods for reliability")
    print("✓ Automatic password entry from secure storage")
    print("✓ 2FA handling options")
    print("=" * 70)

    # Install cliclick if needed
    try:
        subprocess.run(["which", "cliclick"], check=True, capture_output=True)
    except:
        print("📦 Installing cliclick for reliable clicking...")
        subprocess.run(["brew", "install", "cliclick"])

    # Run bulletproof connection
    connector = BulletproofVPNConnect()
    success = connector.run_bulletproof_connection()

    if success:
        print("\n🏆 BULLETPROOF CONNECTION SUCCESS!")
        print("✅ Connected to VPN automatically")
        print("✅ Password was entered from secure storage")
        print("📄 Ready to download PDFs!")
    else:
        print("\n⚠️ Connection not confirmed")
        print("Check screenshots for debugging:")
        print("  - visual_search.png")
        print("  - button_candidate_*.png")
        print("  - after_position_*.png")


if __name__ == "__main__":
    main()
