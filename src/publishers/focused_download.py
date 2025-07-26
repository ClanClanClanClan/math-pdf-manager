#!/usr/bin/env python3
"""
Focused Download
===============

Quick focused attempt to actually download a PDF.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("focused")

nest_asyncio.apply()

async def focused_download():
    from playwright.async_api import async_playwright
    
    # Get credentials
    from src.secure_credential_manager import get_credential_manager
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    output_dir = Path("focused_download")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Use the working DOI URL
            logger.info("Going to DOI (working URL)...")
            await page.goto("https://doi.org/10.1109/JPROC.2018.2820126", wait_until='domcontentloaded', timeout=45000)
            await page.wait_for_timeout(3000)
            
            logger.info("✅ Connected to IEEE page")
            
            # Quick auth
            logger.info("Starting quick auth...")
            
            # Accept cookies if present
            try:
                accept = await page.wait_for_selector('button:has-text("Accept All")', timeout=3000)
                await accept.click()
                await page.wait_for_timeout(1000)
            except Exception:
                pass
            
            # Institutional sign in
            inst = await page.wait_for_selector('a:has-text("Institutional Sign In")', timeout=10000)
            await inst.click()
            await page.wait_for_timeout(3000)
            
            # Access button
            access_btn = await page.wait_for_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn', timeout=10000)
            await access_btn.click()
            await page.wait_for_timeout(3000)
            
            # Search ETH
            search_input = await page.wait_for_selector('input[aria-label="Search for your Institution"]', timeout=10000)
            await search_input.fill("ETH Zurich")
            await search_input.press('Enter')
            await page.wait_for_timeout(3000)
            
            # Click ETH
            eth_link = await page.wait_for_selector('a[id*="ETH Zurich"]', timeout=10000)
            await eth_link.click()
            await page.wait_for_timeout(5000)
            
            logger.info("✅ Auth flow completed, checking login...")
            
            # ETH login
            if 'ethz' in page.url or 'aai' in page.url:
                logger.info("At ETH login page")
                
                await page.fill('[name="j_username"], [id="username"]', username)
                await page.fill('[name="j_password"], [id="password"]', password)
                
                submit = await page.query_selector('[type="submit"]')
                await submit.click()
                
                logger.info("Submitted login, waiting for redirect...")
                await page.wait_for_timeout(8000)
                
                current_url = page.url
                logger.info(f"Current URL: {current_url}")
                
                if 'ieee' in current_url:
                    logger.info("🎉 AUTHENTICATION SUCCESSFUL!")
                    
                    # Extract doc ID
                    doc_id = current_url.split('/document/')[1].split('/')[0] if '/document/' in current_url else None
                    
                    if doc_id:
                        logger.info(f"Document ID: {doc_id}")
                        
                        # Direct PDF attempts
                        pdf_url = f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={doc_id}&ref="
                        logger.info(f"🎯 Trying direct PDF: {pdf_url}")
                        
                        try:
                            # Go directly to PDF
                            pdf_response = await page.goto(pdf_url, wait_until='load', timeout=30000)
                            logger.info(f"PDF response: {pdf_response.status}")
                            
                            # Wait a bit for PDF generation
                            await page.wait_for_timeout(5000)
                            
                            # Get content
                            content = await pdf_response.body()
                            logger.info(f"Content size: {len(content)} bytes")
                            
                            if content.startswith(b'%PDF'):
                                # SAVE THE PDF!
                                pdf_path = output_dir / "ACTUAL_IEEE_PAPER.pdf"
                                with open(pdf_path, 'wb') as f:
                                    f.write(content)
                                
                                # VERIFY IT EXISTS
                                if pdf_path.exists():
                                    file_size = pdf_path.stat().st_size
                                    logger.info(f"🏆 PDF SAVED: {pdf_path}")
                                    logger.info(f"📊 Size: {file_size} bytes")
                                    
                                    # VERIFY IT'S ACTUALLY A PDF
                                    with open(pdf_path, 'rb') as f:
                                        header = f.read(8)
                                        if header.startswith(b'%PDF'):
                                            logger.info("✅ VERIFIED: ACTUAL PDF FILE!")
                                            logger.info("🎉 DOWNLOAD COMPLETE AND VERIFIED!")
                                            return True
                                        else:
                                            logger.error("File doesn't have PDF header")
                                else:
                                    logger.error("File was not saved")
                            else:
                                logger.info(f"Not PDF content. First 100 chars: {content[:100]}")
                                
                                # Try stamp URL as backup
                                stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                                logger.info(f"Trying stamp URL: {stamp_url}")
                                
                                await page.goto(stamp_url, wait_until='load', timeout=30000)
                                await page.wait_for_timeout(5000)
                                
                                # Look for iframe
                                iframes = await page.query_selector_all('iframe')
                                logger.info(f"Found {len(iframes)} iframes")
                                
                                for i, iframe in enumerate(iframes):
                                    src = await iframe.get_attribute('src')
                                    if src and 'pdf' in src.lower():
                                        if not src.startswith('http'):
                                            src = f"https://ieeexplore.ieee.org{src}"
                                        
                                        logger.info(f"Trying iframe {i}: {src}")
                                        iframe_resp = await page.goto(src, timeout=30000)
                                        iframe_content = await iframe_resp.body()
                                        
                                        if iframe_content.startswith(b'%PDF'):
                                            pdf_path = output_dir / f"IFRAME_PDF_{i}.pdf"
                                            with open(pdf_path, 'wb') as f:
                                                f.write(iframe_content)
                                            
                                            if pdf_path.exists():
                                                logger.info(f"🏆 PDF SAVED FROM IFRAME: {pdf_path}")
                                                return True
                                        
                        except Exception as e:
                            logger.error(f"PDF download error: {e}")
                    
                else:
                    logger.error(f"Auth failed, at: {current_url}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            logger.info("Browser open for 15 seconds...")
            await asyncio.sleep(15)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(focused_download())
    if success:
        logger.info("🏆 ACTUALLY DOWNLOADED A PDF!")
    else:
        logger.error("💥 Download failed")