#!/usr/bin/env python3
"""
Direct PDF Extraction
====================

Directly extract PDF content using requests session after authentication.
"""

import asyncio
import sys
import requests
from pathlib import Path
from playwright.async_api import async_playwright

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from secure_credential_manager import get_credential_manager

async def direct_pdf_extraction(headless=True):
    """Extract PDF directly using authenticated session."""
    
    # Get credentials
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        print("❌ No ETH credentials found!")
        return False
    
    print(f"🔑 Using ETH credentials for: {username}")
    print(f"🖥️ Mode: {'Headless' if headless else 'Visual'}")
    
    output_dir = Path("direct_pdf_extraction")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        page = await context.new_page()
        
        try:
            print("🚀 Complete authentication and extract cookies...")
            
            # Complete authentication flow
            print("1️⃣ Complete IEEE authentication")
            await page.goto("https://doi.org/10.1109/JPROC.2018.2820126", wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            # Accept cookies
            try:
                await page.click('button:has-text("Accept All")', timeout=5000)
            except:
                pass
            
            # Full auth flow (enhanced for headless mode)
            await page.click('a:has-text("Institutional Sign In")')
            await page.wait_for_timeout(3000)
            
            modal = await page.wait_for_selector('ngb-modal-window', timeout=15000)
            
            # Enhanced waiting for headless mode - wait for buttons to be both present AND visible
            await page.wait_for_function(
                '''() => {
                    const modal = document.querySelector('ngb-modal-window');
                    if (!modal) return false;
                    
                    const buttons = modal.querySelectorAll('button');
                    const visibleButtons = Array.from(buttons).filter(btn => {
                        const style = window.getComputedStyle(btn);
                        return style.display !== 'none' && style.visibility !== 'hidden' && btn.offsetParent !== null;
                    });
                    
                    return visibleButtons.length > 2;
                }''',
                timeout=30000
            )
            
            # Additional wait for dynamic content in headless mode
            if headless:
                await page.wait_for_timeout(5000)
            
            # Try multiple selectors for the access button
            access_button = None
            button_selectors = [
                'button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn',
                'button:has-text("Access Through Your Institution")',
                'button:has-text("Access through your institution")',
                'button[class*="seamlessaccess"]'
            ]
            
            for selector in button_selectors:
                try:
                    access_button = await modal.wait_for_selector(selector, timeout=10000, state='visible')
                    if access_button:
                        print(f"   Found access button with: {selector}")
                        break
                except:
                    continue
            
            if not access_button:
                print("❌ Could not find access button")
                return False
                
            await access_button.click()
            await page.wait_for_timeout(5000)  # Longer wait for headless
            
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
            password_input = await page.wait_for_selector('input[name="j_password"]', timeout=10000, state='visible')
            
            await username_input.fill(username)
            await password_input.fill(password)
            
            submit_button = await page.query_selector('button[type="submit"]')
            await submit_button.click()
            await page.wait_for_timeout(10000)
            print("✅ Authentication completed")
            
            # Extract cookies from browser context
            print("2️⃣ Extract authentication cookies")
            cookies = await context.cookies()
            
            # Convert to requests session
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            # Add cookies to session
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain', ''))
            
            print(f"✅ Extracted {len(cookies)} cookies")
            
            # Now use requests to download PDF directly
            print("3️⃣ Download PDF using authenticated session")
            
            pdf_urls = [
                "https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber=8347162&ref=",
                "https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=8347162",
                "https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber=8347162",
                "https://ieeexplore.ieee.org/document/8347162/download"
            ]
            
            for i, pdf_url in enumerate(pdf_urls):
                print(f"   Trying URL {i+1}: {pdf_url}")
                
                try:
                    response = session.get(pdf_url, stream=True, timeout=30)
                    print(f"     Status: {response.status_code}")
                    print(f"     Content-Type: {response.headers.get('content-type', 'unknown')}")
                    print(f"     Content-Length: {response.headers.get('content-length', 'unknown')}")
                    
                    if response.status_code == 200:
                        content = response.content
                        print(f"     Downloaded {len(content)} bytes")
                        
                        if content.startswith(b'%PDF'):
                            pdf_path = output_dir / f"ieee_paper_method_{i+1}.pdf"
                            with open(pdf_path, 'wb') as f:
                                f.write(content)
                            
                            file_size = pdf_path.stat().st_size
                            print(f"🎉 SUCCESS! PDF downloaded: {pdf_path} ({file_size} bytes)")
                            
                            # Verify it's a valid PDF with reasonable content
                            if file_size > 50000:  # At least 50KB for a real paper
                                print("✅ PDF appears to be complete")
                                return True
                            else:
                                print("⚠️ PDF seems small, checking next method...")
                        
                        elif len(content) > 10000:  # Large content, might be PDF anyway
                            pdf_path = output_dir / f"ieee_content_method_{i+1}.bin"
                            with open(pdf_path, 'wb') as f:
                                f.write(content)
                            print(f"📄 Large content saved: {pdf_path} ({len(content)} bytes)")
                            
                            # Check if it's actually a PDF despite header
                            if b'PDF' in content[:1000]:  # PDF signature somewhere in first KB
                                pdf_renamed = output_dir / f"ieee_paper_method_{i+1}.pdf"
                                pdf_path.rename(pdf_renamed)
                                print(f"✅ Content appears to be PDF: {pdf_renamed}")
                                return True
                        
                        else:
                            print(f"     Content too small or wrong format")
                    
                    else:
                        print(f"     HTTP error: {response.status_code}")
                
                except Exception as e:
                    print(f"     Error: {e}")
            
            # Final attempt: Navigate to stamp page and extract iframe URL
            print("4️⃣ Final attempt: Extract from stamp page")
            
            await page.goto("https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=8347162", wait_until='networkidle')
            await page.wait_for_timeout(5000)
            
            # Find the PDF iframe
            iframe = await page.query_selector('iframe[src*="getPDF"]')
            if iframe:
                pdf_src = await iframe.get_attribute('src')
                if pdf_src:
                    if not pdf_src.startswith('http'):
                        pdf_src = f"https://ieeexplore.ieee.org{pdf_src}"
                    
                    print(f"   Found PDF iframe URL: {pdf_src}")
                    
                    try:
                        response = session.get(pdf_src, stream=True, timeout=30)
                        
                        if response.status_code == 200:
                            content = response.content
                            print(f"   Downloaded {len(content)} bytes from iframe URL")
                            
                            pdf_path = output_dir / "ieee_paper_iframe.pdf"
                            with open(pdf_path, 'wb') as f:
                                f.write(content)
                            
                            file_size = pdf_path.stat().st_size
                            print(f"🎉 SUCCESS! PDF downloaded from iframe: {pdf_path} ({file_size} bytes)")
                            
                            # Basic validation
                            if content.startswith(b'%PDF') or b'PDF' in content[:100]:
                                print("✅ Content appears to be valid PDF")
                                return True
                            elif file_size > 10000:
                                print("✅ Large file downloaded (likely PDF)")
                                return True
                    
                    except Exception as e:
                        print(f"   Iframe download error: {e}")
            
            print("❌ All download methods failed")
            return False
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        finally:
            await browser.close()

if __name__ == "__main__":
    headless_mode = len(sys.argv) > 1 and sys.argv[1] == "--headless"
    
    success = asyncio.run(direct_pdf_extraction(headless=headless_mode))
    
    mode = "headless" if headless_mode else "visual"
    
    if success:
        print(f"\n🎉 COMPLETE SUCCESS in {mode} mode!")
        print("✅ IEEE authentication works automatically")
        print("✅ PDF downloaded to disk automatically") 
        print("✅ No manual intervention required")
    else:
        print(f"\n❌ FAILED in {mode} mode")
    
    exit(0 if success else 1)