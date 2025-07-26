#!/usr/bin/env python3
"""
ROBUST PUBLISHER TESTS
======================

Test each publisher with multiple papers, multiple attempts, and robust error handling.
Each publisher must prove it can reliably download different papers.
"""

import sys
import asyncio
import time
import random
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

# Test data - multiple papers per publisher
TEST_PAPERS = {
    'arxiv': [
        ('1706.03762', 'Attention is All You Need'),
        ('2103.03404', 'Attention is not all you need'),
        ('1512.03385', 'Deep Residual Learning'),
        ('2010.11929', 'An Image is Worth 16x16 Words'),
        ('1810.04805', 'BERT')
    ],
    'scihub': [
        ('10.1038/nature12373', 'Nanometre-scale thermometry'),
        ('10.1126/science.1102896', 'Graphene discovery'),
        ('10.1038/s41586-019-1666-5', 'Machine learning paper'),
        ('10.1126/science.1243982', 'CRISPR paper'),
        ('10.1038/nature25778', 'AI paper')
    ],
    'ieee': [
        ('10.1109/5.726791', 'Gradient-based learning'),
        ('10.1109/JPROC.2018.2820126', 'Graph signal processing'),
        ('10.1109/MC.2006.5', 'Amdahl\'s law'),
        ('10.1109/JPROC.2016.2515118', 'Computer vision'),
        ('10.1109/5.771073', 'Neural networks')
    ],
    'siam': [
        ('10.1137/S0097539795293172', 'Shor quantum algorithm'),
        ('10.1137/S0097539792240406', 'Complexity theory'),
        ('10.1137/0210022', 'Linear programming'),
        ('10.1137/S0097539700376141', 'Approximation algorithms'),
        ('10.1137/S0097539701399884', 'Graph algorithms')
    ]
}

class RobustTest:
    def __init__(self):
        self.results = []
        self.output_dir = Path("ROBUST_TESTS")
        self.output_dir.mkdir(exist_ok=True)
    
    def log(self, message):
        """Log with timestamp"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    async def test_arxiv_robust(self, max_attempts=3):
        """Test ArXiv with multiple papers"""
        self.log("🧪 TESTING ARXIV (Multiple Papers)")
        print("=" * 60)
        
        successes = 0
        papers_tested = TEST_PAPERS['arxiv'][:3]  # Test 3 papers
        
        for arxiv_id, title in papers_tested:
            self.log(f"Testing {arxiv_id}: {title}")
            
            for attempt in range(max_attempts):
                try:
                    import requests
                    
                    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                    
                    # Add random delay to avoid rate limiting
                    if attempt > 0:
                        delay = random.uniform(2, 5)
                        self.log(f"  Attempt {attempt + 1} after {delay:.1f}s delay")
                        await asyncio.sleep(delay)
                    
                    response = requests.get(pdf_url, timeout=30)
                    
                    if response.status_code == 200 and len(response.content) > 50000:
                        # Save PDF
                        filename = f"arxiv_{arxiv_id.replace('.', '_')}.pdf"
                        output_path = self.output_dir / filename
                        
                        with open(output_path, 'wb') as f:
                            f.write(response.content)
                        
                        # Verify it's a real PDF
                        with open(output_path, 'rb') as f:
                            header = f.read(8)
                            if header.startswith(b'%PDF'):
                                size_kb = len(response.content) / 1024
                                self.log(f"  ✅ SUCCESS: {filename} ({size_kb:.0f} KB)")
                                successes += 1
                                break
                            else:
                                self.log(f"  ❌ Invalid PDF header: {header}")
                    else:
                        self.log(f"  ❌ HTTP {response.status_code} or size {len(response.content)}")
                        
                except Exception as e:
                    self.log(f"  ❌ Attempt {attempt + 1} failed: {e}")
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(2)
            
            # Small delay between papers
            await asyncio.sleep(1)
        
        success_rate = successes / len(papers_tested)
        self.log(f"📊 ArXiv: {successes}/{len(papers_tested)} papers ({success_rate:.1%})")
        return success_rate >= 0.6  # 60% success rate required
    
    async def test_scihub_robust(self, max_attempts=3):
        """Test Sci-Hub with multiple papers"""
        self.log("🧪 TESTING SCI-HUB (Multiple Papers)")
        print("=" * 60)
        
        successes = 0  
        papers_tested = TEST_PAPERS['scihub'][:3]  # Test 3 papers
        
        try:
            from src.downloader.universal_downloader import SciHubDownloader
        except ImportError:
            self.log("❌ SciHubDownloader not available")
            return False
        
        for doi, title in papers_tested:
            self.log(f"Testing {doi}: {title}")
            
            for attempt in range(max_attempts):
                try:
                    sci_hub = SciHubDownloader()
                    
                    # Add delay between attempts
                    if attempt > 0:
                        delay = random.uniform(3, 8)
                        self.log(f"  Attempt {attempt + 1} after {delay:.1f}s delay")
                        await asyncio.sleep(delay)
                    
                    result = await sci_hub.download(doi)
                    
                    if result.success and result.pdf_data:
                        # Save PDF
                        filename = f"scihub_{doi.replace('/', '_').replace('.', '_')}.pdf"
                        output_path = self.output_dir / filename
                        
                        with open(output_path, 'wb') as f:
                            f.write(result.pdf_data)
                        
                        # Verify
                        if result.pdf_data.startswith(b'%PDF'):
                            size_kb = len(result.pdf_data) / 1024
                            self.log(f"  ✅ SUCCESS: {filename} ({size_kb:.0f} KB)")
                            successes += 1
                            
                            # Cleanup
                            if hasattr(sci_hub, 'session') and sci_hub.session:
                                await sci_hub.session.close()
                            break
                        else:
                            self.log("  ❌ Invalid PDF data")
                    else:
                        self.log(f"  ❌ Download failed: {result.error if hasattr(result, 'error') else 'Unknown'}")
                    
                    # Always cleanup
                    if hasattr(sci_hub, 'session') and sci_hub.session:
                        await sci_hub.session.close()
                        
                except Exception as e:
                    self.log(f"  ❌ Attempt {attempt + 1} failed: {e}")
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(3)
            
            # Delay between papers
            await asyncio.sleep(2)
        
        success_rate = successes / len(papers_tested)
        self.log(f"📊 Sci-Hub: {successes}/{len(papers_tested)} papers ({success_rate:.1%})")
        return success_rate >= 0.6
    
    def test_ieee_robust(self, max_attempts=2):
        """Test IEEE with multiple papers (fewer attempts due to browser overhead)"""
        self.log("🧪 TESTING IEEE (Multiple Papers)")
        print("=" * 60)
        
        successes = 0
        papers_tested = TEST_PAPERS['ieee'][:2]  # Test 2 papers (browser tests are slower)
        
        try:
            from src.publishers.ieee_publisher import IEEEPublisher
            from src.publishers import AuthenticationConfig
            from src.secure_credential_manager import get_credential_manager
        except ImportError:
            self.log("❌ IEEE components not available")
            return False
        
        # Get credentials once
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        if not username or not password:
            self.log("❌ No ETH credentials")
            return False
        
        for doi, title in papers_tested:
            self.log(f"Testing {doi}: {title}")
            
            for attempt in range(max_attempts):
                try:
                    # Create fresh publisher instance
                    auth_config = AuthenticationConfig(
                        username=username,
                        password=password,
                        institutional_login='eth'
                    )
                    ieee = IEEEPublisher(auth_config)
                    
                    if attempt > 0:
                        self.log(f"  Attempt {attempt + 1} (browser may open)")
                        time.sleep(5)  # Longer delay for browser tests
                    
                    # Download
                    filename = f"ieee_{doi.replace('/', '_').replace('.', '_')}.pdf"
                    output_path = self.output_dir / filename
                    
                    result = ieee.download_paper(doi, output_path)
                    
                    if result.success and output_path.exists():
                        # Verify PDF
                        with open(output_path, 'rb') as f:
                            header = f.read(8)
                            if header.startswith(b'%PDF'):
                                size_kb = output_path.stat().st_size / 1024
                                self.log(f"  ✅ SUCCESS: {filename} ({size_kb:.0f} KB)")
                                successes += 1
                                break
                            else:
                                self.log(f"  ❌ Invalid PDF: {header}")
                                output_path.unlink()
                    else:
                        error_msg = result.error_message if hasattr(result, 'error_message') else 'Unknown'
                        self.log(f"  ❌ Download failed: {error_msg}")
                        
                except Exception as e:
                    self.log(f"  ❌ Attempt {attempt + 1} failed: {e}")
                    if attempt < max_attempts - 1:
                        time.sleep(10)  # Longer delay for browser recovery
            
            # Delay between papers for browser cleanup
            time.sleep(5)
        
        success_rate = successes / len(papers_tested)
        self.log(f"📊 IEEE: {successes}/{len(papers_tested)} papers ({success_rate:.1%})")
        return success_rate >= 0.5  # 50% for browser tests (more lenient)
    
    async def test_siam_robust(self, max_attempts=2):
        """Test SIAM with multiple papers using direct browser automation"""
        self.log("🧪 TESTING SIAM (Multiple Papers)")
        print("=" * 60)
        
        try:
            from playwright.async_api import async_playwright
            from src.secure_credential_manager import get_credential_manager
        except ImportError:
            self.log("❌ Playwright or credentials not available")
            return False
        
        # Get credentials
        cm = get_credential_manager()
        username = cm.get_credential("eth_username")
        password = cm.get_credential("eth_password")
        
        if not username or not password:
            self.log("❌ No ETH credentials")
            return False
        
        successes = 0
        papers_tested = TEST_PAPERS['siam'][:2]  # Test 2 papers
        
        for doi, title in papers_tested:
            self.log(f"Testing {doi}: {title}")
            
            for attempt in range(max_attempts):
                try:
                    if attempt > 0:
                        self.log(f"  Attempt {attempt + 1} (new browser session)")
                        await asyncio.sleep(10)
                    
                    # Use direct browser automation
                    async with async_playwright() as p:
                        browser = await p.chromium.launch(headless=False)
                        context = await browser.new_context()
                        page = await context.new_page()
                        
                        # Navigate to paper
                        siam_url = f"https://epubs.siam.org/doi/{doi}"
                        await page.goto(siam_url, timeout=60000)
                        await page.wait_for_timeout(3000)
                        
                        # Institutional access
                        inst_button = await page.wait_for_selector('a:has-text("Access via your Institution")', timeout=15000)
                        await inst_button.click()
                        await page.wait_for_timeout(5000)
                        
                        # Search ETH
                        search_input = await page.wait_for_selector('input#shibboleth_search', timeout=15000)
                        await search_input.fill("ETH Zurich")
                        await page.wait_for_timeout(3000)
                        
                        # Click ETH option
                        eth_selectors = [
                            '.ms-res-item a:has-text("ETH Zurich")',
                            'a.sso-institution:has-text("ETH Zurich")',
                            'text="ETH Zurich"'
                        ]
                        
                        eth_clicked = False
                        for selector in eth_selectors:
                            try:
                                eth_option = await page.wait_for_selector(selector, timeout=5000)
                                await eth_option.click()
                                eth_clicked = True
                                break
                            except:
                                continue
                        
                        if not eth_clicked:
                            self.log("  ❌ Could not find ETH option")
                            await browser.close()
                            continue
                        
                        await page.wait_for_timeout(8000)
                        
                        # ETH login
                        try:
                            username_input = await page.wait_for_selector('input[name="j_username"]', timeout=20000)
                            await username_input.fill(username)
                            
                            password_input = await page.wait_for_selector('input[name="j_password"]', timeout=5000)
                            await password_input.fill(password)
                            
                            submit_button = await page.wait_for_selector('button[type="submit"]', timeout=5000)
                            await submit_button.click()
                            await page.wait_for_timeout(15000)
                        except Exception as e:
                            self.log(f"  ❌ ETH login failed: {e}")
                            await browser.close()
                            continue
                        
                        # Navigate to PDF
                        pdf_url = siam_url.replace('/doi/', '/doi/epdf/')
                        await page.goto(pdf_url, timeout=60000)
                        await page.wait_for_timeout(10000)
                        
                        # Setup download
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
                        
                        # Find and click download button
                        download_selectors = [
                            'a[aria-label*="Download"]',
                            'button[aria-label*="Download"]',
                            'a[title*="Download"]',
                            'button[title*="Download"]'
                        ]
                        
                        download_clicked = False
                        for selector in download_selectors:
                            try:
                                download_button = await page.wait_for_selector(selector, timeout=5000, state='visible')
                                await download_button.click()
                                download_clicked = True
                                break
                            except:
                                continue
                        
                        if download_clicked:
                            await page.wait_for_timeout(10000)
                            
                            if download_happened and downloaded_file and downloaded_file.exists():
                                # Verify PDF
                                with open(downloaded_file, 'rb') as f:
                                    header = f.read(8)
                                    if header.startswith(b'%PDF'):
                                        size_kb = downloaded_file.stat().st_size / 1024
                                        self.log(f"  ✅ SUCCESS: {downloaded_file.name} ({size_kb:.0f} KB)")
                                        successes += 1
                                        await browser.close()
                                        break
                        
                        self.log("  ❌ Download did not complete successfully")
                        await browser.close()
                        
                except Exception as e:
                    self.log(f"  ❌ Attempt {attempt + 1} failed: {e}")
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(15)
            
            # Delay between papers
            await asyncio.sleep(10)
        
        success_rate = successes / len(papers_tested)
        self.log(f"📊 SIAM: {successes}/{len(papers_tested)} papers ({success_rate:.1%})")
        return success_rate >= 0.5
    
    async def run_all_tests(self):
        """Run all robust tests"""
        self.log("🚀 STARTING ROBUST PUBLISHER TESTS")
        self.log("Testing multiple papers per publisher with retry logic")
        print("=" * 70)
        
        # Run tests
        results = {}
        
        # Test in order of reliability
        results['arxiv'] = await self.test_arxiv_robust()
        await asyncio.sleep(2)
        
        results['scihub'] = await self.test_scihub_robust()
        await asyncio.sleep(2)
        
        results['ieee'] = self.test_ieee_robust()
        await asyncio.sleep(2)
        
        results['siam'] = await self.test_siam_robust()
        
        # Final summary
        print("\n" + "=" * 70)
        self.log("🎯 ROBUST TEST RESULTS")
        print("=" * 70)
        
        working_publishers = []
        for publisher, success in results.items():
            status = "✅ ROBUST" if success else "❌ UNRELIABLE"
            self.log(f"{status:15} | {publisher.upper()}")
            if success:
                working_publishers.append(publisher)
        
        # Show downloaded files
        pdfs = list(self.output_dir.glob("*.pdf"))
        total_size = sum(pdf.stat().st_size for pdf in pdfs) / 1024
        
        self.log(f"\n📊 SUMMARY:")
        self.log(f"   • Robust publishers: {len(working_publishers)}/4")
        self.log(f"   • PDFs downloaded: {len(pdfs)}")
        self.log(f"   • Total size: {total_size:.0f} KB")
        
        if len(working_publishers) >= 3:
            self.log("\n✅ SYSTEM IS ROBUST - Multiple publishers work reliably!")
        else:
            self.log("\n❌ SYSTEM NEEDS MORE WORK - Not enough reliable publishers")
        
        return working_publishers

async def main():
    tester = RobustTest()
    working = await tester.run_all_tests()
    
    print(f"\n🎯 FINAL ANSWER:")
    if len(working) == 4:
        print("✅ ALL 4 publishers are ROBUST and reliable!")
    else:
        print(f"⚠️  {len(working)}/4 publishers are robust: {', '.join(working)}")

if __name__ == "__main__":
    asyncio.run(main())