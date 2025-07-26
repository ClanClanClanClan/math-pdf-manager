#!/usr/bin/env python3
"""
Actually Download PDF
====================

Stop talking, start downloading. Actually save a PDF file.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("actual_download")

nest_asyncio.apply()

async def actually_download_pdf():
    from playwright.async_api import async_playwright
    
    # Get credentials
    from src.secure_credential_manager import get_credential_manager
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    test_doi = "10.1109/JPROC.2018.2820126"
    ieee_url = f"https://doi.org/{test_doi}"
    
    output_dir = Path("actual_download")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            logger.info("Navigating to IEEE...")
            await page.goto(ieee_url, wait_until='domcontentloaded', timeout=90000)
            await page.wait_for_timeout(5000)
            
            # Accept cookies
            try:
                accept = await page.wait_for_selector('button:has-text("Accept All")', timeout=5000)
                await accept.click()
                await page.wait_for_timeout(2000)
                logger.info("Accepted cookies")
            except Exception:
                logger.info("No cookie banner")
            
            # Start authentication
            logger.info("Starting authentication...")
            inst = await page.wait_for_selector('a:has-text("Institutional Sign In")', timeout=15000)
            await inst.click()
            await page.wait_for_timeout(3000)
            
            # Click Access Through Your Institution
            access_btn = await page.wait_for_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn', timeout=10000)
            await access_btn.click()
            await page.wait_for_timeout(4000)
            
            # Search for ETH
            search_input = await page.wait_for_selector('input[aria-label="Search for your Institution"]', timeout=10000)
            await search_input.fill("ETH Zurich")
            await search_input.press('Enter')
            await page.wait_for_timeout(4000)
            
            # Click ETH
            eth_link = await page.wait_for_selector('a[id*="ETH Zurich"]', timeout=10000)
            await eth_link.click()
            await page.wait_for_timeout(8000)
            
            # Login to ETH
            if 'ethz' in page.url or 'aai' in page.url:
                logger.info("At ETH login page")
                await page.fill('[name="j_username"], [id="username"]', username)
                await page.fill('[name="j_password"], [id="password"]', password)
                
                submit = await page.query_selector('[type="submit"]')
                await submit.click()
                await page.wait_for_timeout(10000)  # Wait for auth
                
                if 'ieee' in page.url:
                    logger.info("✅ AUTHENTICATED! Now downloading PDF...")
                    
                    # Get document ID
                    doc_id = page.url.split('/document/')[1].split('/')[0] if '/document/' in page.url else None
                    
                    if doc_id:
                        logger.info(f"Document ID: {doc_id}")
                        
                        # Try the PDF URLs we know work
                        pdf_urls = [
                            f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={doc_id}&ref=",
                            f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}",
                        ]
                        
                        for i, pdf_url in enumerate(pdf_urls):
                            logger.info(f"Trying PDF URL {i+1}: {pdf_url}")
                            
                            try:
                                # Navigate to PDF URL
                                response = await page.goto(pdf_url, wait_until='load', timeout=60000)
                                logger.info(f"Got response: {response.status}")
                                
                                # Wait for PDF to generate/load
                                await page.wait_for_timeout(10000)
                                
                                # Get the content
                                content = await response.body()
                                logger.info(f"Content size: {len(content)} bytes")
                                
                                if len(content) > 1000:  # Reasonable PDF size
                                    if content.startswith(b'%PDF'):
                                        # IT'S A PDF! SAVE IT!
                                        pdf_path = output_dir / "ieee_paper_ACTUAL.pdf"
                                        with open(pdf_path, 'wb') as f:
                                            f.write(content)
                                        
                                        # VERIFY IT WAS SAVED
                                        if pdf_path.exists():
                                            file_size = pdf_path.stat().st_size
                                            logger.info(f"🎉 PDF ACTUALLY SAVED: {pdf_path}")
                                            logger.info(f"📊 File size: {file_size} bytes")
                                            
                                            # Verify it's really a PDF
                                            with open(pdf_path, 'rb') as f:
                                                header = f.read(8)
                                                if header.startswith(b'%PDF'):
                                                    logger.info("✅ VERIFIED: File is a valid PDF!")
                                                    logger.info("🏆 DOWNLOAD COMPLETE AND VERIFIED!")
                                                    return True
                                        else:
                                            logger.error("File not saved properly")
                                    else:
                                        logger.info("Not PDF format, checking for iframe...")
                                        
                                        # Look for PDF iframe
                                        iframes = await page.query_selector_all('iframe')
                                        for iframe in iframes:
                                            src = await iframe.get_attribute('src')
                                            if src and 'pdf' in src.lower():
                                                if not src.startswith('http'):
                                                    src = f"https://ieeexplore.ieee.org{src}"
                                                
                                                logger.info(f"Trying iframe: {src}")
                                                iframe_resp = await page.goto(src, timeout=30000)
                                                iframe_content = await iframe_resp.body()
                                                
                                                if iframe_content.startswith(b'%PDF'):
                                                    pdf_path = output_dir / "ieee_paper_IFRAME.pdf"
                                                    with open(pdf_path, 'wb') as f:
                                                        f.write(iframe_content)
                                                    
                                                    if pdf_path.exists():
                                                        file_size = pdf_path.stat().st_size
                                                        logger.info(f"🎉 PDF SAVED FROM IFRAME: {pdf_path}")
                                                        logger.info(f"📊 File size: {file_size} bytes")
                                                        return True
                                else:
                                    logger.info(f"Small response: {len(content)} bytes")
                                    
                            except Exception as e:
                                logger.error(f"PDF URL {i+1} failed: {e}")
                        
                        logger.error("❌ All PDF methods failed")
                    else:
                        logger.error("❌ No document ID found")
                else:
                    logger.error(f"❌ Auth failed, at: {page.url}")
            else:
                logger.error(f"❌ Not at ETH login: {page.url}")
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            logger.info("Keeping browser open for 30 seconds...")
            await asyncio.sleep(30)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(actually_download_pdf())
    if success:
        logger.info("🏆 ACTUALLY DOWNLOADED A PDF!")
    else:
        logger.error("💥 Failed to actually download PDF")
    exit(0 if success else 1)