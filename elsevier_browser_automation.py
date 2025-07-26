#!/usr/bin/env python3
"""
Elsevier Browser Automation
===========================

Implement Elsevier/ScienceDirect support with browser automation.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys
import time

sys.path.insert(0, str(Path(__file__).parent))

class ElsevierBrowserAutomation:
    def __init__(self):
        self.output_dir = Path("elsevier_test")
        self.output_dir.mkdir(exist_ok=True)
        
    def log(self, message):
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    async def test_elsevier(self):
        """Test Elsevier authentication and download"""
        
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
        
        # Test DOI - real Elsevier paper
        test_doi = "10.1016/j.jcp.2019.07.031"  # Example: Journal of Computational Physics
        
        try:
            async with async_playwright() as p:
                # Launch browser with anti-detection
                browser = await p.chromium.launch(
                    headless=False,  # Visual mode for debugging
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )
                
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                page = await context.new_page()
                
                self.log("\n🔄 STEP 1: Navigate to Elsevier/ScienceDirect")
                
                # Construct ScienceDirect URL from DOI
                sd_url = f"https://www.sciencedirect.com/science/article/pii/{test_doi.split('/')[-1]}"
                self.log(f"   URL: {sd_url}")
                
                await page.goto(sd_url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(5000)
                
                # Take screenshot
                await page.screenshot(path="elsevier_1_initial.png")
                self.log("   Screenshot: elsevier_1_initial.png")
                
                # Check current page
                current_url = page.url
                self.log(f"   Current URL: {current_url}")
                
                self.log("\n🔄 STEP 2: Look for institutional access")
                
                # Look for institutional access button/link
                inst_selectors = [
                    'a:has-text("Access through your institution")',
                    'a:has-text("Institution")',
                    'a:has-text("Get Access")',
                    'button:has-text("Sign in")',
                    'a:has-text("Log in")',
                    '.u-margin-s-bottom a[href*="login"]',
                    'a[href*="institutional"]',
                    'a[title*="institutional"]',
                    '#sign-in-or-purchase-link'
                ]
                
                inst_button = None
                for selector in inst_selectors:
                    try:
                        inst_button = await page.wait_for_selector(selector, timeout=3000, state='visible')
                        if inst_button:
                            button_text = await inst_button.text_content()
                            self.log(f"   Found institutional link: '{button_text}'")
                            break
                    except:
                        continue
                
                if inst_button:
                    self.log("   Clicking institutional access...")
                    await inst_button.click()
                    await page.wait_for_timeout(5000)
                    
                    # Take screenshot after click
                    await page.screenshot(path="elsevier_2_after_inst_click.png")
                    self.log("   Screenshot: elsevier_2_after_inst_click.png")
                    
                    # Check if we need to search for institution
                    current_url = page.url
                    self.log(f"   After click URL: {current_url}")
                    
                    # Look for institution search
                    if 'institutional' in current_url or 'choice' in current_url:
                        self.log("\n🔄 STEP 3: Search for ETH Zurich")
                        
                        # Look for search input
                        search_selectors = [
                            'input[placeholder*="institution"]',
                            'input[name*="institution"]',
                            'input[type="search"]',
                            'input#institutionNameQuery',
                            'input.institution-search',
                            'input[aria-label*="institution"]'
                        ]
                        
                        search_input = None
                        for selector in search_selectors:
                            try:
                                search_input = await page.wait_for_selector(selector, timeout=3000, state='visible')
                                if search_input:
                                    self.log(f"   Found search input: {selector}")
                                    break
                            except:
                                continue
                        
                        if search_input:
                            await search_input.click()
                            await search_input.fill("")
                            await page.wait_for_timeout(500)
                            
                            self.log("   Typing 'ETH Zurich'...")
                            await search_input.type("ETH Zurich", delay=100)
                            await page.wait_for_timeout(3000)
                            
                            # Take screenshot
                            await page.screenshot(path="elsevier_3_search_results.png")
                            self.log("   Screenshot: elsevier_3_search_results.png")
                            
                            # Look for ETH in results
                            eth_selectors = [
                                'a:has-text("ETH Zurich")',
                                'li:has-text("ETH Zurich")',
                                'button:has-text("ETH Zurich")',
                                'div:has-text("Swiss Federal Institute")',
                                '[data-institution*="ETH"]'
                            ]
                            
                            eth_found = False
                            for selector in eth_selectors:
                                try:
                                    eth_option = await page.wait_for_selector(selector, timeout=3000)
                                    if eth_option:
                                        self.log(f"   Found ETH option: {selector}")
                                        await eth_option.click()
                                        eth_found = True
                                        break
                                except:
                                    continue
                            
                            if eth_found:
                                self.log("   ✅ Selected ETH Zurich")
                                await page.wait_for_timeout(10000)
                                
                                # Check for ETH login
                                current_url = page.url
                                self.log(f"\n   Redirected to: {current_url}")
                                
                                if 'ethz.ch' in current_url or 'aai-logon' in current_url:
                                    self.log("\n🔄 STEP 4: ETH Authentication")
                                    
                                    # Fill credentials
                                    username_input = await page.wait_for_selector('input[name="j_username"]', timeout=30000)
                                    await username_input.fill(username)
                                    self.log("   ✓ Filled username")
                                    
                                    password_input = await page.wait_for_selector('input[name="j_password"]', timeout=10000)
                                    await password_input.fill(password)
                                    self.log("   ✓ Filled password")
                                    
                                    submit_button = await page.wait_for_selector('button[type="submit"]', timeout=10000)
                                    await submit_button.click()
                                    self.log("   ✓ Submitted login")
                                    
                                    await page.wait_for_timeout(20000)
                                    
                                    final_url = page.url
                                    self.log(f"\n   Final URL: {final_url}")
                                    
                                    if 'sciencedirect' in final_url:
                                        self.log("\n🎉 ELSEVIER AUTHENTICATION SUCCESSFUL!")
                                        
                                        # Try to download PDF
                                        self.log("\n🔄 STEP 5: Download PDF")
                                        
                                        # Look for PDF download button
                                        pdf_selectors = [
                                            'a[aria-label*="Download PDF"]',
                                            'button[aria-label*="Download PDF"]',
                                            'a:has-text("Download PDF")',
                                            'button:has-text("Download PDF")',
                                            '.pdf-download-btn',
                                            'a[href*=".pdf"]'
                                        ]
                                        
                                        pdf_button = None
                                        for selector in pdf_selectors:
                                            try:
                                                pdf_button = await page.wait_for_selector(selector, timeout=3000)
                                                if pdf_button:
                                                    self.log(f"   Found PDF button: {selector}")
                                                    break
                                            except:
                                                continue
                                        
                                        if pdf_button:
                                            # Setup download
                                            download_happened = False
                                            
                                            async def handle_download(download):
                                                nonlocal download_happened
                                                download_happened = True
                                                filename = f"elsevier_{test_doi.replace('/', '_').replace('.', '_')}.pdf"
                                                save_path = self.output_dir / filename
                                                await download.save_as(str(save_path))
                                                self.log(f"   ✅ Downloaded: {filename}")
                                            
                                            page.on('download', handle_download)
                                            
                                            await pdf_button.click()
                                            await page.wait_for_timeout(10000)
                                            
                                            if download_happened:
                                                self.log("\n🎉 PDF DOWNLOAD SUCCESSFUL!")
                                                await browser.close()
                                                return True
                else:
                    self.log("   ❌ No institutional access button found")
                    
                    # Check if we already have access
                    pdf_button = await page.query_selector('a[aria-label*="Download PDF"]')
                    if pdf_button:
                        self.log("   ℹ️ PDF download button already visible - may have direct access")
                
                await browser.close()
                
        except Exception as e:
            self.log(f"\n💥 Error: {e}")
        
        return False

async def main():
    tester = ElsevierBrowserAutomation()
    success = await tester.test_elsevier()
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 ELSEVIER WORKS!")
        print("=" * 60)
        print("Successfully:")
        print("  ✅ Found institutional access")
        print("  ✅ Selected ETH Zurich")
        print("  ✅ Completed ETH authentication")
        print("  ✅ Downloaded PDF")
    else:
        print("\n⚠️ Elsevier needs further investigation")
        print("Check the screenshots for debugging")

if __name__ == "__main__":
    asyncio.run(main())