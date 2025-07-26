#!/usr/bin/env python3
"""
Detailed Failure Analysis
=========================

Test each publisher thoroughly and report exact DOIs that fail for manual verification.
"""

import sys
import asyncio
import time
import concurrent.futures
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

class DetailedFailureAnalysis:
    def __init__(self):
        self.output_dir = Path("DETAILED_FAILURE_ANALYSIS")
        self.output_dir.mkdir(exist_ok=True)
        self.failed_dois = {}
        self.successful_dois = {}
        
    def log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    async def test_ieee_comprehensive(self):
        """Test IEEE with more papers to identify failing DOIs"""
        self.log("🔍 IEEE COMPREHENSIVE FAILURE ANALYSIS")
        print("=" * 60)
        
        # Expanded IEEE test set
        papers = [
            ('10.1109/5.726791', 'Gradient-based learning applied to document recognition (LeCun CNN)'),
            ('10.1109/JPROC.2018.2820126', 'Graph Signal Processing: Overview, Challenges, and Applications'),
            ('10.1109/MC.2006.5', 'Amdahl\'s law in the multicore era'),
            ('10.1109/JPROC.2016.2515118', 'Computer vision and image understanding'),
            ('10.1109/5.771073', 'Neural networks for pattern recognition'),
            ('10.1109/JPROC.2015.2460651', 'Deep learning architectures'),
            ('10.1109/5.726787', 'Support vector machines'),
            ('10.1109/JPROC.2017.2761740', 'Internet of Things applications'),
            ('10.1109/5.869037', 'Computer graphics algorithms'),
            ('10.1109/JPROC.2016.2571690', 'Artificial intelligence systems')
        ]
        
        # Get credentials
        try:
            from src.publishers.ieee_publisher import IEEEPublisher
            from src.publishers import AuthenticationConfig
            from src.secure_credential_manager import get_credential_manager
            
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            if not username or not password:
                self.log("❌ No ETH credentials for IEEE")
                return
                
            self.log(f"✅ Using ETH credentials: {username[:3]}***@{username.split('@')[1] if '@' in username else 'unknown'}")
                
        except ImportError as e:
            self.log(f"❌ Cannot import IEEE components: {e}")
            return
        
        ieee_successes = []
        ieee_failures = []
        
        for paper_idx, (doi, title) in enumerate(papers):
            self.log(f"\nPaper {paper_idx + 1}/10: {doi}")
            self.log(f"Title: {title}")
            
            try:
                # Create fresh publisher instance
                auth_config = AuthenticationConfig(
                    username=username,
                    password=password,
                    institutional_login='eth'
                )
                ieee = IEEEPublisher(auth_config)
                
                filename = f"ieee_{doi.replace('/', '_').replace('.', '_')}.pdf"
                output_path = self.output_dir / filename
                
                # Use ThreadPoolExecutor for sync function
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(ieee.download_paper, doi, output_path)
                    result = future.result(timeout=300)  # 5 minute timeout per paper
                
                if result.success and output_path.exists():
                    # Verify PDF
                    with open(output_path, 'rb') as f:
                        header = f.read(8)
                        if header.startswith(b'%PDF'):
                            size_kb = output_path.stat().st_size / 1024
                            self.log(f"  ✅ SUCCESS: {filename} ({size_kb:.0f} KB)")
                            ieee_successes.append((doi, title, size_kb))
                        else:
                            self.log(f"  ❌ INVALID PDF: {filename}")
                            ieee_failures.append((doi, title, "Invalid PDF format"))
                            output_path.unlink()
                else:
                    error_msg = result.error_message if hasattr(result, 'error_message') else 'Unknown error'
                    self.log(f"  ❌ FAILED: {error_msg}")
                    ieee_failures.append((doi, title, error_msg))
                    
            except Exception as e:
                self.log(f"  💥 EXCEPTION: {e}")
                ieee_failures.append((doi, title, str(e)))
            
            # Longer delay between papers for stability
            await asyncio.sleep(10)
        
        # Report results
        self.log(f"\n📊 IEEE COMPREHENSIVE RESULTS:")
        self.log(f"   Successful: {len(ieee_successes)}/10")
        self.log(f"   Failed: {len(ieee_failures)}/10")
        
        if ieee_successes:
            self.log(f"\n✅ SUCCESSFUL IEEE DOIs:")
            for doi, title, size in ieee_successes:
                self.log(f"   {doi} - {title[:50]}... ({size:.0f} KB)")
        
        if ieee_failures:
            self.log(f"\n❌ FAILED IEEE DOIs FOR MANUAL VERIFICATION:")
            for doi, title, error in ieee_failures:
                self.log(f"   {doi} - {title[:50]}... (Error: {error})")
        
        self.successful_dois['ieee'] = ieee_successes
        self.failed_dois['ieee'] = ieee_failures
        
        return len(ieee_successes), len(ieee_failures)
    
    async def test_siam_comprehensive(self):
        """Test SIAM with enhanced anti-detection"""
        self.log("🔍 SIAM COMPREHENSIVE FAILURE ANALYSIS")
        print("=" * 60)
        
        # SIAM test papers
        papers = [
            ('10.1137/S0097539795293172', 'Polynomial-Time Algorithms for Prime Factorization (Shor)'),
            ('10.1137/S0097539792240406', 'Complexity theory fundamentals'),
            ('10.1137/0210022', 'Linear programming algorithms'),
            ('10.1137/S0097539700376141', 'Approximation algorithms'),
            ('10.1137/S0097539701399884', 'Graph algorithms and optimization')
        ]
        
        # Get credentials
        try:
            from playwright.async_api import async_playwright
            from src.secure_credential_manager import get_credential_manager
            
            cm = get_credential_manager()
            username = cm.get_credential("eth_username")
            password = cm.get_credential("eth_password")
            
            if not username or not password:
                self.log("❌ No ETH credentials for SIAM")
                return 0, len(papers)
                
            self.log(f"✅ Using ETH credentials: {username[:3]}***@{username.split('@')[1] if '@' in username else 'unknown'}")
                
        except ImportError as e:
            self.log(f"❌ Cannot import SIAM components: {e}")
            return 0, len(papers)
        
        siam_successes = []
        siam_failures = []
        
        for paper_idx, (doi, title) in enumerate(papers):
            self.log(f"\nPaper {paper_idx + 1}/5: {doi}")
            self.log(f"Title: {title}")
            
            try:
                async with async_playwright() as p:
                    # Enhanced anti-detection browser setup
                    browser = await p.chromium.launch(
                        headless=False,  # Keep visible for debugging
                        args=[
                            '--disable-blink-features=AutomationControlled',  # CRITICAL
                            '--disable-web-security',
                            '--disable-features=VizDisplayCompositor',
                            '--no-first-run',
                            '--no-default-browser-check',
                            '--disable-dev-shm-usage',
                            '--disable-extensions',
                            '--disable-background-timer-throttling',
                            '--disable-backgrounding-occluded-windows',
                            '--disable-renderer-backgrounding',
                            '--disable-features=TranslateUI',
                            '--disable-ipc-flooding-protection',
                            '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        ]
                    )
                    
                    context = await browser.new_context(
                        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        viewport={'width': 1920, 'height': 1080},
                        locale='en-US',
                        timezone_id='America/New_York'
                    )
                    
                    # Multiple anti-detection scripts
                    await context.add_init_script("""
                        // Hide webdriver property
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined,
                        });
                        
                        // Hide automation indicators
                        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                        
                        // Override permissions
                        const originalQuery = window.navigator.permissions.query;
                        window.navigator.permissions.query = (parameters) => (
                            parameters.name === 'notifications' ?
                                Promise.resolve({ state: Cypress.env('notification_permission') || 'denied' }) :
                                originalQuery(parameters)
                        );
                    """)
                    
                    page = await context.new_page()
                    
                    # Navigate to SIAM paper
                    siam_url = f"https://epubs.siam.org/doi/{doi}"
                    self.log(f"  Navigating to: {siam_url}")
                    await page.goto(siam_url, timeout=90000)
                    await page.wait_for_timeout(8000)
                    
                    # Check for Cloudflare challenge
                    page_content = await page.content()
                    if 'verify you are human' in page_content.lower() or 'cloudflare' in page_content.lower():
                        self.log(f"  ❌ CLOUDFLARE CHALLENGE DETECTED")
                        siam_failures.append((doi, title, "Cloudflare protection"))
                        await browser.close()
                        continue
                    
                    # Look for institutional access button
                    try:
                        inst_button = await page.wait_for_selector('a:has-text("Access via your Institution")', timeout=20000)
                        await inst_button.click()
                        self.log(f"  ✓ Clicked institutional access")
                        await page.wait_for_timeout(8000)
                    except:
                        self.log(f"  ❌ No institutional access button found")
                        siam_failures.append((doi, title, "No institutional access button"))
                        await browser.close()
                        continue
                    
                    # Search for ETH
                    try:
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
                        
                    except Exception as e:
                        self.log(f"  ❌ ETH search/selection failed: {e}")
                        siam_failures.append((doi, title, f"ETH selection failed: {e}"))
                        await browser.close()
                        continue
                    
                    # ETH login
                    try:
                        username_input = await page.wait_for_selector('input[name="j_username"]', timeout=30000)
                        await username_input.fill(username)
                        
                        password_input = await page.wait_for_selector('input[name="j_password"]', timeout=10000)
                        await password_input.fill(password)
                        
                        submit_button = await page.wait_for_selector('button[type="submit"]', timeout=10000)
                        await submit_button.click()
                        self.log(f"  ✓ Submitted ETH credentials")
                        await page.wait_for_timeout(20000)
                        
                    except Exception as e:
                        self.log(f"  ❌ ETH login failed: {e}")
                        siam_failures.append((doi, title, f"ETH login failed: {e}"))
                        await browser.close()
                        continue
                    
                    # Navigate to PDF
                    try:
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
                            filename = f"siam_{doi.replace('/', '_').replace('.', '_')}.pdf"
                            save_path = self.output_dir / filename
                            await download.save_as(str(save_path))
                            downloaded_file = save_path
                        
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
                                    siam_successes.append((doi, title, size_kb))
                                else:
                                    self.log(f"  ❌ INVALID PDF")
                                    siam_failures.append((doi, title, "Invalid PDF format"))
                        else:
                            self.log(f"  ❌ NO DOWNLOAD OCCURRED")
                            siam_failures.append((doi, title, "No download occurred"))
                            
                    except Exception as e:
                        self.log(f"  ❌ PDF download failed: {e}")
                        siam_failures.append((doi, title, f"PDF download failed: {e}"))
                    
                    await browser.close()
                    
            except Exception as e:
                self.log(f"  💥 BROWSER EXCEPTION: {e}")
                siam_failures.append((doi, title, f"Browser exception: {e}"))
            
            # Long delay between papers for stability
            await asyncio.sleep(20)
        
        # Report results
        self.log(f"\n📊 SIAM COMPREHENSIVE RESULTS:")
        self.log(f"   Successful: {len(siam_successes)}/5")
        self.log(f"   Failed: {len(siam_failures)}/5")
        
        if siam_successes:
            self.log(f"\n✅ SUCCESSFUL SIAM DOIs:")
            for doi, title, size in siam_successes:
                self.log(f"   {doi} - {title[:50]}... ({size:.0f} KB)")
        
        if siam_failures:
            self.log(f"\n❌ FAILED SIAM DOIs FOR MANUAL VERIFICATION:")
            for doi, title, error in siam_failures:
                self.log(f"   {doi} - {title[:50]}... (Error: {error})")
        
        self.successful_dois['siam'] = siam_successes
        self.failed_dois['siam'] = siam_failures
        
        return len(siam_successes), len(siam_failures)
    
    async def run_detailed_analysis(self):
        """Run comprehensive failure analysis"""
        self.log("🔍 DETAILED FAILURE ANALYSIS: Identifying exact failing DOIs")
        print("=" * 80)
        
        start_time = time.time()
        
        # Test IEEE comprehensively
        ieee_success, ieee_fail = await self.test_ieee_comprehensive()
        
        # Test SIAM comprehensively  
        siam_success, siam_fail = await self.test_siam_comprehensive()
        
        # Final comprehensive report
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "=" * 80)
        self.log("🎯 DETAILED FAILURE ANALYSIS RESULTS")
        print("=" * 80)
        
        # Show files created
        pdfs = list(self.output_dir.glob("*.pdf"))
        total_size = sum(pdf.stat().st_size for pdf in pdfs) / (1024 * 1024)
        
        self.log(f"Analysis Duration: {duration/60:.1f} minutes")
        self.log(f"PDFs Downloaded: {len(pdfs)} ({total_size:.1f} MB)")
        
        # IEEE Summary
        self.log(f"\n📊 IEEE DETAILED RESULTS:")
        self.log(f"   Success Rate: {ieee_success}/{ieee_success + ieee_fail} ({ieee_success/(ieee_success + ieee_fail)*100:.1f}%)")
        
        # SIAM Summary
        self.log(f"\n📊 SIAM DETAILED RESULTS:")
        self.log(f"   Success Rate: {siam_success}/{siam_success + siam_fail} ({siam_success/(siam_success + siam_fail)*100:.1f}%)")
        
        # Critical: List all failed DOIs for manual verification
        self.log(f"\n🔍 MANUAL VERIFICATION NEEDED:")
        self.log(f"Please test these DOIs manually with your credentials:")
        
        if 'ieee' in self.failed_dois and self.failed_dois['ieee']:
            self.log(f"\n❌ IEEE DOIs to verify manually:")
            for doi, title, error in self.failed_dois['ieee']:
                self.log(f"   DOI: {doi}")
                self.log(f"   Title: {title}")
                self.log(f"   Error: {error}")
                self.log(f"   URL: https://ieeexplore.ieee.org/document/{doi.split('/')[-1]}")
                print()
        
        if 'siam' in self.failed_dois and self.failed_dois['siam']:
            self.log(f"\n❌ SIAM DOIs to verify manually:")
            for doi, title, error in self.failed_dois['siam']:
                self.log(f"   DOI: {doi}")
                self.log(f"   Title: {title}")
                self.log(f"   Error: {error}")
                self.log(f"   URL: https://epubs.siam.org/doi/{doi}")
                print()
        
        return {
            'ieee': (ieee_success, ieee_fail),
            'siam': (siam_success, siam_fail),
            'failed_dois': self.failed_dois
        }

async def main():
    analyzer = DetailedFailureAnalysis()
    results = await analyzer.run_detailed_analysis()
    
    total_success = sum(r[0] for r in results.values() if isinstance(r, tuple))
    total_fail = sum(r[1] for r in results.values() if isinstance(r, tuple))
    
    print(f"\n🎯 FINAL DETAILED ANALYSIS:")
    print(f"Total Success: {total_success}")
    print(f"Total Failures: {total_fail}")
    print(f"Overall Rate: {total_success/(total_success + total_fail)*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())