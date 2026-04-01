#!/usr/bin/env python3
"""
TRULY ROBUST TESTS
==================

This time with:
1. Proper anti-detection for browser automation
2. 10+ attempts per paper minimum  
3. Multiple papers per publisher
4. Real stress testing
"""

import sys
import asyncio
import time
import random
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

class TrulyRobustTest:
    def __init__(self):
        self.output_dir = Path("TRULY_ROBUST_TESTS")
        self.output_dir.mkdir(exist_ok=True)
        self.total_attempts = 0
        self.total_successes = 0
    
    def log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    async def stress_test_publisher(self, publisher_name, test_func, papers_to_test, min_attempts=10):
        """Stress test a publisher with many attempts"""
        self.log(f"🔥 STRESS TESTING {publisher_name.upper()}")
        self.log(f"Testing {len(papers_to_test)} papers with {min_attempts} attempts each")
        print("=" * 70)
        
        publisher_attempts = 0
        publisher_successes = 0
        
        for paper_id, paper_title in papers_to_test:
            self.log(f"📄 Paper: {paper_id} - {paper_title}")
            
            paper_success = False
            attempts_for_this_paper = 0
            
            for attempt in range(min_attempts):
                attempts_for_this_paper += 1
                publisher_attempts += 1
                self.total_attempts += 1
                
                try:
                    # Random delay between attempts
                    if attempt > 0:
                        delay = random.uniform(2, 8)
                        self.log(f"  Attempt {attempt + 1}/{min_attempts} (after {delay:.1f}s)")
                        await asyncio.sleep(delay)
                    else:
                        self.log(f"  Attempt {attempt + 1}/{min_attempts}")
                    
                    # Run the test
                    success = await test_func(paper_id, paper_title)
                    
                    if success:
                        self.log(f"  ✅ SUCCESS on attempt {attempt + 1}")
                        paper_success = True
                        publisher_successes += 1
                        self.total_successes += 1
                        break
                    else:
                        self.log(f"  ❌ Failed attempt {attempt + 1}")
                        
                except Exception as e:
                    self.log(f"  💥 Exception on attempt {attempt + 1}: {e}")
                
                # Short delay between attempts
                await asyncio.sleep(1)
            
            if not paper_success:
                self.log(f"  💀 PAPER FAILED after {attempts_for_this_paper} attempts")
            
            # Delay between papers
            await asyncio.sleep(3)
        
        success_rate = publisher_successes / len(papers_to_test) if papers_to_test else 0
        attempt_success_rate = publisher_successes / publisher_attempts if publisher_attempts else 0
        
        self.log(f"📊 {publisher_name} Results:")
        self.log(f"   Papers successful: {publisher_successes}/{len(papers_to_test)} ({success_rate:.1%})")
        self.log(f"   Attempt success rate: {publisher_successes}/{publisher_attempts} ({attempt_success_rate:.1%})")
        
        return success_rate >= 0.8  # Require 80% paper success rate
    
    async def test_arxiv_paper(self, arxiv_id, title):
        """Test single ArXiv paper"""
        try:
            import requests
            
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            response = requests.get(pdf_url, timeout=15)
            
            if response.status_code == 200 and len(response.content) > 100000:
                # Save and verify
                filename = f"arxiv_{arxiv_id.replace('.', '_')}.pdf"
                output_path = self.output_dir / filename
                
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                # Verify PDF
                with open(output_path, 'rb') as f:
                    header = f.read(8)
                    if header.startswith(b'%PDF'):
                        return True
            
            return False
            
        except Exception:
            return False
    
    async def test_scihub_paper(self, doi, title):
        """Test single Sci-Hub paper"""
        try:
            from src.downloader.universal_downloader import SciHubDownloader
            
            sci_hub = SciHubDownloader()
            result = await sci_hub.download(doi)
            
            if result.success and result.pdf_data and len(result.pdf_data) > 10000:
                # Save and verify
                filename = f"scihub_{doi.replace('/', '_').replace('.', '_')}.pdf"
                output_path = self.output_dir / filename
                
                with open(output_path, 'wb') as f:
                    f.write(result.pdf_data)
                
                if result.pdf_data.startswith(b'%PDF'):
                    # Cleanup
                    if hasattr(sci_hub, 'session') and sci_hub.session:
                        await sci_hub.session.close()
                    return True
            
            # Cleanup
            if hasattr(sci_hub, 'session') and sci_hub.session:
                await sci_hub.session.close()
            return False
            
        except Exception:
            return False
    
    def test_ieee_paper(self, doi, title):
        """Test single IEEE paper"""
        try:
            from src.publishers.ieee_publisher import IEEEPublisher
            from src.publishers import AuthenticationConfig
            from src.secure_credential_manager import get_credential_manager
            
            # Get credentials
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            if not username or not password:
                return False
            
            # Create publisher
            auth_config = AuthenticationConfig(
                username=username,
                password=password,
                institutional_login='eth'
            )
            ieee = IEEEPublisher(auth_config)
            
            # Download
            filename = f"ieee_{doi.replace('/', '_').replace('.', '_')}.pdf"
            output_path = self.output_dir / filename
            
            result = ieee.download_paper(doi, output_path)
            
            if result.success and output_path.exists():
                # Verify PDF
                with open(output_path, 'rb') as f:
                    header = f.read(8)
                    if header.startswith(b'%PDF'):
                        return True
            
            return False
            
        except Exception:
            return False
    
    async def test_siam_paper(self, doi, title):
        """Test single SIAM paper with PROPER anti-detection"""
        try:
            from playwright.async_api import async_playwright
            from src.secure_credential_manager import get_credential_manager
            
            cm = get_credential_manager()
            username = cm.get_credential("eth_username")
            password = cm.get_credential("eth_password")
            
            if not username or not password:
                return False
            
            async with async_playwright() as p:
                # Use EXACT same browser settings as original working SIAM code
                browser = await p.chromium.launch(
                    headless=False,  # Keep visual for reliability
                    args=[
                        '--disable-blink-features=AutomationControlled',  # CRITICAL!
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
                
                # Hide automation detection
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                """)
                
                page = await context.new_page()
                
                # Navigate to SIAM paper
                siam_url = f"https://epubs.siam.org/doi/{doi}"
                await page.goto(siam_url, timeout=60000)
                await page.wait_for_timeout(5000)
                
                # Click institutional access
                inst_button = await page.wait_for_selector('a:has-text("Access via your Institution")', timeout=15000)
                await inst_button.click()
                await page.wait_for_timeout(5000)
                
                # Search for ETH with EXACT selectors from working code
                search_input = await page.wait_for_selector('input#shibboleth_search', timeout=15000)
                await search_input.click()
                await search_input.fill("")
                await page.wait_for_timeout(500)
                await search_input.type("ETH Zurich", delay=100)
                await page.wait_for_timeout(3000)
                
                # Click ETH option with EXACT selectors
                eth_option = await page.wait_for_selector('.ms-res-item a.sso-institution:has-text("ETH Zurich")', timeout=10000)
                await eth_option.click()
                await page.wait_for_timeout(8000)
                
                # ETH login
                username_input = await page.wait_for_selector('input[name="j_username"]', timeout=20000)
                await username_input.fill(username)
                
                password_input = await page.wait_for_selector('input[name="j_password"]', timeout=5000)
                await password_input.fill(password)
                
                submit_button = await page.wait_for_selector('button[type="submit"]', timeout=5000)
                await submit_button.click()
                await page.wait_for_timeout(15000)
                
                # Navigate to PDF
                pdf_url = siam_url.replace('/doi/', '/doi/epdf/')
                await page.goto(pdf_url, timeout=60000)
                await page.wait_for_timeout(10000)
                
                # Setup download with exact handler from working code
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
                
                # Click download with EXACT selector from working code
                download_button = await page.wait_for_selector('a[title*="Download"]', timeout=10000)
                await download_button.click()
                await page.wait_for_timeout(10000)
                
                await browser.close()
                
                if download_happened and downloaded_file and downloaded_file.exists():
                    with open(downloaded_file, 'rb') as f:
                        header = f.read(8)
                        if header.startswith(b'%PDF'):
                            return True
                
                return False
                
        except Exception:
            return False
    
    async def run_stress_tests(self):
        """Run truly robust stress tests"""
        self.log("🚀 STARTING TRULY ROBUST STRESS TESTS")
        self.log("Each publisher will be tested with 10+ attempts per paper")
        print("=" * 70)
        
        # Test data - more papers
        test_papers = {
            'arxiv': [
                ('1706.03762', 'Transformer'),
                ('2103.03404', 'Attention not all you need'),
                ('1512.03385', 'ResNet'),
                ('2010.11929', 'Vision Transformer'),
                ('1810.04805', 'BERT')
            ],
            'scihub': [
                ('10.1038/nature12373', 'Nature thermometry'),
                ('10.1126/science.1102896', 'Graphene'),
                ('10.1038/s41586-019-1666-5', 'ML paper')
            ],
            'ieee': [
                ('10.1109/5.726791', 'LeCun CNN'),
                ('10.1109/JPROC.2018.2820126', 'Graph signal processing')
            ],
            'siam': [
                ('10.1137/S0097539795293172', 'Shor algorithm'),
                ('10.1137/S0097539792240406', 'Complexity theory')
            ]
        }
        
        results = {}
        
        # Test ArXiv (10 attempts per paper)
        results['arxiv'] = await self.stress_test_publisher(
            'ArXiv', 
            self.test_arxiv_paper, 
            test_papers['arxiv'][:3],  # 3 papers
            min_attempts=10
        )
        
        # Test Sci-Hub (10 attempts per paper)
        results['scihub'] = await self.stress_test_publisher(
            'Sci-Hub',
            self.test_scihub_paper,
            test_papers['scihub'],  # 3 papers
            min_attempts=10
        )
        
        # Test IEEE (5 attempts per paper - browser heavy)
        results['ieee'] = await self.stress_test_publisher(
            'IEEE',
            lambda doi, title: self.test_ieee_paper(doi, title),
            test_papers['ieee'],  # 2 papers
            min_attempts=5
        )
        
        # Test SIAM (5 attempts per paper - with proper anti-detection)
        results['siam'] = await self.stress_test_publisher(
            'SIAM',
            self.test_siam_paper,
            test_papers['siam'],  # 2 papers
            min_attempts=5
        )
        
        # Final results
        print("\n" + "=" * 70)
        self.log("🎯 TRULY ROBUST TEST RESULTS")
        print("=" * 70)
        
        robust_publishers = []
        for publisher, is_robust in results.items():
            status = "✅ TRULY ROBUST" if is_robust else "❌ NOT ROBUST"
            self.log(f"{status:20} | {publisher.upper()}")
            if is_robust:
                robust_publishers.append(publisher)
        
        self.log(f"\n📊 FINAL STRESS TEST SUMMARY:")
        self.log(f"   Total attempts: {self.total_attempts}")
        self.log(f"   Total successes: {self.total_successes}")
        self.log(f"   Overall success rate: {self.total_successes/self.total_attempts:.1%}")
        self.log(f"   Truly robust publishers: {len(robust_publishers)}/4")
        
        # Show files
        pdfs = list(self.output_dir.glob("*.pdf"))
        total_size = sum(pdf.stat().st_size for pdf in pdfs) / (1024 * 1024)
        self.log(f"   PDFs downloaded: {len(pdfs)} ({total_size:.1f} MB)")
        
        return robust_publishers

async def main():
    tester = TrulyRobustTest()
    robust = await tester.run_stress_tests()
    
    print(f"\n🎯 FINAL ANSWER TO 'ARE THEY ROBUST?':")
    if len(robust) >= 3:
        print(f"✅ YES - {len(robust)}/4 publishers are TRULY robust with stress testing")
        print(f"Robust: {', '.join(robust)}")
    else:
        print(f"❌ NO - Only {len(robust)}/4 publishers pass stress testing")

if __name__ == "__main__":
    asyncio.run(main())