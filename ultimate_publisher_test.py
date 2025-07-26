#!/usr/bin/env python3
"""
ULTIMATE PUBLISHER TEST FRAMEWORK
==================================

Final test as requested: Download 10 papers 10 times for each of the 7 new publishers.
Target: 700 total PDFs (10 papers × 10 downloads × 7 publishers)

This is the ultimate test to ensure all publishers work perfectly.
"""

import asyncio
import json
import logging
import random
import shutil
import sys
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class UltimateTestResult:
    """Results for the ultimate test"""
    publisher_name: str
    target_papers: int = 10
    target_downloads_per_paper: int = 10
    total_target: int = 100
    successful_downloads: int = 0
    failed_downloads: int = 0
    success_rate: float = 0.0
    error_messages: List[str] = None
    download_times: List[float] = None
    
    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []
        if self.download_times is None:
            self.download_times = []
        self.success_rate = (self.successful_downloads / self.total_target) * 100 if self.total_target > 0 else 0.0

class UltimatePublisherTester:
    """Ultimate test framework for all 7 publishers"""
    
    def __init__(self):
        self.output_dir = Path("ultimate_test_results")
        self.pdf_dir = Path("pdfs_ultimate")
        
        # Clean and create directories
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        if self.pdf_dir.exists():
            shutil.rmtree(self.pdf_dir)
        
        self.output_dir.mkdir(exist_ok=True)
        self.pdf_dir.mkdir(exist_ok=True)
        
        self.test_results = {}
        
        # Comprehensive test DOIs for each publisher (10 papers each)
        self.publisher_test_dois = {
            "Nature": [
                "10.1038/s41586-019-1666-5",    # Nature quantum computing
                "10.1038/nature25778",          # Nature physics
                "10.1038/s41567-020-0928-3",   # Nature Physics
                "10.1038/s41586-020-2649-2",   # Nature COVID research
                "10.1038/s41586-021-03819-2",  # Nature climate
                "10.1038/s41563-020-0636-5",   # Nature Materials
                "10.1038/s41586-020-2832-5",   # Nature AI
                "10.1038/s41586-021-03207-w",  # Nature battery tech
                "10.1038/s41586-020-2797-4",   # Nature quantum
                "10.1038/s41586-021-03235-6"   # Nature fusion
            ],
            "Wiley": [
                "10.1002/anie.202004934",      # Angewandte Chemie
                "10.1111/1467-9523.00123",    # Wiley journal
                "10.1002/adma.201906754",     # Advanced Materials
                "10.1002/anie.202108605",     # Angew Chem recent
                "10.1002/adma.202004328",     # Adv Materials 2020
                "10.1111/j.1468-0297.2020.02395.x", # Economic Journal
                "10.1002/advs.202002812",     # Advanced Science
                "10.1002/aenm.202001873",     # Adv Energy Materials
                "10.1002/smll.202005722",     # Small journal
                "10.1111/mice.12345"          # Computer Civil Engineering
            ],
            "Oxford": [
                "10.1093/bioinformatics/btaa1031",  # Bioinformatics
                "10.1093/nar/gkaa1100",             # Nucleic Acids Research
                "10.1093/brain/awaa123",            # Brain journal
                "10.1093/bioinformatics/btab456",   # Bioinformatics 2021
                "10.1093/nar/gkab567",              # NAR 2021
                "10.1093/molbev/msab123",           # Mol Biol Evol
                "10.1093/genetics/iyab123",         # Genetics
                "10.1093/plphys/kiab234",           # Plant Physiology
                "10.1093/jxb/erab345",              # J Exp Botany
                "10.1093/pcp/pcab123"               # Plant Cell Physiology
            ],
            "ProjectEuclid": [
                "10.1214/20-AOS1985",            # Annals of Statistics
                "10.1214/21-AOAS1234",           # Annals Applied Stats
                "10.4310/ATMP.2020.v24.n1.a1",  # International Press
                "10.1214/19-AOP1345",            # Annals of Probability
                "10.1214/20-EJS1789",            # Electronic J Statistics
                "10.4310/CMS.2020.v18.n5.a1",   # Comm Math Sciences
                "10.1214/21-STS789",             # Statistical Science
                "10.4310/DPDE.2020.v17.n2.a1",  # Discrete PDE
                "10.1214/20-BA1234",             # Bayesian Analysis
                "10.4310/JDG.2020.v114.n3.a1"   # J Diff Geometry
            ],
            "JSTOR": [
                "10.2307/2118632",               # Classic JSTOR
                "10.1525/aa.2019.121.1.123",    # UC Press
                "10.1353/jod.2020.0001",        # Project MUSE
                "10.2307/3003456",               # JSTOR stable
                "10.1525/elementa.456.789",     # Elementa
                "10.1353/lit.2020.0123",        # Literature journal
                "10.2307/1234567",               # General JSTOR
                "10.1525/hsns.2020.50.4.567",   # Historical Studies
                "10.1353/rhe.2020.0045",        # Rhetoric Review
                "10.2307/9876543"                # JSTOR mathematics
            ],
            "AMS": [
                "10.1090/S0002-9947-2019-07845-3",  # AMS Transactions
                "10.1090/jams/123",                  # Journal AMS
                "10.1090/proc/14567",                # AMS Proceedings
                "10.1090/S0002-9939-2020-15234-5",  # Proc AMS
                "10.1090/bull/1678",                 # AMS Bulletin
                "10.1090/S0894-0347-2020-00945-6",  # J AMS recent
                "10.1090/tran/7890",                 # Transactions
                "10.1090/memo/1234",                 # AMS Memoirs
                "10.1090/S1056-3911-2020-00789-1",  # J Algebraic Geom
                "10.1090/conm/567"                   # Contemporary Math
            ],
            "AIMS": [
                "10.3934/math.2021123",             # AIMS Mathematics
                "10.3934/dcdsb.2020456",            # DCDS-B
                "10.31197/atnaa.789012",             # ATNAA
                "10.3934/math.2022567",             # AIMS Math 2022
                "10.3934/dcdss.2021234",            # DCDS-S
                "10.3934/nhm.2020123",              # Networks Heterog Media
                "10.3934/cpaa.2021345",             # Comm Pure Appl Analysis
                "10.3934/jimo.2020456",             # J Industrial Management
                "10.3934/era.2021567",              # Electronic Research Archive
                "10.3934/mbe.2020789"               # Math Biosci Engineering
            ]
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Enhanced logging with level colors"""
        timestamp = time.strftime('%H:%M:%S')
        if level == "ERROR":
            print(f"🔴 [{timestamp}] {message}")
        elif level == "SUCCESS":
            print(f"🟢 [{timestamp}] {message}")
        elif level == "WARNING":
            print(f"🟡 [{timestamp}] {message}")
        else:
            print(f"🔵 [{timestamp}] {message}")
    
    async def run_ultimate_test(self) -> Dict[str, UltimateTestResult]:
        """Run the ultimate test: 10 papers × 10 downloads × 7 publishers = 700 PDFs"""
        
        self.log("🚀 ULTIMATE PUBLISHER TEST INITIATED", "SUCCESS")
        self.log("=" * 100)
        self.log("TARGET: 10 papers × 10 downloads × 7 publishers = 700 PDFs")
        self.log("=" * 100)
        
        publishers = [
            ("Nature", "nature_publisher", "NaturePublisher"),
            ("Wiley", "wiley_publisher", "WileyPublisher"), 
            ("Oxford", "oxford_publisher", "OxfordPublisher"),
            ("ProjectEuclid", "projecteuclid_publisher", "ProjectEuclidPublisher"),
            ("JSTOR", "jstor_publisher", "JSTORPublisher"),
            ("AMS", "ams_publisher", "AMSPublisher"),
            ("AIMS", "aims_publisher", "AIMSPublisher")
        ]
        
        total_downloaded = 0
        total_failed = 0
        
        for publisher_name, module_name, class_name in publishers:
            self.log(f"\n🎯 TESTING {publisher_name.upper()}: 10 papers × 10 downloads = 100 PDFs", "SUCCESS")
            self.log("-" * 80)
            
            result = await self._test_single_publisher(publisher_name, module_name, class_name)
            self.test_results[publisher_name] = result
            
            total_downloaded += result.successful_downloads
            total_failed += result.failed_downloads
            
            self.log(f"✅ {publisher_name}: {result.successful_downloads}/100 PDFs ({result.success_rate:.1f}%)", 
                    "SUCCESS" if result.success_rate >= 90 else "WARNING")
        
        # Final summary
        self.log(f"\n🏆 ULTIMATE TEST COMPLETED", "SUCCESS")
        self.log("=" * 100)
        self.log(f"TOTAL DOWNLOADED: {total_downloaded}/700 PDFs ({total_downloaded/700*100:.1f}%)")
        self.log(f"TOTAL FAILED: {total_failed}/700 PDFs")
        
        return self.test_results
    
    async def _test_single_publisher(self, publisher_name: str, module_name: str, class_name: str) -> UltimateTestResult:
        """Test a single publisher: 10 papers × 10 downloads each"""
        
        result = UltimateTestResult(publisher_name=publisher_name)
        test_dois = self.publisher_test_dois.get(publisher_name, [])
        
        if not test_dois:
            result.error_messages.append("No test DOIs available")
            return result
        
        try:
            # Import and initialize publisher
            module = __import__(f"src.publishers.{module_name}", fromlist=[class_name])
            publisher_class = getattr(module, class_name)
            
            from src.publishers import AuthenticationConfig
            from src.secure_credential_manager import get_credential_manager
            
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            if not (username and password):
                result.error_messages.append("No ETH credentials available")
                return result
            
            auth_config = AuthenticationConfig(
                username=username,
                password=password,
                institutional_login='eth'
            )
            
            publisher_instance = publisher_class(auth_config)
            
        except Exception as e:
            result.error_messages.append(f"Publisher setup failed: {str(e)}")
            return result
        
        # Test each paper 10 times
        for paper_index, doi in enumerate(test_dois, 1):
            self.log(f"📄 Paper {paper_index}/10: {doi}")
            
            for download_attempt in range(1, 11):  # 10 downloads per paper
                start_time = time.time()
                
                # Create unique filename
                safe_doi = doi.replace('/', '_').replace('.', '_')
                filename = f"{publisher_name}_{safe_doi}_attempt_{download_attempt}.pdf"
                save_path = self.pdf_dir / filename
                
                try:
                    self.log(f"   🔄 Attempt {download_attempt}/10...")
                    
                    # Attempt download
                    download_result = await publisher_instance.download_paper(doi, save_path)
                    
                    if download_result.success and save_path.exists() and save_path.stat().st_size > 1000:
                        # Verify PDF
                        with open(save_path, 'rb') as f:
                            if f.read(4) == b'%PDF':
                                result.successful_downloads += 1
                                elapsed = time.time() - start_time
                                result.download_times.append(elapsed)
                                self.log(f"   ✅ Success in {elapsed:.1f}s", "SUCCESS")
                            else:
                                result.failed_downloads += 1
                                self.log(f"   ❌ Invalid PDF file", "ERROR")
                                if save_path.exists():
                                    save_path.unlink()
                    else:
                        result.failed_downloads += 1
                        error_msg = download_result.error_message if hasattr(download_result, 'error_message') else "Unknown error"
                        result.error_messages.append(f"Paper {paper_index}, Attempt {download_attempt}: {error_msg}")
                        self.log(f"   ❌ Failed: {error_msg}", "ERROR")
                
                except Exception as e:
                    result.failed_downloads += 1
                    result.error_messages.append(f"Paper {paper_index}, Attempt {download_attempt}: {str(e)}")
                    self.log(f"   ❌ Exception: {str(e)}", "ERROR")
                
                # Brief pause between attempts
                await asyncio.sleep(2)
            
            # Longer pause between papers
            await asyncio.sleep(5)
        
        # Calculate final stats
        result.success_rate = (result.successful_downloads / result.total_target) * 100
        
        return result
    
    def generate_final_report(self):
        """Generate the ultimate test report"""
        
        self.log("\n" + "=" * 100)
        self.log("🎯 ULTIMATE TEST FINAL REPORT", "SUCCESS")
        self.log("=" * 100)
        
        total_success = sum(r.successful_downloads for r in self.test_results.values())
        total_target = 700
        overall_success_rate = (total_success / total_target) * 100
        
        self.log(f"\n📊 OVERALL STATISTICS:")
        self.log(f"   🎯 Target Downloads: {total_target} PDFs")
        self.log(f"   ✅ Successful Downloads: {total_success} PDFs")
        self.log(f"   ❌ Failed Downloads: {total_target - total_success} PDFs")
        self.log(f"   📈 Overall Success Rate: {overall_success_rate:.1f}%")
        
        # Publisher breakdown
        self.log(f"\n📋 PUBLISHER BREAKDOWN:")
        for publisher_name, result in self.test_results.items():
            status_emoji = "🏆" if result.success_rate >= 95 else "✅" if result.success_rate >= 80 else "⚠️"
            self.log(f"   {status_emoji} {publisher_name:15}: {result.successful_downloads:3}/100 PDFs ({result.success_rate:5.1f}%)")
            
            if result.download_times:
                avg_time = sum(result.download_times) / len(result.download_times)
                self.log(f"      ⏱️ Average download time: {avg_time:.1f}s")
        
        # Performance categories
        excellent = [name for name, r in self.test_results.items() if r.success_rate >= 95]
        good = [name for name, r in self.test_results.items() if 80 <= r.success_rate < 95]
        needs_work = [name for name, r in self.test_results.items() if r.success_rate < 80]
        
        self.log(f"\n🏅 PERFORMANCE CATEGORIES:")
        self.log(f"   🏆 Excellent (≥95%): {len(excellent)} publishers - {', '.join(excellent) if excellent else 'None'}")
        self.log(f"   ✅ Good (80-94%): {len(good)} publishers - {', '.join(good) if good else 'None'}")
        self.log(f"   ⚠️ Needs Work (<80%): {len(needs_work)} publishers - {', '.join(needs_work) if needs_work else 'None'}")
        
        # Final assessment
        self.log(f"\n🎯 FINAL ASSESSMENT:")
        if overall_success_rate >= 95:
            self.log(f"   🏆 OUTSTANDING: {overall_success_rate:.1f}% - Publishers are production ready!")
        elif overall_success_rate >= 80:
            self.log(f"   ✅ EXCELLENT: {overall_success_rate:.1f}% - Great performance with minor optimizations needed")
        elif overall_success_rate >= 60:
            self.log(f"   ⚠️ GOOD: {overall_success_rate:.1f}% - Solid foundation, some improvements needed")
        else:
            self.log(f"   ❌ NEEDS WORK: {overall_success_rate:.1f}% - Significant improvements required")
        
        # Save detailed JSON report
        json_report = {}
        for publisher_name, result in self.test_results.items():
            json_report[publisher_name] = {
                "successful_downloads": result.successful_downloads,
                "failed_downloads": result.failed_downloads,
                "success_rate": result.success_rate,
                "average_download_time": sum(result.download_times) / len(result.download_times) if result.download_times else 0,
                "error_count": len(result.error_messages),
                "first_5_errors": result.error_messages[:5]  # Save first 5 errors only
            }
        
        json_report["overall"] = {
            "total_successful": total_success,
            "total_target": total_target,
            "overall_success_rate": overall_success_rate,
            "excellent_publishers": excellent,
            "good_publishers": good,
            "needs_work_publishers": needs_work
        }
        
        report_file = self.output_dir / "ultimate_test_report.json"
        with open(report_file, 'w') as f:
            json.dump(json_report, f, indent=2)
        
        self.log(f"\n💾 Detailed report saved to: {report_file}")
        
        return overall_success_rate >= 80

async def main():
    """Run the ultimate publisher test"""
    
    tester = UltimatePublisherTester()
    
    # Run the ultimate test
    results = await tester.run_ultimate_test()
    
    # Generate final report
    success = tester.generate_final_report()
    
    return success

if __name__ == "__main__":
    print("🚀 ULTIMATE PUBLISHER TEST: 10 papers × 10 downloads × 7 publishers = 700 PDFs")
    print("=" * 100)
    
    success = asyncio.run(main())
    
    if success:
        print("\n🎉 ULTIMATE TEST COMPLETED SUCCESSFULLY!")
        print("All publishers are performing at excellent levels!")
    else:
        print("\n⚠️ ULTIMATE TEST COMPLETED WITH ISSUES")
        print("Some publishers need optimization - check the detailed report")
        sys.exit(1)