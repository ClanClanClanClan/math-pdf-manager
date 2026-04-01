#!/usr/bin/env python3
"""
Final Test - All Three Publishers in Headless Mode
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_final_system():
    """Test all three publishers in headless mode."""
    
    # Get credentials
    cred_manager = get_credential_manager()
    username = cred_manager.get_credential('eth_username')
    password = cred_manager.get_credential('eth_password')
    
    if not username or not password:
        raise ValueError("ETH credentials not found")
    
    # Create output directory
    output_dir = Path.cwd() / "final_headless_test"
    output_dir.mkdir(exist_ok=True)
    
    # Test cases
    test_cases = [
        {
            'publisher': 'IEEE',
            'navigator_class': IEEEStealthNavigator,
            'config': IEEE_STEALTH_CONFIG,
            'doi': '10.1109/CVPR.2015.7298594',
            'title': 'Deep Learning Computer Vision'
        },
        {
            'publisher': 'Springer', 
            'navigator_class': SpringerNavigator,
            'config': SPRINGER_CONFIG,
            'doi': '10.1007/s00211-021-01234-3',
            'title': 'Discontinuous Galerkin Algorithms'
        },
        {
            'publisher': 'Elsevier',
            'navigator_class': ElsevierNavigator,
            'config': ELSEVIER_CONFIG,
            'doi': '10.1016/j.jcp.2024.113362',
            'title': 'Computational Physics'
        }
    ]
    
    results = []
    
    logger.info("FINAL HEADLESS TEST STARTING...")
    logger.info(f"Testing {len(test_cases)} publishers")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,  # HEADLESS MODE!
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        
        try:
            for test_case in test_cases:
                publisher = test_case['publisher']
                navigator_class = test_case['navigator_class']
                config = test_case['config']
                doi = test_case['doi']
                title = test_case['title']
                
                logger.info(f"\n{'='*50}")
                logger.info(f"Testing {publisher}: {title}")
                logger.info(f"DOI: {doi}")
                logger.info("Mode: HEADLESS")
                
                context = None
                page = None
                
                try:
                    # Create context and page
                    context = await browser.new_context(
                        viewport={'width': 1920, 'height': 1080},
                        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                        accept_downloads=True
                    )
                    page = await context.new_page()
                    
                    # Create navigator
                    navigator = navigator_class(page, config)
                    navigator.eth_auth = ETHAuthenticator(page, username, password)
                    
                    # Navigate to paper
                    if hasattr(navigator, 'navigate_to_paper'):
                        success = await navigator.navigate_to_paper(doi)
                    else:
                        url = f"https://doi.org/{doi}"
                        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        success = True
                    
                    if not success:
                        raise Exception("Failed to navigate to paper")
                    
                    # Authenticate
                    await navigator.navigate_to_login()
                    await navigator.select_eth_institution()
                    await navigator.eth_auth.perform_login()
                    await navigator.navigate_after_auth()
                    
                    # Download PDF
                    result = await navigator.download_pdf(output_dir)
                    
                    if result:
                        file_size = result.stat().st_size
                        
                        # Check if it's a real PDF
                        is_pdf = False
                        if result.suffix == '.pdf' and file_size > 1000:
                            try:
                                with open(result, 'rb') as f:
                                    header = f.read(4)
                                    is_pdf = (header == b'%PDF')
                            except:
                                pass
                        
                        success_type = "PDF" if is_pdf else "Confirmation"
                        logger.info(f"✅ SUCCESS: {result.name}")
                        logger.info(f"   Size: {file_size:,} bytes")
                        logger.info(f"   Type: {success_type}")
                        
                        results.append({
                            'publisher': publisher,
                            'status': 'SUCCESS',
                            'file': result.name,
                            'size': file_size,
                            'is_pdf': is_pdf,
                            'type': success_type
                        })
                    else:
                        logger.error(f"❌ FAILED: No file created")
                        results.append({
                            'publisher': publisher,
                            'status': 'FAILED',
                            'file': None,
                            'size': 0,
                            'is_pdf': False,
                            'type': 'None'
                        })
                        
                except Exception as e:
                    logger.error(f"❌ ERROR: {str(e)}")
                    results.append({
                        'publisher': publisher,
                        'status': 'ERROR',
                        'file': None,
                        'size': 0,
                        'is_pdf': False,
                        'type': 'None',
                        'error': str(e)
                    })
                finally:
                    if page:
                        await page.close()
                    if context:
                        await context.close()
                
                # Brief pause between tests
                await asyncio.sleep(1)
                
        finally:
            await browser.close()
    
    # Generate final report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_dir / f"final_headless_report_{timestamp}.txt"
    
    total = len(results)
    successful = sum(1 for r in results if r['status'] == 'SUCCESS')
    pdf_downloads = sum(1 for r in results if r.get('is_pdf', False))
    total_size = sum(r['size'] for r in results)
    
    success_rate = (successful / total * 100) if total > 0 else 0
    pdf_rate = (pdf_downloads / total * 100) if total > 0 else 0
    
    # Write report
    with open(report_file, 'w') as f:
        f.write("FINAL INSTITUTIONAL ACCESS SYSTEM REPORT\\n")
        f.write("=" * 50 + "\\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
        f.write(f"Test Mode: HEADLESS\\n")
        f.write(f"Overall Success Rate: {success_rate:.1f}%\\n")
        f.write(f"PDF Download Rate: {pdf_rate:.1f}%\\n")
        f.write(f"Total Data: {total_size/1024/1024:.2f} MB\\n")
        f.write("\\nResults:\\n")
        
        for r in results:
            status_icon = "✅" if r['status'] == 'SUCCESS' else "❌"
            f.write(f"{status_icon} {r['publisher']}: {r['status']}")
            if r['file']:
                f.write(f" - {r['type']} ({r['size']/1024:.1f} KB)")
            f.write("\\n")
    
    # Display summary
    print(f"\\n{'='*60}")
    print("FINAL HEADLESS TEST SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Success Rate: {success_rate:.1f}% ({successful}/{total})")
    print(f"📄 PDF Downloads: {pdf_downloads}/{total}")
    print(f"📝 Access Confirmations: {successful - pdf_downloads}/{total}")
    print(f"💾 Total Size: {total_size/1024/1024:.2f} MB")
    print(f"📊 Report: {report_file}")
    
    for r in results:
        status_icon = "✅" if r['status'] == 'SUCCESS' else "❌"
        type_desc = "PDF" if r.get('is_pdf') else "Confirmed" if r['status'] == 'SUCCESS' else "Failed"
        print(f"{status_icon} {r['publisher']}: {type_desc}")

if __name__ == "__main__":
    asyncio.run(test_final_system())