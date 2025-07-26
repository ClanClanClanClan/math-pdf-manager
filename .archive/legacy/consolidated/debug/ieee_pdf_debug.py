#!/usr/bin/env python3
"""
IEEE PDF Debug
==============

Debug the PDF download specifically.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pdf_debug")

nest_asyncio.apply()

async def debug_pdf_download():
    from playwright.async_api import async_playwright
    
    # We know authentication works, so let's start from an authenticated state
    # and focus just on the PDF download
    
    output_dir = Path("pdf_debug")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Go directly to the authenticated IEEE document page
            # (assuming we have an active session)
            doc_url = "https://ieeexplore.ieee.org/document/8347162"
            logger.info(f"Going to document page: {doc_url}")
            await page.goto(doc_url, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Check if we need to authenticate
            if 'login' in page.url.lower():
                logger.info("Need to authenticate first...")
                # Quick auth flow (we know this works)
                inst = await page.query_selector('a:has-text("Institutional Sign In")')
                if inst:
                    await inst.click()
                    await page.wait_for_timeout(3000)
                    
                    access_btn = await page.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
                    await access_btn.click()
                    await page.wait_for_timeout(3000)
                    
                    search_input = await page.query_selector('input[aria-label="Search for your Institution"]')
                    await search_input.fill("ETH Zurich")
                    await search_input.press('Enter')
                    await page.wait_for_timeout(3000)
                    
                    eth_link = await page.query_selector('a[id*="ETH Zurich"]')
                    await eth_link.click()
                    await page.wait_for_timeout(5000)
                    
                    # Fill ETH credentials
                    from secure_credential_manager import get_credential_manager
                    cm = get_credential_manager()
                    username, password = cm.get_eth_credentials()
                    
                    await page.fill('[name="j_username"], [id="username"]', username)
                    await page.fill('[name="j_password"], [id="password"]', password)
                    submit = await page.query_selector('[type="submit"]')
                    await submit.click()
                    await page.wait_for_timeout(5000)
            
            logger.info("=== PDF Download Debug ===")
            doc_id = "8347162"
            
            # Method 1: Direct stamp URL with different parameters
            stamp_urls = [
                f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}",
                f"https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber={doc_id}",
                f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={doc_id}",
                f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?arnumber={doc_id}",
                f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={doc_id}&ref="
            ]
            
            for i, url in enumerate(stamp_urls):
                logger.info(f"Trying URL {i+1}: {url}")
                try:
                    response = await page.goto(url, wait_until='networkidle', timeout=30000)
                    content = await response.body()
                    
                    logger.info(f"Response status: {response.status}")
                    logger.info(f"Content length: {len(content)}")
                    logger.info(f"Content type: {response.headers.get('content-type', 'unknown')}")
                    
                    if content.startswith(b'%PDF'):
                        pdf_path = output_dir / f"ieee_paper_{i+1}.pdf"
                        with open(pdf_path, 'wb') as f:
                            f.write(content)
                        logger.info(f"✅ PDF downloaded: {pdf_path}")
                        return True
                    else:
                        # Save HTML for debugging
                        html_path = output_dir / f"response_{i+1}.html"
                        with open(html_path, 'wb') as f:
                            f.write(content)
                        logger.info(f"Saved HTML response to: {html_path}")
                        
                        # Check first 200 chars of content
                        content_preview = content[:200].decode('utf-8', errors='ignore')
                        logger.info(f"Content preview: {content_preview}")
                        
                except Exception as e:
                    logger.warning(f"URL {i+1} failed: {e}")
                
                await page.wait_for_timeout(2000)
            
            # Method 2: Look for download links on the document page
            logger.info("=== Looking for download buttons ===")
            await page.goto(doc_url, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Get all links and buttons that might be downloads
            all_links = await page.query_selector_all('a, button')
            download_candidates = []
            
            for link in all_links[:50]:  # Check first 50 elements
                text = await link.text_content()
                href = await link.get_attribute('href')
                
                if text and ('pdf' in text.lower() or 'download' in text.lower()):
                    download_candidates.append({'element': link, 'text': text, 'href': href})
            
            logger.info(f"Found {len(download_candidates)} download candidates:")
            for i, candidate in enumerate(download_candidates):
                logger.info(f"  {i+1}. Text: '{candidate['text'][:50]}...' | Href: {candidate['href']}")
            
            # Try clicking each download candidate
            for i, candidate in enumerate(download_candidates[:3]):  # Try first 3
                logger.info(f"Trying download candidate {i+1}...")
                try:
                    # Store current URL
                    original_url = page.url
                    
                    await candidate['element'].click()
                    await page.wait_for_timeout(5000)
                    
                    # Check if URL changed
                    new_url = page.url
                    logger.info(f"URL after click: {new_url}")
                    
                    if new_url != original_url:
                        # URL changed, check if we got PDF
                        response = await page.goto(new_url)
                        content = await response.body()
                        
                        if content.startswith(b'%PDF'):
                            pdf_path = output_dir / f"ieee_paper_button_{i+1}.pdf"
                            with open(pdf_path, 'wb') as f:
                                f.write(content)
                            logger.info(f"✅ PDF downloaded via button: {pdf_path}")
                            return True
                    
                    # Go back to original page
                    await page.goto(original_url, wait_until='networkidle')
                    await page.wait_for_timeout(2000)
                    
                except Exception as e:
                    logger.warning(f"Button {i+1} failed: {e}")
            
            logger.warning("No working PDF download method found")
            return False
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            logger.info("Browser staying open for inspection...")
            await asyncio.sleep(30)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(debug_pdf_download())
    if success:
        logger.info("✅ PDF debug successful!")
    else:
        logger.error("❌ PDF debug failed!")