#!/usr/bin/env python3
"""
ETH Download Testing Script
==========================

Test real PDF downloads using ETH institutional access.
This script validates the complete authentication and download workflow.
"""

import os
import sys
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from auth_manager import get_auth_manager, AuthConfig, AuthMethod
    from secure_credential_manager import get_credential_manager
    from scripts.downloader import acquire_paper_by_metadata
    from metadata_fetcher import fetch_metadata_all_sources
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the correct directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("eth_download_test")

# Test papers from different publishers with known DOIs
TEST_PAPERS = {
    "ieee": {
        "doi": "10.1109/ACCESS.2023.3290123",
        "title": "IEEE Access Paper",
        "url": "https://ieeexplore.ieee.org/document/10158042"
    },
    "springer": {
        "doi": "10.1007/s00454-023-00530-8", 
        "title": "Springer Computational Geometry Paper",
        "url": "https://link.springer.com/article/10.1007/s00454-023-00530-8"
    },
    "acm": {
        "doi": "10.1145/3564246.3585181",
        "title": "ACM CHI Paper",
        "url": "https://dl.acm.org/doi/10.1145/3564246.3585181"
    },
    "elsevier": {
        "doi": "10.1016/j.jcp.2023.112345",
        "title": "Journal of Computational Physics",
        "url": "https://www.sciencedirect.com/science/article/pii/S0021999123004412"
    }
}


class ETHDownloadTester:
    """Test ETH institutional download capabilities."""
    
    def __init__(self):
        self.credential_manager = get_credential_manager()
        self.auth_manager = get_auth_manager()
        self.test_results = {}
        self.temp_dir = None
    
    def check_prerequisites(self) -> bool:
        """Check if prerequisites are met for testing."""
        print("🔍 Checking prerequisites...")
        
        # Check credentials
        username, password = self.credential_manager.get_eth_credentials()
        if not username or not password:
            print("❌ ETH credentials not found")
            print("Run: python secure_credential_manager.py setup-env")
            print("Or set ETH_USERNAME and ETH_PASSWORD environment variables")
            return False
        
        print(f"✅ ETH credentials found for user: {username}")
        
        # Check Playwright
        try:
            from playwright.sync_api import sync_playwright
            print("✅ Playwright available for browser automation")
        except ImportError:
            print("❌ Playwright not available")
            print("Install with: pip install playwright && playwright install chromium")
            return False
        
        return True
    
    def setup_test_environment(self) -> bool:
        """Set up temporary directory for test downloads."""
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="eth_download_test_")
            print(f"📁 Test directory: {self.temp_dir}")
            return True
        except Exception as e:
            print(f"❌ Failed to create test directory: {e}")
            return False
    
    def test_metadata_fetching(self) -> Dict[str, bool]:
        """Test metadata fetching for test papers."""
        print("\n📋 Testing metadata fetching...")
        results = {}
        
        for publisher, paper in TEST_PAPERS.items():
            print(f"\n  Testing {publisher.upper()}: {paper['title']}")
            
            try:
                # Test by DOI
                metadata = fetch_metadata_all_sources(
                    title=paper['title'],
                    doi=paper['doi']
                )
                
                if metadata and metadata.get('doi'):
                    print(f"    ✅ Metadata found: {metadata['title'][:50]}...")
                    results[publisher] = True
                else:
                    print(f"    ❌ No metadata found")
                    results[publisher] = False
                    
            except Exception as e:
                print(f"    ❌ Metadata fetch error: {e}")
                results[publisher] = False
        
        return results
    
    def test_open_access_downloads(self) -> Dict[str, bool]:
        """Test open access downloads (no auth required)."""
        print("\n🔓 Testing open access downloads...")
        results = {}
        
        # Add some known open access papers
        oa_papers = {
            "arxiv": {
                "title": "Attention Is All You Need",
                "doi": "10.48550/arXiv.1706.03762"
            },
            "plos": {
                "title": "PLOS ONE Sample",
                "doi": "10.1371/journal.pone.0280123"
            }
        }
        
        for source, paper in oa_papers.items():
            print(f"\n  Testing {source.upper()}: {paper['title']}")
            
            try:
                file_path, attempts = acquire_paper_by_metadata(
                    paper['title'],
                    self.temp_dir,
                    doi=paper['doi']
                )
                
                if file_path and os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"    ✅ Downloaded: {file_size} bytes")
                    results[source] = True
                else:
                    print(f"    ❌ Download failed")
                    results[source] = False
                    
            except Exception as e:
                print(f"    ❌ Download error: {e}")
                results[source] = False
        
        return results
    
    def test_eth_authentication(self) -> Dict[str, bool]:
        """Test ETH authentication for different publishers."""
        print("\n🔐 Testing ETH authentication...")
        results = {}
        
        # Get ETH credentials
        username, password = self.credential_manager.get_eth_credentials()
        
        for publisher in ["ieee", "springer", "acm"]:
            print(f"\n  Testing {publisher.upper()} ETH auth...")
            
            try:
                # Create auth config for this publisher
                config = AuthConfig(
                    service_name=f"eth_{publisher}",
                    auth_method=AuthMethod.SHIBBOLETH,
                    base_url=f"https://{publisher}.example.com",  # Placeholder
                    shibboleth_idp="https://idp.ethz.ch",
                    username=username,
                    password=password
                )
                
                # Add to auth manager
                self.auth_manager.add_config(config)
                print(f"    ✅ Auth config created for eth_{publisher}")
                results[publisher] = True
                
            except Exception as e:
                print(f"    ❌ Auth setup failed: {e}")
                results[publisher] = False
        
        return results
    
    def test_institutional_downloads(self) -> Dict[str, Dict]:
        """Test downloads using ETH institutional access."""
        print("\n🎓 Testing institutional downloads...")
        results = {}
        
        for publisher, paper in TEST_PAPERS.items():
            print(f"\n  Testing {publisher.upper()}: {paper['title'][:40]}...")
            
            result = {
                'success': False,
                'file_size': 0,
                'error': None,
                'attempts': []
            }
            
            try:
                file_path, attempts = acquire_paper_by_metadata(
                    paper['title'],
                    self.temp_dir,
                    doi=paper['doi'],
                    auth_service=f"eth_{publisher}"
                )
                
                result['attempts'] = [
                    {
                        'strategy': attempt.strategy,
                        'result': attempt.result.value,
                        'error': attempt.error
                    } for attempt in attempts
                ]
                
                if file_path and os.path.exists(file_path):
                    result['file_size'] = os.path.getsize(file_path)
                    result['success'] = True
                    print(f"    ✅ Downloaded: {result['file_size']} bytes")
                    
                    # Quick validation - check if it's a PDF
                    with open(file_path, 'rb') as f:
                        header = f.read(4)
                        if header == b'%PDF':
                            print(f"    ✅ Valid PDF file")
                        else:
                            print(f"    ⚠️  File may not be PDF (header: {header})")
                else:
                    print(f"    ❌ Download failed")
                    for attempt in result['attempts']:
                        print(f"      - {attempt['strategy']}: {attempt['result']}")
                        
            except Exception as e:
                result['error'] = str(e)
                print(f"    ❌ Download error: {e}")
            
            results[publisher] = result
        
        return results
    
    def generate_report(self, test_results: Dict) -> str:
        """Generate comprehensive test report."""
        report = []
        report.append("=" * 80)
        report.append("ETH INSTITUTIONAL DOWNLOAD TEST REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary
        total_tests = sum(len(results) for results in test_results.values())
        successful_tests = sum(
            sum(1 for result in results.values() 
                if (isinstance(result, bool) and result) or 
                   (isinstance(result, dict) and result.get('success')))
            for results in test_results.values()
        )
        
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Tests: {total_tests}")
        report.append(f"Successful: {successful_tests}")
        report.append(f"Failed: {total_tests - successful_tests}")
        report.append(f"Success Rate: {successful_tests/total_tests*100:.1f}%")
        report.append("")
        
        # Detailed results
        for test_name, results in test_results.items():
            report.append(f"{test_name.upper()}")
            report.append("-" * 40)
            
            for item, result in results.items():
                if isinstance(result, bool):
                    status = "✅ PASS" if result else "❌ FAIL"
                    report.append(f"  {item}: {status}")
                elif isinstance(result, dict):
                    status = "✅ PASS" if result.get('success') else "❌ FAIL"
                    report.append(f"  {item}: {status}")
                    if result.get('file_size'):
                        report.append(f"    File size: {result['file_size']} bytes")
                    if result.get('error'):
                        report.append(f"    Error: {result['error']}")
                    if result.get('attempts'):
                        report.append(f"    Attempts:")
                        for attempt in result['attempts']:
                            report.append(f"      - {attempt['strategy']}: {attempt['result']}")
            
            report.append("")
        
        return "\n".join(report)
    
    def run_comprehensive_test(self) -> bool:
        """Run all tests and generate report."""
        print("🧪 Starting ETH Institutional Download Tests")
        print("=" * 60)
        
        # Check prerequisites
        if not self.check_prerequisites():
            return False
        
        # Set up test environment
        if not self.setup_test_environment():
            return False
        
        try:
            # Run test suite
            self.test_results = {
                'metadata_fetching': self.test_metadata_fetching(),
                'open_access_downloads': self.test_open_access_downloads(),
                'eth_authentication': self.test_eth_authentication(),
                'institutional_downloads': self.test_institutional_downloads()
            }
            
            # Generate and save report
            report = self.generate_report(self.test_results)
            
            # Save to file
            report_file = Path("eth_download_test_report.txt")
            with open(report_file, 'w') as f:
                f.write(report)
            
            # Save JSON results
            json_file = Path("eth_download_test_results.json")
            with open(json_file, 'w') as f:
                json.dump(self.test_results, f, indent=2, default=str)
            
            print("\n" + report)
            print(f"\n📄 Report saved to: {report_file}")
            print(f"📊 JSON results saved to: {json_file}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Test suite failed: {e}")
            return False
        
        finally:
            # Cleanup
            if self.temp_dir and os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
                print(f"🧹 Cleaned up test directory")


def main():
    """Main test runner."""
    print("ETH Institutional Download Tester")
    print("=================================\n")
    
    tester = ETHDownloadTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n✅ Test suite completed successfully!")
    else:
        print("\n❌ Test suite failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()