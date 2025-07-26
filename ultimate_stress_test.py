#!/usr/bin/env python3
"""
ULTIMATE STRESS TEST
===================

The REAL test: 10 downloads of 10 different papers per publisher.
This is the final test that must pass for the system to be considered robust.
"""

import sys
import asyncio
import time
import random
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

# EXPANDED TEST DATA - 10+ papers per publisher
PAPER_COLLECTIONS = {
    'arxiv': [
        ('1706.03762', 'Attention is All You Need (Transformer)'),
        ('2103.03404', 'Attention is not all you need'),
        ('1512.03385', 'Deep Residual Learning for Image Recognition'),
        ('2010.11929', 'An Image is Worth 16x16 Words (Vision Transformer)'),
        ('1810.04805', 'BERT: Pre-training of Deep Bidirectional Transformers'),
        ('1411.4038', 'Generative Adversarial Nets'),
        ('1301.3781', 'Efficient Estimation of Word Representations'),
        ('1409.1556', 'Very Deep Convolutional Networks'),
        ('1506.01497', 'Faster R-CNN'),
        ('1409.0473', 'Neural Machine Translation'),
        ('2005.14165', 'Language Models are Few-Shot Learners (GPT-3)'),
        ('1409.4842', 'ADAM: A Method for Stochastic Optimization')
    ],
    'scihub': [
        ('10.1038/nature12373', 'Nanometre-scale thermometry in a living cell'),
        ('10.1126/science.1102896', 'Electric Field Effect in Atomically Thin Carbon Films'),
        ('10.1038/s41586-019-1666-5', 'Machine learning paper from Nature'),
        ('10.1126/science.1243982', 'CRISPR-Cas9 gene editing'),
        ('10.1038/nature25778', 'AI discovers new materials'),
        ('10.1126/science.1232033', 'Quantum teleportation'),
        ('10.1038/nature14236', 'Deep learning breakthrough'),
        ('10.1126/science.1204428', 'Stem cell research'),
        ('10.1038/nature13385', 'Climate change study'),
        ('10.1126/science.1193147', 'Physics discovery'),
        ('10.1038/nature08227', 'Biology breakthrough'),
        ('10.1126/science.1165893', 'Chemistry innovation')
    ],
    'ieee': [
        ('10.1109/5.726791', 'Gradient-based learning applied to document recognition'),
        ('10.1109/JPROC.2018.2820126', 'Graph Signal Processing: Overview, Challenges, and Applications'),
        ('10.1109/MC.2006.5', 'Amdahl\'s law in the multicore era'),
        ('10.1109/JPROC.2016.2515118', 'Computer vision and image understanding'),
        ('10.1109/5.771073', 'Neural networks for pattern recognition'),
        ('10.1109/JPROC.2015.2460651', 'Deep learning architectures'),
        ('10.1109/5.726787', 'Support vector machines'),
        ('10.1109/JPROC.2017.2761740', 'Internet of Things'),
        ('10.1109/5.869037', 'Computer graphics algorithms'),
        ('10.1109/JPROC.2016.2571690', 'Artificial intelligence systems'),
        ('10.1109/JPROC.2014.2361250', 'Big data analytics'),
        ('10.1109/5.771074', 'Machine learning fundamentals')
    ],
    'siam': [
        ('10.1137/S0097539795293172', 'Polynomial-Time Algorithms for Prime Factorization (Shor)'),
        ('10.1137/S0097539792240406', 'Complexity theory fundamentals'),
        ('10.1137/0210022', 'Linear programming algorithms'),
        ('10.1137/S0097539700376141', 'Approximation algorithms'),
        ('10.1137/S0097539701399884', 'Graph algorithms and optimization'),
        ('10.1137/S0097539794270957', 'Randomized algorithms'),
        ('10.1137/S0097539790187084', 'Computational geometry'),
        ('10.1137/S0097539793255151', 'Number theory algorithms'),
        ('10.1137/S0097539792242415', 'Combinatorial optimization'),
        ('10.1137/S0097539794261865', 'Algebraic algorithms'),
        ('10.1137/S0097539793260496', 'Parallel algorithms'),
        ('10.1137/S0097539791194094', 'Distributed computing')
    ]
}

class UltimateStressTest:
    def __init__(self):
        self.output_dir = Path("ULTIMATE_STRESS_TEST")
        self.output_dir.mkdir(exist_ok=True)
        self.results = {}
        
    def log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    async def test_arxiv_ultimate(self):
        """Test ArXiv: 10 downloads of 10 different papers"""
        self.log("🚀 ARXIV ULTIMATE TEST: 10 downloads of 10 papers")
        print("=" * 70)
        
        papers = PAPER_COLLECTIONS['arxiv']
        successes = 0
        total_attempts = 0
        
        for paper_idx, (arxiv_id, title) in enumerate(papers[:10]):
            self.log(f"Paper {paper_idx + 1}/10: {arxiv_id} - {title[:50]}...")
            
            for download_attempt in range(10):
                total_attempts += 1
                
                try:
                    # Add jitter to avoid rate limiting
                    if download_attempt > 0:
                        delay = random.uniform(1, 3)
                        await asyncio.sleep(delay)
                    
                    import requests
                    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                    response = requests.get(pdf_url, timeout=20)
                    
                    if response.status_code == 200 and len(response.content) > 100000:
                        # Save PDF
                        filename = f"arxiv_{arxiv_id.replace('.', '_')}_attempt_{download_attempt + 1}.pdf"
                        output_path = self.output_dir / filename
                        
                        with open(output_path, 'wb') as f:
                            f.write(response.content)
                        
                        # Verify PDF
                        with open(output_path, 'rb') as f:
                            header = f.read(8)
                            if header.startswith(b'%PDF'):
                                size_kb = len(response.content) / 1024
                                self.log(f"  ✅ Download {download_attempt + 1}/10: {filename} ({size_kb:.0f} KB)")
                                successes += 1
                            else:
                                self.log(f"  ❌ Invalid PDF on download {download_attempt + 1}")
                    else:
                        self.log(f"  ❌ Failed download {download_attempt + 1}: HTTP {response.status_code}")
                        
                except Exception as e:
                    self.log(f"  💥 Exception on download {download_attempt + 1}: {e}")
            
            # Small delay between papers
            await asyncio.sleep(1)
        
        success_rate = successes / total_attempts
        self.log(f"📊 ArXiv Results: {successes}/{total_attempts} downloads ({success_rate:.1%})")
        self.results['arxiv'] = {'successes': successes, 'attempts': total_attempts, 'rate': success_rate}
        return success_rate >= 0.9  # 90% success rate required
    
    async def test_scihub_ultimate(self):
        """Test Sci-Hub: 10 downloads of 10 different papers"""
        self.log("🚀 SCI-HUB ULTIMATE TEST: 10 downloads of 10 papers")
        print("=" * 70)
        
        papers = PAPER_COLLECTIONS['scihub']
        successes = 0
        total_attempts = 0
        
        for paper_idx, (doi, title) in enumerate(papers[:10]):
            self.log(f"Paper {paper_idx + 1}/10: {doi} - {title[:50]}...")
            
            for download_attempt in range(10):
                total_attempts += 1
                
                try:
                    # Rate limiting delay
                    if download_attempt > 0:
                        delay = random.uniform(2, 5)
                        await asyncio.sleep(delay)
                    
                    from src.downloader.universal_downloader import SciHubDownloader
                    sci_hub = SciHubDownloader()
                    
                    result = await sci_hub.download(doi)
                    
                    if result.success and result.pdf_data and len(result.pdf_data) > 10000:
                        # Save PDF
                        filename = f"scihub_{doi.replace('/', '_').replace('.', '_')}_attempt_{download_attempt + 1}.pdf"
                        output_path = self.output_dir / filename
                        
                        with open(output_path, 'wb') as f:
                            f.write(result.pdf_data)
                        
                        # Verify PDF
                        if result.pdf_data.startswith(b'%PDF'):
                            size_kb = len(result.pdf_data) / 1024
                            self.log(f"  ✅ Download {download_attempt + 1}/10: {filename} ({size_kb:.0f} KB)")
                            successes += 1
                        else:
                            self.log(f"  ❌ Invalid PDF data on download {download_attempt + 1}")
                    else:
                        self.log(f"  ❌ Failed download {download_attempt + 1}: {result.error if hasattr(result, 'error') else 'Unknown'}")
                    
                    # Always cleanup
                    if hasattr(sci_hub, 'session') and sci_hub.session:
                        await sci_hub.session.close()
                        
                except Exception as e:
                    self.log(f"  💥 Exception on download {download_attempt + 1}: {e}")
            
            # Delay between papers
            await asyncio.sleep(2)
        
        success_rate = successes / total_attempts
        self.log(f"📊 Sci-Hub Results: {successes}/{total_attempts} downloads ({success_rate:.1%})")
        self.results['scihub'] = {'successes': successes, 'attempts': total_attempts, 'rate': success_rate}
        return success_rate >= 0.8  # 80% success rate required
    
    async def test_ieee_ultimate(self):
        """Test IEEE: 10 downloads of 10 different papers"""
        self.log("🚀 IEEE ULTIMATE TEST: 10 downloads of 10 papers")
        print("=" * 70)
        
        papers = PAPER_COLLECTIONS['ieee']
        successes = 0
        total_attempts = 0
        
        # Get credentials once
        try:
            from src.publishers.ieee_publisher import IEEEPublisher
            from src.publishers import AuthenticationConfig
            from src.secure_credential_manager import get_credential_manager
            
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            if not username or not password:
                self.log("❌ No ETH credentials for IEEE")
                self.results['ieee'] = {'successes': 0, 'attempts': 0, 'rate': 0.0}
                return False
                
        except ImportError as e:
            self.log(f"❌ Cannot import IEEE components: {e}")
            self.results['ieee'] = {'successes': 0, 'attempts': 0, 'rate': 0.0}
            return False
        
        for paper_idx, (doi, title) in enumerate(papers[:10]):
            self.log(f"Paper {paper_idx + 1}/10: {doi} - {title[:50]}...")
            
            for download_attempt in range(10):
                total_attempts += 1
                
                try:
                    # Longer delay for browser operations
                    if download_attempt > 0:
                        delay = random.uniform(5, 10)
                        await asyncio.sleep(delay)
                    
                    # Create fresh publisher instance
                    auth_config = AuthenticationConfig(
                        username=username,
                        password=password,
                        institutional_login='eth'
                    )
                    ieee = IEEEPublisher(auth_config)
                    
                    # Download - run in executor to handle sync/async properly
                    filename = f"ieee_{doi.replace('/', '_').replace('.', '_')}_attempt_{download_attempt + 1}.pdf"
                    output_path = self.output_dir / filename
                    
                    # Use thread executor for sync function
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(ieee.download_paper, doi, output_path)
                        result = future.result(timeout=300)  # 5 minute timeout
                    
                    if result.success and output_path.exists():
                        # Verify PDF
                        with open(output_path, 'rb') as f:
                            header = f.read(8)
                            if header.startswith(b'%PDF'):
                                size_kb = output_path.stat().st_size / 1024
                                self.log(f"  ✅ Download {download_attempt + 1}/10: {filename} ({size_kb:.0f} KB)")
                                successes += 1
                            else:
                                self.log(f"  ❌ Invalid PDF on download {download_attempt + 1}")
                                output_path.unlink()
                    else:
                        error_msg = result.error_message if hasattr(result, 'error_message') else 'Unknown'
                        self.log(f"  ❌ Failed download {download_attempt + 1}: {error_msg}")
                        
                except Exception as e:
                    self.log(f"  💥 Exception on download {download_attempt + 1}: {e}")
            
            # Longer delay between papers for browser cleanup
            await asyncio.sleep(10)
        
        success_rate = successes / total_attempts if total_attempts > 0 else 0
        self.log(f"📊 IEEE Results: {successes}/{total_attempts} downloads ({success_rate:.1%})")
        self.results['ieee'] = {'successes': successes, 'attempts': total_attempts, 'rate': success_rate}
        return success_rate >= 0.7  # 70% success rate required (browser tests are harder)
    
    async def test_siam_ultimate(self):
        """Test SIAM: 10 downloads of 10 different papers"""
        self.log("🚀 SIAM ULTIMATE TEST: 10 downloads of 10 papers")
        print("=" * 70)
        
        papers = PAPER_COLLECTIONS['siam']
        successes = 0
        total_attempts = 0
        
        # Get credentials once
        try:
            from playwright.async_api import async_playwright
            from src.secure_credential_manager import get_credential_manager
            
            cm = get_credential_manager()
            username = cm.get_credential("eth_username")
            password = cm.get_credential("eth_password")
            
            if not username or not password:
                self.log("❌ No ETH credentials for SIAM")
                self.results['siam'] = {'successes': 0, 'attempts': 0, 'rate': 0.0}
                return False
                
        except ImportError as e:
            self.log(f"❌ Cannot import SIAM components: {e}")
            self.results['siam'] = {'successes': 0, 'attempts': 0, 'rate': 0.0}
            return False
        
        for paper_idx, (doi, title) in enumerate(papers[:10]):
            self.log(f"Paper {paper_idx + 1}/10: {doi} - {title[:50]}...")
            
            for download_attempt in range(10):
                total_attempts += 1
                
                try:
                    # Longer delay for browser operations
                    if download_attempt > 0:
                        delay = random.uniform(10, 20)
                        await asyncio.sleep(delay)
                    
                    async with async_playwright() as p:
                        # Use EXACT anti-detection settings from working SIAM code
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
                        
                        await context.add_init_script("""
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => undefined,
                            });
                        """)
                        
                        page = await context.new_page()
                        
                        # Navigate and authenticate
                        siam_url = f"https://epubs.siam.org/doi/{doi}"
                        await page.goto(siam_url, timeout=90000)
                        await page.wait_for_timeout(5000)
                        
                        # Institutional access
                        inst_button = await page.wait_for_selector('a:has-text("Access via your Institution")', timeout=20000)
                        await inst_button.click()
                        await page.wait_for_timeout(8000)
                        
                        # Search ETH
                        search_input = await page.wait_for_selector('input#shibboleth_search', timeout=20000)
                        await search_input.click()
                        await search_input.fill("")
                        await page.wait_for_timeout(1000)
                        await search_input.type("ETH Zurich", delay=150)
                        await page.wait_for_timeout(4000)
                        
                        # Click ETH
                        eth_option = await page.wait_for_selector('.ms-res-item a.sso-institution:has-text("ETH Zurich")', timeout=15000)
                        await eth_option.click()
                        await page.wait_for_timeout(10000)
                        
                        # ETH login
                        username_input = await page.wait_for_selector('input[name="j_username"]', timeout=30000)
                        await username_input.fill(username)
                        
                        password_input = await page.wait_for_selector('input[name="j_password"]', timeout=10000)
                        await password_input.fill(password)
                        
                        submit_button = await page.wait_for_selector('button[type="submit"]', timeout=10000)
                        await submit_button.click()
                        await page.wait_for_timeout(20000)
                        
                        # Navigate to PDF
                        pdf_url = siam_url.replace('/doi/', '/doi/epdf/')
                        await page.goto(pdf_url, timeout=90000)
                        await page.wait_for_timeout(15000)
                        
                        # Setup download
                        download_happened = False
                        downloaded_file = None
                        
                        async def handle_download(download):
                            nonlocal download_happened, downloaded_file
                            download_happened = True
                            filename = f"siam_{doi.replace('/', '_').replace('.', '_')}_attempt_{download_attempt + 1}.pdf"
                            save_path = self.output_dir / filename
                            await download.save_as(str(save_path))
                            downloaded_file = save_path
                        
                        page.on('download', handle_download)
                        
                        # Click download
                        download_button = await page.wait_for_selector('a[title*="Download"]', timeout=15000)
                        await download_button.click()
                        await page.wait_for_timeout(15000)
                        
                        await browser.close()
                        
                        if download_happened and downloaded_file and downloaded_file.exists():
                            with open(downloaded_file, 'rb') as f:
                                header = f.read(8)
                                if header.startswith(b'%PDF'):
                                    size_kb = downloaded_file.stat().st_size / 1024
                                    self.log(f"  ✅ Download {download_attempt + 1}/10: {downloaded_file.name} ({size_kb:.0f} KB)")
                                    successes += 1
                                else:
                                    self.log(f"  ❌ Invalid PDF on download {download_attempt + 1}")
                        else:
                            self.log(f"  ❌ No download on attempt {download_attempt + 1}")
                        
                except Exception as e:
                    self.log(f"  💥 Exception on download {download_attempt + 1}: {e}")
            
            # Long delay between papers
            await asyncio.sleep(15)
        
        success_rate = successes / total_attempts if total_attempts > 0 else 0
        self.log(f"📊 SIAM Results: {successes}/{total_attempts} downloads ({success_rate:.1%})")
        self.results['siam'] = {'successes': successes, 'attempts': total_attempts, 'rate': success_rate}
        return success_rate >= 0.7  # 70% success rate required
    
    async def run_ultimate_test(self):
        """Run the ultimate stress test"""
        self.log("💥 ULTIMATE STRESS TEST: 10 downloads of 10 papers per publisher")
        self.log("This is the final test to prove true robustness")
        print("=" * 80)
        
        start_time = time.time()
        
        # Run tests for all publishers
        results = {}
        
        results['arxiv'] = await self.test_arxiv_ultimate()
        results['scihub'] = await self.test_scihub_ultimate()
        results['ieee'] = await self.test_ieee_ultimate()
        results['siam'] = await self.test_siam_ultimate()
        
        # Final summary
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "=" * 80)
        self.log("🎯 ULTIMATE STRESS TEST RESULTS")
        print("=" * 80)
        
        passed_publishers = []
        total_downloads = 0
        total_attempts = 0
        
        for publisher, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            if publisher in self.results:
                successes = self.results[publisher]['successes']
                attempts = self.results[publisher]['attempts']
                rate = self.results[publisher]['rate']
                total_downloads += successes
                total_attempts += attempts
                self.log(f"{status:12} | {publisher.upper():8} | {successes:3}/{attempts:3} downloads ({rate:.1%})")
                if passed:
                    passed_publishers.append(publisher)
            else:
                self.log(f"{status:12} | {publisher.upper():8} | No data")
        
        # Show files
        pdfs = list(self.output_dir.glob("*.pdf"))
        total_size = sum(pdf.stat().st_size for pdf in pdfs) / (1024 * 1024)
        
        self.log(f"\n📊 ULTIMATE TEST SUMMARY:")
        self.log(f"   Duration: {duration/60:.1f} minutes")
        self.log(f"   Passed publishers: {len(passed_publishers)}/4")
        self.log(f"   Total downloads: {total_downloads}/{total_attempts} ({total_downloads/total_attempts:.1%})")
        self.log(f"   PDFs saved: {len(pdfs)} ({total_size:.1f} MB)")
        
        if len(passed_publishers) == 4:
            self.log("\n🎉 ALL 4 PUBLISHERS PASSED THE ULTIMATE TEST!")
        else:
            failed = [p for p in ['arxiv', 'scihub', 'ieee', 'siam'] if p not in passed_publishers]
            self.log(f"\n⚠️  {len(passed_publishers)}/4 passed. Failed: {', '.join(failed)}")
        
        return passed_publishers

async def main():
    tester = UltimateStressTest()
    passed = await tester.run_ultimate_test()
    
    print(f"\n🎯 FINAL ANSWER: {len(passed)}/4 publishers passed the ultimate test")
    if len(passed) == 4:
        print("🎉 THE SYSTEM IS TRULY ROBUST!")
    else:
        print(f"🔧 Still need to fix: {[p for p in ['arxiv', 'scihub', 'ieee', 'siam'] if p not in passed]}")

if __name__ == "__main__":
    asyncio.run(main())