#!/usr/bin/env python3
"""
IEEE Download Verification
==========================

Focused test to ensure PDF actually gets downloaded and saved.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("download_verify")

nest_asyncio.apply()

async def verify_pdf_download():
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
    
    output_dir = Path("download_verification")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Keep visible to see what's happening
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            logger.info("=== AUTHENTICATION PHASE ===")
            
            # Navigate to IEEE
            await page.goto(ieee_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Accept cookies
            accept = await page.query_selector('button:has-text("Accept All")')
            if accept:
                await accept.click()
                await page.wait_for_timeout(1000)
                logger.info("✅ Accepted cookies")
            
            # Click institutional sign in
            inst = await page.wait_for_selector('a:has-text("Institutional Sign In")', timeout=10000)
            await inst.click()
            await page.wait_for_timeout(3000)
            logger.info("✅ Clicked Institutional Sign In")
            
            # Click Access Through Your Institution
            access_btn = await page.wait_for_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn', timeout=10000)
            await access_btn.click()
            await page.wait_for_timeout(3000)
            logger.info("✅ Clicked Access Through Your Institution")
            
            # Search for ETH
            search_input = await page.wait_for_selector('input[aria-label="Search for your Institution"]', timeout=10000)
            await search_input.fill("ETH Zurich")
            await search_input.press('Enter')
            await page.wait_for_timeout(3000)
            logger.info("✅ Searched for ETH Zurich")
            
            # Click ETH result
            eth_link = await page.wait_for_selector('a[id*="ETH Zurich"]', timeout=10000)
            await eth_link.click()
            await page.wait_for_timeout(5000)
            logger.info("✅ Clicked ETH Zurich")
            
            # Fill ETH login
            if 'ethz' in page.url or 'aai' in page.url:
                logger.info("✅ At ETH login page")
                await page.fill('[name="j_username"], [id="username"]', username)
                await page.fill('[name="j_password"], [id="password"]', password)
                
                submit = await page.query_selector('[type="submit"]')
                await submit.click()
                await page.wait_for_timeout(8000)  # Wait longer for auth
                
                logger.info(f"Post-auth URL: {page.url}")
                
                if 'ieee' in page.url:
                    logger.info("✅ AUTHENTICATION SUCCESSFUL!")
                    
                    logger.info("=== PDF DOWNLOAD PHASE ===")
                    
                    # Extract document ID
                    doc_id = page.url.split('/document/')[1].split('/')[0] if '/document/' in page.url else None
                    if doc_id:
                        logger.info(f"📄 Document ID: {doc_id}")
                        
                        # Try multiple PDF URLs with extended patience
                        pdf_urls = [
                            f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}",
                            f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={doc_id}&ref=",
                            f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?arnumber={doc_id}",
                        ]
                        
                        for i, pdf_url in enumerate(pdf_urls):
                            logger.info(f"🎯 Trying PDF URL {i+1}: {pdf_url}")
                            
                            try:
                                # Go to PDF URL
                                response = await page.goto(pdf_url, wait_until='domcontentloaded', timeout=45000)
                                logger.info(f"Response status: {response.status}")
                                
                                # Wait for PDF to load/generate
                                await page.wait_for_timeout(8000)
                                
                                # Try to get content
                                content = await response.body()
                                logger.info(f"Content size: {len(content)} bytes")
                                
                                # Check if it's PDF
                                if content.startswith(b'%PDF'):
                                    pdf_path = output_dir / f"ieee_paper_method_{i+1}.pdf"
                                    with open(pdf_path, 'wb') as f:
                                        f.write(content)
                                    
                                    # Verify file was written
                                    if pdf_path.exists():
                                        file_size = pdf_path.stat().st_size
                                        logger.info(f"🎉 SUCCESS! PDF downloaded: {pdf_path}")
                                        logger.info(f"📊 File size: {file_size} bytes")
                                        
                                        # Verify it's a valid PDF
                                        with open(pdf_path, 'rb') as f:
                                            header = f.read(8)
                                            if header.startswith(b'%PDF'):
                                                logger.info("✅ Valid PDF file confirmed!")
                                                return True
                                            else:
                                                logger.warning("❌ File doesn't start with PDF header")
                                    else:
                                        logger.error("❌ File was not created")
                                        
                                elif len(content) < 1000:
                                    logger.info(f"Small response, likely loading page. Content preview: {content[:200]}")
                                    
                                    # Wait longer and try again
                                    logger.info("Waiting 10 more seconds for PDF generation...")
                                    await page.wait_for_timeout(10000)
                                    
                                    content = await page.content()
                                    # Look for iframe on this page
                                    iframes = await page.query_selector_all('iframe')
                                    logger.info(f"Found {len(iframes)} iframes on page")
                                    
                                    for j, iframe in enumerate(iframes):
                                        src = await iframe.get_attribute('src')
                                        logger.info(f"  Iframe {j}: {src}")
                                        if src and ('pdf' in src.lower() or 'getPDF' in src):
                                            if not src.startswith('http'):
                                                src = f"https://ieeexplore.ieee.org{src}"
                                            
                                            logger.info(f"🎯 Trying iframe PDF: {src}")
                                            iframe_response = await page.goto(src, wait_until='domcontentloaded', timeout=30000)
                                            iframe_content = await iframe_response.body()
                                            
                                            if iframe_content.startswith(b'%PDF'):
                                                pdf_path = output_dir / f"ieee_paper_iframe_{j}.pdf"
                                                with open(pdf_path, 'wb') as f:
                                                    f.write(iframe_content)
                                                
                                                if pdf_path.exists():
                                                    file_size = pdf_path.stat().st_size
                                                    logger.info(f"🎉 SUCCESS! PDF downloaded from iframe: {pdf_path}")
                                                    logger.info(f"📊 File size: {file_size} bytes")
                                                    return True
                                else:
                                    logger.info("Got HTML response, content preview:")
                                    logger.info(content[:500].decode('utf-8', errors='ignore'))
                                    
                            except Exception as e:
                                logger.warning(f"PDF URL {i+1} failed: {e}")
                                continue
                        
                        logger.error("❌ All PDF download methods failed")
                    else:
                        logger.error("❌ Could not extract document ID")
                else:
                    logger.error(f"❌ Authentication failed, current URL: {page.url}")
            else:
                logger.error(f"❌ Not at ETH login page: {page.url}")
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            logger.info("Browser will stay open for 20 seconds for inspection...")
            await asyncio.sleep(20)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(verify_pdf_download())
    if success:
        logger.info("🏆 PDF DOWNLOAD VERIFICATION SUCCESSFUL!")
    else:
        logger.error("💥 PDF download verification failed")
    exit(0 if success else 1)