#!/usr/bin/env python3
"""
Final Optimized Test
====================

Fix the real issues:
1. IEEE: Investigate why specific DOIs fail authentication when user can access them
2. SIAM: Fix incorrect Cloudflare detection - the page is loading fine!
"""

import sys
import asyncio
import time
import concurrent.futures
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

class FinalOptimizedTest:
    def __init__(self):
        self.output_dir = Path("FINAL_OPTIMIZED_TEST")
        self.output_dir.mkdir(exist_ok=True)
        
    def log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    async def test_ieee_debug(self):
        """Debug IEEE authentication for specific failing DOIs"""
        self.log("🔍 IEEE DEBUG: Investigating specific DOI authentication issues")
        print("=" * 60)
        
        # Test just one failing DOI with detailed debugging
        test_doi = "10.1109/MC.2006.5"
        test_title = "Amdahl's law in the multicore era"
        
        self.log(f"Debugging DOI: {test_doi}")
        self.log(f"Title: {test_title}")
        self.log(f"User confirmed: This paper is accessible with their credentials")
        
        # Get credentials
        try:
            from src.publishers.ieee_publisher import IEEEPublisher
            from src.publishers import AuthenticationConfig
            from src.secure_credential_manager import get_credential_manager
            
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            if not username or not password:
                self.log("❌ No ETH credentials for IEEE")
                return False
                
            self.log(f"✅ Using ETH credentials: {username[:3]}***")
                
        except ImportError as e:
            self.log(f"❌ Cannot import IEEE components: {e}")
            return False
        
        try:
            # Create publisher instance
            auth_config = AuthenticationConfig(
                username=username,
                password=password,
                institutional_login='eth'
            )
            ieee = IEEEPublisher(auth_config)
            
            filename = f"ieee_{test_doi.replace('/', '_').replace('.', '_')}_debug.pdf"
            output_path = self.output_dir / filename
            
            self.log("🔧 Attempting download with extended timeout and debugging...")
            
            # Use ThreadPoolExecutor with very long timeout
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(ieee.download_paper, test_doi, output_path)
                result = future.result(timeout=600)  # 10 minute timeout
            
            if result.success and output_path.exists():
                # Verify PDF
                with open(output_path, 'rb') as f:
                    header = f.read(8)
                    if header.startswith(b'%PDF'):
                        size_kb = output_path.stat().st_size / 1024
                        self.log(f"✅ SUCCESS: Downloaded {filename} ({size_kb:.0f} KB)")
                        self.log("🎉 IEEE authentication issue resolved with longer timeout!")
                        return True
                    else:
                        self.log(f"❌ Invalid PDF downloaded")
                        output_path.unlink()
                        return False
            else:
                error_msg = result.error_message if hasattr(result, 'error_message') else 'Unknown error'
                self.log(f"❌ Still failed: {error_msg}")
                self.log("🔍 This suggests the DOI resolution or specific paper access may be the issue")
                return False
                
        except Exception as e:
            self.log(f"💥 Exception: {e}")
            return False
    
    async def test_siam_fixed(self):
        """Test SIAM with correct logic - no false Cloudflare detection"""
        self.log("🔍 SIAM FIXED: Correct Cloudflare detection and full flow")
        print("=" * 60)
        
        # Test the Shor's algorithm paper
        test_doi = "10.1137/S0097539795293172" 
        test_title = "Polynomial-Time Algorithms for Prime Factorization (Shor)"
        
        # Get credentials
        try:
            from playwright.async_api import async_playwright
            from src.secure_credential_manager import get_credential_manager
            
            cm = get_credential_manager()
            username = cm.get_credential("eth_username")
            password = cm.get_credential("eth_password")
            
            if not username or not password:
                self.log("❌ No ETH credentials for SIAM")
                return False
                
            self.log(f"✅ Using ETH credentials: {username[:3]}***")
                
        except ImportError as e:
            self.log(f"❌ Cannot import SIAM components: {e}")
            return False
        
        self.log(f"\nTesting: {test_doi}")
        self.log(f"Title: {test_title}")
        
        try:
            async with async_playwright() as p:
                # Simple browser setup that was working
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context()
                page = await context.new_page()
                
                # Navigate to SIAM paper
                siam_url = f"https://epubs.siam.org/doi/{test_doi}"
                self.log(f"  Navigating to: {siam_url}")
                await page.goto(siam_url, timeout=90000)
                await page.wait_for_timeout(8000)
                
                # CORRECT Cloudflare detection - check for actual challenge elements
                page_title = await page.title()
                self.log(f"  Page title: '{page_title}'")
                
                # Real Cloudflare challenge detection
                cloudflare_selectors = [
                    'h1:has-text("Verify you are human")',
                    'h2:has-text("Verify you are human")', 
                    '.cf-challenge-running',
                    '#challenge-form',
                    'input[name="cf_challenge_response"]'
                ]
                
                is_cloudflare_challenge = False
                for selector in cloudflare_selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=2000)
                        if element:
                            is_cloudflare_challenge = True
                            break
                    except:
                        continue
                
                if is_cloudflare_challenge:
                    self.log(f"  ❌ REAL CLOUDFLARE CHALLENGE DETECTED")
                    await browser.close()
                    return False
                else:
                    self.log(f"  ✅ NO CLOUDFLARE - Page loaded successfully!")
                
                # Continue with the full SIAM flow
                try:
                    # Look for "GET ACCESS" or institutional access button
                    access_selectors = [
                        'a:has-text("GET ACCESS")',
                        'button:has-text("GET ACCESS")',
                        'a:has-text("Access via your Institution")',
                        'button:has-text("Access via your Institution")'
                    ]
                    
                    access_button = None
                    for selector in access_selectors:
                        try:
                            access_button = await page.wait_for_selector(selector, timeout=5000)
                            if access_button:
                                self.log(f"  ✓ Found access button: {selector}")
                                break
                        except:
                            continue
                    
                    if not access_button:
                        self.log(f"  ❌ No access button found - checking what's on page")
                        await page.screenshot(path="siam_no_access_button.png")
                        await browser.close()
                        return False
                    
                    # Click access button
                    await access_button.click()
                    self.log(f"  ✓ Clicked access button")
                    await page.wait_for_timeout(8000)
                    
                    # Look for institutional access if needed
                    try:
                        inst_button = await page.wait_for_selector('a:has-text("Access via your Institution")', timeout=10000)
                        await inst_button.click()
                        self.log(f"  ✓ Clicked institutional access")
                        await page.wait_for_timeout(8000)
                    except:
                        self.log(f"  - No additional institutional button needed")
                    
                    # Search for ETH
                    search_input = await page.wait_for_selector('input#shibboleth_search', timeout=20000)
                    await search_input.click()
                    await search_input.fill("")
                    await page.wait_for_timeout(1000)
                    await search_input.type("ETH Zurich", delay=150)
                    self.log(f"  ✓ Typed ETH Zurich")
                    await page.wait_for_timeout(5000)
                    
                    # Click ETH option
                    eth_option = await page.wait_for_selector('.ms-res-item a.sso-institution:has-text("ETH Zurich")', timeout=15000)
                    await eth_option.click()
                    self.log(f"  ✓ Clicked ETH option")
                    await page.wait_for_timeout(10000)
                    
                    # ETH login
                    username_input = await page.wait_for_selector('input[name="j_username"]', timeout=30000)
                    await username_input.fill(username)
                    
                    password_input = await page.wait_for_selector('input[name="j_password"]', timeout=10000)
                    await password_input.fill(password)
                    
                    submit_button = await page.wait_for_selector('button[type="submit"]', timeout=10000)
                    await submit_button.click()
                    self.log(f"  ✓ Submitted ETH credentials")
                    await page.wait_for_timeout(20000)
                    
                    # Navigate to PDF
                    pdf_url = siam_url.replace('/doi/', '/doi/epdf/')
                    await page.goto(pdf_url, timeout=90000)
                    self.log(f"  ✓ Navigated to PDF URL")
                    await page.wait_for_timeout(15000)
                    
                    # Setup download handler
                    download_happened = False
                    downloaded_file = None
                    
                    async def handle_download(download):
                        nonlocal download_happened, downloaded_file
                        download_happened = True
                        filename = f"siam_{test_doi.replace('/', '_').replace('.', '_')}_fixed.pdf"
                        save_path = self.output_dir / filename
                        await download.save_as(str(save_path))
                        downloaded_file = save_path
                        self.log(f"  ✓ Download handler triggered: {save_path.name}")
                    
                    page.on('download', handle_download)
                    
                    # Click download button
                    download_button = await page.wait_for_selector('a[title*="Download"]', timeout=15000)
                    await download_button.click()
                    self.log(f"  ✓ Clicked download button")
                    await page.wait_for_timeout(15000)
                    
                    if download_happened and downloaded_file and downloaded_file.exists():
                        with open(downloaded_file, 'rb') as f:
                            header = f.read(8)
                            if header.startswith(b'%PDF'):
                                size_kb = downloaded_file.stat().st_size / 1024
                                self.log(f"  ✅ SUCCESS: {downloaded_file.name} ({size_kb:.0f} KB)")
                                await browser.close()
                                return True
                            else:
                                self.log(f"  ❌ Invalid PDF format")
                    else:
                        self.log(f"  ❌ No download occurred")
                        
                except Exception as e:
                    self.log(f"  ❌ Authentication flow failed: {e}")
                
                await browser.close()
                return False
                
        except Exception as e:
            self.log(f"  💥 Browser exception: {e}")
            return False
    
    async def run_final_test(self):
        """Run the final optimized tests"""
        self.log("🎯 FINAL OPTIMIZED TEST: Fixing the real issues")
        print("=" * 80)
        
        start_time = time.time()
        
        # Debug IEEE issue
        ieee_working = await self.test_ieee_debug()
        
        # Fix SIAM detection
        siam_working = await self.test_siam_fixed()
        
        # Summary
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "=" * 80)
        self.log("🎯 FINAL OPTIMIZED TEST RESULTS")
        print("=" * 80)
        
        self.log(f"Test Duration: {duration/60:.1f} minutes")
        
        if ieee_working:
            self.log(f"✅ IEEE: Successfully resolved authentication issue!")
        else:
            self.log(f"❌ IEEE: Issue persists - may be DOI-specific access restriction")
        
        if siam_working:
            self.log(f"✅ SIAM: Successfully fixed Cloudflare detection and completed flow!")
        else:
            self.log(f"❌ SIAM: Flow still has issues despite correct detection")
        
        # Show files
        pdfs = list(self.output_dir.glob("*.pdf"))
        if pdfs:
            total_size = sum(pdf.stat().st_size for pdf in pdfs) / (1024 * 1024)
            self.log(f"\n📁 PDFs Downloaded: {len(pdfs)} ({total_size:.1f} MB)")
            for pdf in pdfs:
                size_kb = pdf.stat().st_size / 1024
                self.log(f"   {pdf.name} ({size_kb:.0f} KB)")
        
        return {
            'ieee_working': ieee_working,
            'siam_working': siam_working
        }

async def main():
    tester = FinalOptimizedTest()
    results = await tester.run_final_test()
    
    print(f"\n🎯 OPTIMIZATION RESULTS:")
    total_working = sum(results.values())
    
    if total_working == 2:
        print(f"🎉 SUCCESS: Both IEEE and SIAM issues resolved!")
    elif total_working == 1:
        print(f"✅ PARTIAL: 1/2 publisher issues resolved")
    else:
        print(f"❌ Still need more investigation")
    
    print(f"IEEE working: {results['ieee_working']}")
    print(f"SIAM working: {results['siam_working']}")

if __name__ == "__main__":
    asyncio.run(main())