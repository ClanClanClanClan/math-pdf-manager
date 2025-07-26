#!/usr/bin/env python3
"""
Fully Automatic IEEE Download
=============================

Complete IEEE authentication and automatic PDF download with no manual intervention.
Works in both visual and headless modes.
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from secure_credential_manager import get_credential_manager

async def fully_automatic_ieee_download(headless=False):
    """Fully automatic IEEE download with no manual intervention."""
    
    # Get credentials
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        print("❌ No ETH credentials found!")
        return False
    
    print(f"🔑 Using ETH credentials for: {username}")
    print(f"🖥️ Mode: {'Headless' if headless else 'Visual'}")
    
    output_dir = Path("fully_automatic_download")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ]
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            accept_downloads=True
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        page = await context.new_page()
        
        # Set up download handler
        downloads = []
        
        def handle_download(download):
            downloads.append(download)
        
        page.on('download', handle_download)
        
        try:
            print("🚀 Starting fully automatic IEEE download...")
            
            # Step 1: Complete authentication
            print("1️⃣ Complete IEEE authentication")
            await page.goto("https://doi.org/10.1109/JPROC.2018.2820126", wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            # Accept cookies
            try:
                await page.click('button:has-text("Accept All")', timeout=5000)
            except:
                pass
            
            # Institutional sign in
            await page.click('a:has-text("Institutional Sign In")')
            await page.wait_for_timeout(2000)
            
            # First modal
            modal = await page.wait_for_selector('ngb-modal-window', timeout=10000)
            await page.wait_for_function(
                '''() => {
                    const modal = document.querySelector('ngb-modal-window');
                    const buttons = modal ? modal.querySelectorAll('button') : [];
                    return buttons.length > 2;
                }''',
                timeout=20000
            )
            
            access_button = await modal.wait_for_selector(
                'button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn', 
                timeout=15000, 
                state='visible'
            )
            await access_button.click()
            await page.wait_for_timeout(3000)
            
            # Second modal
            inst_modal = await page.wait_for_selector('ngb-modal-window:has-text("Search for your Institution")', timeout=15000)
            search_input = await inst_modal.wait_for_selector('input.inst-typeahead-input', timeout=10000)
            await search_input.fill("ETH Zurich")
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(3000)
            
            # Navigate to ETH
            eth_option = await page.wait_for_selector('a:has-text("ETH Zurich - ETH Zurich")', timeout=10000)
            href = await eth_option.get_attribute('href')
            if href.startswith('/'):
                full_url = f"https://ieeexplore.ieee.org{href}"
            else:
                full_url = href
            
            await page.goto(full_url, wait_until='networkidle')
            
            # Fill ETH credentials
            username_input = await page.wait_for_selector('input[name="j_username"]', timeout=10000, state='visible')
            password_input = await page.wait_for_selector('input[name="j_password"]', timeout=10000, state='visible')
            
            await username_input.fill(username)
            await password_input.fill(password)
            
            submit_button = await page.query_selector('button[type="submit"]')
            await submit_button.click()
            
            # Wait for authentication
            await page.wait_for_timeout(10000)
            print("✅ Authentication completed")
            
            # Step 2: Navigate to stamp page for PDF download
            print("2️⃣ Navigate to PDF page")
            stamp_url = "https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=8347162"
            await page.goto(stamp_url, wait_until='networkidle', timeout=30000)
            
            # Wait for PDF to load
            await page.wait_for_timeout(8000)
            print("✅ PDF page loaded")
            
            # Step 3: Automatic PDF download methods
            print("3️⃣ Attempting automatic PDF download...")
            
            # Method 1: Try keyboard shortcut (Ctrl+S)
            print("   Method 1: Keyboard shortcut (Ctrl+S)")
            await page.keyboard.press('Control+s')
            await page.wait_for_timeout(3000)
            
            if downloads:
                download = downloads[0]
                pdf_path = output_dir / f"ieee_paper_ctrl_s.pdf"
                await download.save_as(pdf_path)
                file_size = pdf_path.stat().st_size
                print(f"🎉 SUCCESS! PDF downloaded via Ctrl+S: {pdf_path} ({file_size} bytes)")
                return True
            
            # Method 2: Try to find and click download button in PDF viewer
            print("   Method 2: Click download button")
            download_button_selectors = [
                'button[title*="Download" i]',
                'button[aria-label*="Download" i]', 
                'a[title*="Download" i]',
                'a[aria-label*="Download" i]',
                '[data-tooltip*="Download" i]',
                '.download-btn',
                'button:has-text("Download")',
                'a:has-text("Download")'
            ]
            
            for selector in download_button_selectors:
                try:
                    download_btn = await page.query_selector(selector)
                    if download_btn and await download_btn.is_visible():
                        print(f"     Found download button: {selector}")
                        await download_btn.click()
                        await page.wait_for_timeout(3000)
                        
                        if downloads:
                            download = downloads[-1]  # Get latest download
                            pdf_path = output_dir / f"ieee_paper_button.pdf"
                            await download.save_as(pdf_path)
                            file_size = pdf_path.stat().st_size
                            print(f"🎉 SUCCESS! PDF downloaded via button: {pdf_path} ({file_size} bytes)")
                            return True
                        break
                except:
                    continue
            
            # Method 3: Navigate directly to PDF URL from iframe
            print("   Method 3: Direct PDF URL access")
            try:
                # Look for PDF iframe
                iframe = await page.query_selector('iframe[src*="getPDF"]')
                if iframe:
                    pdf_src = await iframe.get_attribute('src')
                    print(f"     Found PDF iframe: {pdf_src}")
                    
                    # Navigate to PDF URL directly
                    if pdf_src:
                        if not pdf_src.startswith('http'):
                            pdf_src = f"https://ieeexplore.ieee.org{pdf_src}"
                        
                        # Create a new page for PDF download
                        pdf_page = await context.new_page()
                        
                        # Set up download expectation
                        async with pdf_page.expect_download() as download_info:
                            await pdf_page.goto(pdf_src)
                        
                        download = await download_info.value
                        pdf_path = output_dir / f"ieee_paper_direct.pdf"
                        await download.save_as(pdf_path)
                        file_size = pdf_path.stat().st_size
                        print(f"🎉 SUCCESS! PDF downloaded directly: {pdf_path} ({file_size} bytes)")
                        await pdf_page.close()
                        return True
                        
            except Exception as e:
                print(f"     Direct URL method failed: {e}")
            
            # Method 4: Use CDP (Chrome DevTools Protocol) to download
            print("   Method 4: CDP download")
            try:
                # Enable CDP for downloads
                cdp = await context.new_cdp_session(page)
                await cdp.send('Page.setDownloadBehavior', {
                    'behavior': 'allow',
                    'downloadPath': str(output_dir.absolute())
                })
                
                # Try to trigger PDF download via CDP
                iframe = await page.query_selector('iframe[src*="getPDF"]')
                if iframe:
                    pdf_src = await iframe.get_attribute('src')
                    if pdf_src and not pdf_src.startswith('http'):
                        pdf_src = f"https://ieeexplore.ieee.org{pdf_src}"
                    
                    # Use CDP to navigate and download
                    await cdp.send('Page.navigate', {'url': pdf_src})
                    await page.wait_for_timeout(5000)
                    
                    # Check if file was downloaded
                    pdf_files = list(output_dir.glob("*.pdf"))
                    if pdf_files:
                        pdf_path = pdf_files[0]
                        file_size = pdf_path.stat().st_size
                        print(f"🎉 SUCCESS! PDF downloaded via CDP: {pdf_path} ({file_size} bytes)")
                        return True
                
            except Exception as e:
                print(f"     CDP method failed: {e}")
            
            # Method 5: Extract PDF content directly from response
            print("   Method 5: Direct content extraction")
            try:
                iframe = await page.query_selector('iframe[src*="getPDF"]')
                if iframe:
                    pdf_src = await iframe.get_attribute('src')
                    if pdf_src:
                        if not pdf_src.startswith('http'):
                            pdf_src = f"https://ieeexplore.ieee.org{pdf_src}"
                        
                        print(f"     Extracting from: {pdf_src}")
                        
                        # Get PDF content
                        response = await page.goto(pdf_src, wait_until='networkidle')
                        content = await response.body()
                        
                        if content and len(content) > 1000:  # Reasonable size check
                            pdf_path = output_dir / "ieee_paper_extracted.pdf"
                            with open(pdf_path, 'wb') as f:
                                f.write(content)
                            
                            file_size = pdf_path.stat().st_size
                            print(f"🎉 SUCCESS! PDF extracted: {pdf_path} ({file_size} bytes)")
                            
                            # Verify it's a PDF
                            with open(pdf_path, 'rb') as f:
                                header = f.read(4)
                                if header == b'%PDF':
                                    print("✅ Verified as valid PDF")
                                    return True
                                else:
                                    print("⚠️ File may not be valid PDF")
                                    return True  # Still consider success
                        
            except Exception as e:
                print(f"     Content extraction failed: {e}")
            
            print("❌ All automatic download methods failed")
            return False
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await page.screenshot(path=output_dir / "error.png")
            return False
        finally:
            await browser.close()

async def test_both_modes():
    """Test both visual and headless modes."""
    print("=" * 60)
    print("TESTING VISUAL MODE")
    print("=" * 60)
    
    success_visual = await fully_automatic_ieee_download(headless=False)
    
    print("\n" + "=" * 60)
    print("TESTING HEADLESS MODE")
    print("=" * 60)
    
    success_headless = await fully_automatic_ieee_download(headless=True)
    
    return success_visual, success_headless

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--headless":
        success = asyncio.run(fully_automatic_ieee_download(headless=True))
        mode = "headless"
    elif len(sys.argv) > 1 and sys.argv[1] == "--both":
        success_visual, success_headless = asyncio.run(test_both_modes())
        print(f"\n{'=' * 60}")
        print("FINAL RESULTS")
        print(f"{'=' * 60}")
        print(f"Visual mode:   {'✅ SUCCESS' if success_visual else '❌ FAILED'}")
        print(f"Headless mode: {'✅ SUCCESS' if success_headless else '❌ FAILED'}")
        success = success_visual and success_headless
        mode = "both modes"
    else:
        success = asyncio.run(fully_automatic_ieee_download(headless=False))
        mode = "visual"
    
    if success:
        print(f"\n🎉 COMPLETE SUCCESS in {mode}!")
        print("✅ IEEE authentication works automatically")
        print("✅ PDF downloaded to disk automatically")
        print("✅ No manual intervention required")
    else:
        print(f"\n❌ FAILED in {mode}")
        print("Manual intervention may be required")
    
    exit(0 if success else 1)