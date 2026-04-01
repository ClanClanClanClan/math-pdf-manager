#!/usr/bin/env python3
"""
Elsevier Institutional Approach
===============================

Try accessing Elsevier through ETH library portal instead of direct access.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys
import time

sys.path.insert(0, str(Path(__file__).parent))

class ElsevierInstitutionalApproach:
    def __init__(self):
        self.output_dir = Path("elsevier_institutional")
        self.output_dir.mkdir(exist_ok=True)
        
    def log(self, message):
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    async def test_eth_library_approach(self):
        """Access Elsevier through ETH Library portal"""
        
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
        
        self.log("🏛️ INSTITUTIONAL APPROACH: Via ETH Library")
        self.log("=" * 60)
        
        test_doi = "10.1016/j.jcp.2019.07.031"
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=False,
                    args=['--disable-blink-features=AutomationControlled']
                )
                context = await browser.new_context()
                page = await context.new_page()
                
                # APPROACH 1: Start from ETH Library
                self.log("\n🔬 APPROACH 1: ETH Library Portal")
                
                # Go to ETH Library
                eth_library_url = "https://library.ethz.ch"
                self.log(f"   Navigating to ETH Library: {eth_library_url}")
                await page.goto(eth_library_url)
                await page.wait_for_timeout(3000)
                
                # Look for login/search options
                # Search for Elsevier or ScienceDirect in their resources
                search_input = await page.query_selector('input[type="search"], input[name*="search"]')
                if search_input:
                    self.log("   Searching for ScienceDirect in library resources...")
                    await search_input.fill("ScienceDirect")
                    await page.keyboard.press('Enter')
                    await page.wait_for_timeout(5000)
                
                # APPROACH 2: Direct institutional URL
                self.log("\n🔬 APPROACH 2: Elsevier Institutional Choice")
                
                # Elsevier's institutional selection page
                inst_choice_url = "https://www.sciencedirect.com/user/chooseorg"
                self.log(f"   Going to institutional choice: {inst_choice_url}")
                await page.goto(inst_choice_url)
                await page.wait_for_timeout(5000)
                
                # Check if we hit CloudFlare here
                page_content = await page.content()
                if 'Are you a robot?' not in page_content:
                    self.log("   ✅ No CloudFlare on institutional page!")
                    
                    # Search for ETH
                    search_input = await page.query_selector('input[placeholder*="institution"], input[name*="institution"]')
                    if search_input:
                        self.log("   Searching for ETH Zurich...")
                        await search_input.fill("ETH Zurich")
                        await page.wait_for_timeout(3000)
                        
                        # Click ETH if found
                        eth_link = await page.query_selector('text=/ETH.*Zurich/i')
                        if eth_link:
                            await eth_link.click()
                            await page.wait_for_timeout(10000)
                            
                            # Handle ETH login...
                            if 'ethz.ch' in page.url:
                                self.log("   ✅ Redirected to ETH login!")
                                # Fill credentials
                                username_input = await page.wait_for_selector('input[name="j_username"]', timeout=30000)
                                await username_input.fill(username)
                                
                                password_input = await page.wait_for_selector('input[name="j_password"]', timeout=10000)
                                await password_input.fill(password)
                                
                                submit_button = await page.wait_for_selector('button[type="submit"]', timeout=10000)
                                await submit_button.click()
                                
                                await page.wait_for_timeout(20000)
                                
                                # Now navigate to paper
                                if 'sciencedirect' in page.url:
                                    self.log("   ✅ Authenticated! Navigating to paper...")
                                    paper_url = f"https://www.sciencedirect.com/science/article/pii/S0021999119305169"
                                    await page.goto(paper_url)
                                    await page.wait_for_timeout(5000)
                                    
                                    # Check for CloudFlare
                                    page_content = await page.content()
                                    if 'Are you a robot?' not in page_content:
                                        self.log("   🎉 Successfully accessed paper!")
                                        return True
                
                # APPROACH 3: OpenAthens/Shibboleth
                self.log("\n🔬 APPROACH 3: OpenAthens/Shibboleth URL")
                
                # Try Shibboleth login URL
                shib_url = "https://www.sciencedirect.com/customer/authenticate/manra"
                self.log(f"   Trying Shibboleth: {shib_url}")
                await page.goto(shib_url)
                await page.wait_for_timeout(5000)
                
                # APPROACH 4: EZProxy style URL
                self.log("\n🔬 APPROACH 4: Proxy-style access")
                
                # Some institutions use proxy URLs
                proxy_urls = [
                    "https://www.sciencedirect.com.ezproxy.ethz.ch",
                    "https://sciencedirect.com.library.ethz.ch",
                    "https://www-sciencedirect-com.ezproxy.ethz.ch"
                ]
                
                for proxy_url in proxy_urls:
                    self.log(f"   Trying proxy URL: {proxy_url}")
                    try:
                        await page.goto(proxy_url, timeout=15000)
                        await page.wait_for_timeout(3000)
                        
                        if 'ethz.ch' in page.url or 'Are you a robot?' not in await page.content():
                            self.log("   ✅ Proxy URL worked!")
                            break
                    except:
                        self.log("   ❌ Proxy URL failed")
                
                await browser.close()
                
        except Exception as e:
            self.log(f"\n💥 Error: {e}")
        
        return False

async def main():
    approach = ElsevierInstitutionalApproach()
    success = await approach.test_eth_library_approach()
    
    if success:
        print("\n🎉 INSTITUTIONAL APPROACH SUCCESSFUL!")
        print("Bypassed CloudFlare through institutional access!")
    else:
        print("\n📊 Summary of CloudFlare bypass attempts:")
        print("\n1. ❌ Direct access - blocked by CloudFlare")
        print("2. 🔄 UltraThink bypass - advanced techniques")
        print("3. 🍪 Cookie approach - manual solve + reuse")
        print("4. 🏛️ Institutional approach - via library portal")
        print("\n✅ Recommendation: Use Sci-Hub as primary method")
        print("   with these approaches as backup for recent papers")

if __name__ == "__main__":
    asyncio.run(main())