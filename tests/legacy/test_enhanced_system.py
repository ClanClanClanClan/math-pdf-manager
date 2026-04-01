#!/usr/bin/env python3
"""
Enhanced Three-Publisher System Test
Test all three publishers with actual PDF downloads
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.publishers.institutional.base import ETHAuthenticator
from src.publishers.institutional.publishers.elsevier_navigator import (
    ELSEVIER_CONFIG,
    ElsevierNavigator,
)
from src.publishers.institutional.publishers.ieee_stealth_navigator import (
    IEEE_STEALTH_CONFIG,
    IEEEStealthNavigator,
)
from src.publishers.institutional.publishers.springer_navigator import (
    SPRINGER_CONFIG,
    SpringerNavigator,
)
from src.secure_credential_manager import get_credential_manager

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('enhanced_system_test.log')
    ]
)
logger = logging.getLogger(__name__)

class EnhancedSystemTest:
    def __init__(self):
        # Get credentials
        cred_manager = get_credential_manager()
        self.username = cred_manager.get_credential('eth_username')
        self.password = cred_manager.get_credential('eth_password')
        
        if not self.username or not self.password:
            raise ValueError("ETH credentials not found. Please run setup_credentials.py")
        
        # Create organized folder structure  
        self.base_dir = Path.cwd() / "academic_pdfs_enhanced"
        self.ieee_dir = self.base_dir / "IEEE"
        self.springer_dir = self.base_dir / "Springer"
        self.elsevier_dir = self.base_dir / "Elsevier"
        self.reports_dir = self.base_dir / "test_reports"
        
        # Create all directories
        for dir_path in [self.ieee_dir, self.springer_dir, self.elsevier_dir, self.reports_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Test cases with known working papers
        self.test_cases = [
            # IEEE papers
            {
                'publisher': 'ieee',
                'doi': '10.1109/CVPR.2015.7298594',
                'title': 'Deep Learning Computer Vision',
                'output_dir': self.ieee_dir
            },
            {
                'publisher': 'ieee',
                'doi': '10.1109/5.771073', 
                'title': 'IEEE Proceedings Paper',
                'output_dir': self.ieee_dir
            },
            
            # Springer papers
            {
                'publisher': 'springer',
                'doi': '10.1007/s00211-021-01234-3',
                'title': 'Discontinuous Galerkin Algorithms',
                'output_dir': self.springer_dir
            },
            {
                'publisher': 'springer',
                'doi': '10.1007/s10444-024-10146-3',
                'title': 'Lambert W Function',
                'output_dir': self.springer_dir
            },
            
            # Elsevier papers  
            {
                'publisher': 'elsevier',
                'doi': '10.1016/j.jmb.2021.166854',
                'title': 'DNA Mechanics',
                'output_dir': self.elsevier_dir
            },
            {
                'publisher': 'elsevier',
                'doi': '10.1016/j.jcp.2024.113362',
                'title': 'Computational Physics',
                'output_dir': self.elsevier_dir
            }
        ]
        
        self.results = []
        
    async def test_paper(self, test_case, browser):
        """Test a single paper download"""
        publisher = test_case['publisher']
        doi = test_case['doi']
        title = test_case['title']
        output_dir = test_case['output_dir']
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing {publisher.upper()}: {title}")
        logger.info(f"DOI: {doi}")
        logger.info(f"Output: {output_dir}")
        
        context = None
        page = None
        
        try:
            # Create browser context
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            # Create appropriate navigator
            if publisher == 'ieee':
                navigator = IEEEStealthNavigator(page, IEEE_STEALTH_CONFIG)
            elif publisher == 'springer':
                navigator = SpringerNavigator(page, SPRINGER_CONFIG)
            elif publisher == 'elsevier':
                navigator = ElsevierNavigator(page, ELSEVIER_CONFIG)
            else:
                raise ValueError(f"Unknown publisher: {publisher}")
            
            # Set ETH authenticator
            navigator.eth_auth = ETHAuthenticator(page, self.username, self.password)
            
            # Navigate to paper
            if hasattr(navigator, 'navigate_to_paper'):
                await navigator.navigate_to_paper(doi)
            else:
                url = f"https://doi.org/{doi}"
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Authenticate
            await navigator.navigate_to_login()
            await navigator.select_eth_institution()
            await navigator.eth_auth.perform_login()
            await navigator.navigate_after_auth()
            
            # Download PDF
            result = await navigator.download_pdf(output_dir)
            
            if result:
                # Check file size
                file_size = result.stat().st_size
                file_size_mb = file_size / (1024 * 1024)
                
                # Determine if it's a real PDF
                is_pdf = False
                if result.suffix == '.pdf' and file_size > 10000:
                    # Check PDF magic bytes
                    with open(result, 'rb') as f:
                        header = f.read(4)
                        is_pdf = (header == b'%PDF')
                
                logger.info(f"✅ SUCCESS: {result.name}")
                logger.info(f"   Size: {file_size:,} bytes ({file_size_mb:.2f} MB)")
                logger.info(f"   Type: {'PDF' if is_pdf else 'Access Confirmation'}")
                
                self.results.append({
                    'publisher': publisher,
                    'title': title,
                    'doi': doi,
                    'status': 'SUCCESS',
                    'file': result.name,
                    'size': file_size,
                    'is_pdf': is_pdf
                })
            else:
                logger.error(f"❌ FAILED: No file downloaded")
                self.results.append({
                    'publisher': publisher,
                    'title': title,
                    'doi': doi,
                    'status': 'FAILED',
                    'file': None,
                    'size': 0,
                    'is_pdf': False
                })
                
        except Exception as e:
            logger.error(f"❌ ERROR: {str(e)}")
            self.results.append({
                'publisher': publisher,
                'title': title,
                'doi': doi,
                'status': 'ERROR',
                'file': None,
                'size': 0,
                'is_pdf': False,
                'error': str(e)
            })
        finally:
            # Cleanup browser resources
            if page:
                await page.close()
            if context:
                await context.close()
    
    async def run_tests(self):
        """Run all tests"""
        logger.info(f"\nStarting Enhanced System Test")
        logger.info(f"Testing {len(self.test_cases)} papers across 3 publishers")
        logger.info(f"Output directory: {self.base_dir}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            
            try:
                # Test each paper
                for test_case in self.test_cases:
                    await self.test_paper(test_case, browser)
                    
                    # Small delay between papers
                    await asyncio.sleep(2)
                
            finally:
                # Always cleanup
                await browser.close()
        
        # Generate report
        self.generate_report()
        
    def generate_report(self):
        """Generate test report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"enhanced_report_{timestamp}.txt"
        
        # Calculate statistics
        total = len(self.results)
        successful = sum(1 for r in self.results if r['status'] == 'SUCCESS')
        pdf_downloads = sum(1 for r in self.results if r.get('is_pdf', False))
        total_size = sum(r['size'] for r in self.results)
        
        success_rate = (successful / total * 100) if total > 0 else 0
        pdf_rate = (pdf_downloads / total * 100) if total > 0 else 0
        
        # Write report
        with open(report_file, 'w') as f:
            f.write("ENHANCED SYSTEM TEST REPORT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Overall Success Rate: {success_rate:.1f}%\n")
            f.write(f"PDF Download Rate: {pdf_rate:.1f}%\n")
            f.write(f"Total Data Downloaded: {total_size/1024/1024:.2f} MB\n")
            f.write("\nResults:\n")
            
            for r in self.results:
                status_icon = "✅" if r['status'] == 'SUCCESS' else "❌"
                pdf_icon = "📄" if r.get('is_pdf') else "📝"
                f.write(f"  {status_icon} {r['publisher'].upper()}: {r['title']} - {r['status']}")
                if r['file']:
                    f.write(f" {pdf_icon} ({r['size']/1024/1024:.2f} MB)")
                f.write("\n")
        
        # Display summary
        print(f"\n{'='*60}")
        print(f"ENHANCED TEST SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Success Rate: {success_rate:.1f}% ({successful}/{total})")
        print(f"📄 PDF Downloads: {pdf_downloads}/{total}")
        print(f"💾 Total Size: {total_size/1024/1024:.2f} MB")
        print(f"📊 Report saved: {report_file}")
        
        # Publisher breakdown
        for pub in ['ieee', 'springer', 'elsevier']:
            pub_results = [r for r in self.results if r['publisher'] == pub]
            pub_success = sum(1 for r in pub_results if r['status'] == 'SUCCESS')
            pub_pdfs = sum(1 for r in pub_results if r.get('is_pdf', False))
            print(f"\n{pub.upper()}:")
            print(f"  Success: {pub_success}/{len(pub_results)}")
            print(f"  PDFs: {pub_pdfs}/{len(pub_results)}")

async def main():
    test = EnhancedSystemTest()
    await test.run_tests()

if __name__ == "__main__":
    asyncio.run(main())