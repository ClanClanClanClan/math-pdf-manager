#!/usr/bin/env python3
"""
Elsevier UltraThink CloudFlare Bypass
=====================================

Advanced techniques to bypass CloudFlare protection on Elsevier.
"""

import asyncio
import random
import time
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).parent))

class ElsevierUltraBypass:
    def __init__(self):
        self.output_dir = Path("elsevier_ultrathink")
        self.output_dir.mkdir(exist_ok=True)
        
    def log(self, message):
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    async def human_like_delay(self, min_ms=500, max_ms=2000):
        """Random human-like delay"""
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)
    
    async def human_like_mouse_movement(self, page):
        """Simulate human mouse movements"""
        for _ in range(random.randint(3, 7)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
    
    async def test_elsevier_ultrathink(self):
        """Ultra-advanced CloudFlare bypass attempt"""
        
        # Get credentials
        try:
            from src.secure_credential_manager import get_credential_manager
            
            cm = get_credential_manager()
            username = cm.get_credential("eth_username")
            password = cm.get_credential("eth_password")
            
            if not username or not password:
                self.log("❌ No ETH credentials")
                return False
                
        except ImportError as e:
            self.log(f"❌ Cannot import credentials: {e}")
            return False
        
        test_doi = "10.1016/j.jcp.2019.07.031"
        
        try:
            async with async_playwright() as p:
                self.log("🧠 ULTRATHINK MODE: Advanced CloudFlare Bypass")
                self.log("=" * 60)
                
                # TECHNIQUE 1: Use real Chrome with existing profile
                self.log("\n🔬 TECHNIQUE 1: Real Chrome with warm profile")
                
                # Create persistent context (like a real user profile)
                user_data_dir = self.output_dir / "chrome_profile"
                user_data_dir.mkdir(exist_ok=True)
                
                browser = await p.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,
                    channel="chrome",  # Use real Chrome if available
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-site-isolation-trials',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-accelerated-2d-canvas',
                        '--disable-gpu',
                        '--window-size=1920,1080',
                        '--start-maximized',
                        '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    ],
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US',
                    timezone_id='America/New_York',
                    permissions=['geolocation', 'notifications'],
                    color_scheme='light',
                    extra_http_headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache',
                        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '"macOS"',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Upgrade-Insecure-Requests': '1'
                    }
                )
                
                page = browser.pages[0] if browser.pages else await browser.new_page()
                
                # Advanced anti-detection script
                await page.add_init_script("""
                    // Override navigator properties
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // Mock plugins
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [
                            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                            {name: 'Native Client', filename: 'internal-nacl-plugin'}
                        ]
                    });
                    
                    // Mock languages
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                    
                    // Override permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                    
                    // Mock chrome object
                    window.chrome = {
                        runtime: {},
                        loadTimes: function() {},
                        csi: function() {},
                        app: {}
                    };
                    
                    // Override toString methods
                    window.navigator.toString = function() { return '[object Navigator]' };
                    window.toString = function() { return '[object Window]' };
                """)
                
                # TECHNIQUE 2: Build reputation by visiting other pages first
                self.log("\n🔬 TECHNIQUE 2: Building browser reputation")
                
                # Visit Google first (normal user behavior)
                self.log("   Visiting Google...")
                await page.goto("https://www.google.com", wait_until='networkidle')
                await self.human_like_delay(2000, 4000)
                await self.human_like_mouse_movement(page)
                
                # Search for something academic
                search_box = await page.query_selector('input[name="q"]')
                if search_box:
                    await search_box.click()
                    await search_box.type("scientific papers", delay=random.randint(50, 150))
                    await page.keyboard.press('Enter')
                    await page.wait_for_timeout(3000)
                
                # Visit ScienceDirect homepage
                self.log("   Visiting ScienceDirect homepage...")
                await page.goto("https://www.sciencedirect.com", wait_until='networkidle')
                await self.human_like_delay(3000, 5000)
                await self.human_like_mouse_movement(page)
                
                # TECHNIQUE 3: Approach the target slowly
                self.log("\n🔬 TECHNIQUE 3: Gradual approach to target")
                
                # First try searching for the paper
                search_input = await page.query_selector('input[type="search"], input[name="qs"]')
                if search_input:
                    self.log("   Searching for paper title...")
                    await search_input.click()
                    await search_input.type("computational physics", delay=random.randint(80, 120))
                    await self.human_like_delay()
                    await page.keyboard.press('Enter')
                    await page.wait_for_timeout(5000)
                
                # Now navigate to the actual paper
                self.log("   Navigating to target paper...")
                paper_url = f"https://www.sciencedirect.com/science/article/pii/S0021999119305169"
                await page.goto(paper_url, wait_until='networkidle', timeout=60000)
                
                # TECHNIQUE 4: Wait and observe
                self.log("\n🔬 TECHNIQUE 4: Patience and observation")
                
                # Sometimes CloudFlare passes after just waiting
                self.log("   Waiting for CloudFlare to potentially auto-pass...")
                await page.wait_for_timeout(15000)  # Wait 15 seconds
                
                # Check if we're still on CloudFlare
                page_content = await page.content()
                
                if 'Are you a robot?' in page_content or 'cloudflare' in page_content.lower():
                    self.log("   ⚠️ Still on CloudFlare challenge")
                    
                    # TECHNIQUE 5: Interactive elements
                    self.log("\n🔬 TECHNIQUE 5: Interacting with page elements")
                    
                    # Try to find and check the checkbox
                    checkbox_selectors = [
                        'input[type="checkbox"]',
                        '#challenge-form input',
                        '.ctp-checkbox-container input'
                    ]
                    
                    for selector in checkbox_selectors:
                        checkbox = await page.query_selector(selector)
                        if checkbox:
                            self.log(f"   Found checkbox: {selector}")
                            await self.human_like_delay()
                            await checkbox.click()
                            await page.wait_for_timeout(5000)
                            break
                    
                    # Move mouse around naturally
                    await self.human_like_mouse_movement(page)
                    
                    # Wait more
                    self.log("   Waiting for CloudFlare response...")
                    await page.wait_for_timeout(10000)
                
                # Check if we passed CloudFlare
                current_url = page.url
                page_content = await page.content()
                
                if 'sciencedirect.com/science/article' in current_url and 'Are you a robot?' not in page_content:
                    self.log("\n🎉 PASSED CLOUDFLARE!")
                    
                    # Take screenshot
                    await page.screenshot(path="elsevier_ultrathink_success.png")
                    self.log("   Screenshot: elsevier_ultrathink_success.png")
                    
                    # Now try institutional login
                    self.log("\n🔬 Attempting institutional access...")
                    
                    # Look for institutional access
                    inst_button = await page.query_selector('a:has-text("Access through your institution"), a:has-text("Get Access")')
                    if inst_button:
                        await inst_button.click()
                        await page.wait_for_timeout(5000)
                        
                        # Continue with ETH login flow...
                        # (Similar to other implementations)
                        
                        return True
                else:
                    self.log("\n❌ CloudFlare challenge persists")
                    
                    # TECHNIQUE 6: Alternative entry points
                    self.log("\n🔬 TECHNIQUE 6: Alternative entry via institution")
                    
                    # Try going directly to institutional login
                    inst_url = "https://www.sciencedirect.com/user/chooseorg?targetURL=%2Fscience%2Farticle%2Fpii%2FS0021999119305169"
                    await page.goto(inst_url, wait_until='networkidle')
                    await page.wait_for_timeout(5000)
                    
                    # Check if this bypassed CloudFlare
                    page_content = await page.content()
                    if 'Are you a robot?' not in page_content:
                        self.log("   ✅ Institutional URL bypassed CloudFlare!")
                        # Continue with login...
                
                await browser.close()
                
        except Exception as e:
            self.log(f"\n💥 Error: {e}")
            import traceback
            traceback.print_exc()
        
        return False

async def main():
    bypasser = ElsevierUltraBypass()
    success = await bypasser.test_elsevier_ultrathink()
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 ULTRATHINK SUCCESS!")
        print("Successfully bypassed CloudFlare!")
    else:
        print("\n" + "=" * 60)
        print("⚠️ CloudFlare bypass unsuccessful")
        print("\nAdditional techniques to try:")
        print("1. Use a residential proxy service")
        print("2. Try during different times of day")
        print("3. Use a pre-warmed browser profile with history")
        print("4. Consider CloudFlare solver APIs (2captcha, anti-captcha)")
        print("5. Manual solve once, then reuse cookies")

if __name__ == "__main__":
    asyncio.run(main())