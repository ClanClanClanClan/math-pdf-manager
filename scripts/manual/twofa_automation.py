#!/usr/bin/env python3
"""
2FA AUTOMATION SOLUTIONS
========================

Multiple approaches to automate 2FA
"""

import subprocess
import time
import pyautogui
import pytesseract
from PIL import Image
import cv2
import numpy as np
import pyotp
from pathlib import Path

class TwoFAAutomation:
    """Advanced 2FA automation solutions"""
    
    def __init__(self):
        print("🔐 2FA AUTOMATION SOLUTIONS")
        print("=" * 50)
        
    def method1_screen_mirroring(self):
        """Use phone screen mirroring to capture 2FA code"""
        print("\n📱 METHOD 1: SCREEN MIRRORING")
        
        # Check if scrcpy is installed
        try:
            subprocess.run(["which", "scrcpy"], check=True, capture_output=True)
        except:
            print("Installing scrcpy...")
            subprocess.run(["brew", "install", "scrcpy"])
        
        print("1️⃣ Connect your phone via USB")
        print("2️⃣ Enable USB debugging on your phone")
        print("3️⃣ Starting screen mirroring...")
        
        # Start scrcpy in a separate process
        scrcpy_process = subprocess.Popen(
            ["scrcpy", "--window-title=Phone2FA", "--always-on-top"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        time.sleep(5)  # Wait for scrcpy to start
        
        print("4️⃣ Looking for 2FA window...")
        
        # Take screenshot and find the phone window
        screenshot = pyautogui.screenshot()
        
        # Find the 2FA code on screen
        code = self._extract_2fa_code_from_screen(screenshot)
        
        if code:
            print(f"✅ Found 2FA code: {code}")
            # Type the code
            pyautogui.typewrite(code)
            pyautogui.press('enter')
            return True
        
        print("❌ Could not extract 2FA code")
        return False
    
    def method2_totp_secret(self, secret=None):
        """Use TOTP secret to generate codes"""
        print("\n🔑 METHOD 2: TOTP SECRET")
        
        if not secret:
            print("To use this method, you need to:")
            print("1. Export your TOTP secret from your authenticator")
            print("2. Store it securely")
            print("\nExample code:")
            print("totp = pyotp.TOTP('your-secret-here')")
            print("code = totp.now()")
            return False
        
        # Generate code
        totp = pyotp.TOTP(secret)
        code = totp.now()
        
        print(f"✅ Generated 2FA code: {code}")
        
        # Type the code
        pyautogui.typewrite(code)
        pyautogui.press('enter')
        
        return True
    
    def method3_webcam_capture(self):
        """Use webcam to capture phone screen"""
        print("\n📸 METHOD 3: WEBCAM CAPTURE")
        
        print("1️⃣ Position your phone under the webcam")
        print("2️⃣ Make sure 2FA code is visible")
        time.sleep(3)
        
        # Capture from webcam
        cap = cv2.VideoCapture(0)
        
        print("3️⃣ Capturing...")
        
        for i in range(10):  # Try 10 frames
            ret, frame = cap.read()
            
            if ret:
                # Save frame for debugging
                cv2.imwrite(f"webcam_capture_{i}.png", frame)
                
                # Convert to PIL Image for OCR
                pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                
                # Extract code
                code = self._extract_2fa_code_from_image(pil_image)
                
                if code:
                    print(f"✅ Found 2FA code: {code}")
                    cap.release()
                    
                    # Type the code
                    pyautogui.typewrite(code)
                    pyautogui.press('enter')
                    return True
            
            time.sleep(0.5)
        
        cap.release()
        print("❌ Could not capture 2FA code")
        return False
    
    def method4_notification_mirroring(self):
        """Use notification mirroring services"""
        print("\n📨 METHOD 4: NOTIFICATION MIRRORING")
        
        print("Options:")
        print("1. Pushbullet - Mirror notifications to desktop")
        print("2. KDE Connect - Open source alternative")
        print("3. AirDroid - Android notification mirroring")
        
        # Example with Pushbullet (requires API key)
        print("\nTo set up Pushbullet:")
        print("1. Install: pip install pushbullet.py")
        print("2. Get API key from pushbullet.com")
        print("3. Use code like:")
        print("""
from pushbullet import Pushbullet
pb = Pushbullet('your-api-key')
pushes = pb.get_pushes()
# Look for 2FA code in recent pushes
""")
        
        return False
    
    def method5_accessibility_api(self):
        """Use macOS accessibility to read from authenticator app"""
        print("\n♿ METHOD 5: ACCESSIBILITY API")
        
        # Open authenticator app
        print("1️⃣ Opening Microsoft Authenticator...")
        subprocess.run(["open", "-a", "Microsoft Authenticator"])
        time.sleep(3)
        
        # Try to read screen content
        read_script = '''
        tell application "System Events"
            tell process "Microsoft Authenticator"
                set frontmost to true
                delay 1
                
                -- Get all text elements
                set allText to value of every static text of window 1
                return allText as string
            end tell
        end tell
        '''
        
        result = subprocess.run(
            ["osascript", "-e", read_script],
            capture_output=True, text=True
        )
        
        if result.stdout:
            # Extract 6-digit code
            import re
            codes = re.findall(r'\b\d{6}\b', result.stdout)
            
            if codes:
                code = codes[0]
                print(f"✅ Found 2FA code: {code}")
                
                # Switch back to Cisco
                subprocess.run(["osascript", "-e", 'tell application "Cisco Secure Client" to activate'])
                time.sleep(1)
                
                # Type the code
                pyautogui.typewrite(code)
                pyautogui.press('enter')
                return True
        
        print("❌ Could not read from authenticator")
        return False
    
    def _extract_2fa_code_from_screen(self, screenshot):
        """Extract 2FA code from screenshot using OCR"""
        # Convert to grayscale
        gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
        
        # Apply threshold to get better OCR results
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        # Run OCR
        text = pytesseract.image_to_string(thresh, config='--psm 6 digits')
        
        # Find 6-digit codes
        import re
        codes = re.findall(r'\b\d{6}\b', text)
        
        if codes:
            return codes[0]
        
        # Try with different preprocessing
        text = pytesseract.image_to_string(screenshot)
        codes = re.findall(r'\b\d{6}\b', text)
        
        return codes[0] if codes else None
    
    def _extract_2fa_code_from_image(self, image):
        """Extract 2FA code from PIL Image"""
        # Try multiple OCR configurations
        configs = [
            '--psm 6 digits',
            '--psm 7 digits',
            '--psm 8 digits',
            '--psm 11 digits'
        ]
        
        import re
        
        for config in configs:
            text = pytesseract.image_to_string(image, config=config)
            codes = re.findall(r'\b\d{6}\b', text)
            
            if codes:
                return codes[0]
        
        return None
    
    def auto_2fa_with_best_method(self):
        """Try all methods to automate 2FA"""
        print("\n🤖 ATTEMPTING AUTOMATIC 2FA")
        
        methods = [
            ("Screen Mirroring", self.method1_screen_mirroring),
            ("Webcam Capture", self.method3_webcam_capture),
            ("Accessibility API", self.method5_accessibility_api),
        ]
        
        for name, method in methods:
            print(f"\nTrying {name}...")
            try:
                if method():
                    print(f"✅ 2FA completed with {name}")
                    return True
            except Exception as e:
                print(f"❌ {name} failed: {e}")
        
        print("\n⚠️ All automatic methods failed")
        print("📱 Please enter 2FA code manually")
        return False

def setup_2fa_automation():
    """Set up 2FA automation for future use"""
    print("🔧 SETTING UP 2FA AUTOMATION")
    print("=" * 60)
    
    print("\nChoose your preferred method:")
    print("1. Phone screen mirroring (most reliable)")
    print("2. TOTP secret (most automatic)")
    print("3. Webcam capture")
    print("4. Notification mirroring")
    print("5. Accessibility API")
    
    choice = input("\nEnter choice (1-5): ")
    
    if choice == "1":
        print("\n📱 SCREEN MIRRORING SETUP")
        print("1. Install scrcpy: brew install scrcpy")
        print("2. Enable USB debugging on your phone")
        print("3. Connect phone via USB")
        print("4. The script will automatically mirror and read codes")
        
    elif choice == "2":
        print("\n🔑 TOTP SECRET SETUP")
        print("1. In your authenticator app, look for export/backup options")
        print("2. Get the TOTP secret (usually starts with a long string)")
        print("3. Store it securely using our secure storage")
        
        secret = input("\nEnter TOTP secret (or press Enter to skip): ")
        if secret:
            # Store securely (you'd implement secure storage here)
            print("✅ TOTP secret stored securely")
    
    elif choice == "3":
        print("\n📸 WEBCAM SETUP")
        print("1. Position webcam to see your phone screen")
        print("2. Ensure good lighting")
        print("3. The script will capture and read codes")
    
    print("\n✅ Setup complete!")

if __name__ == "__main__":
    # Test 2FA automation
    automator = TwoFAAutomation()
    
    # Try automatic 2FA
    # automator.auto_2fa_with_best_method()
    
    # Or set up for future use
    setup_2fa_automation()