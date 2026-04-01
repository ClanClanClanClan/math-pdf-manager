#!/usr/bin/env python3
"""
Final Comprehensive Test - All Three Publishers in Headless Mode
Tests IEEE, Springer, and Elsevier with actual PDF downloads
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FinalSystemTest:
    def __init__(self):
        # Get credentials
        cred_manager = get_credential_manager()
        self.username = cred_manager.get_credential('eth_username')
        self.password = cred_manager.get_credential('eth_password')
        
        if not self.username or not self.password:
            raise ValueError("ETH credentials not found")
        
        # Create final test directory
        self.output_dir = Path.cwd() / "final_test_results"
        self.output_dir.mkdir(exist_ok=True)
        
        # Create publisher-specific directories
        self.ieee_dir = self.output_dir / "IEEE"
        self.springer_dir = self.output_dir / "Springer"
        self.elsevier_dir = self.output_dir / "Elsevier"
        
        for dir_path in [self.ieee_dir, self.springer_dir, self.elsevier_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Test cases - one paper per publisher for quick verification
        self.test_cases = [
            {
                'publisher': 'IEEE',
                'navigator_class': IEEEStealthNavigator,
                'config': IEEE_STEALTH_CONFIG,
                'doi': '10.1109/CVPR.2015.7298594',
                'title': 'Deep Learning Computer Vision',
                'output_dir': self.ieee_dir
            },
            {
                'publisher': 'Springer',
                'navigator_class': SpringerNavigator,
                'config': SPRINGER_CONFIG,
                'doi': '10.1007/s00211-021-01234-3',
                'title': 'Discontinuous Galerkin Algorithms',
                'output_dir': self.springer_dir
            },
            {
                'publisher': 'Elsevier',
                'navigator_class': ElsevierNavigator,
                'config': ELSEVIER_CONFIG,
                'doi': '10.1016/j.jcp.2024.113362',
                'title': 'Computational Physics',
                'output_dir': self.elsevier_dir
            }
        ]
        
        self.results = []
    
    async def test_publisher(self, test_case):
        """Test a single publisher."""
        publisher = test_case['publisher']
        navigator_class = test_case['navigator_class']
        config = test_case['config']
        doi = test_case['doi']
        title = test_case['title']
        output_dir = test_case['output_dir']
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing {publisher}: {title}")
        logger.info(f"DOI: {doi}")
        logger.info(f"Headless Mode: TRUE")
        
        context = None
        page = None
        
        try:\n            # Create browser context\n            context = await self.browser.new_context(\n                viewport={'width': 1920, 'height': 1080},\n                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',\n                accept_downloads=True\n            )\n            page = await context.new_page()\n            \n            # Create navigator\n            navigator = navigator_class(page, config)\n            navigator.eth_auth = ETHAuthenticator(page, self.username, self.password)\n            \n            # Navigate to paper\n            if hasattr(navigator, 'navigate_to_paper'):\n                success = await navigator.navigate_to_paper(doi)\n            else:\n                url = f\"https://doi.org/{doi}\"\n                await page.goto(url, wait_until='domcontentloaded', timeout=30000)\n                success = True\n            \n            if not success:\n                raise Exception(\"Failed to navigate to paper\")\n            \n            # Authenticate\n            await navigator.navigate_to_login()\n            await navigator.select_eth_institution()\n            await navigator.eth_auth.perform_login()\n            await navigator.navigate_after_auth()\n            \n            # Download PDF\n            result = await navigator.download_pdf(output_dir)\n            \n            if result:\n                file_size = result.stat().st_size\n                file_size_mb = file_size / (1024 * 1024)\n                \n                # Check if it's a real PDF\n                is_pdf = False\n                if result.suffix == '.pdf' and file_size > 1000:\n                    try:\n                        with open(result, 'rb') as f:\n                            header = f.read(4)\n                            is_pdf = (header == b'%PDF')\n                    except:\n                        pass\n                \n                success_type = \"PDF\" if is_pdf else \"Confirmation\"\n                logger.info(f\"✅ SUCCESS: {result.name}\")\n                logger.info(f\"   Size: {file_size:,} bytes ({file_size_mb:.2f} MB)\")\n                logger.info(f\"   Type: {success_type}\")\n                \n                self.results.append({\n                    'publisher': publisher,\n                    'title': title,\n                    'doi': doi,\n                    'status': 'SUCCESS',\n                    'file': result.name,\n                    'size': file_size,\n                    'is_pdf': is_pdf,\n                    'type': success_type\n                })\n            else:\n                logger.error(f\"❌ FAILED: No file created\")\n                self.results.append({\n                    'publisher': publisher,\n                    'title': title,\n                    'doi': doi,\n                    'status': 'FAILED',\n                    'file': None,\n                    'size': 0,\n                    'is_pdf': False,\n                    'type': 'None'\n                })\n                \n        except Exception as e:\n            logger.error(f\"❌ ERROR: {str(e)}\")\n            self.results.append({\n                'publisher': publisher,\n                'title': title,\n                'doi': doi,\n                'status': 'ERROR',\n                'file': None,\n                'size': 0,\n                'is_pdf': False,\n                'type': 'None',\n                'error': str(e)\n            })\n        finally:\n            if page:\n                await page.close()\n            if context:\n                await context.close()\n    \n    async def run_final_test(self):\n        \"\"\"Run the final comprehensive test.\"\"\"\n        logger.info(f\"\nFINAL SYSTEM TEST - HEADLESS MODE\")\n        logger.info(f\"Testing {len(self.test_cases)} publishers\")\n        logger.info(f\"Output directory: {self.output_dir}\")\n        \n        async with async_playwright() as p:\n            # Launch in headless mode\n            self.browser = await p.chromium.launch(\n                headless=True,  # HEADLESS MODE!\n                args=[\n                    '--disable-blink-features=AutomationControlled',\n                    '--disable-dev-shm-usage',\n                    '--no-sandbox',\n                    '--disable-gpu',\n                    '--disable-web-security'\n                ]\n            )\n            \n            try:\n                # Test each publisher\n                for test_case in self.test_cases:\n                    await self.test_publisher(test_case)\n                    await asyncio.sleep(1)  # Brief pause between tests\n                \n            finally:\n                await self.browser.close()\n        \n        # Generate final report\n        self.generate_final_report()\n    \n    def generate_final_report(self):\n        \"\"\"Generate final test report.\"\"\"\n        timestamp = datetime.now().strftime(\"%Y%m%d_%H%M%S\")\n        report_file = self.output_dir / f\"final_report_{timestamp}.txt\"\n        \n        # Calculate statistics\n        total = len(self.results)\n        successful = sum(1 for r in self.results if r['status'] == 'SUCCESS')\n        pdf_downloads = sum(1 for r in self.results if r.get('is_pdf', False))\n        total_size = sum(r['size'] for r in self.results)\n        \n        success_rate = (successful / total * 100) if total > 0 else 0\n        pdf_rate = (pdf_downloads / total * 100) if total > 0 else 0\n        \n        # Write comprehensive report\n        with open(report_file, 'w') as f:\n            f.write(\"FINAL INSTITUTIONAL ACCESS SYSTEM REPORT\\n\")\n            f.write(\"=\"*50 + \"\\n\")\n            f.write(f\"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n\")\n            f.write(f\"Test Mode: HEADLESS\\n\")\n            f.write(f\"Overall Success Rate: {success_rate:.1f}%\\n\")\n            f.write(f\"PDF Download Rate: {pdf_rate:.1f}%\\n\")\n            f.write(f\"Total Data: {total_size/1024/1024:.2f} MB\\n\")\n            f.write(\"\\nDetailed Results:\\n\")\n            f.write(\"-\" * 30 + \"\\n\")\n            \n            for r in self.results:\n                status_icon = \"✅\" if r['status'] == 'SUCCESS' else \"❌\"\n                type_icon = \"📄\" if r.get('is_pdf') else \"📝\" if r['status'] == 'SUCCESS' else \"❌\"\n                \n                f.write(f\"{status_icon} {r['publisher']}: {r['title']} - {r['status']}\\n\")\n                if r['file']:\n                    f.write(f\"   {type_icon} File: {r['file']} ({r['size']/1024:.1f} KB)\\n\")\n                if r.get('error'):\n                    f.write(f\"   Error: {r['error']}\\n\")\n                f.write(\"\\n\")\n            \n            # Publisher breakdown\n            f.write(\"Publisher Performance:\\n\")\n            f.write(\"-\" * 20 + \"\\n\")\n            for pub in ['IEEE', 'Springer', 'Elsevier']:\n                pub_results = [r for r in self.results if r['publisher'] == pub]\n                if pub_results:\n                    pub_result = pub_results[0]\n                    status = pub_result['status']\n                    f.write(f\"{pub}: {status}\")\n                    if pub_result.get('is_pdf'):\n                        f.write(\" (PDF)\")\n                    elif status == 'SUCCESS':\n                        f.write(\" (Access Confirmed)\")\n                    f.write(\"\\n\")\n        \n        # Display summary\n        print(f\"\\n{'='*60}\")\n        print(f\"FINAL TEST SUMMARY - HEADLESS MODE\")\n        print(f\"{'='*60}\")\n        print(f\"✅ Success Rate: {success_rate:.1f}% ({successful}/{total})\")\n        print(f\"📄 PDF Downloads: {pdf_downloads}/{total}\")\n        print(f\"📝 Access Confirmations: {successful - pdf_downloads}/{total}\")\n        print(f\"💾 Total Size: {total_size/1024/1024:.2f} MB\")\n        print(f\"📊 Report: {report_file}\")\n        \n        # Individual results\n        for r in self.results:\n            status_icon = \"✅\" if r['status'] == 'SUCCESS' else \"❌\"\n            type_desc = \"PDF\" if r.get('is_pdf') else \"Confirmed\" if r['status'] == 'SUCCESS' else \"Failed\"\n            print(f\"{status_icon} {r['publisher']}: {type_desc}\")\n\nasync def main():\n    test = FinalSystemTest()\n    await test.run_final_test()\n\nif __name__ == \"__main__\":\n    asyncio.run(main())