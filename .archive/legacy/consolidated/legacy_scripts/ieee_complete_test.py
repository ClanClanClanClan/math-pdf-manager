#!/usr/bin/env python3
"""
IEEE Complete Test
==================

Complete test with authentication and PDF download.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("complete_test")

nest_asyncio.apply()

async def complete_ieee_test():
    from playwright.async_api import async_playwright
    
    # Get credentials
    from secure_credential_manager import get_credential_manager
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        logger.error("No ETH credentials found!")
        return False
    
    test_doi = "10.1109/JPROC.2018.2820126"
    ieee_url = f"https://doi.org/{test_doi}"
    
    output_dir = Path("complete_test")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            logger.info("=== STEP 1: Navigate to IEEE ===")
            await page.goto(ieee_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Accept cookies
            accept = await page.query_selector('button:has-text("Accept All")')
            if accept:
                await accept.click()
                await page.wait_for_timeout(1000)
            
            logger.info("=== STEP 2: Authentication Flow ===")
            # Click institutional sign in
            inst = await page.wait_for_selector('a:has-text("Institutional Sign In")')
            await inst.click()
            await page.wait_for_timeout(3000)
            
            # Click Access Through Your Institution button
            access_btn = await page.wait_for_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
            logger.info("Clicking Access Through Your Institution...")
            await access_btn.click()
            await page.wait_for_timeout(3000)
            
            # Find and fill search input
            search_input = await page.wait_for_selector('input[aria-label="Search for your Institution"]', timeout=10000)
            logger.info("Filling search with 'ETH Zurich'...")
            await search_input.fill("ETH Zurich")
            await search_input.press('Enter')
            await page.wait_for_timeout(3000)
            
            # Click ETH result
            eth_link = await page.wait_for_selector('a[id*="ETH Zurich"]', timeout=10000)
            logger.info("Clicking ETH Zurich link...")
            await eth_link.click()
            await page.wait_for_timeout(5000)
            
            # Verify we're at ETH login
            current_url = page.url
            logger.info(f"Current URL: {current_url}")
            
            if 'ethz' in current_url or 'aai' in current_url:
                logger.info("✅ At ETH login page!")
                
                # Fill credentials
                await page.fill('[name="j_username"], [id="username"]', username)
                await page.fill('[name="j_password"], [id="password"]', password)
                
                # Submit
                submit = await page.query_selector('[type="submit"]')
                await submit.click()
                
                logger.info("Authenticating...")
                await page.wait_for_timeout(5000)
                
                final_url = page.url
                logger.info(f"Final URL: {final_url}")
                
                if 'ieee' in final_url:
                    logger.info("✅ SUCCESS! Authenticated and returned to IEEE!")
                    
                    logger.info("=== STEP 3: PDF Download ===")
                    
                    # Extract document ID
                    doc_id = final_url.split('/document/')[1].split('/')[0] if '/document/' in final_url else None
                    if doc_id:
                        logger.info(f"Document ID: {doc_id}")
                        
                        # Method 1: Try stamp URL directly
                        stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                        logger.info(f"Trying stamp URL: {stamp_url}")
                        
                        response = await page.goto(stamp_url, wait_until='networkidle')
                        content = await response.body()
                        
                        if content.startswith(b'%PDF'):
                            pdf_path = output_dir / "ieee_paper.pdf"
                            with open(pdf_path, 'wb') as f:
                                f.write(content)
                            logger.info(f"✅ PDF downloaded directly: {pdf_path}")
                            logger.info(f"PDF size: {len(content)} bytes")
                            return True
                        else:
                            logger.info("Stamp page returned HTML, looking for PDF iframe...")
                            
                            # Wait for iframe to load
                            await page.wait_for_timeout(5000)
                            
                            # Look for PDF iframe
                            iframes = await page.query_selector_all('iframe')
                            logger.info(f"Found {len(iframes)} iframes")
                            
                            for i, iframe in enumerate(iframes):
                                src = await iframe.get_attribute('src')
                                logger.info(f"Iframe {i}: {src}")
                                
                                if src and ('pdf' in src.lower() or 'stamp' in src or 'getPDF' in src):
                                    if not src.startswith('http'):
                                        src = f"https://ieeexplore.ieee.org{src}"
                                    
                                    logger.info(f"Trying PDF iframe: {src}")
                                    iframe_response = await page.goto(src, wait_until='networkidle')
                                    iframe_content = await iframe_response.body()
                                    
                                    if iframe_content.startswith(b'%PDF'):
                                        pdf_path = output_dir / "ieee_paper.pdf"
                                        with open(pdf_path, 'wb') as f:
                                            f.write(iframe_content)
                                        logger.info(f"✅ PDF downloaded from iframe: {pdf_path}")
                                        logger.info(f"PDF size: {len(iframe_content)} bytes")
                                        return True
                            
                            # Method 2: Look for download buttons on document page
                            logger.info("Going back to document page to look for download buttons...")
                            doc_url = f"https://ieeexplore.ieee.org/document/{doc_id}"
                            await page.goto(doc_url, wait_until='networkidle')
                            await page.wait_for_timeout(3000)
                            
                            # Look for PDF download buttons
                            download_selectors = [
                                '.stats-document-abstract-downloadPdf',
                                'button:has-text("PDF")',
                                'a:has-text("PDF")',
                                '[data-testid="pdf-download"]',
                                '.document-pdf-download',
                                'button[title*="PDF"]',
                                'a[title*="PDF"]',
                                'a[href*="stamp.jsp"]'
                            ]
                            
                            for selector in download_selectors:
                                try:
                                    elements = await page.query_selector_all(selector)
                                    for element in elements:
                                        if element and await element.is_visible():
                                            logger.info(f"Found download button: {selector}")
                                            await element.click()
                                            await page.wait_for_timeout(3000)
                                            
                                            # Check if we got PDF
                                            if page.url.endswith('.pdf') or 'stamp.jsp' in page.url:
                                                response = await page.goto(page.url)
                                                content = await response.body()
                                                if content.startswith(b'%PDF'):
                                                    pdf_path = output_dir / "ieee_paper.pdf"
                                                    with open(pdf_path, 'wb') as f:
                                                        f.write(content)
                                                    logger.info(f"✅ PDF downloaded via button: {pdf_path}")
                                                    return True
                                except Exception as e:
                                    logger.debug(f"Button click failed: {e}")
                            
                            logger.warning("Could not find working PDF download method")
                            await page.screenshot(path=output_dir / "final_state.png")
                    else:
                        logger.warning("Could not extract document ID")
                else:
                    logger.warning(f"Not returned to IEEE: {final_url}")
            else:
                logger.warning(f"Not at ETH login: {current_url}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            logger.info("Browser staying open for 10 seconds...")
            await asyncio.sleep(10)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(complete_ieee_test())
    if success:
        logger.info("✅ Complete IEEE test successful!")
    else:
        logger.error("❌ Complete IEEE test failed!")