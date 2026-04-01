#!/usr/bin/env python3
"""
Elsevier CloudFlare Fix
=======================

Handle CloudFlare challenge for Elsevier/ScienceDirect.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys
import time

sys.path.insert(0, str(Path(__file__).parent))

class ElsevierCloudFlareFix:
    def __init__(self):
        self.output_dir = Path("elsevier_test")
        self.output_dir.mkdir(exist_ok=True)
        
    def log(self, message):
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    async def test_elsevier(self):
        """Test Elsevier with CloudFlare bypass"""
        
        # Get credentials
        try:
            from src.secure_credential_manager import get_credential_manager
            
            cm = get_credential_manager()
            username = cm.get_credential("eth_username")
            password = cm.get_credential("eth_password")
            
            if not username or not password:
                self.log("❌ No ETH credentials")
                return False
                
            self.log(f"✅ Using ETH credentials: {username[:3]}***")
                
        except ImportError as e:
            self.log(f"❌ Cannot import credentials: {e}")
            return False
        
        # Test with a different approach - use DOI resolver
        test_doi = "10.1016/j.jcp.2019.07.031"
        
        try:
            async with async_playwright() as p:
                # Launch browser with more anti-detection
                browser = await p.chromium.launch(
                    headless=False,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--no-first-run',
                        '--no-default-browser-check',
                        '--disable-dev-shm-usage',
                        '--disable-extensions',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding'
                    ]
                )
                
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080}
                )
                
                # Add anti-webdriver script
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en'],
                    });
                """)
                
                page = await context.new_page()
                
                self.log("\n🔄 APPROACH 1: Try DOI.org redirect")
                
                # First try DOI.org which should redirect
                doi_url = f"https://doi.org/{test_doi}"
                self.log(f"   Navigating to: {doi_url}")
                
                await page.goto(doi_url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(10000)  # Wait for any redirects
                
                current_url = page.url
                self.log(f"   Redirected to: {current_url}")
                
                # Take screenshot
                await page.screenshot(path="elsevier_doi_redirect.png")
                self.log("   Screenshot: elsevier_doi_redirect.png")
                
                # Check if we hit CloudFlare
                page_content = await page.content()
                if 'Are you a robot?' in page_content or 'cloudflare' in page_content.lower():
                    self.log("   ⚠️ Hit CloudFlare challenge")
                    self.log("   Waiting for manual solve...")
                    await page.wait_for_timeout(30000)  # Give user time to solve
                    
                    # Check if we passed
                    page_content = await page.content()
                    if 'Are you a robot?' not in page_content:
                        self.log("   ✅ CloudFlare passed!")
                
                # Now look for institutional access
                if 'sciencedirect' in page.url:
                    self.log("\n🔄 APPROACH 2: Direct institutional URL")
                    
                    # Try direct institutional login URL
                    inst_url = "https://www.sciencedirect.com/user/login?targetURL=%2Fscience%2Farticle%2Fpii%2FS0021999119305285"
                    await page.goto(inst_url, wait_until='domcontentloaded', timeout=60000)
                    await page.wait_for_timeout(5000)
                    
                    await page.screenshot(path="elsevier_inst_login.png")
                    self.log("   Screenshot: elsevier_inst_login.png")
                    
                    # Look for institution selection
                    self.log("\n🔄 Looking for institution selection...")
                    
                    # Try clicking "Sign in via your institution"
                    inst_selectors = [
                        'button:has-text("Sign in via your institution")',
                        'a:has-text("Sign in via your institution")',
                        'button:has-text("Other institution")',
                        'a:has-text("institutional")',
                        '.inst-login-btn'
                    ]
                    
                    for selector in inst_selectors:
                        try:
                            inst_btn = await page.wait_for_selector(selector, timeout=3000)
                            if inst_btn:
                                self.log(f"   Found: {selector}")
                                await inst_btn.click()
                                await page.wait_for_timeout(5000)
                                break
                        except:
                            continue
                    
                    # Search for ETH
                    search_input = await page.query_selector('input[type="search"], input[placeholder*="institution"]')
                    if search_input:
                        self.log("   Found institution search")
                        await search_input.fill("ETH Zurich")
                        await page.wait_for_timeout(3000)
                        
                        # Look for ETH in results
                        eth_result = await page.query_selector('text=/ETH.*Zurich/i')
                        if eth_result:
                            self.log("   Found ETH Zurich!")
                            await eth_result.click()
                            await page.wait_for_timeout(10000)
                            
                            # Continue with ETH auth...
                            current_url = page.url
                            if 'ethz.ch' in current_url:
                                self.log("\n🎉 Redirected to ETH login!")
                                # Fill credentials...
                                username_input = await page.wait_for_selector('input[name="j_username"]', timeout=30000)
                                await username_input.fill(username)
                                
                                password_input = await page.wait_for_selector('input[name="j_password"]', timeout=10000)
                                await password_input.fill(password)
                                
                                submit_button = await page.wait_for_selector('button[type="submit"]', timeout=10000)
                                await submit_button.click()
                                
                                await page.wait_for_timeout(20000)
                                
                                if 'sciencedirect' in page.url:
                                    self.log("\n🎉 ELSEVIER AUTHENTICATION SUCCESSFUL!")
                                    await browser.close()
                                    return True
                
                # Alternative: Try searching directly on ScienceDirect
                self.log("\n🔄 APPROACH 3: Search on ScienceDirect home")
                await page.goto("https://www.sciencedirect.com", wait_until='domcontentloaded')
                await page.wait_for_timeout(10000)
                
                # Look for sign in
                sign_in = await page.query_selector('a:has-text("Sign in"), button:has-text("Sign in")')
                if sign_in:
                    self.log("   Found Sign in button")
                    await sign_in.click()
                    await page.wait_for_timeout(5000)
                
                await browser.close()
                
        except Exception as e:
            self.log(f"\n💥 Error: {e}")
        
        return False

async def main():
    tester = ElsevierCloudFlareFix()
    success = await tester.test_elsevier()
    
    if success:
        print("\n🎉 ELSEVIER WORKS!")
    else:
        print("\n⚠️ Elsevier has CloudFlare protection")
        print("This requires manual solving or advanced bypass techniques")
        print("Consider using Sci-Hub for Elsevier papers instead")

if __name__ == "__main__":
    asyncio.run(main())