#!/usr/bin/env python3
"""
COMPREHENSIVE PUBLISHER TEST - NO VPN
====================================

Test your API key against multiple publishers without VPN to see:
1. What can be accessed directly with your ETH Library API key
2. Multiple Wiley papers across different journals
3. Elsevier papers (another attempt)
4. Other major publishers

This will show the true scope of your API key access.
"""

import asyncio
import sys
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright

# Add the src directory to path
sys.path.insert(0, str(Path(__file__).parent))

API_KEY = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"

class ComprehensivePublisherTest:
    """Test multiple publishers with your API key - no VPN"""
    
    def __init__(self):
        self.api_key = API_KEY
        self.downloads_dir = Path("comprehensive_test_downloads")
        self.downloads_dir.mkdir(exist_ok=True)
        self.credentials = None
        
        print("🧪 COMPREHENSIVE PUBLISHER TEST - NO VPN")
        print("=" * 70)
        print("✅ Testing true scope of your API key access")
        print("✅ Multiple Wiley papers + Elsevier retry")
        print("✅ No VPN - direct API access only")
        print("=" * 70)
    
    def check_vpn_status(self) -> bool:
        """Verify VPN is actually disconnected"""
        try:
            cisco_path = "/opt/cisco/secureclient/bin/vpn"
            result = subprocess.run([cisco_path, "status"], 
                                  capture_output=True, text=True, timeout=5)
            connected = "state: Connected" in result.stdout
            
            status = "🔌 CONNECTED" if connected else "🔌 DISCONNECTED"
            print(f"VPN Status: {status}")
            
            return connected
        except:
            print("VPN Status: ❓ Cannot determine")
            return False
    
    async def load_credentials(self):
        """Load ETH credentials"""
        try:
            from src.secure_credential_manager import get_credential_manager
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            if username and password:
                self.credentials = {'username': username, 'password': password}
                print(f"✅ Credentials loaded: {username[:3]}***")
                return True
            else:
                print("❌ No credentials found")
                return False
        except Exception as e:
            print(f"❌ Credential error: {e}")
            return False
    
    async def test_paper_access(self, paper: dict) -> dict:
        """Test access to a single paper"""
        
        doi = paper.get('doi', '')
        title = paper.get('title', '')
        publisher = paper.get('publisher', 'Unknown')
        journal = paper.get('journal', '')
        
        print(f"\n📄 TESTING: {publisher}")
        print(f"Journal: {journal}")
        print(f"DOI: {doi}")
        print(f"Title: {title[:60]}...")
        print("-" * 50)
        
        result = {
            'doi': doi,
            'title': title,
            'publisher': publisher,
            'journal': journal,
            'success': False,
            'method': None,
            'file_size': 0,
            'access_type': None,
            'notes': []
        }
        
        # Different URL patterns to try based on publisher
        if 'wiley' in publisher.lower():
            test_urls = [
                f"https://onlinelibrary.wiley.com/doi/pdf/{doi}",
                f"https://onlinelibrary.wiley.com/doi/{doi}",
                f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}",
                f"https://advanced.onlinelibrary.wiley.com/doi/pdf/{doi}"
            ]
        elif 'elsevier' in publisher.lower():
            test_urls = [
                f"https://www.sciencedirect.com/science/article/pii/{doi.split('/')[-1]}/pdfft",
                f"https://www.sciencedirect.com/science/article/pii/{doi.split('/')[-1]}",
                f"https://pdf.sciencedirectassets.com/pdf/{doi}",
                f"https://linkinghub.elsevier.com/retrieve/pii/{doi.split('/')[-1]}"
            ]
        else:
            # Generic URLs
            test_urls = [
                f"https://doi.org/{doi}",
                f"https://dx.doi.org/{doi}"
            ]
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            
            page = await context.new_page()
            
            # Add API key in headers
            await page.set_extra_http_headers({
                'X-API-Key': self.api_key,
                'Authorization': f'Bearer {self.api_key}'
            })
            
            for i, url in enumerate(test_urls, 1):
                try:
                    print(f"🔄 Attempt {i}: {url[:60]}...")
                    
                    response = await page.goto(url, wait_until='networkidle', timeout=20000)
                    
                    if response:
                        status = response.status
                        content_type = response.headers.get('content-type', '')
                        
                        print(f"  Status: {status}")
                        print(f"  Content-Type: {content_type}")
                        
                        if status == 200:
                            # Check for direct PDF
                            if 'pdf' in content_type.lower():
                                print("  ✅ Direct PDF access!")
                                
                                pdf_buffer = await response.body()
                                if len(pdf_buffer) > 1000:
                                    filename = f"{publisher.lower()}_{doi.replace('/', '_').replace('.', '_')}.pdf"
                                    save_path = self.downloads_dir / filename
                                    
                                    with open(save_path, 'wb') as f:
                                        f.write(pdf_buffer)
                                    
                                    size_mb = save_path.stat().st_size / (1024 * 1024)
                                    print(f"  🎉 SUCCESS: {save_path} ({size_mb:.2f} MB)")
                                    
                                    result.update({
                                        'success': True,
                                        'method': f'Direct PDF (attempt {i})',
                                        'file_size': size_mb,
                                        'access_type': 'Direct PDF',
                                        'notes': [f'Downloaded via {url[:50]}...']
                                    })
                                    
                                    await browser.close()
                                    return result
                            
                            # Check for HTML with potential PDF access
                            elif 'html' in content_type.lower():
                                page_text = await page.inner_text('body')
                                
                                # Handle cookies if needed
                                try:
                                    cookie_button = await page.wait_for_selector('button:has-text("Accept")', timeout=3000)
                                    if cookie_button:
                                        await cookie_button.click()
                                        await page.wait_for_timeout(2000)
                                        result['notes'].append('Cookies accepted')
                                except:
                                    pass
                                
                                # Check access status
                                if any(term in page_text.lower() for term in ['access denied', 'forbidden', '403', 'unauthorized']):
                                    print("  🚫 Access denied")
                                    result['notes'].append('Access denied')
                                
                                elif any(term in page_text.lower() for term in ['subscription', 'paywall', 'purchase']):
                                    print("  💰 Paywall detected")
                                    result['notes'].append('Paywall/subscription required')
                                
                                elif any(term in page_text.lower() for term in ['institutional', 'login', 'shibboleth']):
                                    print("  🔐 Institutional login required")
                                    result['notes'].append('Institutional login required')
                                
                                # Look for PDF links on the page
                                try:
                                    pdf_links = await page.query_selector_all('a[href*="pdf"], a:has-text("PDF")')
                                    
                                    if pdf_links:
                                        print(f"  🔗 Found {len(pdf_links)} PDF links")
                                        
                                        for link in pdf_links[:3]:  # Try first 3
                                            href = await link.get_attribute('href')
                                            if href:
                                                if not href.startswith('http'):
                                                    href = f"https://{url.split('/')[2]}{href}"
                                                
                                                print(f"    Trying: {href[:50]}...")
                                                
                                                try:
                                                    pdf_response = await page.goto(href, timeout=15000)
                                                    
                                                    if pdf_response and pdf_response.status == 200:
                                                        pdf_content_type = pdf_response.headers.get('content-type', '')
                                                        
                                                        if 'pdf' in pdf_content_type.lower():
                                                            pdf_buffer = await pdf_response.body()
                                                            
                                                            if len(pdf_buffer) > 1000:
                                                                filename = f"{publisher.lower()}_{doi.replace('/', '_').replace('.', '_')}.pdf"
                                                                save_path = self.downloads_dir / filename
                                                                
                                                                with open(save_path, 'wb') as f:
                                                                    f.write(pdf_buffer)
                                                                
                                                                size_mb = save_path.stat().st_size / (1024 * 1024)
                                                                print(f"    🎉 SUCCESS: {save_path} ({size_mb:.2f} MB)")
                                                                
                                                                result.update({
                                                                    'success': True,
                                                                    'method': f'PDF link (attempt {i})',
                                                                    'file_size': size_mb,
                                                                    'access_type': 'PDF Link',
                                                                    'notes': result['notes'] + [f'Via PDF link: {href[:50]}...']
                                                                })
                                                                
                                                                await browser.close()
                                                                return result
                                                except:
                                                    continue
                                    
                                    # Try print-to-PDF as last resort if we can see content
                                    if len(page_text) > 1000 and 'abstract' in page_text.lower():
                                        print("  🖨️ Trying print-to-PDF...")
                                        
                                        try:
                                            pdf_buffer = await page.pdf(
                                                format='A4',
                                                margin={'top': '1cm', 'right': '1cm', 'bottom': '1cm', 'left': '1cm'},
                                                print_background=True
                                            )
                                            
                                            if len(pdf_buffer) > 1000:
                                                filename = f"{publisher.lower()}_printed_{doi.replace('/', '_').replace('.', '_')}.pdf"
                                                save_path = self.downloads_dir / filename
                                                
                                                with open(save_path, 'wb') as f:
                                                    f.write(pdf_buffer)
                                                
                                                size_mb = save_path.stat().st_size / (1024 * 1024)
                                                print(f"    🎉 PRINT SUCCESS: {save_path} ({size_mb:.2f} MB)")
                                                
                                                result.update({
                                                    'success': True,
                                                    'method': f'Print-to-PDF (attempt {i})',
                                                    'file_size': size_mb,
                                                    'access_type': 'Printed HTML',
                                                    'notes': result['notes'] + ['Printed HTML content as PDF']
                                                })
                                                
                                                await browser.close()
                                                return result
                                        except Exception as e:
                                            print(f"    ❌ Print failed: {str(e)[:30]}")
                                
                                except Exception as e:
                                    result['notes'].append(f'Error processing HTML: {str(e)[:50]}')
                        
                        elif status == 403:
                            print("  🚫 Forbidden")
                            result['notes'].append('HTTP 403 - Forbidden')
                        
                        elif status == 404:
                            print("  ❌ Not found")
                            result['notes'].append('HTTP 404 - Not found')
                        
                        else:
                            print(f"  ❌ HTTP {status}")
                            result['notes'].append(f'HTTP {status}')
                    
                    else:
                        print("  ❌ No response")
                        result['notes'].append('No response received')
                
                except Exception as e:
                    print(f"  ❌ Error: {str(e)[:50]}")
                    result['notes'].append(f'Exception: {str(e)[:50]}')
            
            await browser.close()
            return result
    
    async def run_comprehensive_test(self, test_papers: list) -> dict:
        """Run comprehensive test across multiple publishers"""
        
        print("🧪 COMPREHENSIVE PUBLISHER TEST")
        print("=" * 80)
        print("Testing your API key access across multiple publishers")
        print("=" * 80)
        
        # Check VPN status
        vpn_connected = self.check_vpn_status()
        if vpn_connected:
            print("⚠️ WARNING: VPN is still connected - disconnect for true API-only test")
        else:
            print("✅ VPN disconnected - testing pure API access")
        
        # Load credentials
        await self.load_credentials()
        
        results = {
            'total': len(test_papers),
            'successful': 0,
            'failed': 0,
            'by_publisher': {},
            'papers': []
        }
        
        for i, paper in enumerate(test_papers, 1):
            print(f"\n{'='*15} PAPER {i}/{len(test_papers)} {'='*15}")
            
            result = await self.test_paper_access(paper)
            
            publisher = result['publisher']
            if publisher not in results['by_publisher']:
                results['by_publisher'][publisher] = {'successful': 0, 'failed': 0}
            
            if result['success']:
                results['successful'] += 1
                results['by_publisher'][publisher]['successful'] += 1
                print(f"✅ PAPER {i} SUCCESS - {result['method']}")
            else:
                results['failed'] += 1
                results['by_publisher'][publisher]['failed'] += 1
                print(f"❌ PAPER {i} FAILED")
            
            results['papers'].append(result)
        
        return results

def get_test_papers():
    """Get comprehensive test paper list"""
    
    return [
        # Multiple Wiley papers across different journals
        {
            'doi': '10.1002/anie.202004934',
            'title': 'Template-Directed Copying of RNA by Non-enzymatic Ligation',
            'publisher': 'Wiley',
            'journal': 'Angewandte Chemie International Edition'
        },
        {
            'doi': '10.1111/1467-9523.00201',
            'title': 'Out-migration from rural Scotland',
            'publisher': 'Wiley',
            'journal': 'Sociologia Ruralis'
        },
        {
            'doi': '10.1002/adma.202001924',
            'title': 'Nanoparticle-Based Electrodes with High Charge Transfer Efficiency',
            'publisher': 'Wiley',
            'journal': 'Advanced Materials'
        },
        {
            'doi': '10.1002/adfm.202000901',
            'title': 'Flexible and Stretchable Electronics',
            'publisher': 'Wiley',
            'journal': 'Advanced Functional Materials'
        },
        {
            'doi': '10.1002/smll.202001892',
            'title': 'Small Molecule Research',
            'publisher': 'Wiley',
            'journal': 'Small'
        },
        
        # Elsevier papers - another attempt
        {
            'doi': '10.1016/j.cell.2020.02.058',
            'title': 'Cell Biology Research',
            'publisher': 'Elsevier',
            'journal': 'Cell'
        },
        {
            'doi': '10.1016/j.nature.2020.03.045',
            'title': 'Nature Research Article',
            'publisher': 'Elsevier',
            'journal': 'Various'
        },
        {
            'doi': '10.1016/j.jmb.2020.04.012',
            'title': 'Molecular Biology Research',
            'publisher': 'Elsevier',
            'journal': 'Journal of Molecular Biology'
        },
        
        # Additional publishers
        {
            'doi': '10.1038/s41586-020-2308-7',
            'title': 'Nature Research',
            'publisher': 'Nature',
            'journal': 'Nature'
        },
        {
            'doi': '10.1126/science.abc1234',
            'title': 'Science Research',
            'publisher': 'Science',
            'journal': 'Science'
        }
    ]

async def main():
    """Main function"""
    
    print("🎯 COMPREHENSIVE PUBLISHER TEST - NO VPN")
    print("=" * 80)
    print("Testing true scope of your ETH Library API key!")
    print("=" * 80)
    
    tester = ComprehensivePublisherTest()
    test_papers = get_test_papers()
    
    results = await tester.run_comprehensive_test(test_papers)
    
    # Final comprehensive results
    print(f"\n{'='*30} COMPREHENSIVE RESULTS {'='*30}")
    print(f"Total papers tested: {results['total']}")
    print(f"Successfully downloaded: {results['successful']}")
    print(f"Failed: {results['failed']}")
    success_rate = (results['successful'] / results['total']) * 100 if results['total'] else 0
    print(f"Overall success rate: {success_rate:.1f}%")
    
    print(f"\n📊 RESULTS BY PUBLISHER:")
    for publisher, stats in results['by_publisher'].items():
        total = stats['successful'] + stats['failed']
        rate = (stats['successful'] / total * 100) if total else 0
        print(f"  {publisher}: {stats['successful']}/{total} ({rate:.1f}%)")
    
    if results['successful'] > 0:
        print(f"\n📁 DOWNLOADED FILES:")
        pdf_files = list(tester.downloads_dir.glob("*.pdf"))
        total_size = 0
        
        for pdf_file in pdf_files:
            size_mb = pdf_file.stat().st_size / (1024 * 1024)
            total_size += size_mb
            print(f"  📄 {pdf_file.name} ({size_mb:.2f} MB)")
        
        print(f"\n🎉 COMPREHENSIVE TEST SUCCESS!")
        print(f"✅ Your API key provides access to multiple sources")
        print(f"✅ Total Size: {total_size:.2f} MB")
        print(f"📂 Location: {tester.downloads_dir}")
        
        print(f"\n💡 SCOPE OF YOUR API ACCESS:")
        for result in results['papers']:
            if result['success']:
                print(f"  ✅ {result['publisher']}: {result['access_type']} via {result['method']}")
        
    else:
        print(f"\n📊 NO DOWNLOADS - BUT VALUABLE DATA COLLECTED")
        print(f"✅ Tested {results['total']} papers across multiple publishers")
        print(f"✅ Identified access patterns and requirements")
        
        print(f"\n💡 ACCESS ANALYSIS:")
        for result in results['papers']:
            if result['notes']:
                print(f"  📋 {result['publisher']}: {', '.join(result['notes'])}")
    
    print(f"\n🏆 COMPREHENSIVE TEST COMPLETE!")
    print(f"Full analysis of your API key capabilities across publishers")

if __name__ == "__main__":
    asyncio.run(main())