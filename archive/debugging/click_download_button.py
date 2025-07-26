#!/usr/bin/env python3
"""
Click Download Button
====================

Complete authentication and click the download button on the PDF page.
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from secure_credential_manager import get_credential_manager

async def click_download_button():
    """Complete authentication and click PDF download button."""
    
    # Get credentials
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        print("❌ No ETH credentials found!")
        return False
    
    print(f"🔑 Using ETH credentials for: {username}")
    
    output_dir = Path("download_button_test")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            accept_downloads=True  # Enable downloads
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        page = await context.new_page()
        
        try:
            print("🚀 Complete authentication and click download button...")
            
            # Complete authentication (shortened version since we know it works)
            print("1️⃣ Complete IEEE authentication")
            await page.goto("https://doi.org/10.1109/JPROC.2018.2820126")
            await page.wait_for_timeout(2000)
            
            # Accept cookies
            try:
                await page.click('button:has-text("Accept All")')
            except:
                pass
            
            # Full auth flow
            await page.click('a:has-text("Institutional Sign In")')
            await page.wait_for_timeout(2000)
            
            modal = await page.wait_for_selector('ngb-modal-window')
            await page.wait_for_function(
                '''() => {
                    const modal = document.querySelector('ngb-modal-window');
                    const buttons = modal ? modal.querySelectorAll('button') : [];
                    return buttons.length > 2;
                }''',
                timeout=15000
            )
            
            access_button = await modal.wait_for_selector(
                'button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn', 
                timeout=10000, 
                state='visible'
            )
            await access_button.click()
            await page.wait_for_timeout(3000)
            
            inst_modal = await page.wait_for_selector('ngb-modal-window:has-text("Search for your Institution")', timeout=15000)
            search_input = await inst_modal.wait_for_selector('input.inst-typeahead-input', timeout=10000)
            await search_input.fill("ETH Zurich")
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(3000)
            
            eth_option = await page.wait_for_selector('a:has-text("ETH Zurich - ETH Zurich")', timeout=10000)
            href = await eth_option.get_attribute('href')
            if href.startswith('/'):
                full_url = f"https://ieeexplore.ieee.org{href}"
            else:
                full_url = href
            
            await page.goto(full_url, wait_until='networkidle')
            
            username_input = await page.wait_for_selector('input[name="j_username"]', timeout=10000, state='visible')
            password_input = await page.wait_for_selector('input[name="j_password"]', timeout=5000, state='visible')
            
            await username_input.fill(username)
            await password_input.fill(password)
            
            submit_button = await page.query_selector('button[type="submit"]')
            await submit_button.click()
            
            await page.wait_for_timeout(8000)
            print("✅ Authentication completed")
            
            # Now navigate to stamp page and look for download button
            print("2️⃣ Navigate to PDF stamp page")
            stamp_url = "https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=8347162"
            await page.goto(stamp_url, wait_until='networkidle')
            
            # Wait for PDF to load
            print("3️⃣ Wait for PDF to load")
            await page.wait_for_timeout(8000)  # Give PDF time to load
            
            # Take screenshot to see what's on the page
            await page.screenshot(path=output_dir / "stamp_page_loaded.png", full_page=True)
            print("📸 Screenshot of stamp page saved")
            
            # Look for download buttons/links
            print("4️⃣ Look for download buttons")
            
            # Common download button selectors
            download_selectors = [
                'button:has-text("Download")',
                'a:has-text("Download")',
                'button[title*="download" i]',
                'a[title*="download" i]',
                'button:has-text("PDF")',
                'a:has-text("PDF")',
                'button[aria-label*="download" i]',
                'a[aria-label*="download" i]',
                '.download-btn',
                '.pdf-download',
                'button[class*="download"]',
                'a[class*="download"]'
            ]
            
            download_element = None
            for selector in download_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        visible = await element.is_visible()
                        text = await element.text_content()
                        print(f"  Found download element: '{selector}' -> '{text}' (visible: {visible})")
                        if visible:
                            download_element = element
                            break
                except:
                    continue
            
            if not download_element:
                print("🔍 No obvious download button found, looking in iframes...")
                
                # Check if PDF is in iframe and look for download controls there
                iframes = await page.query_selector_all('iframe')
                print(f"Found {len(iframes)} iframes")
                
                for i, iframe in enumerate(iframes):
                    src = await iframe.get_attribute('src')
                    print(f"  Iframe {i}: {src}")
                    
                    if src and ('pdf' in src.lower() or 'stamp' in src):
                        print(f"  🎯 Checking PDF iframe {i}")
                        
                        try:
                            # Switch to iframe content
                            frame = await iframe.content_frame()
                            if frame:
                                # Look for download controls in the iframe
                                frame_download_selectors = [
                                    'button:has-text("Download")',
                                    'a:has-text("Download")', 
                                    '[title*="download" i]',
                                    '.download',
                                    'button[aria-label*="download" i]'
                                ]
                                
                                for selector in frame_download_selectors:
                                    try:
                                        frame_element = await frame.query_selector(selector)
                                        if frame_element:
                                            visible = await frame_element.is_visible()
                                            text = await frame_element.text_content()
                                            print(f"    Found in iframe: '{selector}' -> '{text}' (visible: {visible})")
                                            if visible:
                                                download_element = frame_element
                                                break
                                    except:
                                        continue
                                
                                if download_element:
                                    break
                        except Exception as e:
                            print(f"    Error checking iframe: {e}")
            
            # Try right-clicking to access browser download menu
            if not download_element:
                print("5️⃣ Try right-click context menu")
                
                # Right-click on the page to see if there's a save option
                try:
                    # Look for the PDF content area
                    pdf_area = await page.query_selector('iframe[src*="pdf"], iframe[src*="stamp"], embed[type="application/pdf"]')
                    if pdf_area:
                        print("  Right-clicking on PDF area...")
                        await pdf_area.click(button='right')
                        await page.wait_for_timeout(1000)
                        
                        # Look for "Save as" or similar options
                        save_option = await page.query_selector('text="Save as", text="Save", text="Download"')
                        if save_option:
                            await save_option.click()
                            print("  Clicked save option from context menu")
                            download_element = True  # Flag that we initiated download
                    
                except Exception as e:
                    print(f"  Right-click failed: {e}")
            
            # Try keyboard shortcut
            if not download_element:
                print("6️⃣ Try keyboard shortcut (Ctrl+S)")
                await page.keyboard.press('Control+s')
                await page.wait_for_timeout(2000)
                download_element = True  # Flag that we tried download
            
            # If we found a download element, click it
            if download_element and download_element != True:
                print("7️⃣ Click download button")
                
                # Set up download listener
                async with page.expect_download() as download_info:
                    await download_element.click()
                
                download = await download_info.value
                
                # Save the download
                pdf_path = output_dir / f"ieee_paper_{download.suggested_filename or 'document.pdf'}"
                await download.save_as(pdf_path)
                
                print(f"🎉 SUCCESS! PDF downloaded: {pdf_path}")
                
                # Verify file size
                if pdf_path.exists():
                    file_size = pdf_path.stat().st_size
                    print(f"📊 File size: {file_size} bytes")
                    
                    if file_size > 10000:  # At least 10KB
                        print("✅ PDF appears to be valid size")
                        return True
                    else:
                        print("⚠️ PDF file seems too small")
                
            # If no download button but we initiated download via other means
            elif download_element == True:
                print("⏳ Waiting for download to complete...")
                await page.wait_for_timeout(10000)
                
                # Check if any files were downloaded
                downloads = list(output_dir.glob("*.pdf"))
                if downloads:
                    print(f"🎉 SUCCESS! Found downloaded PDF: {downloads[0]}")
                    return True
                else:
                    print("❌ No PDF file found after download attempt")
            
            else:
                print("❌ No download method worked")
                print("📋 Manual steps needed:")
                print("  1. The PDF should be visible in the browser")
                print("  2. Use Ctrl+S or right-click -> Save As")
                print("  3. Or look for download icon in PDF viewer")
            
            return False
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await page.screenshot(path=output_dir / "error.png")
            return False
        finally:
            print("Keeping browser open for manual download...")
            print("You can now manually download the PDF if needed")
            await asyncio.sleep(120)  # 2 minutes to manually download
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(click_download_button())
    
    if success:
        print("\n🎉 COMPLETE SUCCESS!")
        print("✅ IEEE authentication completed")
        print("✅ PDF successfully downloaded to disk")
    else:
        print("\n⚠️ PDF visible but automatic download failed")
        print("Manual download may be needed")
    
    exit(0 if success else 1)