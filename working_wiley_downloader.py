#!/usr/bin/env python3
"""
WORKING WILEY DOWNLOADER
========================

Fix the identified issues and create a working Wiley PDF downloader.

Issues found:
1. PDF elements not visible (behind paywall)
2. Elements detached from DOM after page changes
3. Relative URLs need to be made absolute
4. Need to handle institutional access properly

Solution: Handle authentication first, then download PDFs properly.
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).parent))

class WorkingWileyDownloader:
    """Actually working Wiley PDF downloader"""
    
    def __init__(self):
        self.credentials = None
        self.downloads_dir = Path("working_downloads")
        self.downloads_dir.mkdir(exist_ok=True)
    
    async def initialize(self):
        """Get ETH credentials"""
        try:
            from src.secure_credential_manager import get_credential_manager
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            if not (username and password):
                raise Exception("No ETH credentials")
                
            self.credentials = {'username': username, 'password': password}
            print(f"✅ ETH credentials: {username[:3]}***")
            return True
            
        except Exception as e:
            print(f"❌ Credential error: {e}")
            return False
    
    async def download_wiley_paper(self, doi):
        """Download a Wiley paper with proper authentication handling"""
        
        print(f"\n🎯 DOWNLOADING WILEY PAPER")
        print(f"DOI: {doi}")
        print("-" * 50)
        
        paper_url = f"https://onlinelibrary.wiley.com/doi/{doi}"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=['--start-maximized']
            )
            
            context = await browser.new_context(accept_downloads=True)
            page = await context.new_page()
            
            try:
                # Step 1: Load paper page
                print("📍 Step 1: Loading paper page...")
                await page.goto(paper_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(5000)
                print(f"✅ Loaded: {page.url}")
                
                # Step 2: Handle cookies
                print("🍪 Step 2: Handling cookies...")
                await self._handle_cookies(page)
                
                # Step 3: Check if authentication is needed
                print("🔑 Step 3: Checking authentication...")
                page_text = await page.inner_text('body')
                
                needs_auth = any(indicator in page_text.lower() for indicator in [
                    'institutional access', 'sign in to access', 'purchase this article'
                ])
                
                if needs_auth:
                    print("🔒 Authentication required - handling...")
                    auth_success = await self._handle_authentication(page)
                    
                    if not auth_success:
                        print("❌ Authentication failed")
                        await browser.close()
                        return False
                    
                    print("✅ Authentication successful")
                    await page.wait_for_timeout(5000)
                else:
                    print("✅ No authentication needed")
                
                # Step 4: Find and download PDF
                print("📄 Step 4: Finding PDF download...")
                download_success = await self._download_pdf(page, doi)
                
                if download_success:
                    print("🎉 DOWNLOAD SUCCESSFUL!")
                    await browser.close()
                    return True
                else:
                    print("❌ Download failed")
                    
                    # Keep browser open for debugging
                    print("🔍 Keeping browser open for inspection...")
                    await page.wait_for_timeout(20000)
                    
                    await browser.close()
                    return False
                    
            except Exception as e:
                print(f"❌ Download failed: {e}")
                await browser.close()
                return False
    
    async def _handle_cookies(self, page):
        """Handle cookie banners"""
        try:
            cookie_btn = await page.wait_for_selector('button:has-text("Accept All")', timeout=5000)
            if cookie_btn and await cookie_btn.is_visible():
                await cookie_btn.click()
                await page.wait_for_timeout(2000)
                print("   ✅ Cookies accepted")
                return True
        except:
            pass
        
        print("   ❌ No cookie banner")
        return False
    
    async def _handle_authentication(self, page):
        """Handle institutional authentication"""
        
        # Look for institutional access buttons
        institutional_selectors = [
            'a:has-text("Institutional Login")',
            'a:has-text("Access through institution")',
            'button:has-text("Login")',
            'a[href*="ssostart"]'
        ]
        
        for selector in institutional_selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=5000)
                if element and await element.is_visible():
                    print(f"   🔑 Found institutional access: {selector}")
                    await element.click()
                    await page.wait_for_timeout(8000)
                    
                    # Check if redirected to ETH
                    current_url = page.url
                    if 'ethz' in current_url or 'shibboleth' in current_url:
                        print(f"   🔐 ETH authentication page")
                        return await self._do_eth_login(page)
                    else:
                        print(f"   📍 Redirected to: {current_url}")
                        return True
            except:
                continue
        
        print("   ❌ No institutional access found")
        return False
    
    async def _do_eth_login(self, page):
        """Perform ETH login"""
        
        try:
            # Check for Cloudflare
            page_content = await page.content()
            if 'cloudflare' in page_content.lower():
                print("     ❌ Cloudflare detected - cannot proceed")
                return False
            
            await page.wait_for_timeout(3000)
            
            # Fill username
            username_field = await page.wait_for_selector('input[name="username"]', timeout=10000)
            if username_field:
                await username_field.fill(self.credentials['username'])
                print("     ✅ Username filled")
            else:
                print("     ❌ Username field not found")
                return False
            
            # Fill password
            password_field = await page.wait_for_selector('input[name="password"]', timeout=5000)
            if password_field:
                await password_field.fill(self.credentials['password'])
                print("     ✅ Password filled")
            else:
                print("     ❌ Password field not found")
                return False
            
            # Submit
            submit_btn = await page.wait_for_selector('input[type="submit"]', timeout=5000)
            if submit_btn:
                await submit_btn.click()
                await page.wait_for_timeout(15000)  # Wait longer for redirect
                print("     ✅ Login submitted")
                return True
            else:
                print("     ❌ Submit button not found")
                return False
                
        except Exception as e:
            print(f"     ❌ ETH login error: {e}")
            return False
    
    async def _download_pdf(self, page, doi):
        """Download PDF using multiple strategies"""
        
        base_url = "https://onlinelibrary.wiley.com"
        
        # Strategy 1: Direct PDF URL construction
        print("   🎯 Strategy 1: Direct PDF URL")
        pdf_urls = [
            f"{base_url}/doi/pdf/{doi}",
            f"{base_url}/doi/epdf/{doi}",
            f"{base_url}/doi/pdfdirect/{doi}"
        ]
        
        for i, pdf_url in enumerate(pdf_urls, 1):
            try:
                print(f"     Trying PDF URL {i}: {pdf_url}")
                
                # Open PDF URL in new page
                pdf_page = await page.context.new_page()
                response = await pdf_page.goto(pdf_url, timeout=20000)
                
                if response and response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    print(f"     Response: {response.status}, Content-Type: {content_type}")
                    
                    if 'pdf' in content_type.lower():
                        print(f"     ✅ PDF response detected!")
                        
                        # Get PDF content
                        pdf_buffer = await response.body()
                        
                        # Save PDF
                        filename = f"wiley_{doi.replace('/', '_').replace('.', '_')}.pdf"
                        save_path = self.downloads_dir / filename
                        
                        with open(save_path, 'wb') as f:
                            f.write(pdf_buffer)
                        
                        await pdf_page.close()
                        
                        if save_path.exists() and save_path.stat().st_size > 1000:
                            size_mb = save_path.stat().st_size / (1024 * 1024)
                            print(f"     🎉 PDF saved: {save_path} ({size_mb:.2f} MB)")
                            return True
                        else:
                            print(f"     ❌ PDF file too small or empty")
                    else:
                        print(f"     ❌ Not a PDF response")
                else:
                    print(f"     ❌ Bad response: {response.status if response else 'No response'}")
                
                await pdf_page.close()
                
            except Exception as e:
                print(f"     ❌ PDF URL {i} failed: {e}")
                try:
                    await pdf_page.close()
                except:
                    pass
        
        # Strategy 2: Look for PDF links on current page
        print("   🎯 Strategy 2: PDF links on page")
        
        try:
            # Get all links with PDF indicators
            all_links = await page.query_selector_all('a')
            pdf_candidates = []
            
            for link in all_links:
                try:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    
                    if href and ('pdf' in href.lower() or 'pdf' in text.lower()):
                        # Make absolute URL
                        absolute_url = urljoin(page.url, href)
                        pdf_candidates.append({
                            'text': text.strip(),
                            'url': absolute_url,
                            'element': link
                        })
                except:
                    continue
            
            print(f"     Found {len(pdf_candidates)} PDF candidates")
            
            for i, candidate in enumerate(pdf_candidates[:3], 1):  # Try first 3
                try:
                    print(f"     Trying candidate {i}: '{candidate['text']}' -> {candidate['url']}")
                    
                    # Try direct URL access
                    pdf_page = await page.context.new_page()
                    response = await pdf_page.goto(candidate['url'], timeout=15000)
                    
                    if response and response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        
                        if 'pdf' in content_type.lower():
                            print(f"     ✅ PDF found via candidate {i}!")
                            
                            pdf_buffer = await response.body()
                            filename = f"wiley_candidate_{i}_{doi.replace('/', '_').replace('.', '_')}.pdf"
                            save_path = self.downloads_dir / filename
                            
                            with open(save_path, 'wb') as f:
                                f.write(pdf_buffer)
                            
                            await pdf_page.close()
                            
                            if save_path.exists() and save_path.stat().st_size > 1000:
                                size_mb = save_path.stat().st_size / (1024 * 1024)
                                print(f"     🎉 PDF saved: {save_path} ({size_mb:.2f} MB)")
                                return True
                    
                    await pdf_page.close()
                    
                except Exception as e:
                    print(f"     ❌ Candidate {i} failed: {e}")
                    try:
                        await pdf_page.close()
                    except:
                        pass
            
        except Exception as e:
            print(f"   ❌ Strategy 2 failed: {e}")
        
        return False
    
    async def test_multiple_papers(self):
        """Test downloading multiple papers"""
        
        print("🧪 TESTING WORKING WILEY DOWNLOADER")
        print("=" * 60)
        
        test_papers = [
            "10.1002/anie.202004934",  # Angewandte Chemie
            "10.1111/1467-9523.00201", # Economica
            "10.1002/adma.202001924"   # Advanced Materials
        ]
        
        successful_downloads = 0
        
        for i, doi in enumerate(test_papers, 1):
            print(f"\n{'='*15} TEST {i}/{len(test_papers)} {'='*15}")
            
            success = await self.download_wiley_paper(doi)
            
            if success:
                successful_downloads += 1
                print(f"✅ TEST {i} SUCCESS")
            else:
                print(f"❌ TEST {i} FAILED")
        
        # Final results
        print(f"\n{'='*20} FINAL RESULTS {'='*20}")
        print(f"Tests: {len(test_papers)}")
        print(f"Successful downloads: {successful_downloads}")
        
        if successful_downloads > 0:
            print(f"🎉 WILEY DOWNLOADS WORKING!")
            
            # Show downloaded files
            pdf_files = list(self.downloads_dir.glob("*.pdf"))
            if pdf_files:
                print(f"\n📁 Downloaded files:")
                for pdf_file in pdf_files:
                    size_mb = pdf_file.stat().st_size / (1024 * 1024)
                    print(f"   📄 {pdf_file.name} ({size_mb:.2f} MB)")
            
            return True
        else:
            print(f"❌ WILEY DOWNLOADS STILL NOT WORKING")
            return False

async def main():
    """Main test"""
    
    downloader = WorkingWileyDownloader()
    
    if not await downloader.initialize():
        return False
    
    success = await downloader.test_multiple_papers()
    
    if success:
        print(f"\n🎯 WILEY DOWNLOADER IS NOW WORKING!")
    else:
        print(f"\n💥 WILEY DOWNLOADER STILL NEEDS WORK")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())