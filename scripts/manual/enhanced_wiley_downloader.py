#!/usr/bin/env python3
"""
ENHANCED WILEY DOWNLOADER
=========================

Enhanced version that handles institutional login redirects better.
Since we confirmed VPN is working and reaching Wiley successfully.
"""

import asyncio
import requests
from pathlib import Path
from playwright.async_api import async_playwright

# Your working credentials
API_KEY = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"

class EnhancedWileyDownloader:
    """Enhanced Wiley downloader with better institutional login handling"""
    
    def __init__(self):
        self.api_key = API_KEY
        self.downloads_dir = Path("enhanced_downloads")
        self.downloads_dir.mkdir(exist_ok=True)
    
    async def download_with_session_persistence(self, doi: str, title: str = "") -> bool:
        """Download with persistent session to handle redirects"""
        
        print(f"\n📄 ENHANCED DOWNLOAD: {title or doi}")
        print(f"DOI: {doi}")
        print("-" * 50)
        
        # Try different Wiley URL patterns
        url_patterns = [
            f"https://onlinelibrary.wiley.com/doi/pdf/{doi}",
            f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}",
            f"https://onlinelibrary.wiley.com/doi/{doi}/pdf",
            f"https://advanced.onlinelibrary.wiley.com/doi/pdf/{doi}",
        ]
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # Show browser for debugging
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                accept_downloads=True
            )
            
            page = await context.new_page()
            
            # Set API key in cookies and headers
            await context.add_cookies([{
                'name': 'eth_api_key',
                'value': self.api_key,
                'domain': '.wiley.com',
                'path': '/'
            }])
            
            await page.set_extra_http_headers({
                'X-API-Key': self.api_key,
                'Authorization': f'Bearer {self.api_key}'
            })
            
            for i, url in enumerate(url_patterns, 1):
                print(f"\n🔄 Attempt {i}: {url[:60]}...")
                
                try:
                    # Navigate to URL
                    response = await page.goto(url, 
                                             wait_until='networkidle', 
                                             timeout=30000)
                    
                    # Wait a moment for any redirects
                    await page.wait_for_timeout(3000)
                    
                    current_url = page.url
                    print(f"  Final URL: {current_url[:60]}...")
                    
                    # Check for direct PDF
                    if response and response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        
                        if 'pdf' in content_type.lower():
                            print("  ✅ Direct PDF access!")
                            pdf_buffer = await response.body()
                            
                            if len(pdf_buffer) > 1000:
                                filename = f"enhanced_{doi.replace('/', '_').replace('.', '_')}.pdf"
                                save_path = self.downloads_dir / filename
                                
                                with open(save_path, 'wb') as f:
                                    f.write(pdf_buffer)
                                
                                size_mb = save_path.stat().st_size / (1024 * 1024)
                                print(f"  🎉 SUCCESS: {save_path} ({size_mb:.2f} MB)")
                                
                                await browser.close()
                                return True
                    
                    # Check for institutional login page
                    page_content = await page.content()
                    page_text = await page.inner_text('body')
                    
                    # Look for ETH-specific elements
                    eth_indicators = ['eth zurich', 'ethz', 'shibboleth', 'switch aai']
                    has_eth_login = any(indicator in page_text.lower() for indicator in eth_indicators)
                    
                    if has_eth_login:
                        print("  🎯 ETH institutional login detected")
                        
                        # Try to find and click ETH option
                        eth_selectors = [
                            'text="ETH Zurich"',
                            'text="ETH"',
                            '[value*="ethz"]',
                            'a[href*="ethz"]',
                            'option:has-text("ETH")'
                        ]
                        
                        for selector in eth_selectors:
                            try:
                                await page.wait_for_selector(selector, timeout=3000)
                                print(f"    Found ETH option: {selector}")
                                await page.click(selector)
                                await page.wait_for_load_state('networkidle', timeout=10000)
                                
                                # Check if we're now at ETH login
                                if 'ethz.ch' in page.url:
                                    print("    ✅ Redirected to ETH login")
                                    print("    💡 Manual login required here")
                                    
                                    # Wait for potential manual login
                                    print("    ⏳ Waiting 30s for manual login...")
                                    await page.wait_for_timeout(30000)
                                    
                                    # Check if we're back to content
                                    if 'wiley.com' in page.url:
                                        print("    🎉 Back to Wiley - checking for PDF")
                                        
                                        # Try to download again
                                        try:
                                            pdf_response = await page.goto(url)
                                            if pdf_response and 'pdf' in pdf_response.headers.get('content-type', ''):
                                                pdf_buffer = await pdf_response.body()
                                                
                                                if len(pdf_buffer) > 1000:
                                                    filename = f"enhanced_{doi.replace('/', '_').replace('.', '_')}.pdf"
                                                    save_path = self.downloads_dir / filename
                                                    
                                                    with open(save_path, 'wb') as f:
                                                        f.write(pdf_buffer)
                                                    
                                                    size_mb = save_path.stat().st_size / (1024 * 1024)
                                                    print(f"    🎉 SUCCESS: {save_path} ({size_mb:.2f} MB)")
                                                    
                                                    await browser.close()
                                                    return True
                                        except:
                                            pass
                                
                                break
                                
                            except:
                                continue
                    
                    # Look for direct PDF download links
                    pdf_links = await page.query_selector_all('a[href*="pdf"], a[href*="download"]')
                    
                    if pdf_links:
                        print(f"  🔗 Found {len(pdf_links)} potential download links")
                        
                        for j, link in enumerate(pdf_links[:3]):
                            try:
                                href = await link.get_attribute('href')
                                text = await link.inner_text()
                                
                                if href and ('pdf' in href.lower() or 'download' in text.lower()):
                                    print(f"    Trying link {j+1}: {text[:30]}...")
                                    
                                    # Try clicking the link
                                    async with page.expect_download() as download_info:
                                        await link.click()
                                    
                                    download = await download_info.value
                                    
                                    # Save the download
                                    filename = f"enhanced_{doi.replace('/', '_').replace('.', '_')}.pdf"
                                    save_path = self.downloads_dir / filename
                                    
                                    await download.save_as(save_path)
                                    
                                    if save_path.exists() and save_path.stat().st_size > 1000:
                                        size_mb = save_path.stat().st_size / (1024 * 1024)
                                        print(f"    🎉 SUCCESS: {save_path} ({size_mb:.2f} MB)")
                                        
                                        await browser.close()
                                        return True
                                        
                            except Exception as e:
                                print(f"    ❌ Link {j+1} failed: {str(e)[:30]}...")
                                continue
                    
                    print(f"  ❌ No PDF access via this URL")
                    
                except Exception as e:
                    print(f"  ❌ Error: {str(e)[:50]}...")
            
            await browser.close()
            return False
    
    async def batch_download(self, papers: list) -> dict:
        """Enhanced batch download"""
        
        print("🚀 ENHANCED WILEY DOWNLOADER")
        print("=" * 70)
        print("Better institutional login handling + API key integration")
        print("=" * 70)
        
        results = {
            'successful': 0,
            'failed': 0,
            'papers': []
        }
        
        for i, paper in enumerate(papers, 1):
            print(f"\n{'='*15} PAPER {i}/{len(papers)} {'='*15}")
            
            doi = paper.get('doi', '')
            title = paper.get('title', '')
            
            if not doi:
                print("❌ No DOI provided")
                results['failed'] += 1
                continue
            
            success = await self.download_with_session_persistence(doi, title)
            
            if success:
                results['successful'] += 1
                print(f"✅ PAPER {i} SUCCESS")
            else:
                results['failed'] += 1
                print(f"❌ PAPER {i} FAILED")
            
            results['papers'].append({
                'doi': doi,
                'title': title,
                'success': success
            })
        
        return results

async def main():
    """Main function"""
    
    print("🎯 ENHANCED WILEY DOWNLOADER WITH BETTER LOGIN HANDLING")
    print("=" * 80)
    print("Improved institutional access + API key integration")
    print("=" * 80)
    
    downloader = EnhancedWileyDownloader()
    
    # Test with one paper first
    papers = [
        {
            'doi': '10.1002/anie.202004934',
            'title': 'Angewandte Chemie Paper'
        }
    ]
    
    results = await downloader.batch_download(papers)
    
    # Results
    print(f"\n{'='*30} RESULTS {'='*30}")
    print(f"Total papers: {len(papers)}")
    print(f"Successfully downloaded: {results['successful']}")
    print(f"Failed: {results['failed']}")
    
    if results['successful'] > 0:
        print(f"\n📁 Downloaded files:")
        pdf_files = list(downloader.downloads_dir.glob("*.pdf"))
        for pdf_file in pdf_files:
            size_mb = pdf_file.stat().st_size / (1024 * 1024)
            print(f"  📄 {pdf_file.name} ({size_mb:.2f} MB)")
        
        print(f"\n🎉 ENHANCED DOWNLOADER SUCCESS!")

if __name__ == "__main__":
    asyncio.run(main())