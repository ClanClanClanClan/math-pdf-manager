#!/usr/bin/env python3
"""
Focused Stress Test
===================

Test ArXiv, IEEE, and Sci-Hub robustness without getting stuck on SIAM Cloudflare.
ArXiv and IEEE are proven working, let's verify with stress testing.
"""

import sys
import asyncio
import time
import random
import concurrent.futures
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

class FocusedStressTest:
    def __init__(self):
        self.output_dir = Path("FOCUSED_STRESS_TEST")
        self.output_dir.mkdir(exist_ok=True)
        self.results = {}
        
    def log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    async def test_arxiv_stress(self):
        """Stress test ArXiv with 5 papers, 5 attempts each"""
        self.log("🚀 ARXIV STRESS TEST: 5 papers x 5 attempts = 25 downloads")
        print("=" * 60)
        
        papers = [
            ('1706.03762', 'Transformer'),
            ('1512.03385', 'ResNet'),
            ('1810.04805', 'BERT'),
            ('2010.11929', 'Vision Transformer'),
            ('1411.4038', 'GANs')
        ]
        
        successes = 0
        total_attempts = 0
        
        for paper_idx, (arxiv_id, title) in enumerate(papers):
            self.log(f"Paper {paper_idx + 1}/5: {arxiv_id} - {title}")
            
            for attempt in range(5):
                total_attempts += 1
                
                try:
                    if attempt > 0:
                        delay = random.uniform(1, 3)
                        await asyncio.sleep(delay)
                    
                    import requests
                    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                    response = requests.get(pdf_url, timeout=15)
                    
                    if response.status_code == 200 and len(response.content) > 100000:
                        filename = f"arxiv_{arxiv_id.replace('.', '_')}_attempt_{attempt + 1}.pdf"
                        output_path = self.output_dir / filename
                        
                        with open(output_path, 'wb') as f:
                            f.write(response.content)
                        
                        with open(output_path, 'rb') as f:
                            header = f.read(8)
                            if header.startswith(b'%PDF'):
                                size_kb = len(response.content) / 1024
                                self.log(f"  ✅ Attempt {attempt + 1}/5: {filename} ({size_kb:.0f} KB)")
                                successes += 1
                            else:
                                self.log(f"  ❌ Invalid PDF on attempt {attempt + 1}")
                    else:
                        self.log(f"  ❌ Failed attempt {attempt + 1}: HTTP {response.status_code}")
                        
                except Exception as e:
                    self.log(f"  💥 Exception on attempt {attempt + 1}: {e}")
            
            await asyncio.sleep(1)
        
        success_rate = successes / total_attempts
        self.log(f"📊 ArXiv Results: {successes}/{total_attempts} downloads ({success_rate:.1%})")
        self.results['arxiv'] = {'successes': successes, 'attempts': total_attempts, 'rate': success_rate}
        return success_rate >= 0.9  # 90% success rate required
    
    async def test_ieee_stress(self):
        """Stress test IEEE with 3 papers, 3 attempts each"""
        self.log("🚀 IEEE STRESS TEST: 3 papers x 3 attempts = 9 downloads")
        print("=" * 60)
        
        papers = [
            ('10.1109/5.726791', 'LeCun CNN'),
            ('10.1109/JPROC.2018.2820126', 'Graph Signal Processing'),
            ('10.1109/MC.2006.5', 'Amdahl Law')
        ]
        
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
        
        for paper_idx, (doi, title) in enumerate(papers):
            self.log(f"Paper {paper_idx + 1}/3: {doi} - {title}")
            
            for attempt in range(3):
                total_attempts += 1
                
                try:
                    if attempt > 0:
                        delay = random.uniform(5, 10)
                        await asyncio.sleep(delay)
                    
                    # Create fresh publisher instance
                    auth_config = AuthenticationConfig(
                        username=username,
                        password=password,
                        institutional_login='eth'
                    )
                    ieee = IEEEPublisher(auth_config)
                    
                    filename = f"ieee_{doi.replace('/', '_').replace('.', '_')}_attempt_{attempt + 1}.pdf"
                    output_path = self.output_dir / filename
                    
                    # Use ThreadPoolExecutor for sync function
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(ieee.download_paper, doi, output_path)
                        result = future.result(timeout=180)  # 3 minute timeout
                    
                    if result.success and output_path.exists():
                        with open(output_path, 'rb') as f:
                            header = f.read(8)
                            if header.startswith(b'%PDF'):
                                size_kb = output_path.stat().st_size / 1024
                                self.log(f"  ✅ Attempt {attempt + 1}/3: {filename} ({size_kb:.0f} KB)")
                                successes += 1
                            else:
                                self.log(f"  ❌ Invalid PDF on attempt {attempt + 1}")
                                output_path.unlink()
                    else:
                        error_msg = result.error_message if hasattr(result, 'error_message') else 'Unknown'
                        self.log(f"  ❌ Failed attempt {attempt + 1}: {error_msg}")
                        
                except Exception as e:
                    self.log(f"  💥 Exception on attempt {attempt + 1}: {e}")
            
            await asyncio.sleep(5)
        
        success_rate = successes / total_attempts if total_attempts > 0 else 0
        self.log(f"📊 IEEE Results: {successes}/{total_attempts} downloads ({success_rate:.1%})")
        self.results['ieee'] = {'successes': successes, 'attempts': total_attempts, 'rate': success_rate}
        return success_rate >= 0.7  # 70% success rate required (browser tests are harder)
    
    async def test_scihub_stress(self):
        """Stress test Sci-Hub with 3 papers, 5 attempts each"""
        self.log("🚀 SCI-HUB STRESS TEST: 3 papers x 5 attempts = 15 downloads")
        print("=" * 60)
        
        papers = [
            ('10.1038/nature12373', 'Nature thermometry'),
            ('10.1126/science.1102896', 'Graphene'),
            ('10.1038/s41586-019-1666-5', 'ML paper from Nature')
        ]
        
        successes = 0
        total_attempts = 0
        
        for paper_idx, (doi, title) in enumerate(papers):
            self.log(f"Paper {paper_idx + 1}/3: {doi} - {title}")
            
            for attempt in range(5):
                total_attempts += 1
                
                try:
                    if attempt > 0:
                        delay = random.uniform(3, 8)
                        await asyncio.sleep(delay)
                    
                    from src.downloader.universal_downloader import SciHubDownloader
                    sci_hub = SciHubDownloader()
                    
                    result = await sci_hub.download(doi)
                    
                    if result.success and result.pdf_data and len(result.pdf_data) > 10000:
                        filename = f"scihub_{doi.replace('/', '_').replace('.', '_')}_attempt_{attempt + 1}.pdf"
                        output_path = self.output_dir / filename
                        
                        with open(output_path, 'wb') as f:
                            f.write(result.pdf_data)
                        
                        if result.pdf_data.startswith(b'%PDF'):
                            size_kb = len(result.pdf_data) / 1024
                            self.log(f"  ✅ Attempt {attempt + 1}/5: {filename} ({size_kb:.0f} KB)")
                            successes += 1
                        else:
                            self.log(f"  ❌ Invalid PDF data on attempt {attempt + 1}")
                    else:
                        error_msg = result.error if hasattr(result, 'error') else 'Unknown'
                        self.log(f"  ❌ Failed attempt {attempt + 1}: {error_msg}")
                    
                    # Always cleanup
                    if hasattr(sci_hub, 'session') and sci_hub.session:
                        await sci_hub.session.close()
                        
                except Exception as e:
                    self.log(f"  💥 Exception on attempt {attempt + 1}: {e}")
            
            await asyncio.sleep(2)
        
        success_rate = successes / total_attempts
        self.log(f"📊 Sci-Hub Results: {successes}/{total_attempts} downloads ({success_rate:.1%})")
        self.results['scihub'] = {'successes': successes, 'attempts': total_attempts, 'rate': success_rate}
        return success_rate >= 0.6  # 60% success rate required (Sci-Hub can be unreliable)
    
    async def run_focused_test(self):
        """Run focused stress test on working publishers"""
        self.log("🎯 FOCUSED STRESS TEST: Testing proven working publishers")
        self.log("ArXiv (5x5), IEEE (3x3), Sci-Hub (3x5) = 49 total downloads")
        print("=" * 80)
        
        start_time = time.time()
        
        # Run tests
        results = {}
        results['arxiv'] = await self.test_arxiv_stress()
        results['ieee'] = await self.test_ieee_stress()
        results['scihub'] = await self.test_scihub_stress()
        
        # Final summary
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "=" * 80)
        self.log("🎯 FOCUSED STRESS TEST RESULTS")
        print("=" * 80)
        
        passed_publishers = []
        total_downloads = 0
        total_attempts = 0
        
        for publisher, passed in results.items():
            status = "✅ ROBUST" if passed else "❌ NEEDS WORK"
            if publisher in self.results:
                successes = self.results[publisher]['successes']
                attempts = self.results[publisher]['attempts']
                rate = self.results[publisher]['rate']
                total_downloads += successes
                total_attempts += attempts
                self.log(f"{status:12} | {publisher.upper():8} | {successes:2}/{attempts:2} downloads ({rate:.1%})")
                if passed:
                    passed_publishers.append(publisher)
            else:
                self.log(f"{status:12} | {publisher.upper():8} | No data")
        
        # Show files
        pdfs = list(self.output_dir.glob("*.pdf"))
        total_size = sum(pdf.stat().st_size for pdf in pdfs) / (1024 * 1024)
        
        self.log(f"\n📊 FOCUSED TEST SUMMARY:")
        self.log(f"   Duration: {duration/60:.1f} minutes")
        self.log(f"   Robust publishers: {len(passed_publishers)}/3 tested")
        self.log(f"   Total downloads: {total_downloads}/{total_attempts} ({total_downloads/total_attempts:.1%})")
        self.log(f"   PDFs saved: {len(pdfs)} ({total_size:.1f} MB)")
        
        if len(passed_publishers) >= 2:
            self.log(f"\n🎉 SUCCESS! {len(passed_publishers)}/3 publishers are robust")
            self.log(f"Robust: {', '.join(passed_publishers)}")
        else:
            self.log(f"\n⚠️  Only {len(passed_publishers)}/3 passed stress testing")
        
        return passed_publishers

async def main():
    tester = FocusedStressTest()
    robust = await tester.run_focused_test()
    
    print(f"\n🎯 FINAL FOCUSED STRESS TEST RESULT:")
    print(f"Robust publishers: {len(robust)}/3 ({', '.join(robust)})")
    
    if 'arxiv' in robust and 'ieee' in robust:
        print("✅ Core publishers (ArXiv, IEEE) are robust!")
    else:
        print("❌ Core publishers need more work")

if __name__ == "__main__":
    asyncio.run(main())